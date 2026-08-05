from __future__ import annotations

import re
from typing import Any

from agent.config import settings
from agent.knowledge import extract_interests, format_bridge_brief
from agent.llm import build_system_prompt, chat_with_llm
from agent.storage import MemoryStore
from agent.study_path import (
    advance_study_path,
    format_study_path,
    is_continue_intent,
    is_plan_intent,
    plan_study_path,
)


def local_answer(
    store: MemoryStore,
    query: str,
    focus_bridge: str | None,
) -> dict[str, Any]:
    q = query.strip()
    if not q:
        return {
            "text": "请输入问题，例如：介绍赵州桥、宋代有哪些拱桥、对比赵州桥和卢沟桥。",
            "sources": [],
            "mode": "retrieval",
        }

    # 问句中含桥名时优先精确匹配（如「介绍赵州桥」）
    for b in store.list_bridges():
        name = b.get("name") or ""
        if name and name in q:
            full = store.get_bridge_by_name(name) or b
            return {
                "text": format_bridge_brief(full, full.get("_culture")),
                "sources": [name],
                "mode": "retrieval",
            }

    if focus_bridge and (re.match(r"^(介绍|讲解|说说|谈谈)", q) or len(q) <= 8):
        b = store.get_bridge_by_name(focus_bridge)
        if b:
            return {
                "text": format_bridge_brief(b, b.get("_culture")),
                "sources": [b["name"]],
                "mode": "retrieval",
            }

    compare = re.search(r"(.+?)(和|与|、)(.+?)(对比|比较|区别|异同)", q) or re.search(
        r"对比(.+?)(和|与)(.+)", q
    )
    if compare:
        n1 = compare.group(1).strip()
        n2 = (compare.group(3) if compare.lastindex >= 3 else compare.group(2)).strip()
        hits = []
        for name in (n1, n2):
            b = store.get_bridge_by_name(name) or (
                store.search_bridges(name, 1)[0] if store.search_bridges(name, 1) else None
            )
            if b:
                hits.append(b)
        if len(hits) >= 2:
            text = "—— 对比概览 ——\n\n"
            text += format_bridge_brief(hits[0], hits[0].get("_culture"))
            text += "\n\n---\n\n"
            text += format_bridge_brief(hits[1], hits[1].get("_culture"))
            return {
                "text": text,
                "sources": [hits[0]["name"], hits[1]["name"]],
                "mode": "retrieval",
            }

    dynasty = re.search(r"(夏|商|周|汉|晋|隋|唐|宋|南宋|金|元|明|清|秦)", q)
    btype = re.search(r"(拱桥|梁桥|索桥|浮桥)", q)
    if re.search(r"有哪些|列举|列出|都有什么", q) and (dynasty or btype):
        bridges = store.list_bridges()
        if dynasty:
            bridges = [b for b in bridges if b.get("dynasty") == dynasty.group(1)]
        if btype:
            bridges = [b for b in bridges if b.get("type") == btype.group(1)]
        if bridges:
            lines = [
                f"· {b['name']}（{b.get('dynasty', '')}，{b.get('type', '')}）"
                for b in bridges[:20]
            ]
            return {
                "text": f"符合条件的桥梁共 {len(bridges)} 座：\n" + "\n".join(lines),
                "sources": [b["name"] for b in bridges[:5]],
                "mode": "retrieval",
            }

    hits = store.search_bridges(q, 3)
    if len(hits) == 1:
        b = hits[0]
        return {
            "text": format_bridge_brief(b, b.get("_culture")),
            "sources": [b["name"]],
            "mode": "retrieval",
        }
    if len(hits) > 1:
        lines = [
            f"{i + 1}. {b['name']} — "
            + " · ".join(filter(None, [b.get("dynasty"), b.get("type"), b.get("province")]))
            for i, b in enumerate(hits)
        ]
        return {
            "text": "为您找到多座相关古桥，请指定桥名：\n" + "\n".join(lines),
            "sources": [b["name"] for b in hits],
            "mode": "retrieval",
        }

    if re.search(r"推荐|最值得|著名|名桥", q):
        top = sorted(store.list_bridges(), key=lambda b: b.get("span") or 0, reverse=True)[:5]
        text = "按跨度与文献知名度，推荐了解：\n" + "\n".join(
            f"· {b['name']}（{b.get('dynasty', '')}，跨度 {b.get('span', '—')}m）"
            for b in top
        )
        return {"text": text, "sources": [b["name"] for b in top], "mode": "retrieval"}

    return {
        "text": "暂未匹配到明确结果。可尝试直接输入桥名，或问「宋代有哪些拱桥」。",
        "sources": [],
        "mode": "retrieval",
    }


def _exploration_prefix(store: MemoryStore, session_id: str) -> str | None:
    events = store.get_events(session_id)
    if not events:
        return None
    last = events[-1]
    bridge = last.get("bridge")
    source = last.get("source")
    if not bridge:
        return None
    source_label = {
        "knowledge_graph": "知识图谱",
        "bridge_detail": "桥梁档案",
        "museum_map": "地图大屏",
        "word_cloud": "文化热词",
    }.get(source, source or "图鉴")
    return f"您刚从【{source_label}】关注了「{bridge}」"


def _finish_turn(
    store: MemoryStore,
    session_id: str,
    message: str,
    text: str,
    sources: list[str],
    mode: str,
    active_focus: str | None,
    memory: dict[str, Any] | None,
) -> dict[str, Any]:
    interests = extract_interests(message, sources)
    prev = memory.get("interests") if memory else []
    merged = list(dict.fromkeys((prev or []) + interests))[:12]
    summary = f"用户曾询问：{message[:80]}"
    if merged:
        summary += "；兴趣标签：" + "、".join(merged[:6])
    store.upsert_user_memory(session_id, summary, merged)
    assistant_msg = store.add_message(
        session_id,
        "assistant",
        text,
        sources=sources[:5],
        mode=mode,
    )
    return {
        "text": text,
        "sources": sources[:5],
        "mode": mode,
        "message_id": assistant_msg.get("id"),
        "session_id": session_id,
        "focus_bridge": active_focus,
    }


def run_chat(
    store: MemoryStore,
    session_id: str,
    message: str,
    focus_bridge: str | None = None,
) -> dict[str, Any]:
    session = store.get_session(session_id)
    if not session:
        raise KeyError("session_not_found")

    if focus_bridge is not None:
        store.update_session_focus(session_id, focus_bridge or None)

    active_focus = focus_bridge if focus_bridge is not None else session.get("focus_bridge")
    memory = store.get_user_memory(session_id)
    explore_prefix = _exploration_prefix(store, session_id)

    if is_continue_intent(message):
        path = store.get_study_path(session_id)
        if path:
            store.add_message(session_id, "user", message)
            path = advance_study_path(path)
            store.save_study_path(session_id, path)
            text = format_study_path(path, store)
            step = int(path.get("current_step") or 0)
            stops = path.get("stops") or []
            sources: list[str] = []
            if step < len(stops):
                name = stops[step]
                active_focus = name
                store.update_session_focus(session_id, name)
                b = store.get_bridge_by_name(name)
                if b:
                    sources = [name]
                    text += "\n\n—— 本站讲解 ——\n\n" + format_bridge_brief(b, b.get("_culture"))
            return _finish_turn(
                store, session_id, message, text, sources, "study_path", active_focus, memory
            )

    if is_plan_intent(message):
        path = plan_study_path(store, message)
        if path:
            store.add_message(session_id, "user", message)
            store.save_study_path(session_id, path)
            text = format_study_path(path, store)
            stops = path.get("stops") or []
            sources = [stops[0]] if stops else []
            if stops:
                store.update_session_focus(session_id, stops[0])
                active_focus = stops[0]
            return _finish_turn(
                store, session_id, message, text, sources, "study_path", active_focus, memory
            )

    if re.search(r"集群|备份|ccloud|数据库状态", message):
        from agent.tools.ccloud_tool import cluster_health_summary

        store.add_message(session_id, "user", message)
        result = cluster_health_summary()
        store.log_tool_call(session_id, "ccloud_cluster_list", {}, result)
        if result.get("ok"):
            count = result.get("cluster_count", 0)
            text = f"已通过 ccloud CLI 查询 CockroachDB Cloud 集群：共 {count} 个集群。"
            if count:
                text += "\n\n（详细 JSON 见 tool_calls 审计表 / MCP 调试）"
        else:
            text = (
                "ccloud CLI 暂不可用（" + str(result.get("error")) + "）。\n"
                "Hackathon 演示：请在开发机安装 ccloud 并 auth login，或使用 CockroachDB Cloud Console。"
            )
        return _finish_turn(
            store, session_id, message, text, [], "ccloud", active_focus, memory
        )

    store.add_message(session_id, "user", message)

    history = store.get_messages(session_id)
    memory_line = None
    if memory:
        interests = "、".join(memory.get("interests") or [])
        memory_line = memory.get("summary", "")
        if interests:
            memory_line += f"（兴趣：{interests}）"
    if explore_prefix:
        memory_line = (explore_prefix + "。" + (memory_line or "")).strip("。")

    hits = store.search_bridges(message, 5)
    if active_focus:
        fb = store.get_bridge_by_name(active_focus)
        if fb and fb not in hits:
            hits = [fb] + hits

    context_parts = []
    sources: list[str] = []
    for b in hits[:4]:
        culture = b.get("_culture")
        context_parts.append(format_bridge_brief(b, culture))
        if b.get("name"):
            sources.append(b["name"])

    store.log_tool_call(
        session_id,
        "search_bridges",
        {"query": message, "focus": active_focus},
        {"count": len(hits), "sources": sources[:4]},
    )

    mode = "retrieval"
    use_llm = settings.llm_mode in ("openai", "bedrock")
    try:
        if use_llm and hits:
            focus_obj = store.get_bridge_by_name(active_focus) if active_focus else None
            system = build_system_prompt(
                "\n\n---\n\n".join(context_parts),
                memory_line,
                focus_obj,
            )
            hist = [{"role": m["role"], "content": m["content"]} for m in history[:-1]]
            text, mode = chat_with_llm(system, hist, message)
        else:
            raise RuntimeError("retrieval_only")
    except Exception:
        result = local_answer(store, message, active_focus)
        text = result["text"]
        sources = result.get("sources") or sources
        mode = result["mode"]
        if memory_line and mode == "retrieval":
            text = f"（{memory_line}）\n\n{text}"
        elif explore_prefix and mode == "retrieval" and not memory_line:
            text = f"（{explore_prefix}）\n\n{text}"

    return _finish_turn(
        store, session_id, message, text, sources, mode, active_focus, memory
    )
