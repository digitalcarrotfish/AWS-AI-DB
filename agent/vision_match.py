"""古桥外观图匹配（感知哈希）— 扫桥识别，无需外网视觉模型。"""
from __future__ import annotations

import io
import re
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR = ROOT / "桥"

# 汉明距离阈值：越小越像；64 位 dHash
MAX_DISTANCE = 22


def _dhash(img: Any, hash_size: int = 8) -> int:
    from PIL import Image

    if not isinstance(img, Image.Image):
        img = Image.open(img)
    img = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
    # 每行比较相邻像素
    bits = 0
    bit = 0
    for row in range(hash_size):
        row_start = row * (hash_size + 1)
        for col in range(hash_size):
            left = pixels[row_start + col]
            right = pixels[row_start + col + 1]
            if left > right:
                bits |= 1 << bit
            bit += 1
    return bits


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _name_from_path(path: Path) -> str | None:
    # 「赵州桥 外观图.jpg」 / 「赵州桥 线稿图.png」
    stem = path.stem
    m = re.match(r"^(.+?)\s+(外观图|线稿图)$", stem)
    if m:
        return m.group(1).strip()
    return None


@lru_cache(maxsize=1)
def build_gallery_index() -> tuple[tuple[str, str, int], ...]:
    """返回不可变元组缓存：(bridge_name, rel_path, dhash)。"""
    items: list[tuple[str, str, int]] = []
    if not MEDIA_DIR.is_dir():
        return tuple(items)
    for path in sorted(MEDIA_DIR.iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        name = _name_from_path(path)
        if not name:
            continue
        # 优先外观图；线稿也入库作补充
        try:
            h = _dhash(path)
        except Exception:
            continue
        rel = f"桥/{path.name}"
        items.append((name, rel, h))
    return tuple(items)


def identify_image(
    image_bytes: bytes,
    *,
    top_k: int = 5,
    max_distance: int = MAX_DISTANCE,
) -> list[dict[str, Any]]:
    """识别上传图片，返回按相似度排序的候选。"""
    from PIL import Image

    try:
        query = Image.open(io.BytesIO(image_bytes))
        qh = _dhash(query)
    except Exception as exc:
        raise ValueError(f"无法解析图片：{exc}") from exc

    gallery = build_gallery_index()
    if not gallery:
        return []

    scored: list[tuple[int, str, str]] = []
    best_by_name: dict[str, tuple[int, str]] = {}
    for name, rel, h in gallery:
        dist = _hamming(qh, h)
        prev = best_by_name.get(name)
        if prev is None or dist < prev[0]:
            best_by_name[name] = (dist, rel)

    for name, (dist, rel) in best_by_name.items():
        scored.append((dist, name, rel))
    scored.sort(key=lambda x: x[0])

    out: list[dict[str, Any]] = []
    for dist, name, rel in scored[:top_k]:
        if dist > max_distance and out:
            break
        score = round(max(0.0, 1.0 - dist / 64.0), 4)
        preview = "/" + "/".join(urllib.parse.quote(p) for p in Path(rel).parts)
        out.append(
            {
                "name": name,
                "distance": dist,
                "score": score,
                "matched": dist <= max_distance,
                "preview": preview,
                "path": rel,
            }
        )
    # 若全部超过阈值，仍返回最接近的 1–3 个并标记 matched=False
    if not any(x["matched"] for x in out) and out:
        out = out[:3]
    elif out:
        out = [x for x in out if x["matched"]] or out[:1]
    return out


def gallery_stats() -> dict[str, Any]:
    idx = build_gallery_index()
    names = sorted({n for n, _, _ in idx})
    return {
        "images": len(idx),
        "bridges": len(names),
        "names": names,
        "media_dir": str(MEDIA_DIR),
    }
