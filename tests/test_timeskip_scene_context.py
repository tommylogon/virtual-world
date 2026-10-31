"""Test timeskip narrative recap hook with scene_context and cast memories."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import timeskip
from app import create_app


def _world():
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _hero(w):
    p = w.get_active_player_obj()
    if p is None:
        p = next(iter(w.players.values()))
    for other in w.players.values():
        if other is not p:
            other.autonomy = True
    return p


def test_timeskip_updates_scene_context_premise_and_cast_memories():
    w = _world()
    hero = _hero(w)
    w.scene_context = {
        "title": "First Period",
        "premise": "Students are chatting before class.",
        "enabled": True,
    }

    # Identify another character in the world
    other = next(p for p in w.players.values() if p is not hero)
    initial_mem_count = len(getattr(other, "memories", []))

    res = timeskip.advance(w, 15, intent="idle")
    assert res.ok is True
    assert res.elapsed_minutes > 0

    # 1. Verify scene_context was updated
    assert w.scene_context["premise"] != "Students are chatting before class."
    assert "minutes elapsed" in w.scene_context["premise"]
    assert hero.name in w.scene_context["premise"]

    # 2. Verify other cast member received an episodic timeskip memory
    current_mem_count = len(getattr(other, "memories", []))
    assert current_mem_count > initial_mem_count
    recent_mem = other.memories[-1]
    tags = getattr(recent_mem, "tags", [])
    if isinstance(recent_mem, dict):
        tags = recent_mem.get("tags", [])
    assert "timeskip" in tags
