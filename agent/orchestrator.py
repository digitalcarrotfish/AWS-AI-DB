from __future__ import annotations

import re
from typing import Any, Callable

from agent.config import settings
from agent.knowledge import extract_interests, format_bridge_brief
from agent.llm import build_system_prompt, chat_with_llm
from agent.memory_actions import (
    append_related_footer,
    exploration_prefix,
    format_compare,
    format_dossier_answer,
    format_recommend_answer,
    is_dossier_intent,
    is_memory_plan_intent,
    is_recommend_intent,
    last_meaningful_exploration,
    recommend_bridges,
)
from agent.storage import MemoryStore
from agent.study_path import (
    advance_study_path,
    format_study_path,
    is_continue_intent,
    is_plan_intent,
    plan_study_path,
    plan_study_path_from_exploration,
)

TraceCallback = Callable[[dict[str, Any]], None]


def _emit(
    trace: TraceCallback | None,
    stage: str,
    status: str,
    title: str,
    detail: str = "",
    data: dict[str, Any] | None = None,
) -> None:
    """发送可审计执行事件；只含工具与状态，不暴露模型私有思维链。"""
    if trace:
        trace(
            {
                "stage": stage,
                "status": status,
                "title": title,
                "detail": detail,
                "data": data or {},
            }
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

    # 对比意图优先于单桥名命中（否则「对比赵州桥和卢沟桥」会只讲赵州桥）
    compare = re.search(r"(.+?)(和|与|、)(.+?)(对比|比较|区别|异同)", q) or re.search(
        r"对比(.+?)(和|与)(.+)", q
    )
    if compare or re.search(r"对比|比较|区别|异同", q):
        n1 = n2 = None
        if compare:
            n1 = compare.group(1).strip()
            n2 = (compare.group(3) if compare.lastindex >= 3 else compare.group(2)).strip()
            n1 = re.sub(r"^(对比|比较)", "", n1).strip()
            n2 = re.sub(r"(对比|比较|区别|异同)$", "", n2).strip()
        else:
            names = [b.get("name") for b in store.list_bridges() if b.get("name") and b["name"] in q]
            if len(names) >= 2:
                n1, n2 = names[0], names[1]
        if n1 and n2:
            hits = []
            for name in (n1, n2):
                b = store.get_bridge_by_name(name) or (
                    store.search_bridges(name, 1)[0] if store.search_bridges(name, 1) else None
                )
                if b:
                    hits.append(b)
            if len(hits) >= 2:
                return {
                    "text": format_compare(hits[0], hits[1]),
                    "sources": [hits[0]["name"], hits[1]["name"]],
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
                f"· {b['name']}（{b.get('dynasty', '')}，{b.get('type', '')}"
                + (f"，{b.get('province', '')}" if b.get("province") else "")
                + "）"
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
        "text": "暂未匹配到明确结果。可尝试直接输入桥名，或问「宋代有哪些拱桥」「我的档案」「推荐下一座」。",
        "sources": [],
        "mode": "retrieval",
    }


def _finish_turn(
    store: MemoryStore,
    session_id: str,
    message: str,
    text: str,
    sources: list[str],
    mode: str,
    active_focus: str | None,
    memory: dict[str, Any] | None,
    trace: TraceCallback | None = None,
) -> dict[str, Any]:
    _emit(
        trace,
        "persist",
        "running",
        "写回长期记忆",
        "更新兴趣摘要、消息与会话焦点",
    )
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
    _emit(
        trace,
        "persist",
        "done",
        "记忆写回完成",
        f"回答与 {len(sources[:5])} 个来源已持久化",
        {"mode": mode, "sources": sources[:5]},
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
    trace: TraceCallback | None = None,
) -> dict[str, Any]:
    _emit(trace, "session", "running", "恢复会话上下文", "读取焦点、长期记忆与探索足迹")
    session = store.get_session(session_id)
    if not session:
        raise KeyError("session_not_found")

    if focus_bridge is not None:
        store.update_session_focus(session_id, focus_bridge or None)

    active_focus = focus_bridge if focus_bridge is not None else session.get("focus_bridge")
    memory = store.get_user_memory(session_id)
    events = store.get_events(session_id)
    messages = store.get_messages(session_id)
    explore_prefix = exploration_prefix(events)
    _emit(
        trace,
        "session",
        "done",
        "上下文已恢复",
        f"{len(events)} 条探索事件 · {len(messages)} 条消息"
        + (" · 已有长期摘要" if memory else ""),
        {
            "events": len(events),
            "messages": len(messages),
            "has_memory": bool(memory),
            "focus": active_focus,
        },
    )

    # 若无显式焦点，用最近有意义的浏览桥作焦点
    if not active_focus:
        last = last_meaningful_exploration(events)
        if last and last.get("bridge"):
            active_focus = last["bridge"]
            store.update_session_focus(session_id, active_focus)

    # —— 记忆意图：档案 / 推荐 / 按浏览规划 ——
    if is_dossier_intent(message):
        _emit(trace, "route", "done", "意图路由：个人档案", "从长期记忆聚合已探索桥梁与兴趣")
        store.add_message(session_id, "user", message)
        result = format_dossier_answer(store, events, messages, memory)
        return _finish_turn(
            store,
            session_id,
            message,
            result["text"],
            result.get("sources") or [],
            "memory",
            active_focus,
            memory,
            trace,
        )

    if is_recommend_intent(message):
        _emit(trace, "route", "done", "意图路由：记忆推荐", "结合浏览足迹与对话兴趣选择下一座桥")
        store.add_message(session_id, "user", message)
        result = format_recommend_answer(store, events, messages, memory)
        picks = recommend_bridges(store, events, messages, memory, limit=1)
        if picks:
            active_focus = picks[0]["name"]
            store.update_session_focus(session_id, active_focus)
        return _finish_turn(
            store,
            session_id,
            message,
            result["text"],
            result.get("sources") or [],
            "memory",
            active_focus,
            memory,
            trace,
        )

    if is_memory_plan_intent(message) or (
        is_plan_intent(message) and re.search(r"浏览|足迹|档案|记忆", message)
    ):
        _emit(trace, "route", "done", "意图路由：足迹研学", "使用探索记忆生成可续跑路线")
        path = plan_study_path_from_exploration(store, events, messages, memory)
        if path:
            store.add_message(session_id, "user", message)
            store.save_study_path(session_id, path)
            text = format_study_path(path, store)
            stops = path.get("stops") or []
            sources = [stops[0]] if stops else []
            if stops:
                store.update_session_focus(session_id, stops[0])
                active_focus = stops[0]
                b = store.get_bridge_by_name(stops[0])
                if b:
                    text += "\n\n—— 第 1 站讲解 ——\n\n" + format_bridge_brief(
                        b, b.get("_culture")
                    )
            return _finish_turn(
                store, session_id, message, text, sources, "study_path", active_focus, memory, trace
            )

    if is_continue_intent(message):
        _emit(trace, "route", "done", "意图路由：推进任务", "恢复持久化研学任务状态")
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
                store, session_id, message, text, sources, "study_path", active_focus, memory, trace
            )
        # 无线路时，「继续」= 推荐下一座
        store.add_message(session_id, "user", message)
        result = format_recommend_answer(store, events, messages, memory)
        return _finish_turn(
            store,
            session_id,
            message,
            "尚未规划研学路线。先为您按浏览记忆推荐：\n\n" + result["text"],
            result.get("sources") or [],
            "memory",
            active_focus,
            memory,
            trace,
        )

    if is_plan_intent(message):
        _emit(trace, "route", "done", "意图路由：新建研学路线", "解析朝代、结构与地域约束")
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
                b = store.get_bridge_by_name(stops[0])
                if b:
                    text += "\n\n—— 第 1 站讲解 ——\n\n" + format_bridge_brief(
                        b, b.get("_culture")
                    )
            return _finish_turn(
                store, session_id, message, text, sources, "study_path", active_focus, memory, trace
            )

    if re.search(r"集群|备份|ccloud|数据库状态", message):
        _emit(trace, "route", "done", "意图路由：记忆运维", "调用数据面快照与 Cloud 控制面")
        from agent.tools.ccloud_tool import cluster_health_summary

        store.add_message(session_id, "user", message)
        _emit(trace, "tool", "running", "调用 ccloud 与 SQL 诊断", "读取集群、向量索引和工具审计")
        cloud = cluster_health_summary()
        snapshot = store.memory_ops_snapshot()
        store.log_tool_call(
            session_id,
            "memory_ops_diagnose",
            {"request": message},
            {"ccloud": cloud, "memory": snapshot},
        )
        _emit(
            trace,
            "tool",
            "done",
            "运维诊断返回",
            f"数据面 {snapshot.get('backend')} · Cloud {'在线' if cloud.get('ok') else '待连接'}",
            {
                "backend": snapshot.get("backend"),
                "cloud_ok": bool(cloud.get("ok")),
                "counts": snapshot.get("counts") or {},
            },
        )
        counts = snapshot.get("counts") or {}
        vector = snapshot.get("vector_index") or {}
        lines = [
            "记忆层诊断完成：",
            f"· 存储：{snapshot.get('backend', 'unknown')}，"
            f"{'持久化在线' if snapshot.get('backend') == 'cockroach' else '当前为回退模式'}",
            f"· 知识：{counts.get('bridges', 0)} 座桥 / "
            f"{counts.get('embeddings', 0)} 条向量记忆",
            f"· 行为：{counts.get('events', 0)} 条探索事件 / "
            f"{counts.get('messages', 0)} 条消息",
            f"· 审计：{counts.get('tool_calls', 0)} 次工具调用",
            f"· 向量索引：{'在线' if vector.get('active') else '未检测到'}"
            + (f"（{vector.get('name')}）" if vector.get("name") else ""),
        ]
        if cloud.get("ok"):
            lines.append(
                f"· Cloud 控制面：ccloud 已连接，共 "
                f"{cloud.get('cluster_count', 0)} 个集群"
            )
            lines.append("\n结论：数据面与云控制面均可观测，记忆运维闭环正常。")
        else:
            lines.append(
                "· Cloud 控制面：尚未连接（"
                + str(cloud.get("error", "unknown"))
                + "）"
            )
            lines.append(
                "\n结论：CockroachDB 数据面运行正常；接入 Cloud MCP 或 "
                "ccloud 后可补齐集群与备份运维。"
            )
        text = "\n".join(lines)
        return _finish_turn(
            store, session_id, message, text, [], "ccloud", active_focus, memory, trace
        )

    _emit(trace, "route", "done", "意图路由：知识问答", "进入 CockroachDB 语义检索")
    store.add_message(session_id, "user", message)

    history = store.get_messages(session_id)
    # 回答前缀只保留「刚浏览了什么」，避免把整段摘要刷进每条回复
    memory_line = explore_prefix
    if not memory_line and memory and memory.get("interests"):
        tags = [t for t in (memory.get("interests") or []) if t][:4]
        if tags:
            memory_line = "兴趣：" + "、".join(tags)

    _emit(
        trace,
        "tool",
        "running",
        "查询分布式向量索引",
        "bridge_embeddings · cosine distance · top 5",
        {"query": message, "limit": 5},
    )
    hits = store.search_bridges(message, 5)
    # 同一桥有多种 embedding 内容类型；按桥名去重，并将问句中的精确桥名置顶。
    exact = None
    for bridge in store.list_bridges():
        name = bridge.get("name")
        if name and name in message:
            exact = store.get_bridge_by_name(name) or bridge
            break
    if exact:
        hits = [exact] + hits
    if active_focus:
        fb = store.get_bridge_by_name(active_focus)
        if fb and all(h.get("name") != fb.get("name") for h in hits):
            hits = [fb] + hits
    unique_hits = []
    seen_names = set()
    for hit in hits:
        name = hit.get("name")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        unique_hits.append(hit)
    hits = unique_hits[:5]

    context_parts = []
    sources: list[str] = []
    for b in hits[:4]:
        culture = b.get("_culture")
        context_parts.append(format_bridge_brief(b, culture))
        if b.get("name"):
            sources.append(b["name"])
    _emit(
        trace,
        "tool",
        "done",
        "向量检索完成",
        f"命中 {len(hits)} 条，注入 {len(sources[:4])} 个权威来源",
        {"sources": sources[:4], "count": len(hits)},
    )

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
            model_name = (
                settings.openai_model
                if settings.llm_mode == "openai"
                else settings.bedrock_model_id
            )
            _emit(
                trace,
                "model",
                "running",
                "调用生成模型",
                f"{model_name} · RAG 上下文 {len(context_parts)} 段",
                {"provider": settings.llm_mode, "model": model_name},
            )
            focus_obj = store.get_bridge_by_name(active_focus) if active_focus else None
            system = build_system_prompt(
                "\n\n---\n\n".join(context_parts),
                memory_line,
                focus_obj,
            )
            hist = [{"role": m["role"], "content": m["content"]} for m in history[:-1]]
            text, mode = chat_with_llm(system, hist, message)
            _emit(
                trace,
                "model",
                "done",
                "模型生成完成",
                f"{mode} · {len(text)} 字符",
                {"mode": mode, "characters": len(text)},
            )
        else:
            raise RuntimeError("retrieval_only")
    except Exception as exc:
        _emit(
            trace,
            "model",
            "fallback",
            "切换可用性回退",
            "模型未配置或调用失败，使用确定性本地答案",
            {"reason": type(exc).__name__},
        )
        result = local_answer(store, message, active_focus)
        text = result["text"]
        sources = result.get("sources") or sources
        mode = result["mode"]
        if memory_line and mode == "retrieval":
            text = f"（{memory_line}）\n\n{text}"
        elif explore_prefix and mode == "retrieval" and not memory_line:
            text = f"（{explore_prefix}）\n\n{text}"

    # 讲解某桥后，附上「尚未探索的相关桥」——记忆驱动，而非一次性问答
    if mode in ("retrieval", "openai", "bedrock") and sources:
        text = append_related_footer(store, text, sources, events, messages)

    return _finish_turn(
        store, session_id, message, text, sources, mode, active_focus, memory, trace
    )
