"""Library-backed reusable NPC behaviours (task-590).

A behaviour record is the shape ``npc_behaviors.process_simple_npcs`` already
evaluates on ``player.behaviors``:

    {trigger, interval, conditions, actions, priority}

The Behaviours tab (``templates/index.html``) has always been able to search,
create and save those records into ``data/library/behaviours/`` via the generic
registry routes, while the engine read only ``player.behaviors[]`` -- a live
authoring path that produced files the engine ignored. This module is the engine
side of that path, the same "unify, do not remove" treatment traits received
(``engine/traits.py::_load_trait_library``; task-291 §1.3's "remove the
Behaviours tab" row is superseded by task-590).

**Reference or inline-merge: inline-merge at character load.** A character
carries ``behavior_refs: [id]``; hydration copies each resolved library record
into ``player.behaviors`` (tagged with ``_library_id`` so provenance stays
inspectable). The evaluator is untouched, saves keep working because behaviours
were already serialized inline, and no new ``Player`` field is introduced. A ref
that resolves to nothing is **collected and reported**, never silently dropped —
the rule ``world_compile`` follows for an unknown biome id.

Every ``*.json`` under the directory is either loaded into the catalog or
reported in :func:`problems`; a file the engine ignores is the failure mode this
module exists to remove.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

#: Where the Behaviours tab writes one file per entry. Kept as a function so a
#: test can point it at a fixture directory.
def library_dir(data_dir: Optional[str] = None) -> str:
    base = data_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    return os.path.join(base, "library", "behaviours")


_cache: Dict[str, dict] = {}
#: (filename, reason) for every file that could not be loaded, keyed by dir.
_problems: Dict[str, List[Tuple[str, str]]] = {}


def _read_library(data_dir: Optional[str]) -> Tuple[Dict[str, dict], List[Tuple[str, str]]]:
    directory = library_dir(data_dir)
    library: Dict[str, dict] = {}
    problems: List[Tuple[str, str]] = []
    if not os.path.isdir(directory):
        return library, problems
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".json"):
            continue
        entry_id = fname[:-5]
        path = os.path.join(directory, fname)
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                entry = json.load(handle)
        except Exception as exc:  # malformed JSON must be visible, not skipped
            problems.append((fname, f"unreadable: {exc}"))
            continue
        if not isinstance(entry, dict):
            problems.append((fname, "not a JSON object"))
            continue
        library[entry_id] = entry
    return library, problems


def load(data_dir: Optional[str] = None, *, fresh: bool = False) -> Dict[str, dict]:
    """The behaviour catalog, keyed by entry id. Cached like the trait library."""
    key = os.path.abspath(library_dir(data_dir))
    if fresh or key not in _cache:
        library, problems = _read_library(data_dir)
        _cache[key] = library
        _problems[key] = problems
        for fname, reason in problems:
            logger.warning("Behaviour library entry %s would never be read: %s", fname, reason)
    return _cache[key]


def reload(data_dir: Optional[str] = None) -> Dict[str, dict]:
    """Re-read the catalog after a save, so the next character load sees it."""
    return load(data_dir, fresh=True)


def problems(data_dir: Optional[str] = None) -> List[Tuple[str, str]]:
    """Files under the behaviours directory the engine could not consume."""
    load(data_dir)
    return list(_problems.get(os.path.abspath(library_dir(data_dir)), []))


def _ref_id(ref) -> Optional[str]:
    if isinstance(ref, str):
        return ref.strip() or None
    if isinstance(ref, dict):
        value = ref.get("id")
        return str(value).strip() if value else None
    return None


def resolve(refs, data_dir: Optional[str] = None) -> Tuple[List[dict], List[str]]:
    """Resolve behaviour refs to library records.

    Returns ``(records, unresolved_ids)``. Each record is a shallow copy tagged
    with its ``_library_id``; an unknown id lands in ``unresolved_ids`` so the
    caller can report it.
    """
    catalog = load(data_dir)
    records: List[dict] = []
    unresolved: List[str] = []
    for ref in (refs or []):
        ref_id = _ref_id(ref)
        if not ref_id:
            continue
        entry = catalog.get(ref_id)
        if entry is None:
            unresolved.append(ref_id)
            continue
        record = dict(entry)
        record.setdefault("_library_id", ref_id)
        records.append(record)
    return records, unresolved


def merge_into(existing, refs, data_dir: Optional[str] = None) -> Tuple[List[dict], List[str]]:
    """Append resolved library behaviours to an inline ``player.behaviors`` list.

    Idempotent by ``_library_id``: a character refreshed twice does not double
    its behaviour tree. Returns ``(behaviors, unresolved_ids)``.
    """
    out = [b for b in (existing or []) if isinstance(b, dict)]
    already = {b.get("_library_id") for b in out}
    records, unresolved = resolve(refs, data_dir)
    for record in records:
        if record.get("_library_id") in already:
            continue
        out.append(record)
        already.add(record.get("_library_id"))
    return out, unresolved


def report_unresolved(owner: str, unresolved) -> Optional[str]:
    """A single warning line for unresolvable refs, or ``None`` when clean.

    Callers log the returned line (and may surface it in an API response) so an
    unresolvable ref is explicit rather than a behaviour that quietly never runs.
    """
    if not unresolved:
        return None
    ids = ", ".join(sorted(set(unresolved)))
    return (f"{owner}: behaviour refs resolve to no library entry, so they never run: {ids}")


# Load once at import, like the trait catalog, so a malformed shipped entry is
# reported at startup rather than the first time a character happens to use it.
load()

