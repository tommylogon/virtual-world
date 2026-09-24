"""Role-based skill profiles (task-476).

A character's **role** biases which checks they are naturally good at, so a
goblin trapper out-forages a child in the same wood without an LLM ever deciding
it. Roles are *data* (:data:`data/library/roles.json`): each role maps to additive
per-skill bonuses, and adding one is a JSON edit — :func:`validate` is generic.

**Roles are namespaced tags** (``role:trapper``), not a new ``Player`` field.
This follows the existing ``faction:guard`` convention (``player.py`` tag docs),
so a role is authored and serialized exactly like any other tag and no
migration is needed. Only a ``role:``-prefixed tag resolves a profile: a bare
``cook`` or ``farmer`` tag is incidental and stays inert, which keeps every
existing character's checks unchanged until a data pass authors roles.

The bonuses are merged into the single modifier pipeline in
:mod:`engine.checks` (alongside ability, skill value and trait mods), so
``skill_check``, ``resolve`` and ``opposed`` all see them and the breakdown names
the ``role`` source. Nothing here rolls dice or calls a model.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

#: The tag prefix that marks a role. Namespaced so incidental tags never match;
#: the same shape as the documented `faction:guard`.
ROLE_PREFIX = "role:"

#: The shipped role table.
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "library", "roles.json",
)

_cache: Dict[str, dict] = {}


# ───────────────────────────── loading ────────────────────────────────────

def load(path: Optional[str] = None, *, fresh: bool = False) -> dict:
    """Load and cache the role table. ``fresh`` bypasses the cache (tests)."""
    key = os.path.abspath(path or DATA_PATH)
    if fresh or key not in _cache:
        with open(key, "r", encoding="utf-8-sig") as f:
            _cache[key] = json.load(f)
    return _cache[key]


def clear_cache() -> None:
    _cache.clear()


def roles(path: Optional[str] = None) -> Dict[str, dict]:
    return load(path).get("roles") or {}


def role(role_id, path: Optional[str] = None) -> Optional[dict]:
    return roles(path).get(str(role_id))


# ───────────────────────────── resolution ─────────────────────────────────

def _tag_role(tag) -> Optional[str]:
    """The role id named by *tag*, or None when it is not a ``role:`` tag."""
    text = str(tag or "").strip().lower()
    if not text.startswith(ROLE_PREFIX):
        return None
    role_id = text[len(ROLE_PREFIX):].strip()
    return role_id or None


def character_roles(player, path: Optional[str] = None) -> List[str]:
    """The role ids a character carries, deduped and sorted (deterministic)."""
    known = roles(path)
    found = set()
    for tag in (getattr(player, "tags", None) or []):
        role_id = _tag_role(tag)
        if role_id and role_id in known:
            found.add(role_id)
    return sorted(found)


def skill_mods(player, path: Optional[str] = None) -> Dict[str, int]:
    """Merged ``{skill: bonus}`` for a character's roles (additive, may be empty).

    Two roles that both name a skill stack; a roleless character returns ``{}``,
    so the caller's check is exactly what it was before this module existed.
    """
    table = roles(path)
    merged: Dict[str, int] = {}
    for role_id in character_roles(player, path):
        for skill, bonus in (table.get(role_id, {}).get("skills") or {}).items():
            try:
                merged[skill] = merged.get(skill, 0) + int(bonus)
            except (TypeError, ValueError):
                continue
    return merged


# ──────────────────────────── validation ──────────────────────────────────

def validate(data: Optional[dict] = None, path: Optional[str] = None) -> List[str]:
    """Return human-readable problems with the role table; ``[]`` when clean."""
    from engine import checks  # lazy: avoid a checks<->roles import cycle

    problems: List[str] = []
    data = data if data is not None else load(path)
    table = data.get("roles")
    if not isinstance(table, dict) or not table:
        return ["no roles defined"]

    known_skills = set(checks.SKILL_ABILITY)

    for role_id, rec in table.items():
        if not isinstance(rec, dict):
            problems.append(f"role {role_id}: not an object")
            continue
        if ROLE_PREFIX.rstrip(":") in str(role_id).lower():
            problems.append(
                f"role {role_id}: id must not carry the '{ROLE_PREFIX}' prefix")
        if not rec.get("name"):
            problems.append(f"role {role_id}: missing name")
        skills = rec.get("skills")
        if not isinstance(skills, dict) or not skills:
            problems.append(f"role {role_id}: no skill biases")
            continue
        for skill, bonus in skills.items():
            if skill not in known_skills:
                problems.append(
                    f"role {role_id}: unknown skill '{skill}'")
            try:
                value = int(bonus)
            except (TypeError, ValueError):
                problems.append(
                    f"role {role_id}: skill '{skill}' bias is not a number")
                continue
            if value == 0:
                problems.append(f"role {role_id}: skill '{skill}' bias is zero")

    return problems
