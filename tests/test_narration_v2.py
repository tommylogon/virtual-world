"""Unit tests for Narration v2 and the Director Pass (task-692)."""
import json
import re
from pathlib import Path

from engine.narration import (
    BATCH_FILLER_MESSAGES,
    is_batch_filler,
    resolve_action_message_precedence,
    director_pass,
)


def test_authorship_predicate_and_generator_string_counts():
    """Assert the count of messages appearing in the generator scripts is 8,
    and distinct generator strings in items is 8."""
    tool_files = list(Path("tools").glob("item_content_pass*.py"))
    assert len(tool_files) >= 1, "Expected tools/item_content_pass*.py scripts to exist"

    found_in_tools = set()
    for tf in tool_files:
        content = tf.read_text(encoding="utf-8", errors="replace")
        matches = re.findall(r'(?:success_message|message)\s*=\s*["\']([^"\']+)["\']', content)
        for m in matches:
            found_in_tools.add(m)

    assert len(found_in_tools) == 8, f"Expected exactly 8 generator messages in tools, got {len(found_in_tools)}"
    assert found_in_tools == set(BATCH_FILLER_MESSAGES)


def test_protein_bar_distinct_message_precedence():
    """Individually authored success_message (like protein bar on_eat) must outrank
    generated narration in AI mode, and must be read from effects[].params.success_message,
    not the empty outer trigger field."""
    protein_bar_file = Path("data/library/items/protein_bar.json")
    assert protein_bar_file.exists()
    data = json.loads(protein_bar_file.read_text(encoding="utf-8"))

    # on_eat is triggers[1]
    trigger = data["triggers"][1]
    assert trigger["trigger_type"] == "on_eat"

    # Outer trigger success_message is empty
    outer_msg = trigger.get("success_message", "")
    assert not outer_msg, "Outer triggers[].success_message is expected to be empty"

    # Inner effect param has the real authored message
    effect_param_msg = trigger["effects"][0]["params"]["success_message"]
    assert "dry and chalky" in effect_param_msg
    assert not is_batch_filler(effect_param_msg)

    # In AI mode, the authored message must outrank generated narration
    chosen_msg, source = resolve_action_message_precedence(
        item_props=data,
        generated_narration="You take a bite of food.",
        action_name="eat",
    )
    assert source == "authored"
    assert chosen_msg == effect_param_msg


def test_batch_filler_can_be_replaced_by_generated_narration():
    """Batch filler items (carrying e.g. 'You eat it. Better than nothing...')
    can be replaced by generated narration in AI mode."""
    filler_msg = "You eat it. Better than nothing and not much more."
    assert is_batch_filler(filler_msg)

    dummy_item = {
        "triggers": [
            {
                "effects": [
                    {
                        "params": {
                            "success_message": filler_msg
                        }
                    }
                ]
            }
        ]
    }

    # With generated narration provided, filler is superseded
    chosen_msg, source = resolve_action_message_precedence(
        item_props=dummy_item,
        generated_narration="The acorn tastes earthy and bitter.",
    )
    assert source == "generated"
    assert chosen_msg == "The acorn tastes earthy and bitter."

    # Without generated narration, filler is retained as fallback
    fallback_msg, fallback_source = resolve_action_message_precedence(
        item_props=dummy_item,
        generated_narration=None,
    )
    assert fallback_source == "filler"
    assert fallback_msg == filler_msg


def test_human_override_outranks_everything():
    """Human override in player mode outranks both authored messages and generated narration."""
    dummy_item = {
        "triggers": [
            {
                "effects": [
                    {
                        "params": {
                            "success_message": "An authored line from a designer."
                        }
                    }
                ]
            }
        ]
    }
    chosen_msg, source = resolve_action_message_precedence(
        item_props=dummy_item,
        human_override="The player wrote this custom line.",
        generated_narration="AI generated line.",
    )
    assert source == "human_override"
    assert chosen_msg == "The player wrote this custom line."


def test_director_pass_preserves_facts_for_agent_prompt():
    """The director pass combines prose and mechanical facts so an agent can still
    act on Hunger -12 or HP deltas."""
    result = director_pass(
        actor_name="sammy lopez",
        action="eat granola_bar",
        result_output="You eat the granola_bar.",
        system_messages=["Hunger -12", "Energy +5"],
        narration_mode="ai",
        generated_narration="Sammy takes a cautious bite of the dry bar.",
    )

    assert result["actor"] == "sammy lopez"
    assert result["narration"] == "Sammy takes a cautious bite of the dry bar."
    assert "Hunger -12" in result["facts"]
    assert "Energy +5" in result["facts"]
    # combined_for_prompt keeps facts for agent prompt context
    assert "(Hunger -12)" in result["combined_for_prompt"]
    assert "(Energy +5)" in result["combined_for_prompt"]


def test_regression_bug_518_actor_attribution():
    """NPC action results must carry the NPC's name and not default to You."""
    result = director_pass(
        actor_name="kyrie johansen",
        action="use protein_bar",
        result_output="You use the protein_bar.",
        narration_mode="none",
    )
    assert result["actor"] == "kyrie johansen"


def test_cursed_key_flow():
    """The cursed key scenario across all three modes:
    - none: mechanical output, fact preserved
    - ai: atmospheric prose, fact preserved
    - player: human draft edit, fact preserved
    """
    key_props = {
        "triggers": [
            {
                "trigger_type": "on_take",
                "effects": [
                    {
                        "type": "apply_condition",
                        "params": {
                            "condition": "curse_frost",
                            "success_message": "As your fingers touch the cold metal, an unnatural chill spreads through your veins."
                        }
                    }
                ]
            }
        ]
    }

    # 1. Mode: none
    res_none = director_pass(
        actor_name="jake",
        action="take cursed_key",
        result_output="You take the cursed_key.",
        system_messages=["Condition applied: curse_frost"],
        narration_mode="none",
        item_props=key_props,
    )
    assert res_none["narration"] == "You take the cursed_key."
    assert "(Condition applied: curse_frost)" in res_none["combined_for_prompt"]

    # 2. Mode: ai
    res_ai = director_pass(
        actor_name="jake",
        action="take cursed_key",
        result_output="You take the cursed_key.",
        system_messages=["Condition applied: curse_frost"],
        narration_mode="ai",
        item_props=key_props,
    )
    assert "unnatural chill spreads" in res_ai["narration"]
    assert "(Condition applied: curse_frost)" in res_ai["combined_for_prompt"]

    # 3. Mode: player (with human rewrite)
    res_player = director_pass(
        actor_name="jake",
        action="take cursed_key",
        result_output="You take the cursed_key.",
        system_messages=["Condition applied: curse_frost"],
        narration_mode="player",
        item_props=key_props,
        human_override="Frost creeps over Jake's knuckles the instant he lifts the iron key.",
    )
    assert res_player["narration"] == "Frost creeps over Jake's knuckles the instant he lifts the iron key."
    assert "(Condition applied: curse_frost)" in res_player["combined_for_prompt"]
