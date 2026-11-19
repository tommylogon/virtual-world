"""Tests for subjective time perception, timepieces, and outdoor-gated guess time."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from engine.time_perception import (
    describe_timepiece_reading,
    is_non_clock_character,
    is_timepiece_node,
    natural_time_band,
    resolve_guess_time,
)
from graph import Edge, Node, WorldGraph


def _make_world(
    *,
    hour: int = 14,
    minute: int = 23,
    area_tags=None,
    weather: str = "clear",
    player_tags=None,
    player_traits=None,
    items_in_area=None,
    carried_items=None,
    extra_nodes=None,
    extra_edges=None,
):
    g = WorldGraph()
    area = Node(
        id="area_here",
        type="area",
        name="Here",
        properties={
            "tags": list(area_tags or []),
            "environment": {"weather": weather},
        },
    )
    g.add_node(area)
    char = Node(id="character_tester", type="character", name="Tester", properties={})
    g.add_node(char)
    g.add_edge(Edge(source=char.id, target=area.id, type="in"))

    for it in (items_in_area or []):
        g.add_node(it)
        g.add_edge(Edge(source=it.id, target=area.id, type="in"))
    for it in (carried_items or []):
        g.add_node(it)
        g.add_edge(Edge(source=it.id, target=char.id, type="carrying"))
    for n in (extra_nodes or []):
        g.add_node(n)
    for e in (extra_edges or []):
        g.add_edge(e)

    player = SimpleNamespace(
        name="Tester",
        tags=list(player_tags or []),
        traits=dict(player_traits or {}),
        species="",
    )

    skills = SimpleNamespace(skill_check=lambda skill, dc: (True, dc, "ok"))

    world = SimpleNamespace(
        graph=g,
        players={"Tester": player},
        active_player="Tester",
        player=player,
        skills=skills,
        _get_current_area_id=lambda: "area_here",
        _player_node_id=lambda name: "character_tester",
        current_game_hour=lambda: hour,
        total_game_minutes=lambda: hour * 60 + minute,
        current_moon_phase=lambda: {"name": "full_moon", "icon": "🌕"},
    )
    return world


def test_outdoor_guess_time_tiers_and_no_exact_minute_leak():
    world = _make_world(hour=14, minute=23, area_tags=["outdoor"], weather="clear")

    # Tier 1: total >= dc + 10 -> exact HH:MM
    world.skills.skill_check = lambda s, dc: (True, dc + 10, "crit")
    out = resolve_guess_time(world)
    assert any("14:23" in line and "sun" in line.lower() for line in out)

    # Tier 2: success -> bucketed, no exact 14:23
    world.skills.skill_check = lambda s, dc: (True, dc, "pass")
    out = resolve_guess_time(world)
    assert any("14:30" in line for line in out)
    assert all("14:23" not in line for line in out)

    # Tier 3: near-miss (dc - 5 <= total < dc) -> fuzzy hour, must NOT leak 14:23
    world.skills.skill_check = lambda s, dc: (False, dc - 3, "near")
    out = resolve_guess_time(world)
    assert any("14:00" in line and "early afternoon" in line for line in out)
    assert all("14:23" not in line for line in out)

    # Tier 4: bad fail -> daytime only
    world.skills.skill_check = lambda s, dc: (False, 1, "fail")
    out = resolve_guess_time(world)
    assert any("daytime" in line.lower() for line in out)
    assert all("14:23" not in line for line in out)


def test_indoor_without_clock_or_window_cannot_read_sky():
    world = _make_world(hour=14, minute=23, area_tags=["indoor", "cave"])
    world.skills.skill_check = lambda s, dc: (False, 12, "fail")
    out = resolve_guess_time(world)
    joined = " ".join(out).lower()
    assert "indoors" in joined
    assert "no view of the sky" in joined
    assert "sun" not in joined
    assert "14:23" not in joined

    # High internal clock roll gives natural band only, never exact HH:MM
    world.skills.skill_check = lambda s, dc: (True, 20, "pass")
    out_hi = resolve_guess_time(world)
    assert any("early afternoon" in line for line in out_hi)
    assert all("14:23" not in line for line in out_hi)


def test_indoor_with_window_reads_sky_through_window_at_penalty():
    outside = Node(id="area_yard", type="area", name="Yard", properties={"tags": ["outdoor"]})
    win = Node(id="way_win", type="way", name="Classroom Window", properties={"see_through": True})
    edges = [
        Edge(source="area_here", target="way_win", type="way"),
        Edge(source="way_win", target="area_yard", type="way"),
    ]
    world = _make_world(hour=14, minute=23, area_tags=["indoor"], extra_nodes=[outside, win], extra_edges=edges)
    seen_dc = {}

    def _check(skill, dc):
        seen_dc["dc"] = dc
        return (True, dc + 10, "ok")

    world.skills.skill_check = _check
    out = resolve_guess_time(world)
    assert seen_dc["dc"] == 13  # clear (10) + window (+3)
    assert any("through the window" in line.lower() and "14:23" in line for line in out)


def test_indoor_with_working_timepiece_reads_exact_time():
    clock = Node(id="item_clock", type="item", name="Wall Clock", properties={"tags": ["clock"]})
    world = _make_world(hour=12, minute=5, area_tags=["indoor"], items_in_area=[clock])
    out = resolve_guess_time(world)
    assert any("Wall Clock" in line and "12:05" in line for line in out)


def test_broken_timepiece_does_not_tell_time():
    phone = Node(
        id="item_phone",
        type="item",
        name="Smartphone",
        properties={"tags": ["phone"], "current_state": "dead"},
    )
    world = _make_world(hour=12, minute=5, area_tags=["indoor"], carried_items=[phone])
    world.skills.skill_check = lambda s, dc: (False, 5, "fail")
    out = resolve_guess_time(world)
    assert all("12:05" not in line for line in out)
    reading = describe_timepiece_reading(world, phone)
    assert "not running" in reading.lower()


def test_sundial_requires_open_sky_and_daylight():
    sundial = Node(id="item_sd", type="item", name="Stone Sundial", properties={"tags": ["sundial"]})
    indoor_area = Node(id="area_in", type="area", name="Hall", properties={"tags": ["indoor"]})
    outdoor_area = Node(id="area_out", type="area", name="Courtyard", properties={"tags": ["outdoor"], "environment": {"weather": "clear"}})

    world_day = _make_world(hour=12, minute=14, area_tags=["outdoor"])
    assert "casts no shadow" in describe_timepiece_reading(world_day, sundial, area_node=indoor_area).lower()
    assert "12:15" in describe_timepiece_reading(world_day, sundial, area_node=outdoor_area)

    world_night = _make_world(hour=22, minute=0, area_tags=["outdoor"])
    assert "without the sun" in describe_timepiece_reading(world_night, sundial, area_node=outdoor_area).lower()


def test_non_clock_character_goblin_and_cat_lenses():
    # Goblin outdoors gets natural band, never HH:MM
    world = _make_world(hour=14, minute=23, area_tags=["outdoor"], player_tags=["goblin"])
    world.skills.skill_check = lambda s, dc: (True, dc + 12, "crit")
    out = resolve_guess_time(world)
    assert any("early afternoon" in line for line in out)
    assert all("14:23" not in line for line in out)

    # Cat examining a wall clock cannot read digital numbers
    clock = Node(id="item_clock", type="item", name="Wall Clock", properties={"tags": ["clock"]})
    cat_world = _make_world(hour=9, minute=30, area_tags=["indoor"], player_tags=["cat"], items_in_area=[clock])
    assert is_non_clock_character(cat_world.player)
    reading = describe_timepiece_reading(cat_world, clock)
    assert "mean nothing to you" in reading.lower()
    assert "09:30" not in reading
    assert is_timepiece_node(clock)
    assert natural_time_band(9) == "early morning"
