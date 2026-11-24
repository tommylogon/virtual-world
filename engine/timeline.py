"""Scenario Timeline & Branching Engine (task-980, Phase 3).

Manages a tree of isolated scenario branches (``main`` + forked branches),
per-tick world snapshots for rewinding, and decision-redo forking so players
and authors can rewind to any past turn, fork a branch, and redo a character's
decision without contaminating sibling branches or leaking future memories.
"""
from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TimelineBranch:
    branch_id: str
    parent_branch_id: Optional[str] = None
    label: str = "Main"
    fork_tick: int = 0
    fork_seq: Optional[int] = None
    fork_datetime: str = ""
    created_at: float = field(default_factory=time.time)
    # Latest serialized world snapshot for this branch (and optional tick checkpoints)
    snapshot: Optional[Dict[str, Any]] = None
    checkpoints: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def to_summary(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "parent_branch_id": self.parent_branch_id,
            "label": self.label,
            "fork_tick": self.fork_tick,
            "fork_seq": self.fork_seq,
            "fork_datetime": self.fork_datetime,
            "created_at": self.created_at,
            "checkpoint_ticks": sorted(self.checkpoints.keys()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "parent_branch_id": self.parent_branch_id,
            "label": self.label,
            "fork_tick": self.fork_tick,
            "fork_seq": self.fork_seq,
            "fork_datetime": self.fork_datetime,
            "created_at": self.created_at,
            "snapshot": self.snapshot,
            "checkpoints": {str(k): v for k, v in self.checkpoints.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineBranch":
        raw_cp = data.get("checkpoints") or {}
        checkpoints = {int(k): v for k, v in raw_cp.items() if str(k).lstrip("-").isdigit()}
        return cls(
            branch_id=str(data.get("branch_id") or "main"),
            parent_branch_id=data.get("parent_branch_id"),
            label=str(data.get("label") or "Main"),
            fork_tick=int(data.get("fork_tick", 0) or 0),
            fork_seq=data.get("fork_seq"),
            fork_datetime=str(data.get("fork_datetime") or ""),
            created_at=float(data.get("created_at", time.time()) or time.time()),
            snapshot=data.get("snapshot"),
            checkpoints=checkpoints,
        )


class TimelineManager:
    """Authoritative scenario branch graph and decision-redo coordinator."""

    def __init__(self, *, store: Any = None, world_id: str = "default") -> None:
        self.active_branch_id: str = "main"
        self.branches: Dict[str, TimelineBranch] = {
            "main": TimelineBranch(branch_id="main", parent_branch_id=None, label="Main")
        }
        self._store: Any = store
        self._world_id: str = str(world_id or "default")

    def attach_store(self, store: Any, world_id: str = "default", *, hydrate: bool = True) -> None:
        """Attach a SQLite TimelineStore for compressed checkpoint persistence (task-1008)."""
        self._store = store
        self._world_id = str(world_id or "default")
        if store is None or not hydrate:
            return
        rows = store.list_branches(self._world_id)
        if rows:
            loaded: Dict[str, TimelineBranch] = {}
            for r in rows:
                bid = str(r["branch_id"])
                latest_snap = store.load_latest_checkpoint(self._world_id, bid)
                b = TimelineBranch(
                    branch_id=bid,
                    parent_branch_id=r.get("parent_branch_id"),
                    label=str(r.get("label") or "Main"),
                    fork_tick=int(r.get("fork_tick", 0) or 0),
                    fork_seq=r.get("fork_seq"),
                    fork_datetime=str(r.get("fork_datetime") or ""),
                    created_at=float(r.get("created_at", time.time()) or time.time()),
                    snapshot=latest_snap,
                )
                # Populate checkpoint tick keys lazily (None values hydrated on demand from SQLite)
                for t in (r.get("checkpoint_ticks") or []):
                    b.checkpoints[int(t)] = latest_snap if (latest_snap and int(t) == max(r["checkpoint_ticks"])) else {}
                loaded[bid] = b
            if "main" not in loaded:
                loaded["main"] = TimelineBranch(branch_id="main", label="Main")
            self.branches = loaded
            active = store.get_active_branch(self._world_id)
            self.active_branch_id = active if active in self.branches else "main"

    def _persist_branch_meta(self, branch: TimelineBranch) -> None:
        if self._store is None:
            return
        try:
            self._store.save_branch(
                world_id=self._world_id,
                branch_id=branch.branch_id,
                parent_branch_id=branch.parent_branch_id,
                label=branch.label,
                fork_tick=branch.fork_tick,
                fork_seq=branch.fork_seq,
                fork_datetime=branch.fork_datetime,
                created_at=branch.created_at,
            )
            self._store.set_active_branch(self._world_id, self.active_branch_id)
        except Exception:
            pass

    @property
    def active_branch(self) -> TimelineBranch:
        if self.active_branch_id not in self.branches:
            self.branches["main"] = TimelineBranch(branch_id="main", label="Main")
            self.active_branch_id = "main"
        return self.branches[self.active_branch_id]

    def record_checkpoint(self, tick: int, snapshot: Dict[str, Any], *, branch_id: Optional[str] = None) -> None:
        """Record an isolated deep-copy world snapshot for ``tick`` on a branch."""
        bid = branch_id or self.active_branch_id
        branch = self.branches.get(bid)
        if branch is None:
            return
        snap_copy = copy.deepcopy(snapshot)
        branch.snapshot = snap_copy
        branch.checkpoints[int(tick)] = snap_copy
        if self._store is not None:
            try:
                self._persist_branch_meta(branch)
                self._store.save_checkpoint(self._world_id, bid, int(tick), snap_copy)
            except Exception:
                pass

    def _find_checkpoint_at_or_before(self, branch_id: str, tick: int) -> Optional[Dict[str, Any]]:
        """Walk up the branch ancestry to find the nearest checkpoint <= tick."""
        visited = set()
        cur_id: Optional[str] = branch_id
        while cur_id and cur_id not in visited:
            visited.add(cur_id)
            branch = self.branches.get(cur_id)
            if branch is None:
                break
            eligible = [t for t in branch.checkpoints.keys() if t <= tick]
            if eligible:
                best_t = max(eligible)
                snap = branch.checkpoints[best_t]
                if (not snap) and self._store is not None:
                    snap = self._store.load_checkpoint(self._world_id, cur_id, best_t) or {}
                    if snap:
                        branch.checkpoints[best_t] = snap
                if snap:
                    return copy.deepcopy(snap)
            if self._store is not None:
                db_snap = self._store.load_nearest_checkpoint(self._world_id, cur_id, int(tick))
                if db_snap:
                    return copy.deepcopy(db_snap)
            if branch.snapshot is not None and branch.fork_tick <= tick:
                return copy.deepcopy(branch.snapshot)
            cur_id = branch.parent_branch_id
        return None

    def fork_branch(
        self,
        *,
        label: str = "",
        from_branch_id: Optional[str] = None,
        fork_tick: int = 0,
        fork_seq: Optional[int] = None,
        fork_datetime: str = "",
        snapshot: Optional[Dict[str, Any]] = None,
        switch: bool = True,
    ) -> TimelineBranch:
        """Create a new isolated branch forked from ``from_branch_id`` at ``fork_tick``."""
        parent_id = from_branch_id or self.active_branch_id
        if parent_id not in self.branches:
            parent_id = "main"
        new_id = f"branch_{uuid.uuid4().hex[:8]}"
        snap = copy.deepcopy(snapshot) if snapshot is not None else self._find_checkpoint_at_or_before(parent_id, int(fork_tick))
        branch = TimelineBranch(
            branch_id=new_id,
            parent_branch_id=parent_id,
            label=label.strip() or f"Fork @ Tick {fork_tick}",
            fork_tick=int(fork_tick),
            fork_seq=fork_seq,
            fork_datetime=str(fork_datetime or ""),
            snapshot=snap,
        )
        if snap is not None:
            branch.checkpoints[int(fork_tick)] = copy.deepcopy(snap)
        self.branches[new_id] = branch
        if switch:
            self.active_branch_id = new_id
        if self._store is not None:
            self._persist_branch_meta(branch)
            if snap is not None:
                try:
                    self._store.save_checkpoint(self._world_id, new_id, int(fork_tick), snap)
                except Exception:
                    pass
        return branch

    def switch_branch(self, branch_id: str) -> TimelineBranch:
        """Switch the active branch and return it (with its latest snapshot)."""
        if branch_id not in self.branches:
            raise KeyError(f"Unknown branch: {branch_id}")
        self.active_branch_id = branch_id
        branch = self.branches[branch_id]
        if (not branch.snapshot) and self._store is not None:
            branch.snapshot = self._store.load_latest_checkpoint(self._world_id, branch_id)
        if self._store is not None:
            try:
                self._store.set_active_branch(self._world_id, branch_id)
            except Exception:
                pass
        return branch

    def redo_decision(
        self,
        *,
        character: str,
        at_tick: int,
        at_seq: Optional[int] = None,
        label: str = "",
        from_branch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fork a clean sibling branch right before ``character``'s decision at ``at_tick``."""
        parent_id = from_branch_id or self.active_branch_id
        fork_seq = (int(at_seq) - 1) if (at_seq is not None and int(at_seq) > 0) else None
        branch_label = label.strip() or f"Redo {character} @ Tick {at_tick}"
        branch = self.fork_branch(
            label=branch_label,
            from_branch_id=parent_id,
            fork_tick=int(at_tick),
            fork_seq=fork_seq,
            switch=True,
        )
        return {
            "branch": branch.to_summary(),
            "character": character,
            "restore_snapshot": branch.snapshot,
            "fork_seq": fork_seq,
        }

    def list_branches(self) -> List[Dict[str, Any]]:
        return [b.to_summary() for b in self.branches.values()]

    def get_ancestry(self, branch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return root-to-leaf lineage segments for ``branch_id``.

        Each segment has ``{"branch_id": str, "max_tick": Optional[int], "max_seq": Optional[int]}``.
        Ancestor segments are capped at the child's ``fork_tick`` / ``fork_seq``;
        the leaf segment has ``max_tick=None`` (unless clamped by caller ``tick_to``).
        """
        target_id = branch_id or self.active_branch_id
        if target_id not in self.branches:
            target_id = "main"
        chain: List[TimelineBranch] = []
        visited = set()
        cur_id: Optional[str] = target_id
        while cur_id and cur_id not in visited:
            visited.add(cur_id)
            b = self.branches.get(cur_id)
            if b is None:
                break
            chain.append(b)
            cur_id = b.parent_branch_id
        chain.reverse()
        if not chain:
            return [{"branch_id": "main", "max_tick": None, "max_seq": None}]

        segments: List[Dict[str, Any]] = []
        for idx, b in enumerate(chain):
            if idx + 1 < len(chain):
                child = chain[idx + 1]
                segments.append({
                    "branch_id": b.branch_id,
                    "max_tick": int(child.fork_tick),
                    "max_seq": int(child.fork_seq) if child.fork_seq is not None else None,
                })
            else:
                segments.append({
                    "branch_id": b.branch_id,
                    "max_tick": None,
                    "max_seq": None,
                })
        return segments

    def reset_for_world(self, world: Any = None, *, clear_store: bool = False) -> None:
        """Reset to a clean ``main`` branch and seed the initial checkpoint if ``world`` is given."""
        self.active_branch_id = "main"
        self.branches = {
            "main": TimelineBranch(branch_id="main", parent_branch_id=None, label="Main")
        }
        if clear_store and self._store is not None:
            try:
                self._store.clear_world(self._world_id)
            except Exception:
                pass
        if world is not None:
            tick = int(getattr(world, "time_ticks", 0) or 0)
            snap = snapshot_for_timeline(world)
            if snap:
                self.record_checkpoint(tick, snap, branch_id="main")

    def serialize(self) -> Dict[str, Any]:
        return {
            "active_branch_id": self.active_branch_id,
            "branches": {bid: b.to_dict() for bid, b in self.branches.items()},
        }

    def load(self, data: Optional[Dict[str, Any]]) -> None:
        if not isinstance(data, dict):
            return
        raw_branches = data.get("branches") or {}
        if isinstance(raw_branches, dict) and raw_branches:
            self.branches = {
                str(bid): TimelineBranch.from_dict(bdata)
                for bid, bdata in raw_branches.items()
                if isinstance(bdata, dict)
            }
        if "main" not in self.branches:
            self.branches["main"] = TimelineBranch(branch_id="main", label="Main")
        active = str(data.get("active_branch_id") or "main")
        self.active_branch_id = active if active in self.branches else "main"


_STRIP_SNAPSHOT_KEYS = ("timeline", "areas", "rooms", "areas_by_id", "_save_metadata")


def snapshot_for_timeline(world: Any) -> Dict[str, Any]:
    """Capture a compact, non-recursive runtime snapshot of ``world`` for timeline checkpoints."""
    if world is None or not hasattr(world, "to_dict"):
        return {}
    # Sync any direct Player mutations (e.g. current_area or persona fields) onto
    # authoritative graph nodes/edges before capturing to_dict(), matching to_scenario_dict().
    pm = getattr(world, "player_manager", None)
    graph = getattr(world, "graph", None)
    if pm is not None and graph is not None and hasattr(pm, "players"):
        try:
            from engine.serialization import sync_player_to_node
            for pname, p in pm.players.items():
                pnode_id = pm.player_node_id(pname)
                node = graph.get_node(pnode_id)
                if node is not None:
                    sync_player_to_node(p, node)
                cur_area = getattr(p, "current_area", None)
                if cur_area and hasattr(pm, "_set_player_area"):
                    edge_area_id = graph.area_of(pnode_id) if hasattr(graph, "area_of") else None
                    edge_area_node = graph.get_node(edge_area_id) if edge_area_id else None
                    if edge_area_node is None or getattr(edge_area_node, "name", None) != cur_area:
                        pm._set_player_area(pname, cur_area)
        except Exception:
            pass
    data = world.to_dict()
    if not isinstance(data, dict):
        return {}
    snap = dict(data)
    for k in _STRIP_SNAPSHOT_KEYS:
        snap.pop(k, None)
    return snap


def restore_from_timeline(world: Any, snapshot: Optional[Dict[str, Any]]) -> bool:
    """Restore ``world`` in-place from a timeline checkpoint without clobbering ``timeline_manager``."""
    if world is None or not isinstance(snapshot, dict) or not snapshot or not hasattr(world, "load_from_dict"):
        return False
    prev_source = getattr(world, "_scenario_source", None)
    prev_name = getattr(world, "_scenario_name", "")
    prev_tm = getattr(world, "timeline_manager", None)
    prev_tick_min = getattr(world, "time_per_tick_minutes", 5)

    clean_snap = dict(snapshot)
    clean_snap.pop("timeline", None)

    world._restoring_timeline = True
    try:
        world.load_from_dict(clean_snap)
    finally:
        world._restoring_timeline = False

    world._scenario_source = prev_source
    if prev_name and not getattr(world, "_scenario_name", ""):
        world._scenario_name = prev_name
    if prev_tm is not None:
        world.timeline_manager = prev_tm
    if "time_per_tick_minutes" not in clean_snap:
        world.time_per_tick_minutes = prev_tick_min

    # Restore runtime logs & per-player hearing/lived_log that load_from_dict may reset
    players_data = clean_snap.get("players") or {}
    if isinstance(players_data, dict):
        for pname, pdata in players_data.items():
            pobj = (getattr(world, "players", None) or {}).get(pname)
            if pobj is None or not isinstance(pdata, dict):
                continue
            if "recent_hearing" in pdata and isinstance(pdata["recent_hearing"], list):
                pobj.recent_hearing = copy.deepcopy(pdata["recent_hearing"])
            if "lived_log" in pdata and isinstance(pdata["lived_log"], list):
                pobj.lived_log = copy.deepcopy(pdata["lived_log"])

    if "turn_events" in clean_snap and isinstance(clean_snap["turn_events"], list):
        ev_copy = copy.deepcopy(clean_snap["turn_events"])
        if hasattr(world, "game_logger"):
            world.game_logger.turn_events = list(ev_copy)
        if hasattr(world, "legacy_compat"):
            world.legacy_compat.turn_events = list(ev_copy)
    return True


def record_world_checkpoint(world: Any, tick: Optional[int] = None) -> None:
    """Record a checkpoint of ``world`` on its active timeline branch."""
    if world is None:
        return
    tm = getattr(world, "timeline_manager", None)
    if tm is None:
        return
    cur_tick = int(getattr(world, "time_ticks", 0) or 0) if tick is None else int(tick)
    snap = snapshot_for_timeline(world)
    if snap:
        tm.record_checkpoint(cur_tick, snap)


def expand_timeline_earlier(
    world: Any,
    delta_days: int,
    *,
    stream_store: Any = None,
    world_id: str = "default",
) -> Dict[str, Any]:
    """Shift calendar_config epoch earlier by ``delta_days`` while preserving existing calendar dates.

    Shifts ``world.time_ticks``, player memory/hearing ticks, turn events, timeline
    checkpoints/fork_ticks, and StreamStore rows forward by ``delta_ticks`` so
    existing history stays pinned to its exact calendar date while ``0..delta_ticks``
    opens for prequel play.
    """
    req_days = max(1, int(delta_days or 0))
    cfg = dict(getattr(world, "calendar_config", None) or {})
    dpm = max(1, int(cfg.get("days_per_month", 30) or 30))
    mpy = max(1, int(cfg.get("months_per_year", 12) or 12))
    start_year = int(cfg.get("start_year", 1) or 1)
    start_month = int(cfg.get("start_month", 1) or 1)
    start_day = int(cfg.get("start_day", 1) or 1)

    old_base = (start_year - 1) * dpm * mpy + (start_month - 1) * dpm + (start_day - 1)
    new_base = max(0, old_base - req_days)
    actual_days = old_base - new_base
    if actual_days <= 0:
        return {"ok": False, "delta_days": 0, "delta_ticks": 0}

    new_year = (new_base // (dpm * mpy)) + 1
    rem = new_base % (dpm * mpy)
    new_month = (rem // dpm) + 1
    new_day = (rem % dpm) + 1
    cfg["start_year"] = new_year
    cfg["start_month"] = new_month
    cfg["start_day"] = new_day
    world.calendar_config = cfg

    per_tick = abs(float(getattr(world, "time_per_tick_minutes", 1) or 1))
    delta_ticks = int(round((actual_days * 1440.0) / per_tick))
    world.time_ticks = int(getattr(world, "time_ticks", 0) or 0) + delta_ticks

    for p in (getattr(world, "players", None) or {}).values():
        for m in (getattr(p, "memories", None) or []):
            if isinstance(m, dict) and m.get("tick") is not None:
                m["tick"] = int(m["tick"]) + delta_ticks
            elif hasattr(m, "tick") and getattr(m, "tick") is not None:
                m.tick = int(m.tick) + delta_ticks
        for h in (getattr(p, "recent_hearing", None) or []):
            if isinstance(h, dict) and h.get("tick") is not None:
                h["tick"] = int(h["tick"]) + delta_ticks

    if hasattr(world, "game_logger"):
        for ev in (getattr(world.game_logger, "turn_events", None) or []):
            if isinstance(ev, dict) and ev.get("tick") is not None:
                ev["tick"] = int(ev["tick"]) + delta_ticks

    tm = getattr(world, "timeline_manager", None)
    if tm is not None:
        for b in tm.branches.values():
            b.fork_tick = int(b.fork_tick) + delta_ticks
            b.checkpoints = {int(t) + delta_ticks: s for t, s in b.checkpoints.items()}
            if isinstance(b.snapshot, dict) and b.snapshot.get("time_ticks") is not None:
                b.snapshot["time_ticks"] = int(b.snapshot["time_ticks"]) + delta_ticks
        if getattr(tm, "_store", None) is not None:
            try:
                tm._store.shift_ticks(tm._world_id, delta_ticks)
            except Exception:
                pass

    if stream_store is not None and hasattr(stream_store, "shift_ticks"):
        try:
            stream_store.shift_ticks(world_id=world_id, delta_ticks=delta_ticks)
        except Exception:
            pass

    return {
        "ok": True,
        "delta_days": actual_days,
        "delta_ticks": delta_ticks,
        "new_start_date": f"{new_year:04d}-{new_month:02d}-{new_day:02d}",
        "current_tick": int(world.time_ticks),
        "current_datetime": world.datetime_for_tick() if hasattr(world, "datetime_for_tick") else "",
    }


def connect_branches(
    world: Any,
    source_branch_id: str,
    target_branch_id: str,
    *,
    label: str = "",
) -> Dict[str, Any]:
    """Propagate non-conflicting prequel outcomes (memories, relationships, deaths)
    from ``source_branch_id`` forward onto ``target_branch_id``, returning a new
    connected branch without mutating either source branch.
    """
    tm = getattr(world, "timeline_manager", None)
    if tm is None:
        raise ValueError("World has no timeline_manager")
    if source_branch_id not in tm.branches:
        raise KeyError(f"Unknown source branch: {source_branch_id}")
    if target_branch_id not in tm.branches:
        raise KeyError(f"Unknown target branch: {target_branch_id}")

    src_branch = tm.branches[source_branch_id]
    tgt_branch = tm.branches[target_branch_id]
    src_snap = copy.deepcopy(src_branch.snapshot) if src_branch.snapshot else None
    tgt_snap = copy.deepcopy(tgt_branch.snapshot) if tgt_branch.snapshot else None
    if src_snap is None and getattr(tm, "_store", None) is not None:
        src_snap = tm._store.load_latest_checkpoint(tm._world_id, source_branch_id)
    if tgt_snap is None and getattr(tm, "_store", None) is not None:
        tgt_snap = tm._store.load_latest_checkpoint(tm._world_id, target_branch_id)
    if not isinstance(src_snap, dict) or not isinstance(tgt_snap, dict):
        raise ValueError("Both source and target branches must have a snapshot to connect")

    merged = copy.deepcopy(tgt_snap)
    src_players = src_snap.get("players") or {}
    tgt_players = merged.get("players") or {}
    merged_memories = 0
    propagated_deaths = 0
    merged_rels = 0

    for pname, sp in src_players.items():
        tp = tgt_players.get(pname)
        if not isinstance(sp, dict) or not isinstance(tp, dict):
            continue
        # 1. Union memories from prequel source into target
        t_mems = list(tp.get("memories") or [])
        seen_ids = {m.get("id") for m in t_mems if isinstance(m, dict) and m.get("id")}
        seen_texts = {str(m.get("text") or "").strip().lower() for m in t_mems if isinstance(m, dict)}
        added_mems = []
        for sm in (sp.get("memories") or []):
            if not isinstance(sm, dict):
                continue
            mid = sm.get("id")
            mtxt = str(sm.get("text") or "").strip().lower()
            if (mid and mid in seen_ids) or (mtxt and mtxt in seen_texts):
                continue
            added_mems.append(copy.deepcopy(sm))
            if mid:
                seen_ids.add(mid)
            if mtxt:
                seen_texts.add(mtxt)
            merged_memories += 1
        if added_mems:
            tp["memories"] = added_mems + t_mems

        # 2. Propagate relationships not already present in target
        s_rels = sp.get("relationships") if isinstance(sp.get("relationships"), dict) else {}
        t_rels = dict(tp.get("relationships") if isinstance(tp.get("relationships"), dict) else {})
        for other_name, rdata in s_rels.items():
            if other_name not in t_rels:
                t_rels[other_name] = copy.deepcopy(rdata)
                merged_rels += 1
        tp["relationships"] = t_rels

        # 3. Propagate death from earlier prequel branch
        if sp.get("state") == "dead" and tp.get("state") != "dead":
            tp["state"] = "dead"
            propagated_deaths += 1

    conn_tick = int(merged.get("time_ticks", getattr(world, "time_ticks", 0)) or 0)
    conn_label = label.strip() or f"{src_branch.label} -> {tgt_branch.label}"
    new_branch = tm.fork_branch(
        label=conn_label,
        from_branch_id=target_branch_id,
        fork_tick=conn_tick,
        snapshot=merged,
        switch=True,
    )
    restored = restore_from_timeline(world, merged)
    return {
        "ok": True,
        "branch": new_branch.to_summary(),
        "active_branch_id": tm.active_branch_id,
        "restored": restored,
        "merged_memories": merged_memories,
        "merged_relationships": merged_rels,
        "propagated_deaths": propagated_deaths,
    }
