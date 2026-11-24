"""SQLite-backed Event Stream & LLM Trace store.

Replaces browser-local IndexedDB DOM scraping with an authoritative,
chronologically ordered backend store that survives reloads, powers range
exports and timeline scrubbing, and keeps heavy LLM prompt/response payloads
in a separate ``llm_traces`` table linked by ``request_id``.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

_NON_ACTOR_LABELS = frozenset({"think-decide", "result-reaction", "intermediator", "plan", "plan-repair"})


class StreamStore:
    """Thread-safe SQLite store for simulation stream events and LLM traces."""

    def __init__(self, db_path: str = "saves/event_stream.db") -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            parent = os.path.dirname(os.path.abspath(db_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;

                CREATE TABLE IF NOT EXISTS stream_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    world_id TEXT NOT NULL DEFAULT 'default',
                    branch_id TEXT NOT NULL DEFAULT 'main',
                    tick INTEGER NOT NULL DEFAULT 0,
                    game_time TEXT NOT NULL DEFAULT '',
                    turn_id TEXT,
                    actor TEXT NOT NULL DEFAULT 'World',
                    area TEXT,
                    kind TEXT NOT NULL,
                    phase TEXT,
                    outcome TEXT,
                    request_id TEXT,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_stream_world_seq
                    ON stream_events (world_id, seq);
                CREATE INDEX IF NOT EXISTS idx_stream_world_tick
                    ON stream_events (world_id, tick);
                CREATE INDEX IF NOT EXISTS idx_stream_world_actor
                    ON stream_events (world_id, actor);
                CREATE INDEX IF NOT EXISTS idx_stream_world_kind
                    ON stream_events (world_id, kind);
                CREATE INDEX IF NOT EXISTS idx_stream_world_area
                    ON stream_events (world_id, area);

                CREATE TABLE IF NOT EXISTS llm_traces (
                    request_id TEXT PRIMARY KEY,
                    world_id TEXT NOT NULL DEFAULT 'default',
                    tick INTEGER NOT NULL DEFAULT 0,
                    actor TEXT NOT NULL DEFAULT '',
                    phase TEXT NOT NULL DEFAULT '',
                    prompt TEXT NOT NULL DEFAULT '',
                    response TEXT NOT NULL DEFAULT '',
                    tokens_in INTEGER NOT NULL DEFAULT 0,
                    tokens_out INTEGER NOT NULL DEFAULT 0,
                    latency_ms INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_traces_world_tick
                    ON llm_traces (world_id, tick);
                """
            )
            # Safe migration for existing event_stream.db files created before branch_id
            cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(stream_events)").fetchall()}
            if "branch_id" not in cols:
                self._conn.execute("ALTER TABLE stream_events ADD COLUMN branch_id TEXT NOT NULL DEFAULT 'main'")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_stream_world_branch ON stream_events (world_id, branch_id, seq)")
            self._conn.commit()

    def append_event(
        self,
        *,
        kind: str,
        actor: str = "World",
        tick: int = 0,
        game_time: str = "",
        turn_id: Optional[str] = None,
        area: Optional[str] = None,
        phase: Optional[str] = None,
        outcome: Optional[str] = None,
        request_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        world_id: str = "default",
        branch_id: str = "main",
    ) -> Dict[str, Any]:
        now = time.time()
        payload_dict = payload if isinstance(payload, dict) else {}
        payload_json = json.dumps(payload_dict, ensure_ascii=False)
        clean_actor = str(actor or "World").strip() or "World"
        clean_branch = str(branch_id or "main").strip() or "main"
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO stream_events
                    (world_id, branch_id, tick, game_time, turn_id, actor, area, kind, phase, outcome, request_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    world_id,
                    clean_branch,
                    int(tick or 0),
                    str(game_time or ""),
                    turn_id,
                    clean_actor,
                    area,
                    str(kind),
                    phase,
                    outcome,
                    request_id,
                    payload_json,
                    now,
                ),
            )
            seq = int(cur.lastrowid)
            self._conn.commit()
        return {
            "seq": seq,
            "world_id": world_id,
            "branch_id": clean_branch,
            "tick": int(tick or 0),
            "game_time": str(game_time or ""),
            "turn_id": turn_id,
            "actor": clean_actor,
            "area": area,
            "kind": str(kind),
            "phase": phase,
            "outcome": outcome,
            "request_id": request_id,
            "payload": payload_dict,
            "created_at": now,
        }

    def append_events_batch(
        self,
        events: List[Dict[str, Any]],
        *,
        world_id: str = "default",
        branch_id: str = "main",
    ) -> List[Dict[str, Any]]:
        """Append multiple events in a single SQLite transaction."""
        out: List[Dict[str, Any]] = []
        now = time.time()
        default_branch = str(branch_id or "main").strip() or "main"
        with self._lock:
            for item in events:
                if not isinstance(item, dict) or not item.get("kind"):
                    continue
                payload_dict = item.get("payload") if isinstance(item.get("payload"), dict) else {}
                payload_json = json.dumps(payload_dict, ensure_ascii=False)
                clean_actor = str(item.get("actor") or "World").strip() or "World"
                wid = str(item.get("world_id") or world_id)
                bid = str(item.get("branch_id") or default_branch).strip() or default_branch
                cur = self._conn.execute(
                    """
                    INSERT INTO stream_events
                        (world_id, branch_id, tick, game_time, turn_id, actor, area, kind, phase, outcome, request_id, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        wid,
                        bid,
                        int(item.get("tick", 0) or 0),
                        str(item.get("game_time") or ""),
                        item.get("turn_id"),
                        clean_actor,
                        item.get("area"),
                        str(item["kind"]),
                        item.get("phase"),
                        item.get("outcome"),
                        item.get("request_id"),
                        payload_json,
                        now,
                    ),
                )
                out.append(
                    {
                        "seq": int(cur.lastrowid),
                        "world_id": wid,
                        "branch_id": bid,
                        "tick": int(item.get("tick", 0) or 0),
                        "game_time": str(item.get("game_time") or ""),
                        "turn_id": item.get("turn_id"),
                        "actor": clean_actor,
                        "area": item.get("area"),
                        "kind": str(item["kind"]),
                        "phase": item.get("phase"),
                        "outcome": item.get("outcome"),
                        "request_id": item.get("request_id"),
                        "payload": payload_dict,
                        "created_at": now,
                    }
                )
            self._conn.commit()
        return out

    def query_events(
        self,
        *,
        world_id: str = "default",
        branch_id: Optional[str] = None,
        limit: int = 500,
        before_seq: Optional[int] = None,
        after_seq: Optional[int] = None,
        actor: Optional[str] = None,
        kind: Optional[str] = None,
        area: Optional[str] = None,
        tick_from: Optional[int] = None,
        tick_to: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses = ["world_id = ?"]
        params: List[Any] = [world_id]
        if branch_id:
            clauses.append("branch_id = ?")
            params.append(branch_id)
        if before_seq is not None:
            clauses.append("seq < ?")
            params.append(int(before_seq))
        if after_seq is not None:
            clauses.append("seq > ?")
            params.append(int(after_seq))
        if actor:
            clauses.append("actor = ?")
            params.append(actor)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if area:
            clauses.append("area = ?")
            params.append(area)
        if tick_from is not None:
            clauses.append("tick >= ?")
            params.append(int(tick_from))
        if tick_to is not None:
            clauses.append("tick <= ?")
            params.append(int(tick_to))
        if search:
            clauses.append("(payload_json LIKE ? OR actor LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])

        where_sql = " AND ".join(clauses)
        safe_limit = max(1, min(5000, int(limit or 500)))
        sql = f"""
            SELECT * FROM (
                SELECT * FROM stream_events
                WHERE {where_sql}
                ORDER BY seq DESC
                LIMIT ?
            ) sub
            ORDER BY seq ASC
        """
        params.append(safe_limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_event(r) for r in rows]

    def list_actors(self, *, world_id: str = "default") -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT actor FROM stream_events WHERE world_id = ? ORDER BY actor ASC",
                (world_id,),
            ).fetchall()
        return [r["actor"] for r in rows if r["actor"] and r["actor"].lower() not in _NON_ACTOR_LABELS]

    def save_llm_trace(
        self,
        *,
        request_id: str,
        actor: str = "",
        phase: str = "",
        prompt: str = "",
        response: str = "",
        tick: int = 0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
        world_id: str = "default",
    ) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO llm_traces
                    (request_id, world_id, tick, actor, phase, prompt, response, tokens_in, tokens_out, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    world_id,
                    int(tick or 0),
                    str(actor or ""),
                    str(phase or ""),
                    str(prompt or ""),
                    str(response or ""),
                    int(tokens_in or 0),
                    int(tokens_out or 0),
                    int(latency_ms or 0),
                    now,
                ),
            )
            self._conn.commit()
        return {
            "request_id": request_id,
            "world_id": world_id,
            "tick": int(tick or 0),
            "actor": str(actor or ""),
            "phase": str(phase or ""),
            "tokens_in": int(tokens_in or 0),
            "tokens_out": int(tokens_out or 0),
            "latency_ms": int(latency_ms or 0),
            "created_at": now,
        }

    def get_llm_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM llm_traces WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return dict(row) if row else None

    def query_branch_lineage(
        self,
        *,
        world_id: str = "default",
        ancestry: List[Dict[str, Any]],
        limit: int = 500,
        before_seq: Optional[int] = None,
        after_seq: Optional[int] = None,
        actor: Optional[str] = None,
        kind: Optional[str] = None,
        area: Optional[str] = None,
        tick_from: Optional[int] = None,
        tick_to: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query events walking root-to-leaf branch ancestry without sibling contamination."""
        if not ancestry:
            return self.query_events(
                world_id=world_id,
                branch_id="main",
                limit=limit,
                before_seq=before_seq,
                after_seq=after_seq,
                actor=actor,
                kind=kind,
                area=area,
                tick_from=tick_from,
                tick_to=tick_to,
                search=search,
            )
        seg_clauses: List[str] = []
        params: List[Any] = [world_id]
        for seg in ancestry:
            bid = str(seg.get("branch_id") or "main")
            sub = ["branch_id = ?"]
            params.append(bid)
            if seg.get("max_tick") is not None:
                sub.append("tick <= ?")
                params.append(int(seg["max_tick"]))
            if seg.get("max_seq") is not None:
                sub.append("seq <= ?")
                params.append(int(seg["max_seq"]))
            seg_clauses.append("(" + " AND ".join(sub) + ")")

        clauses = ["world_id = ?", "(" + " OR ".join(seg_clauses) + ")"]
        if before_seq is not None:
            clauses.append("seq < ?")
            params.append(int(before_seq))
        if after_seq is not None:
            clauses.append("seq > ?")
            params.append(int(after_seq))
        if actor:
            clauses.append("actor = ?")
            params.append(actor)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if area:
            clauses.append("area = ?")
            params.append(area)
        if tick_from is not None:
            clauses.append("tick >= ?")
            params.append(int(tick_from))
        if tick_to is not None:
            clauses.append("tick <= ?")
            params.append(int(tick_to))
        if search:
            clauses.append("(payload_json LIKE ? OR actor LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])

        where_sql = " AND ".join(clauses)
        safe_limit = max(1, min(5000, int(limit or 500)))
        sql = f"""
            SELECT * FROM (
                SELECT * FROM stream_events
                WHERE {where_sql}
                ORDER BY seq DESC
                LIMIT ?
            ) sub
            ORDER BY seq ASC
        """
        params.append(safe_limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_event(r) for r in rows]

    def clear_branch(
        self,
        *,
        world_id: str = "default",
        branch_id: str = "main",
        from_tick: Optional[int] = None,
    ) -> int:
        """Clear events belonging ONLY to ``branch_id`` (optionally from ``from_tick`` onward)."""
        clean_branch = str(branch_id or "main").strip() or "main"
        with self._lock:
            if from_tick is not None:
                cur = self._conn.execute(
                    "DELETE FROM stream_events WHERE world_id = ? AND branch_id = ? AND tick >= ?",
                    (world_id, clean_branch, int(from_tick)),
                )
            else:
                cur = self._conn.execute(
                    "DELETE FROM stream_events WHERE world_id = ? AND branch_id = ?",
                    (world_id, clean_branch),
                )
            self._conn.commit()
            return int(cur.rowcount)

    def clear_world(self, *, world_id: str = "default") -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM stream_events WHERE world_id = ?", (world_id,))
            self._conn.execute("DELETE FROM llm_traces WHERE world_id = ?", (world_id,))
            self._conn.commit()
            return int(cur.rowcount)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Dict[str, Any]:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except Exception:
            payload = {}
        return {
            "seq": row["seq"],
            "world_id": row["world_id"],
            "branch_id": row["branch_id"] if "branch_id" in row.keys() else "main",
            "tick": row["tick"],
            "game_time": row["game_time"],
            "turn_id": row["turn_id"],
            "actor": row["actor"],
            "area": row["area"],
            "kind": row["kind"],
            "phase": row["phase"],
            "outcome": row["outcome"],
            "request_id": row["request_id"],
            "payload": payload,
            "created_at": row["created_at"],
        }
