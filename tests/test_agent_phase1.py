"""Unit tests for Phase 1 Python agent foundation (engine/agent/)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from engine.agent import (
    AGENT_ACTION,
    AGENT_REACT,
    LLMClient,
    LLMConfig,
    parse_turn_response,
    repair_json,
)


def test_schemas_include_tone_and_exclude_legacy_memory_emotion():
    for schema_wrap in (AGENT_ACTION, AGENT_REACT):
        props = schema_wrap["json_schema"]["schema"]["properties"]
        req = schema_wrap["json_schema"]["schema"]["required"]
        assert "tone" in props and "tone" in req
        assert "memory" not in props
        assert "emotion" not in props


def test_parse_turn_response_handles_clean_and_truncated_json():
    raw = """<think>let me think</think>
    ```json
    {"inner_monologue":"Checking the door.","action":"go","target":"dining_room_door","speech":"Wait up!","volume":"shout","tone":"sarcastic","emote":"glances back","learned_names":["Miki"]}
    ```"""
    parsed = parse_turn_response(raw)
    assert parsed.parse_error is None
    assert parsed.action == "go"
    assert parsed.target == "dining_room_door"
    assert parsed.speech == "Wait up!"
    assert parsed.speech_volume == "shout"
    assert parsed.speech_tone == "sarcastic"
    assert parsed.learned_names == ["Miki"]

    # Truncated JSON repair
    trunc = '{"inner_monologue":"Almost done","action":"wait","speech":"Hold on'
    obj, repaired = repair_json(trunc)
    assert repaired is True
    assert obj is not None and obj["action"] == "wait"


def test_llm_client_json_prefill_prepends_opening_brace():
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "model": "gemma-4-e4b",
        "choices": [{"message": {"content": '"action":"wait"}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    client = LLMClient(LLMConfig(model="gemma-4-e4b", suppress_local_thinking=True))
    with patch("engine.agent.llm_client.requests.post", return_value=fake_resp) as mock_post:
        res = client.chat([{"role": "user", "content": "hi"}], response_format=AGENT_ACTION)
        sent_msgs = mock_post.call_args.kwargs["json"]["messages"]
        assert sent_msgs[-1] == {"role": "assistant", "content": "{"}
        assert res.content == '{"action":"wait"}'
