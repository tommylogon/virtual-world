"""Drift guard and unit tests for the action verbs registry (task-491).

Ensures that every command surface (dispatcher, trigger UI, agent normalizer,
bracket builder, prompt prose, and autocomplete) derives its verbs from the
single scoped registry in `engine/action_verbs.py`, and fails when any surface
declares a verb the registry lacks or when the generated client mirror drifts.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
import pytest

import engine.action_verbs as av
from engine.action_tiers import VERB_TIERS
from engine.pleasure_actions import INTIMACY_VERBS

ROOT = Path(__file__).resolve().parent.parent


def test_registry_uniqueness_and_canonical_specs():
    """Every registered verb has a unique ID, valid tier, and no colliding aliases."""
    ids = set()
    all_names = {}
    for spec in av.VERBS:
        assert spec.id, "VerbSpec must have a non-empty id"
        assert spec.id not in ids, f"Duplicate verb ID registered: {spec.id}"
        ids.add(spec.id)
        assert spec.cost_key in ("free", "minor", "major", "activity"), f"Invalid cost tier: {spec.cost_key}"

        for name in spec.all_names:
            name_lower = name.lower()
            if name_lower in all_names:
                pytest.fail(f"Verb collision: '{name_lower}' is declared in {spec.id} and {all_names[name_lower]}")
            all_names[name_lower] = spec.id


def test_mature_verbs_match_intimacy_source():
    """Mature verbs must match INTIMACY_VERBS exactly."""
    reg_mature = set(av.mature_verbs())
    intimacy_set = set(INTIMACY_VERBS)
    assert reg_mature == intimacy_set, f"Mature verbs mismatch: diff={reg_mature ^ intimacy_set}"


def test_bracket_order_matches_expected_sequence():
    """BRACKET_ORDER must match the 13 canonical item action brackets in order."""
    expected = [
        "take", "use", "use_on", "open", "close", "eat", "drink",
        "read", "wear", "remove", "toggle", "drop", "examine"
    ]
    assert av.bracket_order() == expected
    for verb in expected:
        spec = av.get_verb(verb)
        assert spec is not None, f"Bracket order verb '{verb}' is not registered"


def test_action_tiers_coverage():
    """Every verb classified in engine/action_tiers.py must be registered in action_verbs."""
    registered_names = set(av.all_verbs(include_aliases=True, mature=True))
    missing = set(VERB_TIERS.keys()) - registered_names
    assert not missing, f"Verbs in action_tiers missing from action_verbs: {missing}"


def test_autocomplete_groups_registered():
    """Every verb grouped in AUTOCOMPLETE_GROUPS must be in the registry."""
    registered_names = set(av.all_verbs(include_aliases=True, mature=True))
    for group_name, verbs in av.AUTOCOMPLETE_GROUPS.items():
        for v in verbs:
            assert v in registered_names, f"Verb '{v}' in autocomplete group '{group_name}' not registered"


def test_scope_queries():
    """verbs_for_scope filters verbs accurately."""
    item_verbs = {s.id for s in av.verbs_for_scope("item")}
    for required in ("take", "use", "open", "close", "eat", "drink", "drop", "toggle", "combine", "split"):
        assert required in item_verbs, f"Required item verb '{required}' missing from item scope"

    way_verbs = {s.id for s in av.verbs_for_scope("way")}
    for required in ("go", "dash", "climb", "crawl", "jump", "open", "close"):
        assert required in way_verbs, f"Required way verb '{required}' missing from way scope"

    intimacy_verbs = {s.id for s in av.verbs_for_scope("intimacy")}
    assert intimacy_verbs == set(INTIMACY_VERBS)


def test_alias_resolution():
    """get_verb resolves aliases to their canonical specs."""
    assert av.get_verb("pickup").id == "take"
    assert av.get_verb("consume").id == "eat"
    assert av.get_verb("quaff").id == "drink"
    assert av.get_verb("use_on").id == "use"
    assert av.get_verb("walk").id == "go"
    assert av.get_verb("search").id == "examine"
    assert av.get_verb("nonexistent_action_xyz") is None


def test_generated_js_file_in_sync():
    """tools/action_verbs_index.py --check must pass with exit code 0."""
    result = subprocess.run(
        [sys.executable, "tools/action_verbs_index.py", "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"--check failed:\n{result.stderr}\n{result.stdout}"


def test_action_normalizer_drift_guard():
    """All verbs declared in action-normalizer.ts/js must be in the registry."""
    an_ts = ROOT / "static" / "js" / "agent" / "action-normalizer.ts"
    text = an_ts.read_text(encoding="utf-8")

    registered = set(av.all_verbs(include_aliases=True, mature=True))

    # Match literal array in fallback
    m = re.search(r"VALID_VERBS\s*=\s*_registry\?\.VALID_SET\s*\|\|\s*new Set\(_registry\?\.VALID_VERBS\s*\|\|\s*\[([^\]]+)\]\)", text)
    if m:
        fallback_verbs = re.findall(r"'([a-z_]+)'", m.group(1))
        missing = set(fallback_verbs) - registered
        assert not missing, f"action-normalizer.ts fallback declares verbs missing from registry: {missing}"


def test_contextual_actions_drift_guard():
    """All verbs in contextual-actions.ts BRACKET_ORDER must match registry bracket_order."""
    ca_ts = ROOT / "static" / "js" / "agent" / "prompt-builder" / "contextual-actions.ts"
    text = ca_ts.read_text(encoding="utf-8")
    m = re.search(r"BRACKET_ORDER\s*=\s*_registryBO\s*\|\|\s*\[([^\]]+)\]", text)
    assert m, "BRACKET_ORDER declaration not found in contextual-actions.ts"
    ts_brackets = re.findall(r"'([a-z_]+)'", m.group(1))
    assert ts_brackets == av.bracket_order(), "contextual-actions.ts BRACKET_ORDER diverged from registry"


def test_action_handlers_dispatch_prefixes_in_registry():
    """Every command prefix dispatched by routes/action_handlers.py must be registered."""
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

    # Filter non-command strings
    non_commands = {"characters", "allowed", "feel", "grope"}
    prefixes = prefixes - non_commands

    registered = set(av.all_verbs(include_aliases=True, mature=True))
    missing = prefixes - registered
    assert not missing, f"action_handlers.py dispatches prefixes missing from action_verbs registry: {missing}"


def test_drift_guard_catches_unregistered_verb():
    """Drift guard correctly flags an unregistered verb."""
    unregistered = "fake_verb_qwerty"
    assert not av.is_valid_verb(unregistered)
    assert av.get_verb(unregistered) is None
