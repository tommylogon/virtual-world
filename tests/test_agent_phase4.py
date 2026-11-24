"""Tests for Phase 4 Python Agent Migration (task-1004): Generators, Commons Agent, NL Editor."""
from __future__ import annotations

import json
from types import SimpleNamespace

from engine.agent.commons_agent import run_commons_turn
from engine.agent.generators import (
    generate_description,
    generate_insights,
    generate_personality,
    generate_tags,
)
from engine.agent.nl_editor import run_nl_edit


class _StubClient:
    def __init__(self, reply: str) -> None:
        self._reply = reply

    def chat(self, messages, **kwargs) -> str:
        return self._reply


def test_generators_roundtrip():
    p = generate_personality(
        _StubClient(json.dumps({"personality": "Skeptical", "appearance": "Tall", "speech_style": "Clipped"})),
        name="Elena",
    )
    assert p["personality"] == "Skeptical"

    tags = generate_tags(_StubClient(json.dumps({"tags": ["Occult", " Dusty "]})), name="Diary", description="Old book")
    assert tags == ["occult", "dusty"]

    ins = generate_insights(
        _StubClient(json.dumps({"insights": [{"text": "The skull is the key.", "importance": 8}]})),
        char_name="Elena",
        memories=["Found diary"],
    )
    assert len(ins) == 1 and ins[0]["importance"] == 8

    desc = generate_description(_StubClient(json.dumps({"description": "A dim library."})), name="Library")
    assert desc["description"] == "A dim library."


def test_commons_agent_turn():
    player = SimpleNamespace(
        name="miki",
        personality="Chaotic ASMR artist",
        emotions_description=lambda: "curious",
        somatic_description=lambda: "steady pulse",
    )
    world = SimpleNamespace(players={"miki": player})
    stub = _StubClient(
        json.dumps(
            {
                "inner_monologue": "Whoa, spooky.",
                "speech": "Did anyone else hear that?",
                "volume": "whisper",
                "tone": "guarded",
                "emote": "taps their phone case",
                "learned_names": [],
            }
        )
    )
    parsed = run_commons_turn(world, stub, "miki", transcript=[{"speaker": "elena", "text": "Stay close."}], topic="The Mansion")
    assert parsed.speech == "Did anyone else hear that?"
    assert parsed.speech_volume == "whisper"
    assert parsed.speech_tone == "guarded"


def test_nl_editor_executes_world_mutations():
    lib = SimpleNamespace(name="library", description="Old text")
    elena = SimpleNamespace(name="elena vance", personality="Old persona")
    world = SimpleNamespace(graph=SimpleNamespace(nodes={"library": lib}), players={"elena vance": elena})

    stub = _StubClient(
        json.dumps(
            {
                "calls": [
                    {"tool": "set_area_description", "area": "library", "description": "Cold marble fireplace and shelves."},
                    {"tool": "set_character_personality", "character": "elena vance", "personality": "Methodical investigator."},
                ],
                "summary": "Updated library and Elena.",
            }
        )
    )
    res = run_nl_edit(world, stub, "Update the library description and Elena's personality.")
    assert res["ok"] is True
    assert lib.description == "Cold marble fireplace and shelves."
    assert elena.personality == "Methodical investigator."
    assert all(r["ok"] for r in res["results"])
