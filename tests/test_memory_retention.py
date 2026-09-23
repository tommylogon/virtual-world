"""Character memory retention (player.py add_memory).

`add_memory` used to drop the oldest memory past a hardcoded 200. That cap was
never chosen, and FIFO meant generated chatter would push out a character's
hand-written backstory. It is now `memory.max_per_character` (default 0 =
unlimited) and eviction skips `source: "manual"` memories.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import player as player_module
from player import Player
from engine.runtime_config import DEFAULTS, SCHEMA


def test_cap_defaults_to_unlimited():
    """No configuration means keep everything — the old 200 cap is gone."""
    p = Player("Uncapped")
    for i in range(600):
        p.add_memory("memory %d" % i, tick=i, source="auto")
    assert len(p.memories) == 600
    assert p.memories[0]["text"] == "memory 0"


def test_cap_is_exposed_in_engine_config():
    assert DEFAULTS["memory.max_per_character"] == 0
    assert SCHEMA["memory.max_per_character"]["section"] == "memory"


def test_configured_cap_trims_the_newest_first(monkeypatch):
    monkeypatch.setattr(player_module, "_memory_limit", lambda: 50)
    p = Player("Capped")
    for i in range(120):
        p.add_memory("memory %d" % i, tick=i, source="auto")
    assert len(p.memories) == 50
    # The most recent memories are the ones worth keeping.
    assert p.memories[-1]["text"] == "memory 119"


def test_authored_backstory_survives_eviction(monkeypatch):
    """`source: manual` memories are the character's past; they go last."""
    monkeypatch.setattr(player_module, "_memory_limit", lambda: 50)
    p = Player("Authored")
    for i in range(10):
        p.add_memory("backstory %d" % i, tick=0, importance=7, source="manual")
    for i in range(600):
        p.add_memory("chatter %d" % i, tick=i, source="auto")

    assert len(p.memories) == 50
    authored = [m for m in p.memories if m["source"] == "manual"]
    assert len(authored) == 10
    assert {m["text"] for m in authored} == {"backstory %d" % i for i in range(10)}


def test_generated_memories_are_evicted_before_authored_ones(monkeypatch):
    monkeypatch.setattr(player_module, "_memory_limit", lambda: 3)
    p = Player("Mixed")
    p.add_memory("the one thing I remember", tick=0, source="manual")
    for i in range(10):
        p.add_memory("chatter %d" % i, tick=i, source="auto")
    assert len(p.memories) == 3
    assert p.memories[0]["text"] == "the one thing I remember"
