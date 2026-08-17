from __future__ import annotations

import re
from typing import Any

CONTINUE_RE = re.compile(r"继续|下一站|下一站|接着")


def plan_study_path(store: Any, query: str) -> dict[str, Any] | None:
    dynasty = None
    btype = None
    region = None
    m = re.search(r"(夏|商|周|汉|晋|隋|唐|宋|南宋|金|元|明|清)", query)
    if m:
        dynasty = m.group(1)
    t = re.search(r"(拱桥|梁桥|索桥|浮桥)", query)
    if t:
        btype = t.group(1)
    if "南方" in query or "岭南" in query:
        region = "south"
    elif "北方" in query:
        region = "north"

    bridges = store.list_bridges()
    if dynasty:
        bridges = [b for b in bridges if b.get("dynasty") == dynasty]
    if btype:
        bridges = [b for b in bridges if b.get("type") == btype]
    if region == "south":
        south = ("广东", "广西", "福建", "云南", "贵州", "四川", "湖南", "江西", "浙江", "江苏")
        bridges = [b for b in bridges if any(p in (b.get("province") or "") for p in south)]
    elif region == "north":
        north = ("北京", "河北", "山西", "陕西", "河南", "山东", "辽宁", "吉林", "黑龙江", "天津")
        bridges = [b for b in bridges if any(p in (b.get("province") or "") for p in north)]

    bridges.sort(key=lambda b: b.get("year") or 0)
    if len(bridges) < 2:
        return None

    stops = [b["name"] for b in bridges[:7]]
    return {
        "title": _path_title(dynasty, btype, region),
        "stops": stops,
        "current_step": 0,
        "status": "in_progress",
    }


def plan_study_path_from_exploration(
    store: Any,
    events: list[dict[str, Any]],
    messages: list[dict[str, Any]] | None = None,
    memory: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """用浏览足迹生成研学路线：已看过的作序章，再接推荐未看桥梁。"""
    from agent.memory_actions import learned_bridge_names, recommend_bridges

    learned = learned_bridge_names(events, None)  # 只计浏览，不计对话引用
    picks = recommend_bridges(store, events, messages, memory, limit=5)
    stops: list[str] = []
    # 最近浏览的 2 座作回顾站（倒序时间 → 正序路线）
    recent = []
    for ev in reversed(events or []):
        name = ev.get("bridge")
        if name and name not in recent:
            recent.append(name)
        if len(recent) >= 2:
            break
    recent.reverse()
    for name in recent:
        if name not in stops:
            stops.append(name)
    for b in picks:
        name = b.get("name")
        if name and name not in stops:
            stops.append(name)
        if len(stops) >= 6:
            break
    if len(stops) < 2:
        # 无浏览时退回跨度名桥
        top = sorted(store.list_bridges(), key=lambda x: x.get("span") or 0, reverse=True)
        stops = [b["name"] for b in top[:5] if b.get("name")]
    if len(stops) < 2:
        return None
    title = "入门研学路线"
    if learned:
        title = f"足迹研学（已探 {len(learned)} 座）"
    return {
        "title": title,
        "stops": stops,
        "current_step": 0,
        "status": "in_progress",
        "from_exploration": True,
    }


def _path_title(dynasty: str | None, btype: str | None, region: str | None) -> str:
    parts = []
    if dynasty:
        parts.append(dynasty + "代")
    if btype:
        parts.append(btype)
    if region == "south":
        parts.append("南方")
    elif region == "north":
        parts.append("北方")
    parts.append("研学路线")
    return "".join(parts) if parts else "古桥研学路线"


def format_study_path(path: dict[str, Any], store: Any) -> str:
    stops: list[str] = path.get("stops") or []
    step = int(path.get("current_step") or 0)
    lines = [f"📜 {path.get('title', '研学路线')}（共 {len(stops)} 站）", ""]
    for i, name in enumerate(stops):
        mark = "▶ " if i == step else ("✓ " if i < step else "  ")
        b = store.get_bridge_by_name(name) or {}
        meta = " · ".join(filter(None, [b.get("dynasty"), b.get("type")]))
        lines.append(f"{mark}{i + 1}. {name}" + (f"（{meta}）" if meta else ""))
    lines.append("")
    if step < len(stops):
        lines.append(f"当前站：{stops[step]}。发送「继续」进入下一站。")
    else:
        lines.append("路线已完成！可开启新的专题。")
    return "\n".join(lines)


def advance_study_path(path: dict[str, Any]) -> dict[str, Any]:
    stops = path.get("stops") or []
    step = int(path.get("current_step") or 0)
    if step < len(stops) - 1:
        path = {**path, "current_step": step + 1}
    else:
        path = {**path, "current_step": len(stops), "status": "completed"}
    return path


def is_plan_intent(query: str) -> bool:
    return bool(re.search(r"规划|研学|路线|之旅|行程", query))


def is_continue_intent(query: str) -> bool:
    return bool(CONTINUE_RE.search(query))
