"""记忆驱动的 Agent 行为：档案、推荐、关联、结构化对比。"""
from __future__ import annotations

import re
from typing import Any

from agent.dossier import build_dossier
from agent.knowledge import format_bridge_brief

SOURCE_LABEL = {
    "knowledge_graph": "知识图谱",
    "bridge_detail": "桥梁档案",
    "museum_map": "地图大屏",
    "word_cloud": "文化热词",
    "bridge_3d": "三维模型",
    "museum": "数字博物馆",
    "agent": "档案员",
}

# 打开档案员本身不算「关注某桥」的证据
NOISE_EVENTS = {"open_archivist", "view_map", "view_knowledge"}


def last_meaningful_exploration(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for ev in reversed(events or []):
        if not ev.get("bridge"):
            continue
        if ev.get("event_type") in NOISE_EVENTS:
            continue
        return ev
    # 回退：任意带桥名的事件
    for ev in reversed(events or []):
        if ev.get("bridge"):
            return ev
    return None


def exploration_prefix(events: list[dict[str, Any]]) -> str | None:
    last = last_meaningful_exploration(events)
    if not last:
        return None
    src = SOURCE_LABEL.get(last.get("source") or "", last.get("source") or "图鉴")
    return f"您刚从【{src}】关注了「{last['bridge']}」"


def learned_bridge_names(
    events: list[dict[str, Any]],
    messages: list[dict[str, Any]] | None = None,
) -> list[str]:
    dossier = build_dossier(events, messages or [], None)
    return list(dossier.get("learned_bridges") or [])


def format_dossier_answer(
    store: Any,
    events: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    memory: dict[str, Any] | None,
) -> dict[str, Any]:
    dossier = build_dossier(events, messages, memory)
    total = len(store.list_bridges())
    learned = dossier.get("learned_bridges") or []
    interests = dossier.get("interests") or []
    lines = [
        "📒 您的古桥档案",
        f"已了解 {len(learned)} / {total} 座",
        "",
    ]
    if learned:
        lines.append("已探索：")
        for name in learned[:12]:
            b = store.get_bridge_by_name(name) or {}
            meta = " · ".join(filter(None, [b.get("dynasty"), b.get("type"), b.get("province")]))
            lines.append(f"· {name}" + (f"（{meta}）" if meta else ""))
        if len(learned) > 12:
            lines.append(f"……另有 {len(learned) - 12} 座")
    else:
        lines.append("尚未记录浏览。可先去地图或图谱点开几座桥，再回来问我。")

    if interests:
        lines.extend(["", "兴趣标签：" + "、".join(interests[:8])])

    trail = [e for e in events if e.get("bridge")][-5:]
    if trail:
        lines.extend(["", "最近轨迹："])
        for ev in reversed(trail):
            src = SOURCE_LABEL.get(ev.get("source") or "", ev.get("source") or "图鉴")
            lines.append(f"· {src} → {ev['bridge']}")

    unseen = recommend_bridges(store, events, messages, memory, limit=3)
    if unseen:
        lines.extend(["", "根据档案，下一站可看："])
        for b in unseen:
            lines.append(
                f"· {b['name']}（"
                + " · ".join(filter(None, [b.get("dynasty"), b.get("type")]))
                + "）"
            )
        lines.append("发送桥名，或说「推荐下一座」继续。")

    return {
        "text": "\n".join(lines),
        "sources": learned[:5],
        "mode": "memory",
    }


def recommend_bridges(
    store: Any,
    events: list[dict[str, Any]],
    messages: list[dict[str, Any]] | None,
    memory: dict[str, Any] | None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    seen = set(learned_bridge_names(events, messages))
    interests = list((memory or {}).get("interests") or [])

    # 从浏览推断偏好朝代 / 桥型
    for name in list(seen)[:8]:
        b = store.get_bridge_by_name(name)
        if not b:
            continue
        for key in ("dynasty", "type"):
            val = b.get(key)
            if val and val not in interests:
                interests.append(val)

    last = last_meaningful_exploration(events)
    focus = store.get_bridge_by_name(last["bridge"]) if last else None

    candidates: list[tuple[float, dict[str, Any]]] = []
    for b in store.list_bridges():
        name = b.get("name")
        if not name or name in seen:
            continue
        score = 1.0
        if focus:
            if b.get("dynasty") and b.get("dynasty") == focus.get("dynasty"):
                score += 5
            if b.get("type") and b.get("type") == focus.get("type"):
                score += 4
            if b.get("province") and b.get("province") == focus.get("province"):
                score += 2
            # 同材料、相近跨度
            if b.get("material") and b.get("material") == focus.get("material"):
                score += 1.5
            fs, bs = focus.get("span"), b.get("span")
            if isinstance(fs, (int, float)) and isinstance(bs, (int, float)):
                score += max(0.0, 3.0 - abs(fs - bs) / 20.0)
        for tag in interests:
            if tag in (b.get("dynasty"), b.get("type"), b.get("name"), b.get("province")):
                score += 2.5
        # 名气：跨度略加权
        if isinstance(b.get("span"), (int, float)):
            score += min(2.0, float(b["span"]) / 40.0)
        item = dict(b)
        item["_culture"] = (store.get_bridge_by_name(name) or {}).get("_culture")
        candidates.append((score, item))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in candidates[:limit]]


def format_recommend_answer(
    store: Any,
    events: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    memory: dict[str, Any] | None,
) -> dict[str, Any]:
    learned = learned_bridge_names(events, messages)
    picks = recommend_bridges(store, events, messages, memory, limit=5)
    if not picks:
        return {
            "text": "您似乎已浏览完当前图鉴中的全部桥梁，或数据尚未导入。可换个专题问「规划宋代研学路线」。",
            "sources": [],
            "mode": "memory",
        }

    last = last_meaningful_exploration(events)
    why = ""
    if last and last.get("bridge"):
        why = f"基于您刚关注的「{last['bridge']}」"
        if learned:
            why += f"，以及已了解的 {len(learned)} 座桥"
        why += "，推荐："
    elif learned:
        why = f"基于您已了解的 {len(learned)} 座桥，推荐尚未探索的："
    else:
        why = "您还没有浏览记录。先推荐几座入门名桥："

    lines = ["🧭 " + why, ""]
    sources: list[str] = []
    for i, b in enumerate(picks, 1):
        sources.append(b["name"])
        meta = " · ".join(
            filter(None, [b.get("dynasty"), b.get("type"), b.get("province"), 
                          f"跨度 {b['span']}m" if b.get("span") is not None else ""])
        )
        reason = _recommend_reason(b, last, learned, store)
        lines.append(f"{i}. 【{b['name']}】{meta}")
        if reason:
            lines.append(f"   理由：{reason}")
    lines.extend(["", "点名一座，或说「介绍」+ 桥名。也可「根据浏览规划研学路线」。"])
    return {"text": "\n".join(lines), "sources": sources, "mode": "memory"}


def _recommend_reason(
    b: dict[str, Any],
    last: dict[str, Any] | None,
    learned: list[str],
    store: Any,
) -> str:
    bits: list[str] = []
    focus = store.get_bridge_by_name(last["bridge"]) if last and last.get("bridge") else None
    if focus:
        if b.get("dynasty") == focus.get("dynasty"):
            bits.append(f"同属{b.get('dynasty')}代")
        if b.get("type") == focus.get("type"):
            bits.append(f"同为{b.get('type')}")
        if b.get("province") == focus.get("province"):
            bits.append("同省可对照")
    if not bits and b.get("span"):
        bits.append("跨度突出，文献常见")
    if not bits and learned:
        bits.append("补全您尚未覆盖的类型/朝代")
    return "，".join(bits)


def format_compare(b1: dict[str, Any], b2: dict[str, Any]) -> str:
    def row(label: str, a: Any, b: Any) -> str:
        return f"· {label}：{a or '—'}  vs  {b or '—'}"

    y1, y2 = b1.get("year"), b2.get("year")
    y1s = f"约公元{y1}年" if isinstance(y1, int) and y1 >= 0 else (f"约公元前{-y1}年" if isinstance(y1, int) else "—")
    y2s = f"约公元{y2}年" if isinstance(y2, int) and y2 >= 0 else (f"约公元前{-y2}年" if isinstance(y2, int) else "—")

    lines = [
        f"—— 「{b1.get('name')}」与「{b2.get('name')}」对比 ——",
        "",
        row("朝代", b1.get("dynasty"), b2.get("dynasty")),
        row("年代", y1s, y2s),
        row("类型", b1.get("type"), b2.get("type")),
        row("材质", b1.get("material"), b2.get("material")),
        row("省份", b1.get("province"), b2.get("province")),
        row("跨度(m)", b1.get("span"), b2.get("span")),
        row("桥长(m)", b1.get("length"), b2.get("length")),
    ]

    # 简短解读
    notes: list[str] = []
    if b1.get("type") and b1.get("type") == b2.get("type"):
        notes.append(f"同为{b1['type']}，可对照营造手法与尺度。")
    elif b1.get("type") and b2.get("type"):
        notes.append(f"桥型不同（{b1['type']} / {b2['type']}），反映不同水文与工艺选择。")
    if isinstance(b1.get("span"), (int, float)) and isinstance(b2.get("span"), (int, float)):
        bigger = b1 if b1["span"] >= b2["span"] else b2
        notes.append(f"单孔跨度上「{bigger['name']}」更大（{bigger['span']} m）。")
    if notes:
        lines.extend(["", "要点："] + [f"· {n}" for n in notes])

    c1, c2 = b1.get("_culture") or {}, b2.get("_culture") or {}
    if c1.get("culturalInsight") or c2.get("culturalInsight"):
        lines.append("")
        lines.append("文化侧记：")
        if c1.get("culturalInsight"):
            lines.append(f"· {b1.get('name')}：{c1['culturalInsight'][:120]}…")
        if c2.get("culturalInsight"):
            lines.append(f"· {b2.get('name')}：{c2['culturalInsight'][:120]}…")

    lines.extend(["", "分述：", "", format_bridge_brief(b1, b1.get("_culture")), "", "---", "", format_bridge_brief(b2, b2.get("_culture"))])
    return "\n".join(lines)


def related_unseen(
    store: Any,
    bridge_name: str,
    events: list[dict[str, Any]],
    messages: list[dict[str, Any]] | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    focus = store.get_bridge_by_name(bridge_name)
    if not focus:
        return []
    fake_last = {"bridge": bridge_name, "source": "agent", "event_type": "focus"}
    # 临时把当前桥视为已看，推荐同类
    evs = list(events or []) + [fake_last]
    return recommend_bridges(store, evs, messages, {"interests": [focus.get("dynasty"), focus.get("type")]}, limit=limit)


def append_related_footer(
    store: Any,
    text: str,
    sources: list[str],
    events: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> str:
    if not sources:
        return text
    name = sources[0]
    related = related_unseen(store, name, events, messages, limit=3)
    related = [b for b in related if b.get("name") != name][:2]
    if not related:
        return text
    lines = [text, "", "—— 记忆延伸 ——", f"看完「{name}」，您尚未探索且相关的还有："]
    for b in related:
        meta = " · ".join(filter(None, [b.get("dynasty"), b.get("type")]))
        lines.append(f"· {b['name']}" + (f"（{meta}）" if meta else ""))
    lines.append("可以说「推荐下一座」或直接点名。")
    return "\n".join(lines)


def is_dossier_intent(q: str) -> bool:
    return bool(
        re.search(
            r"我的档案|看过什么|看过哪些|浏览(过|了|记录|轨迹)|了解了几|档案进度|记忆摘要|我的记忆",
            q,
        )
    )


def is_recommend_intent(q: str) -> bool:
    return bool(
        re.search(
            r"推荐(下一座|一座|几座)?|下一座|还没看|尚未看|接着看|该看什么|看什么好|建议(看|游览)",
            q,
        )
    )


def is_memory_plan_intent(q: str) -> bool:
    return bool(re.search(r"(根据|基于).*(浏览|足迹|档案|记忆).*(路线|研学|规划)", q)) or bool(
        re.search(r"(浏览|足迹|档案).*(规划|路线|研学)", q)
    )
