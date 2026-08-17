from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

STOP = set("的了吗呢啊吧呀与及在是有了和")
EMBED_DIM = 1024


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            out.append(ch)
    for w in re.split(r"[\s，。；、？！,.;:!?]+", text):
        if len(w) >= 2:
            out.append(w)
        if len(w) >= 4:
            for i in range(len(w) - 1):
                out.append(w[i : i + 2])
    return out


def score_text(query: str, blob: str) -> float:
    qt = _tokens(query.lower())
    if not blob:
        return 0.0
    hay = blob
    score = 0.0
    for tok in qt:
        if len(tok) < 2 and tok in STOP:
            continue
        if tok in hay:
            score += 4 if len(tok) >= 3 else 2
    return score


def hash_embed(text: str, dim: int = EMBED_DIM) -> list[float]:
    """开发用确定性伪向量（无 Bedrock 时用于本地 CRDB 演示）。"""
    vec = [0.0] * dim
    for tok in _tokens(text):
        h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def bridge_to_blob(bridge: dict[str, Any], culture: dict[str, Any] | None = None) -> str:
    parts = [
        bridge.get("name", ""),
        bridge.get("dynasty", ""),
        str(bridge.get("year", "")),
        bridge.get("province", ""),
        bridge.get("city", ""),
        bridge.get("type", ""),
        bridge.get("material", ""),
        bridge.get("poetry", ""),
        bridge.get("intro", ""),
    ]
    if culture:
        parts.extend([
            culture.get("anecdote", ""),
            culture.get("poetryRefs", ""),
            culture.get("culturalInsight", ""),
        ])
    return " ".join(p for p in parts if p)


def format_bridge_brief(bridge: dict[str, Any], culture: dict[str, Any] | None = None) -> str:
    year = bridge.get("year")
    if year is not None:
        year_s = f"约公元前{-year}年" if year < 0 else f"约公元{year}年"
    else:
        year_s = ""
    lines = [
        f"【{bridge.get('name', '')}】",
        " · ".join(
            p
            for p in [
                bridge.get("dynasty"),
                year_s,
                f"{bridge.get('province', '')} {bridge.get('city', '')}".strip(),
                bridge.get("type"),
                bridge.get("material"),
            ]
            if p
        ),
    ]
    if bridge.get("span") is not None:
        span_line = f"最大单孔跨度约 {bridge['span']} 米"
        if bridge.get("length") is not None:
            span_line += f"，桥长约 {bridge['length']} 米"
        lines.append(span_line)
    if bridge.get("poetry"):
        lines.append(f"名句：「{bridge['poetry']}」")
    intro = bridge.get("intro") or ""
    if intro:
        lines.append(intro[:280] + ("…" if len(intro) > 280 else ""))
    if culture and culture.get("culturalInsight"):
        ci = culture["culturalInsight"]
        lines.append("文化解读：" + ci[:200] + ("…" if len(ci) > 200 else ""))
    return "\n".join(lines)


def extract_interests(query: str, sources: list[str]) -> list[str]:
    interests: list[str] = []
    for d in re.findall(r"(夏|商|周|汉|晋|隋|唐|宋|南宋|金|元|明|清)", query):
        if d not in interests:
            interests.append(d)
    for t in re.findall(r"(拱桥|梁桥|索桥|浮桥)", query):
        if t not in interests:
            interests.append(t)
    # 桥名最多记 2 个，避免兴趣标签被检索 sources 刷屏
    for s in sources[:2]:
        if s and s not in interests:
            interests.append(s)
    return interests[:8]
