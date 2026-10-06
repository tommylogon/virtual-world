"""Character memory retention (player.py add_memory).

`add_memory` used to drop the oldest memory past a hardcoded 200; that was later
made configurable (`memory.max_per_character`). **2026-10-06: all caps were
removed.** A character keeps every memory for life — nothing is evicted, at any
configured limit.
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


def test_configured_cap_is_ignored_nothing_is_evicted(monkeypatch):
    """2026-10-06: memories are never evicted, even when a cap is configured."""
    monkeypatch.setattr(player_module, "_memory_limit", lambda: 50)
    p = Player("Capped")
    for i in range(120):
        p.add_memory("memory %d" % i, tick=i, source="auto")
    assert len(p.memories) == 120
    assert p.memories[-1]["text"] == "memory 119"


def test_authored_backstory_and_generated_chatter_all_survive(monkeypatch):
    monkeypatch.setattr(player_module, "_memory_limit", lambda: 50)
    p = Player("Authored")
    for i in range(10):
        p.add_memory("backstory %d" % i, tick=0, importance=7, source="manual")
    for i in range(600):
        p.add_memory("chatter %d" % i, tick=i, source="auto")
    assert len(p.memories) == 610
    authored = [m for m in p.memories if m["source"] == "manual"]
    assert len(authored) == 10
    assert {m["text"] for m in authored} == {"backstory %d" % i for i in range(10)}
