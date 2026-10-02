"""bug-512: /api/tags/validate must not invent near-misses for short ids.

The old matcher used difflib at cutoff 0.6, which proposed ``underwear`` for
``wanderer`` and ``footwear`` for ``fear``. A caller that trusted the
suggestion wrote a worse tag than the one it rejected. A suggestion must now
clear a higher ratio *and* be close in length, and ``None`` means "no idea".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from routes.helpers import closest_tag_match

CANDIDATES = [
    "underwear", "footwear", "evidence", "hosiery", "water", "ghost",
    "mansion", "tool", "mechanism", "hidden_door", "blackwood_mansion",
]


def test_reported_nonsense_pairs_are_rejected():
    for bad in ("wanderer", "fear", "silence", "hostile", "master", "chaos", "attention"):
        assert closest_tag_match(bad, CANDIDATES) is None, bad


def test_real_inflections_are_kept():
    assert closest_tag_match("tools", CANDIDATES) == "tool"
    assert closest_tag_match("mechanisms", CANDIDATES) == "mechanism"


def test_typo_within_a_shorter_id_suggests():
    assert closest_tag_match("blackwod_mansion", CANDIDATES) == "blackwood_mansion"


def test_length_guard_rejects_a_wildly_longer_candidate():
    assert closest_tag_match("cat", ["catalogue"]) is None


def test_empty_input_has_no_suggestion():
    assert closest_tag_match("", CANDIDATES) is None
    assert closest_tag_match("tool", []) is None


def test_route_returns_null_for_no_idea():
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    resp = client.get("/api/tags/validate?tags=wanderer,fear,tools,mechanisms")
    assert resp.status_code == 200
    payload = resp.get_json()
    unknown = {u["tag"]: u["suggestion"] for u in payload["unknown"]}
    assert unknown["wanderer"] is None
    assert unknown["fear"] is None
    assert unknown["tools"] == "tool"
    assert unknown["mechanisms"] == "mechanism"
