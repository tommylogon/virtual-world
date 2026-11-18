"""Reproductive cycles: periods and going into heat, feeding the fertility window (task-928).

@module reproductive_cycle
@contributes menstrual cycles, estrus/heat cycles, fertility windows, cycle phase conditions
@docs docs/virtualWorld/Characters/Persona.md

A separate recurring system alongside task-846's one-shot pregnancy state machine.
Cycle state is one bounded dict on ``Player.reproductive_cycle``, advanced in
``lifecycle.on_clock`` beside pregnancy. No unbounded event stores.

Species table ``SPECIES_CYCLES`` declares the pattern in one place:
- ``none``: no recurring cycle (constructs, undead, ghosts, plants, fish, birds)
- ``cycle``: monthly menstrual cycle with phases ``menstruating``, ``follicular``,
  ``ovulating`` (the fertile window), and ``luteal``
- ``heat``: periodic estrus cycle with phases ``anestrus``, ``proestrus``,
  ``in_heat`` (the fertile window), and ``metestrus``

Phases surface through the existing conditions system (``menstruating``,
``ovulating``, ``in_heat``). Pregnancy suspends the cycle and birth resumes it.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional, Tuple

from engine import lifecycle


#: Phase conditions managed by the reproductive cycle. Cleared or swapped on
#: phase transitions and when pregnancy suspends the cycle.
CYCLE_CONDITIONS = ("menstruating", "ovulating", "in_heat")

#: Typical age of menarche for monthly physiological cycles (`pattern: "cycle"`).
#: Pregnancy and fertile/flirt-drive conditions remain gated on `ADULT_AGE` (18).
MENARCHE_AGE = 12
PREPUBESCENT_TAGS = frozenset({"child", "kid", "infant", "toddler", "baby"})

#: Species reproductive cycle table (single source of truth).
#: - pattern "cycle": length_days, phases as (end_day_inclusive, phase_name),
#:   fertile_days as (start_day_inclusive, end_day_inclusive).
#: - pattern "heat": length_days, heat_days, proestrus_days, metestrus_days.
#: - pattern "none": no cycle.
SPECIES_CYCLES: Dict[str, Dict[str, Any]] = {
    "human": {
        "pattern": "cycle",
        "length_days": 28,
        "phases": (
            (5, "menstruating"),
            (12, "follicular"),
            (16, "ovulating"),
            (28, "luteal"),
        ),
        "fertile_days": (12, 16),
    },
    "elf": {
        "pattern": "cycle",
        "length_days": 30,
        "phases": (
            (4, "menstruating"),
            (13, "follicular"),
            (17, "ovulating"),
            (30, "luteal"),
        ),
        "fertile_days": (13, 17),
    },
    "dwarf": {
        "pattern": "cycle",
        "length_days": 28,
        "phases": (
            (5, "menstruating"),
            (12, "follicular"),
            (16, "ovulating"),
            (28, "luteal"),
        ),
        "fertile_days": (12, 16),
    },
    "goblin": {
        "pattern": "heat",
        "length_days": 15,
        "phases": (
            (9, "anestrus"),
            (11, "proestrus"),
            (14, "in_heat"),
            (15, "metestrus"),
        ),
        "fertile_days": (11, 14),
    },
    "animal": {
        "pattern": "heat",
        "length_days": 20,
        "phases": (
            (13, "anestrus"),
            (15, "proestrus"),
            (19, "in_heat"),
            (20, "metestrus"),
        ),
        "fertile_days": (15, 19),
    },
    "beast": {
        "pattern": "heat",
        "length_days": 20,
        "phases": (
            (13, "anestrus"),
            (15, "proestrus"),
            (19, "in_heat"),
            (20, "metestrus"),
        ),
        "fertile_days": (15, 19),
    },
    "wolf": {
        "pattern": "heat",
        "length_days": 20,
        "phases": (
            (13, "anestrus"),
            (15, "proestrus"),
            (19, "in_heat"),
            (20, "metestrus"),
        ),
        "fertile_days": (15, 19),
    },
    "worg": {
        "pattern": "heat",
        "length_days": 20,
        "phases": (
            (13, "anestrus"),
            (15, "proestrus"),
            (19, "in_heat"),
            (20, "metestrus"),
        ),
        "fertile_days": (15, 19),
    },
    "boar": {
        "pattern": "heat",
        "length_days": 21,
        "phases": (
            (14, "anestrus"),
            (16, "proestrus"),
            (20, "in_heat"),
            (21, "metestrus"),
        ),
        "fertile_days": (16, 20),
    },
    "bear": {
        "pattern": "heat",
        "length_days": 24,
        "phases": (
            (16, "anestrus"),
            (18, "proestrus"),
            (22, "in_heat"),
            (24, "metestrus"),
        ),
        "fertile_days": (18, 22),
    },
    "frog": {
        "pattern": "heat",
        "length_days": 18,
        "phases": (
            (11, "anestrus"),
            (13, "proestrus"),
            (17, "in_heat"),
            (18, "metestrus"),
        ),
        "fertile_days": (13, 17),
    },
    "undead": {"pattern": "none"},
    "zombie": {"pattern": "none"},
    "ghost": {"pattern": "none"},
    "construct": {"pattern": "none"},
    "plant": {"pattern": "none"},
}

#: Phase -> condition id applied while in that phase (None if the phase has no
#: dedicated status condition).
PHASE_CONDITION: Dict[str, Optional[str]] = {
    "menstruating": "menstruating",
    "follicular": None,
    "ovulating": "ovulating",
    "luteal": None,
    "anestrus": None,
    "proestrus": None,
    "in_heat": "in_heat",
    "metestrus": None,
}


def _node_properties(node) -> dict:
    if isinstance(node, dict):
        return node.get("properties") or {}
    return getattr(node, "properties", None) or {}


def _identity_of(node) -> dict:
    if node is None:
        return {}
    try:
        from engine import character_appearance as ca
        record = node if isinstance(node, dict) else ca.get_record(node)
        ident = (record or {}).get("identity")
    except Exception:
        ident = None
    if not isinstance(ident, dict):
        appearance = _node_properties(node).get("appearance")
        ident = appearance.get("identity") if isinstance(appearance, dict) else None
    return ident if isinstance(ident, dict) else {}


def _tags_of(player, node=None) -> set:
    tags = set()
    for source in (getattr(player, "tags", None), _node_properties(node).get("tags")):
        if isinstance(source, str):
            source = [t for t in source.split(",")]
        for tag in source or []:
            tags.add(str(tag).strip().lower())
    return tags


def resolve_species(player, node=None) -> str:
    """Resolve species from Player.species, node properties, identity, or tags."""
    for source in (getattr(player, "species", None),
                   _node_properties(node).get("species"),
                   _identity_of(node).get("species")):
        if isinstance(source, str) and source.strip():
            return source.strip().lower()
    tags = _tags_of(player, node)
    # Check specific species tags before generic ones
    for sp in ("undead", "zombie", "ghost", "construct", "plant", "goblin", "elf",
               "dwarf", "frog", "worg", "wolf", "boar", "bear", "animal", "beast", "human"):
        if sp in tags:
            return sp
    return "human"


def resolve_sex(player, node=None) -> Optional[str]:
    """Resolve biological sex ('female', 'male', or None if unknown/unspecified)."""
    ident = _identity_of(node)
    for key in ("sex", "gender"):
        val = ident.get(key)
        if isinstance(val, str) and val.strip():
            v = val.strip().lower()
            if v in ("female", "woman", "girl", "f", "mare", "sow", "she"):
                return "female"
            if v in ("male", "man", "boy", "m", "stallion", "boar", "he"):
                return "male"
    pronouns = str(ident.get("pronouns") or "").strip().lower()
    if pronouns.startswith("she/") or pronouns == "she":
        return "female"
    if pronouns.startswith("he/") or pronouns == "he":
        return "male"
    tags = _tags_of(player, node)
    if "female" in tags:
        return "female"
    if "male" in tags:
        return "male"
    return None


def cycle_spec_for_species(species: str) -> Dict[str, Any]:
    """Return the cycle specification for *species* from ``SPECIES_CYCLES``."""
    sp = str(species or "").strip().lower()
    if sp in SPECIES_CYCLES:
        return dict(SPECIES_CYCLES[sp])
    tail = sp.replace("_", " ").split()[-1] if sp else ""
    if tail and tail in SPECIES_CYCLES:
        return dict(SPECIES_CYCLES[tail])
    return {"pattern": "none"}


def pattern_for_species(species: str) -> str:
    """Return pattern name for *species* ('none', 'cycle', or 'heat')."""
    return str(cycle_spec_for_species(species).get("pattern", "none"))


def ticks_per_day(world) -> int:
    """Number of simulation ticks in a 24-hour game day."""
    per_tick = float(getattr(world, "time_per_tick_minutes", 5) or 5)
    if per_tick <= 0:
        per_tick = 5.0
    return max(1, int(round(1440.0 / per_tick)))


def _deterministic_offset_days(name: str, length_days: int) -> int:
    """Stable per-character day offset so an authored cast is not synchronized to day 1."""
    if length_days <= 1:
        return 0
    digest = hashlib.md5(str(name or "").encode("utf-8")).digest()
    return int.from_bytes(digest[:2], "big") % length_days


def _phase_for_day(spec: Dict[str, Any], day_in_cycle: int) -> Tuple[str, int]:
    """Return ``(phase_name, phase_end_day)`` for 1-based *day_in_cycle*."""
    phases = spec.get("phases") or ()
    for end_day, phase_name in phases:
        if day_in_cycle <= end_day:
            return phase_name, int(end_day)
    if phases:
        last_end, last_name = phases[-1]
        return last_name, int(last_end)
    return "none", int(spec.get("length_days", 1) or 1)


def _is_day_fertile(spec: Dict[str, Any], day_in_cycle: int) -> bool:
    window = spec.get("fertile_days")
    if not window or len(window) != 2:
        return False
    start_day, end_day = int(window[0]), int(window[1])
    return start_day <= day_in_cycle <= end_day


def is_eligible_for_cycle(player, world, node=None) -> Tuple[bool, str]:
    """Check whether *player* should run a recurring cycle.

    Monthly menstrual cycles (`pattern == "cycle"`) track physiological
    phases starting from menarche (`MENARCHE_AGE`, excluding pre-pubescent
    children and elders), while pregnancy and fertile/flirt conditions remain
    gated on adulthood (`ADULT_AGE` in `engine/pregnancy.py`). Estrus
    (`pattern == "heat"`) remains adult-only.
    """
    if getattr(player, "state", "") == "dead":
        return False, "deceased"

    if node is None and world is not None:
        try:
            node = world.graph.get_node(world._player_node_id(getattr(player, "name", "")))
        except Exception:
            node = None

    traits = dict(getattr(player, "traits", {}) or {})
    node_traits = _node_properties(node).get("traits") or {}
    if isinstance(node_traits, dict):
        traits.update(node_traits)
    tags = _tags_of(player, node)
    if traits.get("infertile") or traits.get("sterile") or "infertile" in tags or "sterile" in tags:
        return False, "sterile"
    if "undead" in tags or "ghost" in tags or "construct" in tags:
        return False, "non-living"

    sex = resolve_sex(player, node)
    if sex != "female":
        return False, "not a cycling carrier"

    species = resolve_species(player, node)
    spec = cycle_spec_for_species(species)
    pattern = spec.get("pattern")
    if pattern in (None, "none"):
        return False, f"species {species} has no cycle"

    from engine import pregnancy as _preg
    minor = _preg.minor_reason(player, node)
    stage = _preg.effective_life_stage(player, world, node)

    if pattern == "heat":
        if minor:
            return False, f"minor ({minor})"
        if stage != "adult":
            return False, f"life stage {stage or 'unknown'}"
        return True, pattern

    # pattern == "cycle": allow post-pubescent adolescents & adults, exclude children & elders
    if tags & PREPUBESCENT_TAGS:
        return False, "pre-pubescent"
    if stage == "elder":
        return False, "life stage elder"

    ident_age = None
    try:
        raw_age = _identity_of(node).get("age")
        if raw_age is not None:
            ident_age = float(raw_age)
    except (TypeError, ValueError):
        ident_age = None
    if ident_age is None:
        ident_age = lifecycle.age_years(player, world, node)
    if ident_age is not None and ident_age < MENARCHE_AGE:
        return False, f"pre-pubescent (age {ident_age:g} < {MENARCHE_AGE})"
    if stage not in ("adult", "adolescent") and not (ident_age is not None and ident_age >= MENARCHE_AGE):
        return False, f"life stage {stage or 'unknown'}"

    return True, pattern


def _sync_cycle_conditions(
    player,
    phase: Optional[str],
    duration_minutes: Optional[int] = None,
    *,
    allow_fertile_conditions: bool = True,
) -> None:
    """Apply the condition for *phase* and clear any other cycle phase conditions."""
    wanted = PHASE_CONDITION.get(phase or "") if phase else None
    if not allow_fertile_conditions and wanted in ("ovulating", "in_heat"):
        wanted = None
    conds = getattr(player, "conditions", None)
    if not isinstance(conds, dict):
        return
    for cid in CYCLE_CONDITIONS:
        if cid != wanted and cid in conds:
            try:
                player.remove_condition(cid)
            except Exception:
                conds.pop(cid, None)
    if wanted:
        try:
            if hasattr(player, "add_condition"):
                player.add_condition(wanted, duration=duration_minutes, source="reproductive_cycle")
            else:
                conds[wanted] = [{"duration": duration_minutes, "source": "reproductive_cycle", "level": 0}]
        except Exception:
            pass


def clear_cycle_conditions(player) -> None:
    """Remove all cycle-specific conditions from *player*."""
    _sync_cycle_conditions(player, None)


def suspend_for_pregnancy(player) -> None:
    """Suspend an active reproductive cycle when pregnancy begins."""
    cyc = getattr(player, "reproductive_cycle", None)
    if isinstance(cyc, dict):
        cyc["suspended"] = True
        cyc["phase"] = "pregnant"
        cyc["fertile_window"] = False
    clear_cycle_conditions(player)


def resume_after_birth(player, world, node=None) -> Optional[Dict[str, Any]]:
    """Resume the reproductive cycle from day 1 after giving birth."""
    if getattr(player, "reproductive_cycle", None) is not None:
        player.reproductive_cycle = None
    clear_cycle_conditions(player)
    return update_cycle(player, world, node=node, reset_day_one=True)


def update_cycle(player, world, node=None, *, reset_day_one: bool = False) -> Optional[Dict[str, Any]]:
    """Compute or advance ``player.reproductive_cycle`` at ``world.time_ticks``.

    Returns the updated bounded cycle dict, or ``None`` if the character does not
    have an active cycle.
    """
    if getattr(player, "pregnancy", None):
        suspend_for_pregnancy(player)
        return getattr(player, "reproductive_cycle", None)

    if node is None and world is not None:
        try:
            node = world.graph.get_node(world._player_node_id(getattr(player, "name", "")))
        except Exception:
            node = None

    eligible, _reason = is_eligible_for_cycle(player, world, node)
    if not eligible:
        if getattr(player, "reproductive_cycle", None):
            player.reproductive_cycle = None
        clear_cycle_conditions(player)
        return None

    species = resolve_species(player, node)
    spec = cycle_spec_for_species(species)
    pattern = spec.get("pattern", "none")
    length_days = max(1, int(spec.get("length_days", 28) or 28))
    tpd = ticks_per_day(world)
    now = lifecycle.now_ticks(world)

    existing = getattr(player, "reproductive_cycle", None)
    if isinstance(existing, dict) and existing.get("pattern") == pattern and not reset_day_one and not existing.get("suspended"):
        anchor_tick = int(existing.get("anchor_tick", 0) or 0)
    elif reset_day_one:
        anchor_tick = now
    else:
        offset_days = _deterministic_offset_days(getattr(player, "name", ""), length_days)
        anchor_tick = now - (offset_days * tpd)

    elapsed_ticks = max(0, now - anchor_tick)
    elapsed_days = elapsed_ticks // tpd
    day_in_cycle = (elapsed_days % length_days) + 1
    phase, phase_end_day = _phase_for_day(spec, day_in_cycle)
    from engine import pregnancy as _preg
    is_minor = bool(_preg.minor_reason(player, node))
    fertile = False if is_minor else _is_day_fertile(spec, day_in_cycle)

    cycle_Start_tick = anchor_tick + (elapsed_days - (day_in_cycle - 1)) * tpd
    next_phase_tick = cycle_Start_tick + (phase_end_day * tpd)
    per_tick = float(getattr(world, "time_per_tick_minutes", 5) or 5)
    remaining_minutes = max(1, int(round(max(1, next_phase_tick - now) * per_tick)))

    old_phase = existing.get("phase") if isinstance(existing, dict) else None
    cycle_state = {
        "pattern": pattern,
        "species": species,
        "phase": phase,
        "day": int(day_in_cycle),
        "length_days": int(length_days),
        "fertile_window": bool(fertile),
        "next_phase_tick": int(next_phase_tick),
        "anchor_tick": int(anchor_tick),
        "suspended": False,
    }
    player.reproductive_cycle = cycle_state
    _sync_cycle_conditions(
        player,
        phase,
        duration_minutes=remaining_minutes,
        allow_fertile_conditions=not is_minor,
    )

    if old_phase and old_phase != phase and old_phase != "pregnant":
        try:
            if hasattr(world, "player_manager") and hasattr(world.player_manager, "record_turn_event"):
                world.player_manager.record_turn_event(
                    player.name, "cycle", f"entered {phase}",
                    area_name=getattr(player, "current_area", None)
                )
        except Exception:
            pass

    return cycle_state


def in_fertile_window(player, world, node=None) -> Tuple[bool, str]:
    """Check whether *player* is currently in their fertile window.

    - Characters whose species has ``pattern: "none"`` or who are male (sires)
      do not have a cycle gate and return ``(True, "no cycle gate")``.
    - Cycling or heat-pattern female adults must be inside their fertile window
      (``ovulating`` or ``in_heat``). If ``player.reproductive_cycle`` has not
      been initialized yet, only an already-present ``reproductive_cycle`` dict
      or an explicit cycle call gates conception unless ``ensure_cycle`` is active;
      here we evaluate or read the cycle when the character has a cycle state or
      when their species declares a pattern.
    """
    if node is None and world is not None:
        try:
            node = world.graph.get_node(world._player_node_id(getattr(player, "name", "")))
        except Exception:
            node = None

    sex = resolve_sex(player, node)
    if sex != "female":
        return True, "no cycle gate"

    species = resolve_species(player, node)
    spec = cycle_spec_for_species(species)
    pattern = spec.get("pattern", "none")
    if pattern in (None, "none"):
        return True, "species has no cycle pattern"

    cyc = getattr(player, "reproductive_cycle", None)
    if not isinstance(cyc, dict):
        # If the character has an active cycle condition directly applied, honour it
        conds = getattr(player, "conditions", None) or {}
        if "ovulating" in conds or "in_heat" in conds:
            return True, "in fertile condition"
        if "menstruating" in conds:
            return False, "currently menstruating (outside fertile window)"
        return True, "cycle not yet initialized"

    if cyc.get("suspended"):
        return False, "cycle is suspended"

    if cyc.get("fertile_window"):
        return True, f"in fertile window ({cyc.get('phase')}, day {cyc.get('day')}/{cyc.get('length_days')})"

    return False, f"outside fertile window (phase: {cyc.get('phase')}, day {cyc.get('day')}/{cyc.get('length_days')})"
