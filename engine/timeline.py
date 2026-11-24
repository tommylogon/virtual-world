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

    def __init__(self) -> None:
        self.active_branch_id: str = "main"
        self.branches: Dict[str, TimelineBranch] = {
            "main": TimelineBranch(branch_id="main", parent_branch_id=None, label="Main")
        }

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
                return copy.deepcopy(branch.checkpoints[max(eligible)])
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
        return branch

    def switch_branch(self, branch_id: str) -> TimelineBranch:
        """Switch the active branch and return it (with its latest snapshot)."""
        if branch_id not in self.branches:
            raise KeyError(f"Unknown branch: {branch_id}")
        self.active_branch_id = branch_id
        return self.branches[branch_id]

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
