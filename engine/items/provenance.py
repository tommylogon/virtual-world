"""Item provenance: where a carried thing came from (task-514).

A library template may declare a default story for an item ("traded from a
scout"); an instance records its own when it is given, stolen, looted or spawned.
The record is a small dict on the **instance** node's properties -- never on the
shared template id -- and renders as one bounded line on examine and in the agent
prompt.

Shape::

    {"text": "Stolen from a human wagon on the old road.",
     "source": "a human wagon",   # optional
     "area": "old road",          # optional
     "tick": 42}                  # optional

Stacking decision (task-514): provenance does **not** participate in stack
identity (``engine/items/stacking.py::_STACKABLE_KEYS``). Per-instance
provenance would otherwise make two otherwise-identical loaves unmergeable.
When twins combine, the surviving stack keeps its own provenance; the merged
copy's story is discarded with it.
"""
from __future__ import annotations

from typing import Optional

MAX_LINE = 160

_KEYS = ("text", "source", "area", "tick")


def normalize_provenance(raw) -> Optional[dict]:
    """Coerce an authored value to the canonical dict, or None when empty.

    Accepts a plain string (the common case) or a dict with any of ``text``,
    ``source``, ``area``, ``tick``.
    """
    if isinstance(raw, str):
        text = raw.strip()
        return {"text": text} if text else None
    if isinstance(raw, dict):
        out = {}
        for key in _KEYS:
            value = raw.get(key)
            if value is None or value == "":
                continue
            out[key] = value
        if str(out.get("text", "")).strip():
            return out
    return None


def render_provenance(raw) -> str:
    """One bounded flavor line, or "" when there is nothing to say."""
    prov = normalize_provenance(raw)
    if not prov:
        return ""
    text = " ".join(str(prov.get("text", "")).split())
    source = str(prov.get("source", "")).strip()
    if source and source.lower() not in text.lower():
        text = f"{text} (from {source})"
    if len(text) > MAX_LINE:
        text = text[: MAX_LINE - 1].rstrip() + "…"
    return text


def stamp_provenance(node, text=None, source=None, area=None, tick=None) -> Optional[dict]:
    """Attach provenance to an instance node's properties, in place.

    Only the fields given are set; anything already stored is preserved. Returns
    the stored dict, or None when there is nothing to store (a story needs text).
    """
    if node is None:
        return None
    current = normalize_provenance((node.properties or {}).get("provenance")) or {}
    for key, value in (("text", text), ("source", source),
                       ("area", area), ("tick", tick)):
        if value:
            current[key] = value
    prov = normalize_provenance(current)
    if prov:
        node.properties["provenance"] = prov
    return prov
