from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.config import settings
from agent.dossier import build_dossier
from agent.orchestrator import run_chat
from agent.storage import get_store
from agent.tools.ccloud_tool import cluster_health_summary

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

app = FastAPI(
    title="qianhong-agent",
    description="千古飞虹 · 飞虹智忆 — Agent 记忆层 API",
    version="0.1.0",
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
    return {
        "ok": True,
        "storage_mode": settings.storage_mode,
        "llm_mode": settings.llm_mode,
        "bridge_data": str(settings.bridge_data_dir),
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
    return {
        "session": session,
        "memory": memory,
        "messages": messages,
    }


@app.get("/api/cluster/status")
def cluster_status() -> dict:
    """ccloud CLI tool — Agent 可调用的集群健康检查（Hackathon: ccloud CLI）。"""
    result = cluster_health_summary()
    store = get_store()
    store.log_tool_call(None, "ccloud_cluster_list", {}, result)
    return result


@app.get("/api/hackathon/checklist")
def hackathon_checklist() -> dict:
    """提交自检：当前环境满足哪些 Hackathon 要求。"""
    import shutil

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
            },
            "ccloud_cli": {
                "module": "agent/tools/ccloud_tool.py",
                "api": "/api/cluster/status",
                "installed": shutil.which("ccloud") is not None,
            },
            "agent_skills": {
                "repo": "https://github.com/cockroachlabs/cockroachdb-skills",
                "docs": "docs/SKILLS.md",
            },
        },
        "aws_services": {
            "bedrock": settings.llm_mode == "bedrock",
            "lambda": "infra/template.yaml (SAM deploy)",
            "s3": "infra/template.yaml AgentReportsBucket",
            "api_gateway": "infra/template.yaml HttpApi",
        },
        "storage_mode": settings.storage_mode,
        "llm_mode": settings.llm_mode,
    }


@app.post("/api/events")
def record_event(body: EventRequest) -> dict:
    session_id = body.session_id
    if not session_id:
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
    }


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    session_id = body.session_id
    if not session_id:
        session_id = store.create_session(body.focus_bridge)["id"]
    try:
        result = run_chat(store, session_id, body.message.strip(), body.focus_bridge)
    except KeyError:
        raise HTTPException(404, "session not found") from None
    return result


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


if WEB.exists():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")


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
