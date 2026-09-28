#!/usr/bin/env python3
"""scenario_refs.py — resolve a scenario's area references to canonical node ids.

A scenario may address an area by its node id (``area_chiefs_pit``) or by its
display name (``Chief's Pit``); the engine accepts both, so authored data drifts
between the two styles. Strict-id pathfinding only accepts the first, so the
authoring-time tools need one resolver both styles funnel through.

Ambiguity is an error, not a guess: two areas whose names normalise to the same
string have no single correct answer, and silently picking one would move a way
onto the wrong side of the camp.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def normalize_ref(text: Any) -> str:
    """Fold a reference to its comparison form: lowercase alphanumerics only."""
    return _NON_ALNUM.sub("", str(text or "").lower())


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


class AmbiguousRef(LookupError):
    """A reference matched more than one area, so it cannot be canonicalized."""


class AreaResolver:
    """Map an area node id or display name onto the canonical node id."""

    def __init__(self, nodes: Dict[str, Any]):
        self._by_id: Dict[str, str] = {}
        self._by_name: Dict[str, List[str]] = {}
        self._by_normal: Dict[str, List[str]] = {}
        for node_id, node in (nodes or {}).items():
            if not isinstance(node, dict) or node.get("type") != "area":
                continue
            self._by_id[str(node_id)] = str(node_id)
            declared = node.get("id")
            if declared and str(declared) not in self._by_id:
                self._by_id[str(declared)] = str(node_id)
            name = str(node.get("name") or "").strip()
            if name:
                self._by_name.setdefault(name, []).append(str(node_id))
            folded = normalize_ref(name) or normalize_ref(node_id)
            if folded:
                self._by_normal.setdefault(folded, []).append(str(node_id))

    def __contains__(self, reference: Any) -> bool:
        return self.resolve(reference) is not None

    def resolve(self, reference: Any) -> Optional[str]:
        """The canonical area node id for *reference*, or None when unknown.

        Raises :class:`AmbiguousRef` rather than guessing between the equally
        good candidates a normalized match produced.
        """
        if reference is None:
            return None
        text = str(reference).strip()
        if not text:
            return None
        if text in self._by_id:
            return self._by_id[text]
        exact = self._by_name.get(text)
        if exact:
            return self._unique(text, exact)
        folded = self._by_normal.get(normalize_ref(text))
        if folded:
            return self._unique(text, folded)
        return None

    def _unique(self, reference: str, candidates: Iterable[str]) -> str:
        unique = sorted(set(candidates))
        if len(unique) == 1:
            return unique[0]
        raise AmbiguousRef(
            f"area reference {reference!r} matches {len(unique)} areas: "
            f"{', '.join(unique)}"
        )

    def unresolved(self, references: Iterable[Any]) -> List[Tuple[Any, Any]]:
        """``(owner, reference)`` pairs that name no area at all."""
        missing = []
        for owner, reference in references:
            if reference is None or str(reference).strip() == "":
                continue
            try:
                resolved = self.resolve(reference)
            except AmbiguousRef:
                resolved = None
            if resolved is None:
                missing.append((owner, reference))
        return missing


def way_area_refs(nodes: Dict[str, Any]) -> List[Tuple[str, str, Any]]:
    """``(way_id, field, value)`` for every ``area_from`` / ``area_to`` entry."""
    refs = []
    for node_id, node in (nodes or {}).items():
        if not isinstance(node, dict) or node.get("type") != "way":
            continue
        props = node.get("properties")
        if not isinstance(props, dict):
            continue
        for field in ("area_from", "area_to"):
            value = props.get(field)
            if value:
                refs.append((node_id, field, value))
    return refs


def way_connection_pairs(nodes: Dict[str, Any], edges: Iterable[dict]) -> Dict[str, set]:
    """Area ids that reach each way, read off the ``connection`` edges.

    The graph is the truth about which areas a way touches; the way's own
    ``area_from`` / ``area_to`` properties are the authored claim. This reports
    the two so a tool can show where they disagree instead of assuming.
    """
    pairs: Dict[str, set] = {}
    for edge in edges or []:
        if not isinstance(edge, dict) or edge.get("type") != "connection":
            continue
        source, target = edge.get("source"), edge.get("target")
        source_node = (nodes or {}).get(source) or {}
        target_node = (nodes or {}).get(target) or {}
        if source_node.get("type") == "area" and target_node.get("type") == "way":
            pairs.setdefault(str(target), set()).add(str(source))
        elif target_node.get("type") == "area" and source_node.get("type") == "way":
            pairs.setdefault(str(source), set()).add(str(target))
    return pairs
