#!/usr/bin/env python3
"""将 data/ 古桥数据导入 CockroachDB，并写入向量 embedding。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import settings  # noqa: E402
from agent.embeddings import embed_text  # noqa: E402


def main() -> None:
    import psycopg

    dsn = settings.database_url or "postgresql://root@localhost:26257/defaultdb?sslmode=disable"
    bridges_path = settings.bridge_data_dir / "bridges.json"
    culture_path = settings.bridge_data_dir / "poetry-culture.json"

    bridges = json.loads(bridges_path.read_text(encoding="utf-8"))
    culture_raw = json.loads(culture_path.read_text(encoding="utf-8")) if culture_path.exists() else {}
    culture = culture_raw.get("entries", culture_raw)

    schema = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")

    with psycopg.connect(dsn, autocommit=True) as conn:
        # CockroachDB 26+：启用分布式向量索引（需 autocommit）
        try:
            conn.execute("SET CLUSTER SETTING feature.vector_index.enabled = true")
            print("vector_index.enabled = true")
        except Exception as exc:
            print("warn: enable vector_index:", exc)

        for stmt in _split_sql(schema):
            if not stmt.strip():
                continue
            try:
                conn.execute(stmt)
            except Exception as exc:
                msg = str(exc).lower()
                if "already exists" in msg or "duplicate" in msg:
                    print("skip:", stmt.strip().split("\n", 1)[0][:80], "…")
                    continue
                if "vector index" in stmt.lower() or "create vector index" in stmt.lower():
                    print("warn vector index:", exc)
                    continue
                raise

        for b in bridges:
            name = b["name"]
            row = conn.execute(
                """
                INSERT INTO bridges (
                  name, dynasty, year, province, city, lon, lat,
                  length, span, width, bridge_type, material,
                  protection, poetry, intro, raw_json
                ) VALUES (
                  %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb
                )
                ON CONFLICT (name) DO UPDATE SET
                  dynasty = EXCLUDED.dynasty,
                  intro = EXCLUDED.intro,
                  raw_json = EXCLUDED.raw_json
                RETURNING id
                """,
                (
                    name,
                    b.get("dynasty"),
                    b.get("year"),
                    b.get("province"),
                    b.get("city"),
                    b.get("lon"),
                    b.get("lat"),
                    b.get("length"),
                    b.get("span"),
                    b.get("width"),
                    b.get("type"),
                    b.get("material"),
                    b.get("protection"),
                    b.get("poetry"),
                    b.get("intro"),
                    json.dumps(b, ensure_ascii=False),
                ),
            ).fetchone()
            bridge_id = row[0]
            c = culture.get(name) or {}
            conn.execute(
                """
                INSERT INTO bridge_culture (bridge_id, anecdote, poetry_refs, cultural_insight)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (bridge_id) DO UPDATE SET
                  anecdote = EXCLUDED.anecdote,
                  poetry_refs = EXCLUDED.poetry_refs,
                  cultural_insight = EXCLUDED.cultural_insight
                """,
                (
                    bridge_id,
                    c.get("anecdote"),
                    c.get("poetryRefs"),
                    c.get("culturalInsight"),
                ),
            )
            for ctype, text in _content_chunks(b, c):
                if not text.strip():
                    continue
                vec = embed_text(text)
                vec_lit = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
                conn.execute(
                    """
                    INSERT INTO bridge_embeddings (bridge_id, dynasty, content_type, content_text, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    ON CONFLICT (bridge_id, content_type) DO UPDATE SET
                      content_text = EXCLUDED.content_text,
                      embedding = EXCLUDED.embedding
                    """,
                    (bridge_id, b.get("dynasty"), ctype, text[:4000], vec_lit),
                )
        print(f"已导入 {len(bridges)} 座桥梁 → {dsn}")


def _content_chunks(bridge: dict, culture: dict) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    if bridge.get("intro"):
        chunks.append(("intro", bridge["intro"]))
    if culture.get("anecdote"):
        chunks.append(("anecdote", culture["anecdote"]))
    if culture.get("culturalInsight"):
        chunks.append(("culture", culture["culturalInsight"]))
    poetry = " ".join(filter(None, [bridge.get("poetry"), culture.get("poetryRefs")]))
    if poetry.strip():
        chunks.append(("poetry", poetry))
    return chunks


def _split_sql(sql: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            parts.append("\n".join(buf))
            buf = []
    if buf:
        parts.append("\n".join(buf))
    return parts


if __name__ == "__main__":
    main()
