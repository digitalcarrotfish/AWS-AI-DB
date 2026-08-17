from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.config import settings
from agent.dossier import build_dossier
from agent.orchestrator import run_chat
from agent.storage import get_store
from agent.tools.ccloud_tool import cluster_health_summary

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
# 博物馆根目录页面由显式路由托管；媒体目录见下方 mount
MUSEUM_ASSETS = ROOT / "assets"
MUSEUM_DATA = ROOT / "data"
MUSEUM_BRIDGE_MEDIA = ROOT / "桥"
app = FastAPI(
    title="qianhong-agent",
    description="千古飞虹 · 飞虹智忆 — Agent 记忆层 API + 博物馆同域托管",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = get_store()


class SessionCreate(BaseModel):
    focus_bridge: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    focus_bridge: str | None = None


class EventRequest(BaseModel):
    session_id: str | None = None
    event_type: str = Field(min_length=1, max_length=64)
    source: str = Field(min_length=1, max_length=64)
    bridge: str | None = None
    meta: dict | None = None


@app.get("/api/health")
def health() -> dict:
    from agent import aws_s3

    return {
        "ok": True,
        "storage_mode": settings.storage_mode,
        "llm_mode": settings.llm_mode,
        "llm_configured": bool(
            (settings.llm_mode == "openai" and settings.openai_api_key)
            or settings.llm_mode == "bedrock"
        ),
        "llm_model": (
            settings.openai_model
            if settings.llm_mode == "openai"
            else settings.bedrock_model_id
            if settings.llm_mode == "bedrock"
            else None
        ),
        "bridge_data": str(settings.bridge_data_dir),
        "museum": "same-origin",
        "agent_ui": "/agent/",
        "identify": "/api/identify",
        "aws": {
            "region": settings.aws_region,
            "bedrock": settings.llm_mode == "bedrock",
            "s3": aws_s3.s3_enabled(),
            "s3_bucket": settings.s3_bucket or None,
        },
    }


@app.get("/api/aws/status")
def aws_status() -> dict:
    """Hackathon：检查 Amazon S3 / Bedrock 是否可用。"""
    from agent import aws_s3

    bedrock = {"enabled": settings.llm_mode == "bedrock", "model": settings.bedrock_model_id}
    if settings.llm_mode == "bedrock":
        try:
            import boto3

            kwargs = {"region_name": settings.aws_region}
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                kwargs["aws_access_key_id"] = settings.aws_access_key_id
                kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
            client = boto3.client("bedrock-runtime", **kwargs)
            # 轻量探测：能创建 client 即凭证链可用；真正 Invoke 需模型权限
            bedrock["credentials"] = True
            bedrock["region"] = settings.aws_region
            _ = client.meta.region_name
        except Exception as exc:
            bedrock["credentials"] = False
            bedrock["error"] = str(exc)
    s3 = aws_s3.status()
    return {
        "ok": s3.get("ok") or bedrock.get("enabled") is True,
        "region": settings.aws_region,
        "s3": s3,
        "bedrock": bedrock,
        "docs": "docs/AWS.md",
    }


@app.get("/api/bridges")
def list_bridges() -> dict:
    bridges = store.list_bridges()
    return {
        "count": len(bridges),
        "items": [
            {
                "name": b.get("name"),
                "dynasty": b.get("dynasty"),
                "type": b.get("type"),
                "province": b.get("province"),
                "span": b.get("span"),
            }
            for b in bridges
        ],
    }


@app.post("/api/sessions")
def create_session(body: SessionCreate) -> dict:
    return store.create_session(body.focus_bridge)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    memory = store.get_user_memory(session_id)
    messages = store.get_messages(session_id)
    events = store.get_events(session_id)
    return {
        "session": session,
        "memory": memory,
        "messages": messages,
        "events": events[-30:],
    }


@app.get("/api/cluster/status")
def cluster_status() -> dict:
    """ccloud CLI tool — Agent 可调用的集群健康检查（Hackathon: ccloud CLI）。"""
    result = cluster_health_summary()
    store.log_tool_call(None, "ccloud_cluster_list", {}, result)
    return result


@app.get("/api/memory/ops")
def memory_ops() -> dict:
    """记忆运维驾驶舱：CRDB 状态、向量索引、行为规模与工具审计。"""
    from agent.tools.ccloud_tool import _ccloud_available

    try:
        memory = store.memory_ops_snapshot()
    except Exception as exc:
        raise HTTPException(503, f"memory snapshot failed: {exc}") from exc

    counts = memory.get("counts") or {}
    vector_active = bool((memory.get("vector_index") or {}).get("active"))
    cockroach_active = memory.get("backend") == "cockroach"
    score = 0
    score += 35 if cockroach_active else 10
    score += 25 if vector_active else 0
    score += 20 if counts.get("bridges", 0) else 0
    score += 10 if counts.get("events", 0) else 0
    score += 10 if counts.get("tool_calls", 0) else 0

    insights = []
    if cockroach_active:
        insights.append("持久记忆已由 CockroachDB 承载")
    else:
        insights.append("当前为 JSON 回退模式，生产演示应切换 CockroachDB")
    if vector_active:
        insights.append("分布式向量索引在线，语义检索与事务记忆同库")
    else:
        insights.append("向量索引未检测到，请执行 db/schema.sql")
    if counts.get("events", 0):
        insights.append(f"已沉淀 {counts['events']} 条探索行为，可驱动个性化推荐")
    else:
        insights.append("尚无探索行为，请先从博物馆打开一座桥")

    ccloud = (
        cluster_health_summary()
        if _ccloud_available()
        else {
            "ok": False,
            "error": "ccloud_not_installed",
            "hint": "见 docs/CCLOUD.md；本地记忆统计不受影响",
        }
    )
    return {
        "ok": True,
        "status": "healthy" if score >= 70 else "attention",
        "health_score": score,
        "memory": memory,
        "ccloud": ccloud,
        "insights": insights,
        "next_action": (
            "连接 CockroachDB Cloud MCP / ccloud，形成云端运维闭环"
            if not ccloud.get("ok")
            else "云集群已连接，可在 Agent 中查询集群状态"
        ),
    }


@app.get("/api/hackathon/checklist")
def hackathon_checklist() -> dict:
    """提交自检：当前环境满足哪些 Hackathon 要求。"""
    from pathlib import Path

    from agent import aws_s3
    from agent.tools.ccloud_tool import _ccloud_available, _ccloud_bin

    root = Path(__file__).resolve().parents[1]
    mcp_cfg = root / ".cursor" / "mcp.json"
    home_mcp = Path.home() / ".cursor" / "mcp.json"
    mcp_configured = False
    for p in (mcp_cfg, home_mcp):
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="ignore")
            if "cockroachlabs.cloud/mcp" in text or "cockroachdb" in text.lower():
                mcp_configured = True
                break
    skills_dir = Path.home() / ".cursor" / "skills"
    skills_alt = root / ".agents" / "skills"
    skills_installed = any(
        d.is_dir() and any(d.iterdir())
        for d in (skills_dir, skills_alt, root / "skills")
        if d.exists()
    )

    s3_st = aws_s3.status()
    ccloud_ok = _ccloud_available()
    return {
        "project": "飞虹智忆 qianhong-agent",
        "devpost": "https://cockroachdb-ai.devpost.com/",
        "cockroachdb_tools": {
            "vector_indexing": {
                "schema": "db/schema.sql bridge_embeddings + CREATE VECTOR INDEX",
                "import": "scripts/import_bridge_data.py",
                "active": settings.storage_mode == "cockroach",
            },
            "mcp_server": {
                "endpoint": "https://cockroachlabs.cloud/mcp",
                "docs": "docs/MCP.md",
                "cursor_configured": mcp_configured,
            },
            "ccloud_cli": {
                "module": "agent/tools/ccloud_tool.py",
                "api": "/api/cluster/status",
                "installed": ccloud_ok,
                "binary": _ccloud_bin(),
                "docs": "docs/CCLOUD.md",
            },
            "agent_skills": {
                "repo": "https://github.com/cockroachlabs/cockroachdb-skills",
                "docs": "docs/SKILLS.md",
                "installed": skills_installed,
            },
        },
        "requirement_crdb_tools_hint": "需 ≥2：vector 已亮；再开 MCP 或 ccloud（Cloud 账号）",
        "aws_services": {
            "bedrock": {
                "active": settings.llm_mode == "bedrock",
                "model": settings.bedrock_model_id,
                "docs": "docs/AWS.md",
            },
            "s3": {
                "active": bool(s3_st.get("ok")),
                "configured": aws_s3.s3_enabled(),
                "bucket": settings.s3_bucket or None,
                "usage": "扫桥存证 + 研学报告导出 POST /api/reports/export",
                "docs": "docs/AWS.md",
            },
            "lambda": "infra/template.yaml (SAM deploy)",
            "api_gateway": "infra/template.yaml HttpApi",
        },
        "requirement_aws_met": bool(s3_st.get("ok")) or settings.llm_mode == "bedrock",
        "storage_mode": settings.storage_mode,
        "llm_mode": settings.llm_mode,
        "llm_configured": bool(
            (settings.llm_mode == "openai" and settings.openai_api_key)
            or settings.llm_mode == "bedrock"
        ),
        "same_origin_museum": True,
    }


@app.post("/api/events")
def record_event(body: EventRequest) -> dict:
    session_id = body.session_id
    if not session_id:
        session_id = store.create_session(body.bridge)["id"]
    elif not store.get_session(session_id):
        # 过期 / 清库后的陈旧 session：重建并继续写事件
        session_id = store.create_session(body.bridge)["id"]
    try:
        ev = store.record_event(
            session_id,
            body.event_type,
            body.source,
            bridge=body.bridge,
            meta=body.meta,
        )
    except KeyError:
        raise HTTPException(404, "session not found") from None
    return {"ok": True, "session_id": session_id, "event": ev}


@app.get("/api/dossier/{session_id}")
def get_dossier(session_id: str) -> dict:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    events = store.get_events(session_id)
    messages = store.get_messages(session_id)
    memory = store.get_user_memory(session_id)
    dossier = build_dossier(events, messages, memory)
    dossier["total_bridges"] = len(store.list_bridges())
    study_path = store.get_study_path(session_id)
    return {
        "session": session,
        "dossier": dossier,
        "study_path": study_path,
        "events": events[-20:],
    }


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    session_id = body.session_id
    if not session_id:
        session_id = store.create_session(body.focus_bridge)["id"]
    elif not store.get_session(session_id):
        session_id = store.create_session(body.focus_bridge)["id"]
    try:
        result = run_chat(store, session_id, body.message.strip(), body.focus_bridge)
    except KeyError:
        raise HTTPException(404, "session not found") from None
    result["session_id"] = session_id
    return result


@app.post("/api/chat/stream")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    """SSE 白盒对话：流式返回可审计步骤，最终事件携带完整回答。"""
    session_id = body.session_id
    if not session_id or not store.get_session(session_id):
        session_id = store.create_session(body.focus_bridge)["id"]

    event_queue: queue.Queue[dict | None] = queue.Queue()
    started = time.monotonic()
    sequence = 0

    def send(event_name: str, payload: dict) -> None:
        nonlocal sequence
        sequence += 1
        event_queue.put(
            {
                "id": sequence,
                "event": event_name,
                "data": {
                    **payload,
                    "seq": sequence,
                    "elapsed_ms": round((time.monotonic() - started) * 1000),
                },
            }
        )

    def trace(payload: dict) -> None:
        send("trace", payload)

    def work() -> None:
        send(
            "start",
            {
                "session_id": session_id,
                "title": "白盒执行开始",
                "detail": "以下为可审计工具轨迹，不包含模型私有思维链",
            },
        )
        try:
            result = run_chat(
                store,
                session_id,
                body.message.strip(),
                body.focus_bridge,
                trace=trace,
            )
            result["session_id"] = session_id
            send("final", result)
        except KeyError:
            send("error", {"code": "session_not_found", "message": "session not found"})
        except Exception as exc:
            send(
                "error",
                {
                    "code": "chat_failed",
                    "message": str(exc),
                },
            )
        finally:
            event_queue.put(None)

    threading.Thread(target=work, daemon=True, name=f"chat-sse-{session_id[:8]}").start()

    async def event_stream():
        while True:
            item = await asyncio.to_thread(event_queue.get)
            if item is None:
                break
            data = json.dumps(item["data"], ensure_ascii=False, default=str)
            yield f"id: {item['id']}\nevent: {item['event']}\ndata: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/identify/status")
def identify_status() -> dict:
    from agent.vision_match import gallery_stats

    stats = gallery_stats()
    return {"ok": True, "ready": stats["images"] > 0, **stats}


@app.post("/api/identify")
async def identify_bridge(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
) -> dict:
    """扫桥识别：上传照片 / 截图，与图鉴外观图做感知哈希匹配。"""
    from agent import aws_s3
    from agent.vision_match import identify_image

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "empty image")
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(400, "image too large (max 12MB)")
    try:
        matches = identify_image(raw, top_k=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    top = matches[0] if matches else None
    sid = session_id
    s3_obj = None
    if top and top.get("matched"):
        if not sid or not store.get_session(sid):
            sid = store.create_session(top["name"])["id"]
        try:
            s3_obj = aws_s3.upload_scan_image(
                session_id=sid,
                bridge_name=top.get("name"),
                filename=file.filename,
                raw=raw,
            )
        except Exception as exc:
            s3_obj = {"ok": False, "error": str(exc)}
        meta = {
            "score": top.get("score"),
            "distance": top.get("distance"),
            "filename": file.filename,
        }
        if s3_obj and s3_obj.get("uri"):
            meta["s3_uri"] = s3_obj["uri"]
        store.record_event(
            sid,
            "scan_identify",
            "camera_scan",
            bridge=top["name"],
            meta=meta,
        )
        store.update_session_focus(sid, top["name"])
        store.log_tool_call(
            sid,
            "vision_identify",
            {"filename": file.filename, "bytes": len(raw)},
            {"top": top, "candidates": matches[:3], "s3": s3_obj},
        )

    brief = None
    if top and top.get("name"):
        b = store.get_bridge_by_name(top["name"])
        if b:
            brief = {
                "name": b.get("name"),
                "dynasty": b.get("dynasty"),
                "type": b.get("type"),
                "province": b.get("province"),
                "span": b.get("span"),
            }

    return {
        "ok": True,
        "session_id": sid,
        "matched": bool(top and top.get("matched")),
        "top": top,
        "candidates": matches,
        "bridge": brief,
        "s3": s3_obj,
    }


class ReportExportRequest(BaseModel):
    session_id: str = Field(min_length=1)


@app.post("/api/reports/export")
def export_report(body: ReportExportRequest) -> dict:
    """将个人档案 + 研学路线导出到 Amazon S3（Hackathon AWS）。"""
    from agent import aws_s3

    if not aws_s3.s3_enabled():
        raise HTTPException(400, "S3_BUCKET 未配置，见 docs/AWS.md")
    session = store.get_session(body.session_id)
    if not session:
        raise HTTPException(404, "session not found")
    events = store.get_events(body.session_id)
    messages = store.get_messages(body.session_id)
    memory = store.get_user_memory(body.session_id)
    dossier = build_dossier(events, messages, memory)
    dossier["total_bridges"] = len(store.list_bridges())
    study_path = store.get_study_path(body.session_id)
    try:
        result = aws_s3.export_study_report(
            session_id=body.session_id,
            dossier=dossier,
            study_path=study_path,
            events=events,
        )
    except Exception as exc:
        raise HTTPException(502, f"S3 export failed: {exc}") from exc
    store.log_tool_call(body.session_id, "s3_export_report", {"session_id": body.session_id}, result)
    return {"ok": True, **result}


# —— Agent Chat UI（/agent）——
@app.get("/agent")
@app.get("/agent/")
def agent_home() -> FileResponse:
    return FileResponse(WEB / "index.html")


# —— 博物馆页面（与 Agent 同域，共享 localStorage）——
@app.get("/")
def museum_home() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


def _file_or_404(path: Path) -> FileResponse:
    if not path.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(path)


@app.get("/museum.html")
def page_museum() -> FileResponse:
    return _file_or_404(ROOT / "museum.html")


@app.get("/knowledge.html")
def page_knowledge() -> FileResponse:
    return _file_or_404(ROOT / "knowledge.html")


@app.get("/bridge-detail.html")
def page_detail() -> FileResponse:
    return _file_or_404(ROOT / "bridge-detail.html")


@app.get("/bridge-3d.html")
def page_3d() -> FileResponse:
    return _file_or_404(ROOT / "bridge-3d.html")


@app.get("/closing.html")
def page_closing() -> FileResponse:
    return _file_or_404(ROOT / "closing.html")


@app.get("/config.js")
def page_config() -> FileResponse:
    return _file_or_404(ROOT / "config.js")


@app.get("/config.example.js")
def page_config_example() -> FileResponse:
    return _file_or_404(ROOT / "config.example.js")


@app.get("/{glb_name}.glb")
def page_glb(glb_name: str) -> FileResponse:
    path = ROOT / f"{glb_name}.glb"
    return _file_or_404(path)


# 静态资源挂载（放在路由定义之后；注意不要盖住 /api）
if (WEB / "assets").exists():
    app.mount("/agent/assets", StaticFiles(directory=WEB / "assets"), name="agent_assets")
if MUSEUM_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=MUSEUM_ASSETS), name="museum_assets")
if MUSEUM_DATA.exists():
    app.mount("/data", StaticFiles(directory=MUSEUM_DATA), name="museum_data")
if MUSEUM_BRIDGE_MEDIA.exists():
    app.mount("/桥", StaticFiles(directory=MUSEUM_BRIDGE_MEDIA), name="bridge_media")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
