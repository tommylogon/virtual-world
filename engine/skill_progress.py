"""Skill growth, proficiency and setting skill packs (task-480).

Three separable pieces of a progression model:

* **Setting skill packs** — :data:`data/library/skill_packs.json` names a pack of
  starting skills a setting grants its characters on top of the base sheet
  (task-474). :func:`apply_pack` raises skills toward the pack value and never
  lowers one unless asked, so applying a pack twice is idempotent.
* **Proficiency** — an optional, separate term so the sheet expresses a trained
  value (``player.skills``) and proficiency independently. It is merged into the
  one check pipeline in :mod:`engine.checks` and defaults to 0, which is exactly
  the pre-task-480 behaviour (task-472 left the term out deliberately).
* **Use-based advancement** — :func:`record_use` counts *successful* uses and
  raises the skill at the threshold. This is **opt-in**: nothing grows unless a
  scenario sets ``skill_growth``, so no existing save or soak changes.

No LLM is involved and every rule is deterministic.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

#: The ceiling a skill can grow to by use.
MAX_SKILL = 10

#: Successful uses that raise a skill when a caller does not say otherwise.
DEFAULT_THRESHOLD = 5

PACKS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "library", "skill_packs.json",
)

_cache: Dict[str, dict] = {}


# ────────────────────────────── packs ─────────────────────────────────────

def load_packs(path: Optional[str] = None, *, fresh: bool = False) -> dict:
    key = os.path.abspath(path or PACKS_PATH)
    if fresh or key not in _cache:
        with open(key, "r", encoding="utf-8-sig") as f:
            _cache[key] = json.load(f)
    return _cache[key]


def clear_cache() -> None:
    _cache.clear()


def packs(path: Optional[str] = None) -> Dict[str, dict]:
    return load_packs(path).get("packs") or {}


def pack(pack_id, path: Optional[str] = None) -> Optional[dict]:
    return packs(path).get(str(pack_id))


def apply_pack(player, pack_id, *, path: Optional[str] = None,
               allow_lower: bool = False) -> Dict[str, int]:
    """Grant *pack_id*'s skills to *player*; return ``{skill: new_value}``.

    Raises a skill only toward the pack value (never lowers unless
    ``allow_lower``), so this is idempotent and safe to re-run on load.
    """
    rec = pack(pack_id, path) or {}
    granted: Dict[str, int] = {}
    skills = getattr(player, "skills", None)
    if not isinstance(skills, dict):
        return granted
    for skill, value in (rec.get("skills") or {}).items():
        try:
            target = int(value)
        except (TypeError, ValueError):
            continue
        current = int(skills.get(skill, 0) or 0)
        if allow_lower or target > current:
            skills[skill] = target
            granted[skill] = target
    return granted


def validate(data: Optional[dict] = None, path: Optional[str] = None) -> List[str]:
    """Return human-readable problems with the packs; ``[]`` when clean."""
    from engine import checks  # lazy: avoid import churn

    problems: List[str] = []
    data = data if data is not None else load_packs(path)
    table = data.get("packs")
    if not isinstance(table, dict) or not table:
        return ["no skill packs defined"]
    known = set(checks.SKILL_ABILITY)
    for pack_id, rec in table.items():
        if not isinstance(rec, dict):
            problems.append(f"pack {pack_id}: not an object")
            continue
        if not rec.get("name"):
            problems.append(f"pack {pack_id}: missing name")
        skills = rec.get("skills")
        if not isinstance(skills, dict) or not skills:
            problems.append(f"pack {pack_id}: no skills")
            continue
        for skill, value in skills.items():
            if skill not in known:
                problems.append(f"pack {pack_id}: unknown skill '{skill}'")
            try:
                amount = int(value)
            except (TypeError, ValueError):
                problems.append(f"pack {pack_id}: '{skill}' is not a number")
                continue
            if amount <= 0:
                problems.append(f"pack {pack_id}: '{skill}' must be positive")
            elif amount > MAX_SKILL:
                problems.append(
                    f"pack {pack_id}: '{skill}' exceeds MAX_SKILL ({MAX_SKILL})")
    return problems


# ─────────────────────────── proficiency ──────────────────────────────────

def proficiency_bonus(player) -> int:
    """The optional proficiency term added to every skill check (default 0)."""
    try:
        return int(getattr(player, "proficiency", 0) or 0)
    except (TypeError, ValueError):
        return 0


# ─────────────────────── use-based advancement ────────────────────────────

def growth_enabled(gs) -> bool:
    """Whether a scenario has opted in to use-based skill growth."""
    return bool(getattr(gs, "skill_growth", False))


def growth_threshold(gs) -> int:
    try:
        return max(1, int(getattr(gs, "skill_growth_threshold",
                                  DEFAULT_THRESHOLD) or DEFAULT_THRESHOLD))
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD


def skill_progress(player) -> dict:
    """The player's per-skill use counter, created lazily."""
    prog = getattr(player, "skill_progress", None)
    if not isinstance(prog, dict):
        prog = {}
        try:
            player.skill_progress = prog
        except Exception:
            pass
    return prog


def record_use(player, skill, *, success: bool = True, amount: int = 1,
               threshold: Optional[int] = None, cap: int = MAX_SKILL) -> bool:
    """Count a use; raise the skill at the threshold. Returns True if it rose.

    Only *successful* uses count — failing teaches little — and the counter is
    reset when the skill rises so progress is not double-counted. A skill at
    *cap* stops accruing. The threshold is per-call so a scenario can tune it.
    """
    if not success or not skill:
        return False
    skills = getattr(player, "skills", None)
    if not isinstance(skills, dict):
        return False
    try:
        step = max(1, int(amount))
    except (TypeError, ValueError):
        step = 1
    limit = max(1, int(threshold or DEFAULT_THRESHOLD))
    current = int(skills.get(skill, 0) or 0)
    if current >= cap:
        return False

    prog = skill_progress(player)
    prog[skill] = int(prog.get(skill, 0)) + step
    if prog[skill] >= limit:
        skills[skill] = current + 1
        prog[skill] = 0
        return True
    return False
