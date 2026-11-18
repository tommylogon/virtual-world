"""Drift guard and unit tests for the actions registry (task-491, task-988, bug-598, bug-600).

Ensures that every action surface (dispatcher, trigger UI, agent normalizer,
bracket builder, prompt prose, and autocomplete) derives its actions from the
single scoped registry in `engine/actions.py`, and fails when any surface
declares an action the registry lacks or when the generated client mirror drifts.
"""

import re
import subprocess
import sys
from pathlib import Path
import pytest

import engine.actions as act_reg
from engine.action_tiers import VERB_TIERS
from engine.pleasure_actions import INTIMACY_VERBS

ROOT = Path(__file__).resolve().parent.parent


def test_registry_uniqueness_and_canonical_specs():
    """Every registered action has a unique ID, valid tier, and no colliding aliases."""
    ids = set()
    all_names = {}
    for spec in act_reg.ACTIONS:
        assert spec.id, "ActionSpec must have a non-empty id"
        assert spec.id not in ids, f"Duplicate action ID registered: {spec.id}"
        ids.add(spec.id)
        assert spec.cost_key in ("free", "minor", "major", "activity"), f"Invalid cost tier: {spec.cost_key}"

        for name in spec.all_names:
            name_lower = name.lower()
            if name_lower in all_names:
                pytest.fail(f"Action collision: '{name_lower}' is declared in {spec.id} and {all_names[name_lower]}")
            all_names[name_lower] = spec.id


def test_mature_actions_match_intimacy_source():
    """Mature actions must match INTIMACY_VERBS exactly."""
    reg_mature = set(act_reg.mature_actions())
    intimacy_set = set(INTIMACY_VERBS)
    assert reg_mature == intimacy_set, f"Mature actions mismatch: diff={reg_mature ^ intimacy_set}"


def test_bracket_order_matches_expected_sequence():
    """BRACKET_ORDER must match the 13 canonical item action brackets in order."""
    expected = [
        "take", "use", "use_on", "open", "close", "eat", "drink",
        "read", "wear", "remove", "toggle", "drop", "examine"
    ]
    assert act_reg.bracket_order() == expected
    for action_name in expected:
        spec = act_reg.get_action(action_name)
        assert spec is not None, f"Bracket order action '{action_name}' is not registered"


def test_action_tiers_coverage():
    """Every action classified in engine/action_tiers.py must be registered in engine/actions.py."""
    registered_names = set(act_reg.all_actions(include_aliases=True, mature=True))
    missing = set(VERB_TIERS.keys()) - registered_names
    assert not missing, f"Actions in action_tiers missing from actions registry: {missing}"


def test_autocomplete_groups_registered():
    """Every action grouped in AUTOCOMPLETE_GROUPS must be in the registry."""
    registered_names = set(act_reg.all_actions(include_aliases=True, mature=True))
    for group_name, actions in act_reg.AUTOCOMPLETE_GROUPS.items():
        for a in actions:
            assert a in registered_names, f"Action '{a}' in autocomplete group '{group_name}' not registered"


def test_scope_queries():
    """actions_for_scope filters actions accurately."""
    item_actions = {s.id for s in act_reg.actions_for_scope("item")}
    for required in ("take", "use", "open", "close", "eat", "drink", "drop", "toggle", "combine", "split"):
        assert required in item_actions, f"Required item action '{required}' missing from item scope"

    way_actions = {s.id for s in act_reg.actions_for_scope("way")}
    for required in ("go", "dash", "climb", "crawl", "jump", "swim", "dive", "open", "close"):
        assert required in way_actions, f"Required way action '{required}' missing from way scope"

    intimacy_actions = {s.id for s in act_reg.actions_for_scope("intimacy")}
    assert intimacy_actions == set(INTIMACY_VERBS)


def test_alias_resolution():
    """get_action resolves aliases to their canonical specs."""
    assert act_reg.get_action("pickup").id == "take"
    assert act_reg.get_action("consume").id == "eat"
    assert act_reg.get_action("quaff").id == "drink"
    assert act_reg.get_action("use_on").id == "use"
    assert act_reg.get_action("walk").id == "go"
    assert act_reg.get_action("move_to").id == "go"
    assert act_reg.get_action("ride").id == "mount"
    assert act_reg.get_action("search").id == "examine"
    assert act_reg.get_action("nonexistent_action_xyz") is None


def test_generated_js_file_in_sync():
    """tools/actions_index.py --check must pass with exit code 0."""
    result = subprocess.run(
        [sys.executable, "tools/actions_index.py", "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"--check failed:\n{result.stderr}\n{result.stdout}"


def test_action_normalizer_drift_guard():
    """All actions declared in action-normalizer.ts/js must be in the registry."""
    an_ts = ROOT / "static" / "js" / "agent" / "action-normalizer.ts"
    text = an_ts.read_text(encoding="utf-8")

    registered = set(act_reg.all_actions(include_aliases=True, mature=True))

    m = re.search(r"VALID_ACTIONS\s*=\s*_registry\?\.VALID_SET\s*\|\|\s*new Set\(_registry\?\.VALID_ACTIONS\s*\|\|\s*\[([^\]]+)\]\)", text)
    if m:
        fallback_actions = re.findall(r"'([a-z_]+)'", m.group(1))
        missing = set(fallback_actions) - registered
        assert not missing, f"action-normalizer.ts fallback declares actions missing from registry: {missing}"


def test_contextual_actions_drift_guard():
    """All actions in contextual-actions.ts BRACKET_ORDER must match registry bracket_order."""
    ca_ts = ROOT / "static" / "js" / "agent" / "prompt-builder" / "contextual-actions.ts"
    text = ca_ts.read_text(encoding="utf-8")
    m = re.search(r"BRACKET_ORDER\s*=\s*_registryBO\s*\|\|\s*\[([^\]]+)\]", text)
    assert m, "BRACKET_ORDER declaration not found in contextual-actions.ts"
    ts_brackets = re.findall(r"'([a-z_]+)'", m.group(1))
    assert ts_brackets == act_reg.bracket_order(), "contextual-actions.ts BRACKET_ORDER diverged from registry"


def test_action_handlers_dispatch_prefixes_in_registry():
    """Every action prefix dispatched by routes/action_handlers.py must be registered."""
    ah_file = ROOT / "routes" / "action_handlers.py"
    text = ah_file.read_text(encoding="utf-8")

    prefixes = set()
    for match in re.finditer(r"(?:cmd|command|c)\.startswith\(\s*\(?([^\)]+)\)?\s*\)", text):
        raw = match.group(1)
        for s in re.findall(r"""['"]([a-z_ ]+)['"]""", raw):
            parts = s.strip().split()
            if parts:
                prefixes.add(parts[0])

    for match in re.finditer(r"(?:cmd|command|c)\s*(?:==|\bin\b)\s*\(?([^\n:\)]+)\)?", text):
        raw = match.group(1)
        for s in re.findall(r"""['"]([a-z_ ]+)['"]""", raw):
            parts = s.strip().split()
            if parts:
                prefixes.add(parts[0])

    # Multi-word phrase tokens or non-action strings in action_handlers.py
    non_commands = {"characters", "allowed", "feel", "grope", "hang", "end"}
    prefixes = prefixes - non_commands

    registered = set(act_reg.all_actions(include_aliases=True, mature=True))
    missing = prefixes - registered
    assert not missing, f"action_handlers.py dispatches prefixes missing from actions registry: {missing}"


def test_drift_guard_catches_unregistered_action():
    """Drift guard correctly flags an unregistered action."""
    unregistered = "fake_action_qwerty"
    assert not act_reg.is_valid_action(unregistered)
    assert act_reg.get_action(unregistered) is None


def test_phone_actions_registered():
    """Phone actions call, answer, hangup, and text (alias message) are registered."""
    for action_name in ("call", "answer", "hangup", "text", "message"):
        assert act_reg.is_valid_action(action_name), f"Phone action '{action_name}' should be valid"
    assert act_reg.get_action("message").id == "text"
    assert act_reg.get_action("call").cost_key == "free"
    assert act_reg.get_action("answer").cost_key == "free"
    assert act_reg.get_action("hangup").cost_key == "free"
    assert act_reg.get_action("text").cost_key == "free"


def test_swim_dive_mount_dismount_ride_saddle_registered_and_dispatched():
    """bug-600: swim, dive, mount, dismount, ride, and saddle are registered and handled."""
    for action_name in ("swim", "dive", "mount", "dismount", "ride", "saddle"):
        assert act_reg.is_valid_action(action_name), f"Traversal action '{action_name}' should be registered"
    from app import create_app
    from area import Area
    from graph import Node
    from player import Player

    app = create_app({"TESTING": True})
    world = app.world
    world.movement.add_area(Area("Stable", "A warm stable.", []))
    rider = Player("Rider")
    rider.current_area = "Stable"
    world.add_player(rider)
    horse = Player("Storm")
    horse.current_area = "Stable"
    horse.tags = ["horse", "animal", "mountable"]
    world.add_player(horse)
    world.graph.add_node(Node(world._player_node_id("Storm"), "character", "Storm", {"tags": ["horse", "mountable"]}))
    world.set_active_player("Rider")

    client = app.test_client()
    r_saddle = client.post("/api/action", json={"action": "saddle Storm", "character": "Rider"})
    assert r_saddle.status_code == 200 and "You saddle Storm." in r_saddle.get_json()["output"]

    r_mount = client.post("/api/action", json={"action": "mount Storm", "character": "Rider"})
    assert r_mount.status_code == 200 and "You mount Storm." in r_mount.get_json()["output"]
    assert rider.mounted_on == "Storm"

    r_dismount = client.post("/api/action", json={"action": "dismount", "character": "Rider"})
    assert r_dismount.status_code == 200 and "You dismount from Storm." in r_dismount.get_json()["output"]
    assert rider.mounted_on is None
