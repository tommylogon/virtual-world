"""Background characters reach the player: social approach (task-469/464)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine import timeskip
from engine.background_social import run_social_approach


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _hero(w):
    p = w.get_active_player_obj() or next(iter(w.players.values()))
    p.vitals.update({"HP": 100, "Thirst": 0, "Hunger": 0, "Bladder": 0,
                     "Energy": 100, "Hygiene": 100, "Sanity": 100,
                     "Social": 100, "Entertainment": 100})
    p.conditions.clear()
    p.state = "idle"
    p.fear_tags = []
    p._social_last_tick = None
    return p


def _npc(w, name, area):
    previous = w.active_player
    p = Player(name)
    w.add_player(p)                      # makes the new character active
    p.current_area = area
    w.set_player_area(name, area)
    p.simulation_mode = "background"
    p.next_due_tick = 0
    p.vitals.update({"Social": 50, "Entertainment": 50, "Hunger": 0,
                     "Thirst": 0, "Energy": 90})
    p._social_last_tick = None
    if previous:
        try:
            w.player_manager.set_active_player(previous)
        except Exception:
            pass
    return p


def test_approach_writes_a_turn_event_and_gives_the_player_a_memory():
    w = _world()
    hero = _hero(w)
    _npc(w, "Rikka", hero.current_area)
    before = len(hero.memories)
    resolved = run_social_approach(w)
    assert resolved, "no approach resolved"
    events = [e for e in w.game_logger.turn_events
              if e.get("action") == "social_approach"]
    assert events and events[-1]["area"] == hero.current_area
    assert len(hero.memories) == before + 1
    assert "Rikka" in hero.memories[-1]["text"]


def test_no_approach_when_nobody_is_present():
    w = _world()
    _hero(w)
    assert run_social_approach(w) == []


def test_timeskip_pauses_on_a_social_approach():
    w = _world()
    hero = _hero(w)
    _npc(w, "Rikka", hero.current_area)
    res = timeskip.advance(w, 30, intent="idle")
    assert res.interrupted
    assert res.interrupt["kind"] == "social"


def test_the_player_is_not_approached_twice_in_a_row():
    w = _world()
    hero = _hero(w)
    _npc(w, "Rikka", hero.current_area)
    assert run_social_approach(w)          # first approach lands
    assert run_social_approach(w) == []    # cooldown now applies to the player
