"""Aging and lifecycle for long-horizon soaks (task-735).

@module lifecycle
@contributes birth ticks, life stages, old-age death, lifecycle read model
@docs docs/virtualWorld/Characters/Persona.md

A 10-year soak should change who people are: ages advance with sim time,
life stages gate behaviour, and the very old can die. Pregnancy and birth
ride a follow-up card - this module is the clock, the stages, and death.

Clock source: ``world.time_ticks`` - the sim clock every turn,
need and trait system already reads. NOT wall time, and not the
``player_manager.time_ticks`` name (TickManager IS constructed with
the world in that seat, so both names reach the same counter).

Storage (bounded - three scalars on the Player, no event stores):

- ``birth_tick`` - sim tick of birth (nullable). An authored
  ``identity.age`` resolves to one exactly once, against the current
  date; ``advance_age`` shifts it earlier.
- ``life_stage`` - cached stage string (child/adolescent/adult/elder);
  transitions emit a turn event so soaks show them.
- ``last_mortality_year`` - last game-year the old-age roll ran, so
  death is checked once per year, not once per tick.

Species pacing: ``SPECIES_AGE_RATE`` (goblins age ~3x, per the race
bible) scales effective age; ``SPECIES_LIFESPAN`` gates the mortality
roll. Both are starting values in one table, not a biology sim.
"""

from __future__ import annotations

from typing import Any, Optional

#: Effective years per chronological year. Goblin rate from the race
#: bible (3x human under normal conditions); everything else 1.0.
SPECIES_AGE_RATE = {
    "goblin": 3.0,
}

#: Typical lifespan in effective years. Death is probabilistic past
#: this, never scheduled - an elder may live years beyond it.
SPECIES_LIFESPAN = {
    "human": 80,
    "elf": 300,
    "dwarf": 200,
    "goblin": 45,
}
DEFAULT_LIFESPAN = 80

#: (upper bound in effective years, stage). Adult is open-ended until
#: elder; elder begins where the mortality roll starts caring.
LIFE_STAGES = (
    (13, "child"),
    (18, "adolescent"),
    (60, "adult"),
    (float("inf"), "elder"),
)


def minutes_per_year(world) -> int:
    """Game minutes in a year from the calendar config (default 360d)."""
    cfg = getattr(world, "calendar_config", None) or {}
    try:
        days = max(1, int(cfg.get("days_per_month", 30)))
        months = max(1, int(cfg.get("months_per_year", 12)))
    except (TypeError, ValueError):
        days, months = 30, 12
    return days * months * 1440


def now_ticks(world) -> int:
    """The sim clock both the turns and the soaks advance.

    Read off the world itself: TickManager is constructed with the
    world as its ``player_manager`` (tick_manager.py), so
    ``world.time_ticks`` IS the live clock the turns advance.
    """
    return int(getattr(world, "time_ticks", 0) or 0)


def _species_of(player, node=None) -> str:
    for source in (getattr(player, "species", None),
                   ((node.get("properties") or {}).get("species")
                    if isinstance(node, dict) else None)):
        if isinstance(source, str) and source.strip():
            return source.strip().lower()
    return "human"


def ensure_birth_tick(player, world, node=None) -> Optional[int]:
    """Resolve a birth tick once: authored age → date, or stay unknown.

    A character with neither stays ageless (prose-only authors are not
    forced onto the clock). Returns the tick or None.
    """
    birth = getattr(player, "birth_tick", None)
    if birth is not None:
        return int(birth)
    authored = None
    try:
        from engine import character_appearance as ca
        record = node if isinstance(node, dict) else ca.get_record(node)
        authored = (record.get("identity") or {}).get("age")
    except Exception:
        authored = None
    if authored is None:
        return None
    try:
        years = float(authored)
    except (TypeError, ValueError):
        return None
    per_tick = float(getattr(world, "time_per_tick_minutes", 5) or 5)
    year_ticks = minutes_per_year(world) / per_tick if per_tick else 0
    birth = int(now_ticks(world) - years * year_ticks)
    player.birth_tick = birth
    return birth


def age_years(player, world, node=None) -> Optional[float]:
    """Effective age in years, or None for the ageless."""
    birth = ensure_birth_tick(player, world, node)
    if birth is None:
        return None
    per_tick = float(getattr(world, "time_per_tick_minutes", 5) or 5)
    year_ticks = minutes_per_year(world) / per_tick if per_tick else 0
    if not year_ticks:
        return None
    rate = SPECIES_AGE_RATE.get(_species_of(player, node), 1.0)
    return max(0.0, (now_ticks(world) - birth) / year_ticks * rate)


def life_stage(age: Optional[float]) -> Optional[str]:
    """Stage for an effective age (None stays None - ageless)."""
    if age is None:
        return None
    for bound, stage in LIFE_STAGES:
        if age < bound:
            return stage
    return "elder"


def lifespan_years(player, node=None) -> int:
    """Lifespan for mortality, by species (authored override: none yet)."""
    return SPECIES_LIFESPAN.get(_species_of(player, node), DEFAULT_LIFESPAN)


def shift_birth_tick(player, world, years: float) -> Optional[float]:
    """Age a character by *years* (task-829 ``advance_age`` engine side).

    Moves the birth tick earlier so the clock agrees; returns the new
    effective age, or None when the character is ageless (no birth
    tick and no authored age to resolve from).
    """
    try:
        delta = float(years)
    except (TypeError, ValueError):
        return None
    birth = getattr(player, "birth_tick", None)
    if birth is None:
        return None
    per_tick = float(getattr(world, "time_per_tick_minutes", 5) or 5)
    year_ticks = minutes_per_year(world) / per_tick if per_tick else 0
    player.birth_tick = int(birth - delta * year_ticks)
    return age_years(player, world)


def mortality_roll(player, age: float, lifespan: int, rng=None) -> bool:
    """True when old age takes them this year. Never before lifespan."""
    if age < lifespan:
        return False
    over = age - lifespan
    chance = min(0.8, 0.15 + 0.10 * over)
    roll = rng() if rng is not None else __import__("random").random()
    return roll < chance


def _character_node(world, name: str):
    try:
        return world.graph.get_node(world._player_node_id(name))
    except Exception:
        return None


def on_clock(world, rng=None) -> list:
    """Advance aging for every living character. Called after the clock
    moves (turns, ticks, timeskips). Returns human-readable events."""
    events: list = []
    players = getattr(getattr(world, "player_manager", None), "players", None) or {}
    try:
        year_len = minutes_per_year(world)
        per_tick = float(getattr(world, "time_per_tick_minutes", 5) or 5)
        year = int(now_ticks(world) * per_tick // year_len) if year_len and per_tick else 0
    except Exception:
        year = 0
    for name, player in list(players.items()):
        try:
            if getattr(player, "state", "") == "dead":
                continue
            node = _character_node(world, name)
            age = age_years(player, world, node)
            if age is None:
                continue
            stage = life_stage(age)
            if stage and stage != getattr(player, "life_stage", None):
                player.life_stage = stage
                events.append(f"{name} is now {stage} ({age:.1f}).")
                try:
                    world.player_manager.record_turn_event(
                        name, "age", f"became {stage}",
                        area_name=getattr(player, "current_area", None))
                except Exception:
                    pass
            span = lifespan_years(player, node)
            if age >= span and getattr(player, "last_mortality_year", None) != year:
                player.last_mortality_year = year
                if mortality_roll(player, age, span, rng):
                    try:
                        world.kill_player(name, cause=f"old age ({age:.0f})")
                    except Exception:
                        player.state = "dead"
                    events.append(f"{name} died of old age ({age:.0f}).")
        except Exception:
            continue
    return events


def status(player, world, node=None) -> dict:
    """The lifecycle read model for prompts, prose and the Bio tab."""
    age = age_years(player, world, node)
    return {
        "age": round(age, 1) if age is not None else None,
        "life_stage": life_stage(age),
        "lifespan": lifespan_years(player, node),
        "birth_tick_known": getattr(player, "birth_tick", None) is not None,
    }
