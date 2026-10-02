"""Tests for tools/scenario_tag_check.py — the gap bug-513 names.

`tools/lint_library.py` checks interest/fear tags in `data/library/` only, so a
scenario save could carry any number of tags that can never match and nothing
reported it. This pins the *rules*, which are the part that has to match the
runtime, and then runs the checker against the shipped scenarios so a NEW dead
tag fails the suite.

The rule most likely to be got wrong: an interest matches **item** tags only,
while a fear also matches area and character tags plus trait keys. If interests
were checked against the same wide vocabulary as fears, a tag that can never
score would look live.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import scenario_tag_check as stc  # noqa: E402


def _scenario(tmp_path, players, nodes=None):
    payload = {
        "players": players,
        "graph": {"nodes": nodes or {}, "edges": []},
    }
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _check(path, item_tags=(), fear_tags=()):
    return stc.scan_scenario(path, set(item_tags), set(fear_tags))


def _ids(findings, check_id):
    return sorted(tag for cid, _key, tag in findings if cid == check_id)


# ── interests match item tags, and nothing else ────────────────────────────


def test_interest_matched_by_a_library_item_is_live(tmp_path):
    path = _scenario(tmp_path, {"Belne": {"interest_tags": ["bread"]}})
    assert _ids(_check(path, item_tags={"bread"}), "dead_interests") == []


def test_interest_matched_by_a_scenario_item_node_is_live(tmp_path):
    nodes = {"item_coin": {"type": "item", "properties": {"tags": ["coin"]}}}
    path = _scenario(tmp_path, {"Leslie": {"interest_tags": ["coin"]}}, nodes=nodes)
    assert _ids(_check(path), "dead_interests") == []


def test_interest_matching_only_an_area_tag_is_dead(tmp_path):
    """The whole point of the narrow interest vocabulary: an area is not an item,
    so the attention list never sees this interest."""
    nodes = {"area_camp": {"type": "area", "properties": {"tags": ["marsh"]}}}
    path = _scenario(tmp_path, {"Croak-Mother": {"interest_tags": ["marsh"]}}, nodes=nodes)
    assert _ids(_check(path), "dead_interests") == ["marsh"]


def test_interest_nothing_carries_is_dead(tmp_path):
    path = _scenario(tmp_path, {"Arix": {"interest_tags": ["jokes", "chaos"]}})
    assert _ids(_check(path), "dead_interests") == ["chaos", "jokes"]


# ── fears span every fear source ───────────────────────────────────────────


def test_fear_matched_by_an_area_tag_is_live(tmp_path):
    nodes = {"area_ruins": {"type": "area", "properties": {"tags": ["ruins"]}}}
    path = _scenario(tmp_path, {"Farmer": {"fear_tags": ["ruins"]}}, nodes=nodes)
    assert _ids(_check(path), "dead_fears") == []


def test_fear_matched_by_a_character_tag_is_live(tmp_path):
    path = _scenario(tmp_path, {
        "Snarl": {"tags": ["goblin"]},
        "Farmer": {"fear_tags": ["goblin"]},
    })
    assert _ids(_check(path), "dead_fears") == []


def test_fear_matched_by_a_trait_key_is_live(tmp_path):
    path = _scenario(tmp_path, {
        "Captain": {"traits": {"guard": True}},
        "Farmer": {"fear_tags": ["guard"]},
    })
    assert _ids(_check(path), "dead_fears") == []


def test_fear_nothing_carries_is_dead(tmp_path):
    path = _scenario(tmp_path, {"Farmer": {"fear_tags": ["wyrm"]}})
    assert _ids(_check(path), "dead_fears") == ["wyrm"]


def test_fear_in_the_library_vocabulary_is_live(tmp_path):
    path = _scenario(tmp_path, {"Farmer": {"fear_tags": ["goblin"]}})
    assert _ids(_check(path, fear_tags={"goblin"}), "dead_fears") == []


def test_matching_is_case_insensitive(tmp_path):
    path = _scenario(tmp_path, {"Leslie": {"interest_tags": ["COIN"]}})
    assert _ids(_check(path, item_tags={"coin"}), "dead_interests") == []


def test_a_scenario_without_players_reports_nothing(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"graph": {"nodes": {}, "edges": []}}), encoding="utf-8")
    assert _check(path) == []


# ── the gate: a new dead tag fails, existing debt is baselined ──────────────


def test_the_shipped_scenarios_have_no_new_dead_tags(monkeypatch):
    """Absolute paths so this cannot pass vacuously from the wrong cwd. This is
    the assertion that makes bug-513 a gate rather than a one-off report."""
    monkeypatch.setattr(stc, "LIB_DIR", ROOT / "data" / "library")
    monkeypatch.setattr(stc, "SCENARIO_DIR", ROOT / "data" / "scenarios")
    monkeypatch.setattr(stc, "BASELINE_PATH",
                        ROOT / "docs" / "virtualWorld" / "World Building" / "scenario-tag-baseline.txt")

    result = stc.scan()
    assert result["scanned"] > 0, "no scenarios were found"

    all_sigs = stc._all_signatures(result["findings"])
    new = sorted(all_sigs - stc._read_baseline())
    assert not new, (
        f"new scenario dead-tag findings not in {stc.BASELINE_PATH}: {new}. "
        "Run --report for detail; --update-baseline only if the debt is deliberate."
    )


def test_signatures_are_per_tag_not_per_file():
    """Adding a brand-new dead tag to an already-dirty character must register."""
    a = stc._signature("dead_interests", "camp.json", "Belne", "jokes")
    b = stc._signature("dead_interests", "camp.json", "Belne", "chaos")
    assert a != b
    assert a != stc._signature("dead_fears", "camp.json", "Belne", "jokes")


def test_baseline_round_trip_ignores_comments(tmp_path, monkeypatch):
    monkeypatch.setattr(stc, "BASELINE_PATH", tmp_path / "baseline.txt")
    sigs = {stc._signature("dead_interests", "camp.json", "Belne", "jokes")}
    stc._write_baseline(sigs)
    assert stc._read_baseline() == sigs
