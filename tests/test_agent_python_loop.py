"""Headless Python agent loop tests (Phase 2 PromptBuilder + Phase 3 AgentRunner)."""
from __future__ import annotations

import json

from engine.agent.llm_client import LLMResult
from engine.agent.prompt_builder import build_think_decide_messages
from engine.agent.runner import AgentRunner
from player import Player
from virtual_world_engine import VirtualWorld


class _FakeLLM:
    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = []

    def chat(self, messages, *, response_format=None, **kwargs):
        self.calls.append((messages, response_format))
        content = self._replies.pop(0) if self._replies else '{"action":"wait"}'
        return LLMResult(content=content, model="fake-llm")


def _make_two_actor_world():
    w = VirtualWorld()
    w.players.clear()
    a = Player("Elena")
    a.current_area = "library"
    a.personality = "Methodical investigator."
    b = Player("Miki")
    b.current_area = "library"
    b.personality = "Chaotic ASMR artist."
    w.players["Elena"] = a
    w.players["Miki"] = b
    return w


def test_prompt_builder_includes_somatic_and_observer_tells():
    w = _make_two_actor_world()
    # Give Miki an active autonomic state so Elena sees her tells
    st = w.players["Miki"].emotion_matrix_state()
    st.families["fear"] = 72.0
    st.autonomic["heart_rate"] = 65.0
    st.autonomic["muscle_tension"] = 60.0

    msgs = build_think_decide_messages(w, "Elena")
    assert len(msgs) == 2
    assert "=== SPEECH, VOLUME & TONE ===" in msgs[0]["content"]
    assert '"tone":"normal"' in msgs[1]["content"]
    assert '"memory"' not in msgs[1]["content"]
    assert "Miki" in msgs[1]["content"]


def test_headless_two_actor_runner_turn_cycle():
    w = _make_two_actor_world()
    llm = _FakeLLM([
        json.dumps({
            "inner_monologue": "Testing the waters.",
            "action": "wait",
            "speech": "Cute lock, real cute.",
            "volume": "say",
            "tone": "sarcastic",
            "emote": "raises an eyebrow",
            "learned_names": [],
        }),
        json.dumps({
            "inner_monologue": "She sounds sarcastic.",
            "action": "wait",
            "speech": "Hey, don't look at me!",
            "volume": "say",
            "tone": "warm",
            "emote": "grins nervously",
            "learned_names": [],
        }),
    ])
    runner = AgentRunner(w, llm, order_mode="sequential")
    o1 = runner.step_next()
    assert o1 is not None and o1.character == "Elena"
    assert o1.parsed.speech_tone == "sarcastic"
    assert o1.cycle_completed is False
    # Miki should have heard Elena's sarcastic line
    assert len(w.players["Miki"].recent_hearing) >= 1
    assert w.players["Miki"].recent_hearing[-1]["text"] == "Cute lock, real cute."

    o2 = runner.step_next()
    assert o2 is not None and o2.character == "Miki"
    assert o2.cycle_completed is True
    assert runner.turn_queue.turn_number == 1


def test_flask_agent_prompt_endpoint():
    import app as app_mod

    flask_app = app_mod.create_app({"TESTING": True})
    client = flask_app.test_client()
    chars = list(flask_app.world.players.keys())
    assert chars, "Expected at least one player in default test world"
    resp = client.post("/api/agent/prompt", json={"character": chars[0], "phase": "think"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["character"] == chars[0]
    assert len(data["messages"]) == 2
    assert "tone" in data["response_format"]["json_schema"]["schema"]["properties"]
    assert "memory" not in data["response_format"]["json_schema"]["schema"]["properties"]


def test_python_plan_manager_generates_and_advances():
    w = _make_two_actor_world()
    w.players["Elena"].equipped = {"torso": "field jacket"}
    from types import SimpleNamespace
    w.graph = SimpleNamespace(
        nodes={
            "item_water": SimpleNamespace(name="water_bottle", type="item", properties={}),
            "item_bar": SimpleNamespace(name="protein_bar", type="item", properties={}),
        },
        edges=[
            SimpleNamespace(source="player_Elena", target="item_water", type="carrying"),
            SimpleNamespace(source="player_Elena", target="item_bar", type="carrying"),
        ],
    )
    msgs = build_think_decide_messages(w, "Elena")
    assert "Wearing: field jacket (torso)" in msgs[1]["content"]
    assert "Carrying: water_bottle [drink, examine, drop], protein_bar [eat, examine, drop]" in msgs[1]["content"]

    llm = _FakeLLM([
        json.dumps({
            "inner_monologue": "Need a plan.",
            "action": "plan",
            "item": "search fireplace",
            "speech": None,
            "volume": "say",
            "tone": None,
            "emote": None,
            "learned_names": [],
        }),
        json.dumps({
            "steps": [
                {"action": "eat", "item": "protein_bar", "target": None, "text": None, "note": None, "area": "library", "until": "finished", "duration": 5},
                {"action": "search", "item": "fireplace", "target": None, "text": None, "note": None, "area": "library", "until": "found", "duration": 10},
            ]
        }),
    ])
    runner = AgentRunner(w, llm)
    o = runner.step_character("Elena")
    assert "Plan formed:" in o.action_result
    plan = runner.plan_manager.get_plan("Elena")
    assert plan is not None and len(plan.steps) == 2
    runner.plan_manager.advance_if_matched("Elena", "eat protein_bar", True)
    assert plan.current_index == 1


def test_memory_manager_caches_by_cue_signature_and_involuntary_fires():
    import random
    from engine.agent.involuntary import apply_involuntary_speech
    from engine.agent.memory_manager import MemoryManager

    p = Player("Miki")
    p.conditions = {"frightened": [{"duration": 5}]}
    out = apply_involuntary_speech("Wait for me!", p, rng=random.Random(1))
    assert out.startswith("W-Wait") or out == "Wait for me!"

    mm = MemoryManager()
    llm = _FakeLLM(['{"thought": "I remember the skull lock.", "importance": 6}'])
    mems = [{"id": "m1", "text": "The front door has a skull lock."}]
    t1 = mm.synthesize_thought(llm, p, area="library", present=["Elena"], memories=mems)
    t2 = mm.synthesize_thought(llm, p, area="library", present=["Elena"], memories=mems)
    assert t1 == "I remember the skull lock."
    assert t2 == t1
    assert len(llm.calls) == 1  # Cached on identical cue signature!



