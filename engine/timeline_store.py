"""SQLite-backed storage for Scenario Timeline branches and compressed checkpoints (task-1008).

Stores branch metadata and zlib-compressed world JSON checkpoints in WAL-mode SQLite
(default ``saves/timeline.db``) so multi-month timelines survive reloads and restarts
without bloating scenario JSON files.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import zlib
from typing import Any, Dict, List, Optional


class TimelineStore:
    """Thread-safe SQLite persistence for TimelineManager branches and checkpoints."""

    def __init__(self, db_path: str = "saves/timeline.db") -> None:
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

                CREATE TABLE IF NOT EXISTS timeline_meta (
                    world_id TEXT PRIMARY KEY,
                    active_branch_id TEXT NOT NULL DEFAULT 'main',
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS timeline_branches (
                    world_id TEXT NOT NULL,
                    branch_id TEXT NOT NULL,
                    parent_branch_id TEXT,
                    label TEXT NOT NULL DEFAULT 'Main',
                    fork_tick INTEGER NOT NULL DEFAULT 0,
                    fork_seq INTEGER,
                    fork_datetime TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    PRIMARY KEY (world_id, branch_id)
                );

                CREATE TABLE IF NOT EXISTS timeline_checkpoints (
                    world_id TEXT NOT NULL,
                    branch_id TEXT NOT NULL,
                    tick INTEGER NOT NULL,
                    snapshot_zlib BLOB NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (world_id, branch_id, tick)
                );

                CREATE INDEX IF NOT EXISTS idx_tl_cp_lookup
                    ON timeline_checkpoints (world_id, branch_id, tick);
                """
            )
            self._conn.commit()

    @staticmethod
    def _pack(snapshot: Dict[str, Any]) -> bytes:
        raw = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return zlib.compress(raw, level=6)

    @staticmethod
    def _unpack(blob: bytes) -> Dict[str, Any]:
        raw = zlib.decompress(blob).decode("utf-8")
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}

    def set_active_branch(self, world_id: str, branch_id: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO timeline_meta (world_id, active_branch_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(world_id) DO UPDATE SET
                    active_branch_id = excluded.active_branch_id,
                    updated_at = excluded.updated_at
                """,
                (world_id, branch_id, time.time()),
            )
            self._conn.commit()

    def get_active_branch(self, world_id: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT active_branch_id FROM timeline_meta WHERE world_id = ?",
                (world_id,),
            ).fetchone()
        return str(row["active_branch_id"]) if row else "main"

    def save_branch(
        self,
        *,
        world_id: str,
        branch_id: str,
        parent_branch_id: Optional[str],
        label: str,
        fork_tick: int,
        fork_seq: Optional[int],
        fork_datetime: str,
        created_at: float,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO timeline_branches
                    (world_id, branch_id, parent_branch_id, label, fork_tick, fork_seq, fork_datetime, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(world_id, branch_id) DO UPDATE SET
                    parent_branch_id = excluded.parent_branch_id,
                    label = excluded.label,
                    fork_tick = excluded.fork_tick,
                    fork_seq = excluded.fork_seq,
                    fork_datetime = excluded.fork_datetime
                """,
                (
                    world_id,
                    branch_id,
                    parent_branch_id,
                    label,
                    int(fork_tick),
                    int(fork_seq) if fork_seq is not None else None,
                    str(fork_datetime or ""),
                    float(created_at),
                ),
            )
            self._conn.commit()

    def list_branches(self, world_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM timeline_branches WHERE world_id = ? ORDER BY created_at ASC",
                (world_id,),
            ).fetchall()
            out: List[Dict[str, Any]] = []
            for r in rows:
                cp_rows = self._conn.execute(
                    "SELECT tick FROM timeline_checkpoints WHERE world_id = ? AND branch_id = ? ORDER BY tick ASC",
                    (world_id, r["branch_id"]),
                ).fetchall()
                out.append(
                    {
                        "branch_id": r["branch_id"],
                        "parent_branch_id": r["parent_branch_id"],
                        "label": r["label"],
                        "fork_tick": int(r["fork_tick"]),
                        "fork_seq": r["fork_seq"],
                        "fork_datetime": r["fork_datetime"],
                        "created_at": float(r["created_at"]),
                        "checkpoint_ticks": [int(c["tick"]) for c in cp_rows],
                    }
                )
            return out

    def save_checkpoint(self, world_id: str, branch_id: str, tick: int, snapshot: Dict[str, Any]) -> None:
        blob = self._pack(snapshot)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO timeline_checkpoints (world_id, branch_id, tick, snapshot_zlib, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(world_id, branch_id, tick) DO UPDATE SET
                    snapshot_zlib = excluded.snapshot_zlib,
                    updated_at = excluded.updated_at
                """,
                (world_id, branch_id, int(tick), blob, time.time()),
            )
            self._conn.commit()

    def load_checkpoint(self, world_id: str, branch_id: str, tick: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT snapshot_zlib FROM timeline_checkpoints WHERE world_id = ? AND branch_id = ? AND tick = ?",
                (world_id, branch_id, int(tick)),
            ).fetchone()
        return self._unpack(row["snapshot_zlib"]) if row else None

    def load_nearest_checkpoint(self, world_id: str, branch_id: str, max_tick: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT snapshot_zlib FROM timeline_checkpoints
                WHERE world_id = ? AND branch_id = ? AND tick <= ?
                ORDER BY tick DESC LIMIT 1
                """,
                (world_id, branch_id, int(max_tick)),
            ).fetchone()
        return self._unpack(row["snapshot_zlib"]) if row else None

    def load_latest_checkpoint(self, world_id: str, branch_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT snapshot_zlib FROM timeline_checkpoints
                WHERE world_id = ? AND branch_id = ?
                ORDER BY tick DESC LIMIT 1
                """,
                (world_id, branch_id),
            ).fetchone()
        return self._unpack(row["snapshot_zlib"]) if row else None

    def shift_ticks(self, world_id: str, delta_ticks: int) -> None:
        """Offset all stored branch fork_ticks and checkpoint ticks by ``delta_ticks``."""
        if not delta_ticks:
            return
        with self._lock:
            self._conn.execute(
                "UPDATE timeline_branches SET fork_tick = fork_tick + ? WHERE world_id = ?",
                (int(delta_ticks), world_id),
            )
            # Shift checkpoints in descending order to avoid PK collisions on positive delta
            rows = self._conn.execute(
                "SELECT branch_id, tick, snapshot_zlib, updated_at FROM timeline_checkpoints WHERE world_id = ?",
                (world_id,),
            ).fetchall()
            self._conn.execute("DELETE FROM timeline_checkpoints WHERE world_id = ?", (world_id,))
            for r in rows:
                self._conn.execute(
                    """
                    INSERT INTO timeline_checkpoints (world_id, branch_id, tick, snapshot_zlib, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (world_id, r["branch_id"], int(r["tick"]) + int(delta_ticks), r["snapshot_zlib"], r["updated_at"]),
                )
            self._conn.commit()

    def clear_world(self, world_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM timeline_checkpoints WHERE world_id = ?", (world_id,))
            self._conn.execute("DELETE FROM timeline_branches WHERE world_id = ?", (world_id,))
            self._conn.execute("DELETE FROM timeline_meta WHERE world_id = ?", (world_id,))
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
