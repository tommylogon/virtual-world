"""Pregnancy, gestation, and birth (task-846).

@module pregnancy
@contributes conception, gestation, birth, fertility checks
@docs docs/virtualWorld/Characters/Persona.md

Lifecycle follow-up to task-735. Handles conception gated on willingness
and life-stage fertility, gestation progression across sim time ticks,
and live delivery spawning a real character into the world.

Storage is bounded (a single dict on Player.pregnancy, cleared on birth;
no unbounded event stores).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from engine import lifecycle


DEFAULT_GESTATION_MONTHS = 9


#: Tags that mark a character as a minor. Any of these is a hard exclusion from
#: conception, whatever the life-stage clock says (a species age rate or a stale
#: birth tick must never promote a minor to adult).
MINOR_TAGS = frozenset({"child", "kid", "teen", "teenager", "minor", "adolescent", "juvenile"})

#: Chronological age below which a character cannot conceive or sire, regardless
#: of the species age rate.
ADULT_AGE = 18


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


def minor_reason(player, node=None):
    """Why this character counts as a minor, or None.

    Checks the authored age and the age tags, independently of lifecycle stages.
    """
    tags = _tags_of(player, node) & MINOR_TAGS
    if tags:
        return f"tagged {sorted(tags)[0]}"
    try:
        age = float(_identity_of(node).get("age"))
    except (TypeError, ValueError):
        age = None
    if age is not None and age < ADULT_AGE:
        return f"authored age {age:g} is under {ADULT_AGE}"
    return None


def _species_of(player, node=None) -> str:
    for source in (getattr(player, "species", None),
                   _node_properties(node).get("species"),
                   _identity_of(node).get("species")):
        if isinstance(source, str) and source.strip():
            return source.strip().lower()
    tags = _tags_of(player, node)
    for sp in ("undead", "zombie", "ghost", "construct", "plant", "goblin", "elf",
               "dwarf", "frog", "worg", "wolf", "boar", "bear", "animal", "beast", "human"):
        if sp in tags:
            return sp
    return "human"


def _node(world, name: str):
    if world is None:
        return None
    try:
        return world.graph.get_node(world._player_node_id(name))
    except Exception:
        return None


def effective_life_stage(player, world, node=None) -> Optional[str]:
    """Resolve effective life stage from clock age, cached stage, or authored tags."""
    if node is None and world is not None:
        node = _node(world, getattr(player, "name", ""))
    tags = _tags_of(player, node)
    # If explicitly tagged elder, honour it
    if "elder" in tags:
        return "elder"
    age = lifecycle.age_years(player, world, node)
    stage = lifecycle.life_stage(age)
    if stage is None:
        stage = getattr(player, "life_stage", None)
    # If species age rate pushed an adult-tagged character (like 18yo goblin Belne)
    # into 'elder' despite explicit 'adult' tag and chronological age < 40, respect 'adult' tag
    if stage == "elder" and "adult" in tags and "elder" not in tags:
        try:
            chron_age = float(_identity_of(node).get("age"))
        except (TypeError, ValueError):
            chron_age = None
        if chron_age is not None and ADULT_AGE <= chron_age < 40:
            stage = "adult"
    if stage is None:
        if "adult" in tags:
            return "adult"
        if tags & {"animal", "beast", "frog", "wolf", "worg", "boar", "bear"} and not (tags & MINOR_TAGS):
            return "adult"
    return stage


def get_gestation_ticks(world, species: str = "human") -> int:
    """Calculate gestation period in ticks for this world calendar."""
    per_tick = float(getattr(world, "time_per_tick_minutes", 5) or 5)
    if per_tick <= 0:
        per_tick = 5.0
    year_minutes = lifecycle.minutes_per_year(world)
    year_ticks = year_minutes / per_tick
    # 9 months is 0.75 of a year
    fraction = 0.75
    if species == "goblin":
        fraction = 0.4
    elif species in ("animal", "beast", "wolf", "worg", "boar", "bear", "frog"):
        fraction = 0.25
    return max(1, int(fraction * year_ticks))


def is_fertile(player, world, node=None) -> Tuple[bool, str]:
    """Check if a character is biologically fertile based on life stage, traits, and cycle window.

    Fertility is strictly gated by life stage (adults only, never minors) and
    by the reproductive cycle window when present (task-928).
    """
    if getattr(player, "state", "") == "dead":
        return False, "character is deceased"

    if getattr(player, "pregnancy", None):
        return False, "already pregnant"

    if node is None and world is not None:
        node = _node(world, getattr(player, "name", ""))

    minor = minor_reason(player, node)
    if minor:
        return False, f"minor ({minor}); never eligible"

    traits = getattr(player, "traits", {}) or {}
    node_traits = _node_properties(node).get("traits") or {}
    if isinstance(node_traits, dict):
        traits = {**traits, **node_traits}
    tags = _tags_of(player, node)
    if traits.get("infertile") or traits.get("sterile") or "infertile" in tags or "sterile" in tags:
        return False, "character is sterile"
    if "undead" in tags or "ghost" in tags or "construct" in tags:
        return False, "non-living entity is not fertile"

    stage = effective_life_stage(player, world, node)
    if stage is None:
        return False, "life stage unknown (must be adult)"

    if stage in ("child", "adolescent"):
        return False, f"not physically mature (life stage: {stage})"

    if stage == "elder":
        return False, "past reproductive age (life stage: elder)"

    if stage != "adult":
        return False, f"life stage {stage} is not fertile"

    # task-928: check the reproductive cycle's fertile window
    try:
        from engine import reproductive_cycle as _rc
        in_win, win_reason = _rc.in_fertile_window(player, world, node)
        if not in_win:
            return False, win_reason
    except Exception:
        pass

    return True, "fertile"


def check_willingness(carrier, partner, world=None) -> Tuple[bool, str]:
    """Check whether both parties consent and neither has a boundary against reproduction."""
    # Explicit override flags
    if getattr(carrier, "willing", True) is False:
        return False, f"{carrier.name} is unwilling"
    if getattr(partner, "willing", True) is False:
        return False, f"{partner.name} is unwilling"

    # Check boundaries / hard limits
    forbidden_terms = {"pregnancy", "reproduction", "child", "children", "breeding", "intimacy"}
    for person in (carrier, partner):
        node = _node(world, getattr(person, "name", "")) if world else None
        boundaries: List[str] = []
        try:
            from engine import character_appearance as ca
            if node:
                bounds_data = ca.get_character_boundaries(node)
                boundaries.extend(bounds_data.get("boundaries") or [])
                boundaries.extend(bounds_data.get("hard_limits") or [])
        except Exception:
            pass
        boundaries.extend(getattr(person, "boundaries", []) or [])
        pers = getattr(person, "personality", {}) or {}
        if isinstance(pers, dict):
            boundaries.extend(pers.get("boundaries") or [])

        for b in boundaries:
            b_norm = str(b).strip().lower()
            if any(term in b_norm for term in forbidden_terms):
                return False, f"{person.name} has a boundary against {b}"

    # Check relationship consent if recorded
    c_rels = getattr(carrier, "relationships", {}) or {}
    rel_carrier = c_rels.get(partner.name) or {}
    c_consent = rel_carrier.get("consent")
    if c_consent is not None and c_consent < 0:
        return False, f"{carrier.name} does not consent to intimacy with {partner.name} (consent: {c_consent})"

    p_rels = getattr(partner, "relationships", {}) or {}
    rel_partner = p_rels.get(carrier.name) or {}
    p_consent = rel_partner.get("consent")
    if p_consent is not None and p_consent < 0:
        return False, f"{partner.name} does not consent to intimacy with {carrier.name} (consent: {p_consent})"

    return True, "willing"


def attempt_conception(carrier, partner, world, *, gestation_ticks: Optional[int] = None,
                      bypass_willingness: bool = False) -> Tuple[bool, str]:
    """Attempt conception between a carrier and partner.

    Requires both fertility by stage (and cycle window when active) and willingness
    from both characters. When both sexes are authored, checks that the pair is
    reproductively compatible (carrier is not male, partner is not female).
    """
    node_c = _node(world, carrier.name)
    fertile_c, reason_c = is_fertile(carrier, world, node_c)
    if not fertile_c:
        return False, f"conception failed for {carrier.name}: {reason_c}"

    node_p = _node(world, partner.name)
    fertile_p, reason_p = is_fertile(partner, world, node_p)
    if not fertile_p:
        return False, f"conception failed for {partner.name}: {reason_p}"

    try:
        from engine import reproductive_cycle as _rc
        sex_c = _rc.resolve_sex(carrier, node_c)
        sex_p = _rc.resolve_sex(partner, node_p)
        if sex_c == "male":
            return False, f"conception failed for {carrier.name}: male character cannot carry a pregnancy"
        if sex_c == "female" and sex_p == "female":
            return False, f"conception failed: {carrier.name} and {partner.name} are both female"
    except Exception:
        pass

    if not bypass_willingness:
        willing, reason_w = check_willingness(carrier, partner, world)
        if not willing:
            return False, f"conception refused: {reason_w}"

    if gestation_ticks is None:
        species = _species_of(carrier, node_c)
        gestation_ticks = get_gestation_ticks(world, species)

    now = lifecycle.now_ticks(world)
    due_tick = now + gestation_ticks

    carrier.pregnancy = {
        "partner": partner.name,
        "conception_tick": now,
        "due_tick": due_tick,
        "gestation_ticks": gestation_ticks,
        "stage": "first_trimester",
    }

    # task-928: pregnancy suspends the reproductive cycle
    try:
        from engine import reproductive_cycle as _rc
        _rc.suspend_for_pregnancy(carrier)
    except Exception:
        pass

    try:
        if hasattr(world, "player_manager") and hasattr(world.player_manager, "record_turn_event"):
            world.player_manager.record_turn_event(
                carrier.name, "pregnancy", f"conceived with {partner.name}",
                area_name=getattr(carrier, "current_area", None)
            )
    except Exception:
        pass

    return True, f"{carrier.name} conceived with {partner.name} (due at tick {due_tick})."


def update_pregnancy(carrier, world) -> Tuple[Optional[str], Optional[str]]:
    """Advance gestation based on the world clock.

    Returns (stage, event_message).
    """
    preg = getattr(carrier, "pregnancy", None)
    if not preg or not isinstance(preg, dict):
        return None, None

    now = lifecycle.now_ticks(world)
    c_tick = preg.get("conception_tick")
    conception = int(c_tick if c_tick is not None else now)
    d_tick = preg.get("due_tick")
    due = int(d_tick if d_tick is not None else now)
    total = max(1, due - conception)
    elapsed = max(0, now - conception)
    progress = elapsed / float(total)

    if now >= due or progress >= 1.0:
        stage = "due"
    elif progress >= 0.66:
        stage = "third_trimester"
    elif progress >= 0.33:
        stage = "second_trimester"
    else:
        stage = "first_trimester"

    old_stage = preg.get("stage")
    preg["stage"] = stage

    event = None
    if stage != old_stage and stage != "due":
        event = f"{carrier.name}'s pregnancy entered {stage}."
        try:
            if hasattr(world, "player_manager") and hasattr(world.player_manager, "record_turn_event"):
                world.player_manager.record_turn_event(
                    carrier.name, "pregnancy", f"entered {stage}",
                    area_name=getattr(carrier, "current_area", None)
                )
        except Exception:
            pass

    return stage, event


def deliver_birth(carrier, world, *, child_name: Optional[str] = None) -> Tuple[Any, str]:
    """Deliver a baby from a pregnant carrier, spawning a new character into the world."""
    preg = getattr(carrier, "pregnancy", None) or {}
    partner_name = preg.get("partner") or "Unknown"

    from player import Player
    if not child_name:
        child_name = f"Child of {carrier.name}"
        pm = getattr(world, "player_manager", None)
        existing = getattr(pm, "players", {}) or {}
        counter = 1
        while child_name in existing:
            child_name = f"Child of {carrier.name} {counter}"
            counter += 1

    child = Player(child_name)
    now = lifecycle.now_ticks(world)
    child.birth_tick = now
    child.life_stage = "child"
    carrier_node = _node(world, carrier.name)
    child.species = _species_of(carrier, carrier_node)

    # Establish family relationships
    child.relationships[carrier.name] = {"closeness": 90, "role": "mother", "label": "mother"}
    carrier.relationships[child_name] = {"closeness": 90, "role": "child", "label": "child"}
    if partner_name and partner_name != "Unknown":
        child.relationships[partner_name] = {"closeness": 90, "role": "father", "label": "father"}
        partner = world.get_player(partner_name) if hasattr(world, "get_player") else None
        if partner:
            partner.relationships[child_name] = {"closeness": 90, "role": "child", "label": "child"}

    # Placement in world
    area_name = getattr(carrier, "current_area", None)
    if world is not None and hasattr(world, "add_player"):
        world.add_player(child)
        if area_name and hasattr(world, "set_player_area"):
            world.set_player_area(child_name, area_name)

    # Clear carrier pregnancy and resume reproductive cycle (task-928)
    carrier.pregnancy = None
    try:
        from engine import reproductive_cycle as _rc
        _rc.resume_after_birth(carrier, world, carrier_node)
    except Exception:
        pass

    msg = f"{carrier.name} gave birth to {child_name}!"
    try:
        if hasattr(world, "player_manager") and hasattr(world.player_manager, "record_turn_event"):
            world.player_manager.record_turn_event(
                carrier.name, "birth", f"gave birth to {child_name}",
                area_name=area_name
            )
    except Exception:
        pass

    return child, msg
