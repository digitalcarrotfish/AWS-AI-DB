from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore(ABC):
    @abstractmethod
    def list_bridges(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_bridge_by_name(self, name: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def search_bridges(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...

    @abstractmethod
    def create_session(self, focus_bridge: str | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def get_session(self, session_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def update_session_focus(self, session_id: str, focus_bridge: str | None) -> None: ...

    @abstractmethod
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        sources: list[str] | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    def get_messages(self, session_id: str, limit: int = 40) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_user_memory(self, session_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def upsert_user_memory(
        self, session_id: str, summary: str, interests: list[str]
    ) -> None: ...

    @abstractmethod
    def log_tool_call(
        self,
        session_id: str | None,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
    ) -> None: ...

    @abstractmethod
    def record_event(
        self,
        session_id: str,
        event_type: str,
        source: str,
        *,
        bridge: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    def get_events(self, session_id: str, limit: int = 30) -> list[dict[str, Any]]: ...

    @abstractmethod
    def memory_ops_snapshot(self) -> dict[str, Any]: ...


class JsonMemoryStore(MemoryStore):
    """无需 CockroachDB，读取 bridge 数据 + 本地 JSON 存会话。"""

    def __init__(self) -> None:
        self.bridges: list[dict[str, Any]] = []
        self.culture: dict[str, Any] = {}
        self._load_knowledge()
        self.sessions_path = settings.sessions_dir / "index.json"
        self._sessions: dict[str, dict[str, Any]] = self._load_sessions()

    def _load_knowledge(self) -> None:
        bridges_path = settings.bridge_data_dir / "bridges.json"
        culture_path = settings.bridge_data_dir / "poetry-culture.json"
        if not bridges_path.exists():
            raise FileNotFoundError(f"找不到 bridge 数据：{bridges_path}")
        self.bridges = json.loads(bridges_path.read_text(encoding="utf-8"))
        if culture_path.exists():
            raw = json.loads(culture_path.read_text(encoding="utf-8"))
            self.culture = raw.get("entries", raw if isinstance(raw, dict) else {})

    def _load_sessions(self) -> dict[str, dict[str, Any]]:
        if self.sessions_path.exists():
            return json.loads(self.sessions_path.read_text(encoding="utf-8"))
        return {}

    def _save_sessions(self) -> None:
        self.sessions_path.write_text(
            json.dumps(self._sessions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _culture_for(self, name: str) -> dict[str, Any] | None:
        c = self.culture.get(name)
        return c if isinstance(c, dict) else None

    def list_bridges(self) -> list[dict[str, Any]]:
        return sorted(self.bridges, key=lambda b: b.get("year") or 0)

    def get_bridge_by_name(self, name: str) -> dict[str, Any] | None:
        for b in self.bridges:
            if b.get("name") == name:
                out = dict(b)
                out["_culture"] = self._culture_for(name)
                return out
        return None

    def search_bridges(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        from agent.knowledge import bridge_to_blob, score_text

        ranked: list[tuple[float, dict[str, Any]]] = []
        q = query.lower()
        for b in self.bridges:
            name = b.get("name", "")
            blob = bridge_to_blob(b, self._culture_for(name))
            s = score_text(query, blob)
            if q and name.lower() in q:
                s += 30
            if s > 0:
                item = dict(b)
                item["_culture"] = self._culture_for(name)
                item["_score"] = s
                ranked.append((s, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in ranked[:limit]]

    def create_session(self, focus_bridge: str | None = None) -> dict[str, Any]:
        sid = str(uuid.uuid4())
        session = {
            "id": sid,
            "focus_bridge": focus_bridge,
            "created_at": _now(),
            "updated_at": _now(),
            "messages": [],
            "events": [],
            "study_path": None,
            "user_memory": None,
        }
        self._sessions[sid] = session
        self._save_sessions()
        return {"id": sid, "focus_bridge": focus_bridge}

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self._sessions.get(session_id)

    def update_session_focus(self, session_id: str, focus_bridge: str | None) -> None:
        s = self._sessions.get(session_id)
        if not s:
            return
        s["focus_bridge"] = focus_bridge
        s["updated_at"] = _now()
        self._save_sessions()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        sources: list[str] | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        s = self._sessions.get(session_id)
        if not s:
            raise KeyError(session_id)
        msg = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "sources": sources or [],
            "mode": mode,
            "created_at": _now(),
        }
        s.setdefault("messages", []).append(msg)
        s["updated_at"] = _now()
        self._save_sessions()
        return msg

    def get_messages(self, session_id: str, limit: int = 40) -> list[dict[str, Any]]:
        s = self._sessions.get(session_id)
        if not s:
            return []
        return s.get("messages", [])[-limit:]

    def get_user_memory(self, session_id: str) -> dict[str, Any] | None:
        s = self._sessions.get(session_id)
        return s.get("user_memory") if s else None

    def upsert_user_memory(
        self, session_id: str, summary: str, interests: list[str]
    ) -> None:
        s = self._sessions.get(session_id)
        if not s:
            return
        s["user_memory"] = {
            "summary": summary,
            "interests": interests,
            "updated_at": _now(),
        }
        s["updated_at"] = _now()
        self._save_sessions()

    def log_tool_call(
        self,
        session_id: str | None,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
    ) -> None:
        log_path = settings.runtime_dir / "tool_calls.jsonl"
        entry = {
            "session_id": session_id,
            "tool_name": tool_name,
            "input": input_data,
            "output": output_data,
            "created_at": _now(),
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def record_event(
        self,
        session_id: str,
        event_type: str,
        source: str,
        *,
        bridge: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        s = self._sessions.get(session_id)
        if not s:
            raise KeyError(session_id)
        ev = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "source": source,
            "bridge": bridge,
            "meta": meta or {},
            "created_at": _now(),
        }
        s.setdefault("events", []).append(ev)
        if bridge:
            s["focus_bridge"] = bridge
        s["updated_at"] = _now()
        self._save_sessions()
        return ev

    def get_events(self, session_id: str, limit: int = 30) -> list[dict[str, Any]]:
        s = self._sessions.get(session_id)
        if not s:
            return []
        return s.get("events", [])[-limit:]

    def memory_ops_snapshot(self) -> dict[str, Any]:
        messages = sum(len(s.get("messages", [])) for s in self._sessions.values())
        events = [
            event
            for session in self._sessions.values()
            for event in session.get("events", [])
        ]
        event_types: dict[str, int] = {}
        for event in events:
            name = str(event.get("event_type") or "unknown")
            event_types[name] = event_types.get(name, 0) + 1

        calls: list[dict[str, Any]] = []
        calls_path = settings.runtime_dir / "tool_calls.jsonl"
        if calls_path.exists():
            for line in calls_path.read_text(encoding="utf-8").splitlines():
                try:
                    calls.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        tool_counts: dict[str, int] = {}
        for call in calls:
            name = str(call.get("tool_name") or "unknown")
            tool_counts[name] = tool_counts.get(name, 0) + 1

        return {
            "backend": "json",
            "counts": {
                "bridges": len(self.bridges),
                "embeddings": 0,
                "sessions": len(self._sessions),
                "messages": messages,
                "events": len(events),
                "memories": sum(
                    1 for s in self._sessions.values() if s.get("user_memory")
                ),
                "tasks": sum(
                    1 for s in self._sessions.values() if s.get("study_path")
                ),
                "tool_calls": len(calls),
            },
            "vector_index": {"active": False, "name": None},
            "event_types": [
                {"name": name, "count": count}
                for name, count in sorted(
                    event_types.items(), key=lambda item: item[1], reverse=True
                )[:6]
            ],
            "tool_usage": [
                {"name": name, "count": count}
                for name, count in sorted(
                    tool_counts.items(), key=lambda item: item[1], reverse=True
                )[:6]
            ],
            "recent_tools": [
                {
                    "tool_name": call.get("tool_name"),
                    "created_at": call.get("created_at"),
                    "ok": bool((call.get("output") or {}).get("ok", True)),
                }
                for call in reversed(calls[-8:])
            ],
            "captured_at": _now(),
        }

    def get_study_path(self, session_id: str) -> dict[str, Any] | None:
        s = self._sessions.get(session_id)
        return s.get("study_path") if s else None

    def save_study_path(self, session_id: str, path: dict[str, Any]) -> None:
        s = self._sessions.get(session_id)
        if not s:
            return
        s["study_path"] = path
        s["updated_at"] = _now()
        self._save_sessions()


class CockroachMemoryStore(MemoryStore):
    """CockroachDB 生产存储（需 DATABASE_URL + 已导入数据）。"""

    def __init__(self, dsn: str) -> None:
        import psycopg
        from psycopg.rows import dict_row

        self.dsn = dsn
        self._psycopg = psycopg
        self._dict_row = dict_row

    def _connect(self):
        """每次连接切到 qianhong 库（schema 默认库名）。"""
        conn = self._psycopg.connect(self.dsn, row_factory=self._dict_row)
        try:
            conn.execute("SET DATABASE = qianhong")
        except Exception:
            # 库尚未创建时由 import 脚本负责
            pass
        return conn

    def list_bridges(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT name, dynasty, year, province, city, lon, lat,
                       length, span, width, bridge_type AS type, material,
                       protection, poetry, intro
                FROM bridges ORDER BY year NULLS LAST, name
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def get_bridge_by_name(self, name: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT b.*, b.bridge_type AS type,
                       c.anecdote, c.poetry_refs, c.cultural_insight
                FROM bridges b
                LEFT JOIN bridge_culture c ON c.bridge_id = b.id
                WHERE b.name = %s
                """,
                (name,),
            ).fetchone()
        if not row:
            return None
        out = dict(row)
        if out.get("cultural_insight"):
            out["_culture"] = {
                "anecdote": out.pop("anecdote", None),
                "poetryRefs": out.pop("poetry_refs", None),
                "culturalInsight": out.pop("cultural_insight", None),
            }
        return out

    def search_bridges(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """优先用 bridge_embeddings 向量检索（Distributed Vector Indexing）。"""
        from agent.embeddings import embed_text

        qvec = embed_text(query)
        vec_literal = "[" + ",".join(f"{x:.8f}" for x in qvec) + "]"
        with self._connect() as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT b.name, b.dynasty, b.year, b.province, b.city,
                           b.bridge_type AS type, b.material, b.poetry, b.intro,
                           (e.embedding <=> %s::vector) AS dist
                    FROM bridge_embeddings e
                    JOIN bridges b ON b.id = e.bridge_id
                    ORDER BY e.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vec_literal, vec_literal, limit),
                ).fetchall()
                if rows:
                    out = []
                    for r in rows:
                        item = dict(r)
                        dist = item.pop("dist", None)
                        if dist is not None:
                            try:
                                item["_score"] = 1.0 - float(dist)
                            except (TypeError, ValueError):
                                item["_score"] = 0.0
                        out.append(item)
                    return out
            except Exception:
                # 旧集群 / 无向量算子时回退到应用层余弦
                pass

            from agent.knowledge import cosine

            rows = conn.execute(
                """
                SELECT b.name, b.dynasty, b.year, b.province, b.city,
                       b.bridge_type AS type, b.material, b.poetry, b.intro,
                       e.content_text, e.embedding
                FROM bridge_embeddings e
                JOIN bridges b ON b.id = e.bridge_id
                """
            ).fetchall()
        scored: list[tuple[float, dict[str, Any]]] = []
        for r in rows:
            vec = r["embedding"]
            if vec is None:
                continue
            if isinstance(vec, str):
                vec = [float(x) for x in vec.strip("[]").split(",") if x.strip()]
            s = cosine(qvec, list(vec))
            item = {k: r[k] for k in r if k not in ("content_text", "embedding")}
            item["_score"] = s
            scored.append((s, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            return JsonMemoryStore().search_bridges(query, limit)
        return [x[1] for x in scored[:limit]]

    def create_session(self, focus_bridge: str | None = None) -> dict[str, Any]:
        focus_id = None
        if focus_bridge:
            b = self.get_bridge_by_name(focus_bridge)
            focus_id = b.get("id") if b else None
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO sessions (focus_bridge_id) VALUES (%s)
                RETURNING id, focus_bridge_id, created_at
                """,
                (focus_id,),
            ).fetchone()
            conn.commit()
        return {"id": str(row["id"]), "focus_bridge": focus_bridge}

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT s.id, s.focus_bridge_id, b.name AS focus_bridge, s.created_at
                FROM sessions s
                LEFT JOIN bridges b ON b.id = s.focus_bridge_id
                WHERE s.id = %s
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_session_focus(self, session_id: str, focus_bridge: str | None) -> None:
        focus_id = None
        if focus_bridge:
            b = self.get_bridge_by_name(focus_bridge)
            focus_id = b.get("id") if b else None
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET focus_bridge_id = %s, updated_at = now() WHERE id = %s",
                (focus_id, session_id),
            )
            conn.commit()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        sources: list[str] | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO messages (session_id, role, content, sources, mode)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, role, content, sources, mode, created_at
                """,
                (session_id, role, content, sources or [], mode),
            ).fetchone()
            conn.execute(
                "UPDATE sessions SET updated_at = now() WHERE id = %s",
                (session_id,),
            )
            conn.commit()
        out = dict(row)
        out["sources"] = list(out.get("sources") or [])
        return out

    def get_messages(self, session_id: str, limit: int = 40) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, sources, mode, created_at
                FROM messages WHERE session_id = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (session_id, limit),
            ).fetchall()
        rows.reverse()
        return [dict(r) for r in rows]

    def get_user_memory(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary, interests, updated_at FROM user_memory WHERE session_id = %s",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def upsert_user_memory(
        self, session_id: str, summary: str, interests: list[str]
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_memory (session_id, summary, interests, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (session_id) DO UPDATE SET
                  summary = EXCLUDED.summary,
                  interests = EXCLUDED.interests,
                  updated_at = now()
                """,
                (session_id, summary, interests),
            )
            conn.commit()

    def log_tool_call(
        self,
        session_id: str | None,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tool_calls (session_id, tool_name, input, output)
                VALUES (%s, %s, %s::jsonb, %s::jsonb)
                """,
                (
                    session_id,
                    tool_name,
                    json.dumps(input_data, ensure_ascii=False),
                    json.dumps(output_data, ensure_ascii=False),
                ),
            )
            conn.commit()

    def record_event(
        self,
        session_id: str,
        event_type: str,
        source: str,
        *,
        bridge: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "event_type": event_type,
            "source": source,
            "bridge": bridge,
            "meta": meta or {},
        }
        self.log_tool_call(session_id, "exploration_event", payload, {"ok": True})
        if bridge:
            self.update_session_focus(session_id, bridge)
        bridge_id = None
        if bridge:
            b = self.get_bridge_by_name(bridge)
            bridge_id = b.get("id") if b else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO exploration_events
                  (session_id, event_type, source, bridge_id, bridge_name, meta)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    session_id,
                    event_type,
                    source,
                    bridge_id,
                    bridge,
                    json.dumps(meta or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        return {"session_id": session_id, **payload, "created_at": _now()}

    def get_events(self, session_id: str, limit: int = 30) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type, source, bridge_name AS bridge, meta, created_at
                FROM exploration_events
                WHERE session_id = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (session_id, limit),
            ).fetchall()
        rows.reverse()
        out: list[dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            item["created_at"] = str(item.get("created_at", ""))
            out.append(item)
        return out

    def memory_ops_snapshot(self) -> dict[str, Any]:
        with self._connect() as conn:
            count_row = conn.execute(
                """
                SELECT
                  (SELECT count(*) FROM bridges) AS bridges,
                  (SELECT count(*) FROM bridge_embeddings) AS embeddings,
                  (SELECT count(*) FROM sessions) AS sessions,
                  (SELECT count(*) FROM messages) AS messages,
                  (SELECT count(*) FROM exploration_events) AS events,
                  (SELECT count(*) FROM user_memory) AS memories,
                  (SELECT count(*) FROM agent_tasks) AS tasks,
                  (SELECT count(*) FROM tool_calls) AS tool_calls
                """
            ).fetchone()
            event_rows = conn.execute(
                """
                SELECT event_type AS name, count(*) AS count
                FROM exploration_events
                GROUP BY event_type
                ORDER BY count DESC, event_type
                LIMIT 6
                """
            ).fetchall()
            tool_rows = conn.execute(
                """
                SELECT tool_name AS name, count(*) AS count
                FROM tool_calls
                GROUP BY tool_name
                ORDER BY count DESC, tool_name
                LIMIT 6
                """
            ).fetchall()
            recent_rows = conn.execute(
                """
                SELECT tool_name, created_at,
                       COALESCE((output->>'ok')::BOOL, true) AS ok
                FROM tool_calls
                ORDER BY created_at DESC
                LIMIT 8
                """
            ).fetchall()
            try:
                index_row = conn.execute(
                    """
                    SELECT index_name
                    FROM [SHOW INDEXES FROM bridge_embeddings]
                    WHERE index_name = 'idx_bridge_embeddings_vector'
                    LIMIT 1
                    """
                ).fetchone()
            except Exception:
                index_row = None

        counts = {key: int(value or 0) for key, value in dict(count_row).items()}
        recent_tools = []
        for row in recent_rows:
            item = dict(row)
            item["created_at"] = str(item.get("created_at", ""))
            item["ok"] = bool(item.get("ok"))
            recent_tools.append(item)
        return {
            "backend": "cockroach",
            "counts": counts,
            "vector_index": {
                "active": bool(index_row),
                "name": index_row["index_name"] if index_row else None,
            },
            "event_types": [
                {"name": row["name"], "count": int(row["count"])}
                for row in event_rows
            ],
            "tool_usage": [
                {"name": row["name"], "count": int(row["count"])}
                for row in tool_rows
            ],
            "recent_tools": recent_tools,
            "captured_at": _now(),
        }

    def get_study_path(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload FROM agent_tasks
                WHERE session_id = %s AND task_type = 'study_path'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        if not row:
            return None
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return payload

    def save_study_path(self, session_id: str, path: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_tasks (session_id, task_type, status, payload, step)
                VALUES (%s, 'study_path', %s, %s::jsonb, %s)
                """,
                (
                    session_id,
                    path.get("status", "in_progress"),
                    json.dumps(path, ensure_ascii=False),
                    path.get("current_step", 0),
                ),
            )
            conn.commit()


def get_store() -> MemoryStore:
    if settings.storage_mode == "cockroach" and settings.database_url:
        return CockroachMemoryStore(settings.database_url)
    return JsonMemoryStore()
