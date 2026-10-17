"""Trait definition catalog: data-driven loading and seeding of TRAIT_DEFINITIONS.

Owns the on-disk trait library (data/library/traits/*.json) and the merge
rules that fold it into the engine catalog. The catalog dict itself lives in
engine/traits.py (TRAIT_DEFINITIONS) so TraitSystem and the rest of the engine
keep importing it from one place; this module only reads/writes it through the
trait_definitions argument so there is no second source of truth.
"""

import json as _json
import os as _os


def _trait_library_dir():
    return _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
        "data", "library", "traits",
    )


def _trait_is_active(defn: dict) -> bool:
    return bool(defn.get("effects") or defn.get("grants_conditions") or defn.get("save_on"))


_TRAIT_BASE = {
    "name": "", "description": "", "category": "custom", "params": None,
    "effects": {}, "conflicts": [], "behavior_prompt": "",
    "grants_conditions": [], "save_on": [], "immune_to_condition": [],
}


def _merge_trait_definition(tid: str, entry: dict, trait_definitions: dict):
    base = trait_definitions[tid] if tid in trait_definitions else dict(_TRAIT_BASE)
    merged = base
    merged.update(entry)
    merged.setdefault("name", merged.get("name") or tid.title().replace("_", " "))
    trait_definitions[tid] = merged


def _load_trait_library(trait_definitions: dict):
    trait_dir = _trait_library_dir()
    if not _os.path.isdir(trait_dir):
        return
    for fname in sorted(_os.listdir(trait_dir)):
        if not fname.endswith(".json"):
            continue
        tid = fname[:-5]
        try:
            with open(_os.path.join(trait_dir, fname), "r", encoding="utf-8-sig") as f:
                entry = _json.load(f)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        if tid in trait_definitions or _trait_is_active(entry):
            _merge_trait_definition(tid, entry, trait_definitions)


def seed_trait_library(trait_definitions: dict):
    trait_dir = _trait_library_dir()
    try:
        _os.makedirs(trait_dir, exist_ok=True)
    except OSError:
        return
    for tid, definition in trait_definitions.items():
        path = _os.path.join(trait_dir, f"{tid}.json")
        if _os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    existing = _json.load(f)
            except Exception:
                existing = {}
            if _trait_is_active(existing):
                continue
        try:
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(definition, f, indent=2, ensure_ascii=False)
        except OSError:
            continue