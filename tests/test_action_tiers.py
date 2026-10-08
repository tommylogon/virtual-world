"""task-352 slice 1: the action-tier classification.

The load-bearing test is `test_every_dispatched_verb_has_a_tier`: it derives the
verb set from `routes/action_handlers.py` itself, so adding a command without a
tier fails here rather than silently defaulting to `major` at runtime.
"""

import re
from pathlib import Path

from engine import action_tiers as at


REPO = Path(__file__).resolve().parent.parent
HANDLERS = REPO / "routes" / "action_handlers.py"

#: Multi-word dispatch tokens whose leading word would mis-map.
_TOKEN_EXCEPTIONS = {
    "get dressed": "dress",
    "sit down": "sit",
    "lie down": "lie",
    "lay down": "lay",
    "guess time": "guess",
    "pick up": "pick",
    "stop doing that": "stop",
    "stand up": "stand",
    "get up": "stand",
}


def _dispatched_tokens() -> set:
    src = HANDLERS.read_text(encoding="utf-8")
    tokens = set()
    for pat in (
        r'cmd\s*==\s*"([^"]+)"',
        r'cmd\.startswith\(\s*"([^"]+)"',
    ):
        tokens.update(re.findall(pat, src))
    for pat in (
        r'cmd\.startswith\(\s*\(([^)]*)\)',
        r'cmd\s+in\s*\(([^)]*)\)',
    ):
        for group in re.findall(pat, src):
            tokens.update(re.findall(r'"([^"]+)"', group))
    return tokens


def _leading_verb(token: str) -> str:
    t = token.strip().lower()
    if t in _TOKEN_EXCEPTIONS:
        return _TOKEN_EXCEPTIONS[t]
    return t.split()[0]


def test_tier_values_are_valid():
    for verb, tier in at.VERB_TIERS.items():
        assert tier in at.VALID_TIERS, f"{verb} has invalid tier {tier}"


def test_every_dispatched_verb_has_a_tier():
    missing = sorted(
        {_leading_verb(tok) for tok in _dispatched_tokens()}
        - set(at.VERB_TIERS)
    )
    assert not missing, (
        "verbs dispatched by routes/action_handlers.py with no tier in "
        f"engine/action_tiers.py: {missing}"
    )


def test_budget_shape():
    assert at.DEFAULT_BUDGET == {at.MAJOR: 1, at.MINOR: 1, at.FREE: 3, at.ACTIVITY: 1}


def test_tier_of_reads_the_table():
    assert at.tier_of("go") == at.MAJOR
    assert at.tier_of("open") == at.FREE
    assert at.tier_of("approach") == at.MINOR
    assert at.tier_of("sleep") == at.ACTIVITY
    assert at.tier_of("recall") == at.FREE


def test_tier_of_honours_per_item_override():
    class Node:
        def __init__(self, props):
            self.properties = props

    free_use = Node({"action_costs": {"use": {"tier": "free"}}})
    assert at.tier_of("use", free_use) == at.FREE
    # no override -> falls through to the verb table
    plain = Node({})
    assert at.tier_of("use", plain) == at.MAJOR


def test_tier_of_defaults_intrinsic_ability_to_minor():
    class Node:
        def __init__(self, props):
            self.properties = props

    spell = Node({"tags": ["spell"]})
    assert at.tier_of("use", spell) == at.MINOR
    # an explicit override still wins over the ability default
    spell_free = Node({"tags": ["spell"], "action_costs": {"use": {"tier": "free"}}})
    assert at.tier_of("use", spell_free) == at.FREE


def test_reset_slots_fills_the_budget():
    slots = at.reset_slots({})
    assert slots == {at.MAJOR: 1, at.MINOR: 1, at.FREE: 3, at.ACTIVITY: 1}


def test_spend_slot_prefers_exact_then_downgrades():
    slots = at.reset_slots({})
    assert [at.spend_slot(slots, at.FREE) for _ in range(3)] == [at.FREE] * 3
    assert slots[at.FREE] == 0
    # once free is spent, the minor pays, then the major
    assert at.spend_slot(slots, at.FREE) == at.MINOR
    assert at.spend_slot(slots, at.FREE) == at.MAJOR
    assert at.spend_slot(slots, at.FREE) is None


def test_major_slot_pays_for_a_minor_action():
    slots = at.reset_slots({})
    assert at.spend_slot(slots, at.MINOR) == at.MINOR
    # minor exhausted -> the major pays for the second approach
    assert at.spend_slot(slots, at.MINOR) == at.MAJOR
    assert at.spend_slot(slots, at.MINOR) is None


def test_activity_slot_does_not_downgrade():
    slots = at.reset_slots({})
    assert at.spend_slot(slots, at.ACTIVITY) == at.ACTIVITY
    assert at.spend_slot(slots, at.ACTIVITY) is None
