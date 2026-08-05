"""用户古桥档案：从浏览事件与对话中聚合。"""
from __future__ import annotations

from typing import Any


def build_dossier(
    events: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    memory: dict[str, Any] | None,
) -> dict[str, Any]:
    learned: list[str] = []
    seen: set[str] = set()

    for ev in events:
        name = ev.get("bridge")
        if name and name not in seen:
            seen.add(name)
            learned.append(name)

    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for name in msg.get("sources") or []:
            if name and name not in seen:
                seen.add(name)
                learned.append(name)

    interests = list(memory.get("interests") or []) if memory else []
    last_event = events[-1] if events else None

    return {
        "learned_count": len(learned),
        "total_bridges": 34,
        "learned_bridges": learned[:20],
        "interests": interests,
        "last_exploration": last_event,
        "summary": memory.get("summary") if memory else None,
    }
