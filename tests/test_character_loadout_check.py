"""Tests for tools/character_loadout_check.py.

The tool exists because bad character data fails SILENTLY: a dict in an `equipped`
slot takes down `GET /api/state` only once somebody refreshes that character from
the library, and a non-list slot is dropped by import with no error at all. A
checker that misses those cases would be worse than none, so each rule is pinned
here against the shape of data that actually exists in the library.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import character_loadout_check as clc


def _char(name="Test Char", equipped=None, inventory=None):
    return {
        "name": name,
        "equipped": equipped if equipped is not None else {},
        "inventory": inventory if inventory is not None else [],
    }


def _check(data, library_ids=None):
    path = Path(f"{data['name']}.json")
    return clc.check_character(path, data, set(library_ids or ()))


def _ids(data, library_ids=None):
    return {cid for cid, _ in _check(data, library_ids)}


# ───────────────────────── the three silent failures ─────────────────────────


def test_dict_entry_in_equipped_is_an_error():
    """The one that 500s /api/state on refresh-to-world."""
    data = _char(equipped={"hand_right": [{"name": "hammer", "node_id": "item_hammer"}]})
    assert "equipped_dict_entry" in _ids(data)


def test_non_list_slot_is_an_error():
    """Import `continue`s on non-list slots, so the gear vanishes silently."""
    data = _char(equipped={"hand_right": "item_hammer"})
    assert "equipped_slot_not_list" in _ids(data)


def test_equipped_id_without_inventory_is_an_error():
    """Import resolves ids against carrying edges, so this slot ends up empty."""
    data = _char(equipped={"head": ["item_cap"]}, inventory=[])
    assert "equipped_id_not_in_inventory" in _ids(data)


def test_runtime_markers_are_not_treated_as_node_ids():
    """`__multi_slot_<id>` is written by the equipment system at runtime, not
    authored. Flagging it would make the checker cry wolf on live saves."""
    data = _char(
        equipped={"hands": ["__multi_slot_item_hammer"]},
        inventory=[{"node_id": "item_hammer", "properties": {"equip_slots": ["hands"]}}],
    )
    assert "equipped_id_not_in_inventory" not in _ids(data)


# ───────────────────────────── the warnings ──────────────────────────────────


def test_name_differing_only_by_case_or_punctuation_is_not_flagged():
    """`miki-takahashi.json` vs "miki takahashi" and `Miki.json` vs "miki" are the
    same identity. Flagging them would bury the finding that matters, which is a
    file renamed to a personal name whose `name` field still holds the old role."""
    assert "name_does_not_match_file" not in _ids(_char(name="miki-takahashi"))
    assert "name_does_not_match_file" not in _ids(_char(name="Miki"))
    assert "name_does_not_match_file" not in _ids(_char(name="dr. eliza reed"))


def test_genuinely_different_name_is_flagged():
    """The real case from the library: renamed to a personal name, `name` field
    still holds the old role, so a browser save writes the old name back out as a
    second file (task-665)."""
    found = _check(_char(name="Eldenford Merchant"))
    assert ("name_does_not_match_file", "file 'Eldenford Merchant' vs name 'Eldenford Merchant'") not in found

    found = clc.check_character(Path("Pell Ardin.json"), _char(name="Eldenford Merchant"), set())
    assert ("name_does_not_match_file", "file 'Pell Ardin' vs name 'Eldenford Merchant'") in found


def test_equipping_into_an_undeclared_slot_is_flagged():
    data = _char(
        equipped={"torso": ["item_apron"]},
        inventory=[{"node_id": "item_apron", "properties": {"equip_slots": ["hands"]}}],
    )
    assert "slot_not_declared" in _ids(data)


def test_declared_slot_is_accepted():
    data = _char(
        equipped={"torso": ["item_apron"]},
        inventory=[{"node_id": "item_apron", "properties": {"equip_slots": ["torso", "hands"]}}],
    )
    assert "slot_not_declared" not in _ids(data)


def test_empty_equip_slots_does_not_trip_the_slot_check():
    """Item declares nothing, so there is nothing to disagree with."""
    data = _char(
        equipped={"torso": ["item_apron"]},
        inventory=[{"node_id": "item_apron", "properties": {"equip_slots": []}}],
    )
    assert "slot_not_declared" not in _ids(data)


def test_unknown_library_id_is_flagged_only_when_absent_from_the_library():
    data = _char(inventory=[{"node_id": "item_x", "library_id": "not_in_library", "properties": {}}])
    assert "unknown_library_id" in _ids(data)
    assert "unknown_library_id" not in _ids(data, library_ids={"not_in_library"})


def test_missing_node_id_and_properties_are_flagged():
    ids = _ids(_char(inventory=[{"name": "thing"}]))
    assert "missing_node_id" in ids
    assert "missing_properties" in ids


def test_clean_character_produces_nothing():
    data = _char(
        name="Clean",
        equipped={"torso": ["item_apron"]},
        inventory=[{"node_id": "item_apron", "name": "apron", "properties": {"equip_slots": ["torso"]}}],
    )
    assert _check(data) == []


# ─────────────────── template-aware resolution (string refs) ─────────────────


def _check_with_templates(data, templates):
    return clc.check_character(Path(f"{data['name']}.json"), data, templates)


def test_string_inventory_ref_equipped_by_library_id_is_accepted():
    """The canonical authored shape: inventory is a library-id ref and equipped
    names it, resolved against the template's equip_slots."""
    data = _char(equipped={"hand_right": ["goblin_cleaver"]},
                 inventory=["goblin_cleaver"])
    templates = {"goblin_cleaver": {"name": "Goblin Cleaver",
                                    "equip_slots": ["hand_right"]}}
    assert _check_with_templates(data, templates) == []


def test_library_id_equipped_into_an_undeclared_slot_is_flagged():
    data = _char(equipped={"torso": ["goblin_cleaver"]},
                 inventory=["goblin_cleaver"])
    templates = {"goblin_cleaver": {"name": "Goblin Cleaver",
                                    "equip_slots": ["hand_right"]}}
    ids = {cid for cid, _ in _check_with_templates(data, templates)}
    assert "slot_not_declared" in ids


def test_library_id_entry_without_inline_properties_does_not_warn():
    """A library-id-backed entry takes its props from the template, so absent
    inline `properties` is not a defect while the id resolves."""
    data = _char(inventory=[{"library_id": "scavenged_plate", "node_id": "item_x"}])
    templates = {"scavenged_plate": {"name": "Plate", "equip_slots": ["torso"]}}
    ids = {cid for cid, _ in _check_with_templates(data, templates)}
    assert "missing_properties" not in ids


# ─────────────────────────────── the tool itself ─────────────────────────────


def test_check_ids_are_all_declared():
    """An undeclared id would be reported with no severity and no explanation,
    which is how a rule silently stops being enforced."""
    for cid in clc.CHECKS:
        assert clc.CHECKS[cid][0] in (clc.ERROR, clc.WARN), cid
        assert clc.CHECKS[cid][1], f"{cid} has no label"
        assert clc.CHECKS[cid][2], f"{cid} has no explanation"


def test_normalise_identity_folds_case_and_punctuation():
    assert clc._normalise_identity("miki-takahashi") == clc._normalise_identity("miki takahashi")
    assert clc._normalise_identity("Miki") == clc._normalise_identity("miki")
    assert clc._normalise_identity("Pell Ardin") != clc._normalise_identity("Eldenford Merchant")
    # A title is NOT folded away, and should not be: a browser save writes
    # "<name>.json", so "dr. eliza reed" produces a different file from
    # "eliza-reed.json". That is exactly the duplicate this check exists for.
    assert clc._normalise_identity("dr. eliza reed") != clc._normalise_identity("eliza-reed")


def test_signature_distinguishes_check_and_file():
    assert (clc._signature("equipped_dict_entry", "Lyrie.json")
            != clc._signature("equipped_dict_entry", "nia.json"))
    assert (clc._signature("equipped_dict_entry", "Lyrie.json")
            != clc._signature("missing_node_id", "Lyrie.json"))


def test_baseline_round_trip_ignores_comment_lines(tmp_path, monkeypatch):
    """Without filtering `#`, the header is read as findings and every run reports
    stale entries forever -- which reads as 'N findings are now fixed'."""
    monkeypatch.setattr(clc, "BASELINE_PATH", tmp_path / "baseline.txt")
    sigs = {clc._signature("equipped_dict_entry", "Lyrie.json")}
    clc._write_baseline(sigs)
    assert any(l.startswith("#") for l in clc.BASELINE_PATH.read_text(encoding="utf-8").splitlines())
    assert clc._read_baseline() == sigs


def test_read_baseline_of_missing_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(clc, "BASELINE_PATH", tmp_path / "absent.txt")
    assert clc._read_baseline() == set()


def test_scan_survives_an_unparseable_entry(tmp_path, monkeypatch):
    """A malformed file must not abort the whole run."""
    chars = tmp_path / "chars"
    chars.mkdir()
    (chars / "broken.json").write_text("{not json", encoding="utf-8")
    (chars / "fine.json").write_text('{"name": "fine", "equipped": {}, "inventory": []}', encoding="utf-8")
    monkeypatch.setattr(clc, "CHAR_DIR", chars)
    monkeypatch.setattr(clc, "ITEM_DIR", chars)
    result = clc.scan()
    assert result["scanned"] == 1
    assert result["findings"]["unparseable"] == [("broken.json", "not a JSON object")]


@pytest.mark.parametrize("severity", [clc.ERROR, clc.WARN])
def test_severities_are_distinct_constants(severity):
    assert severity in ("ERROR", "WARN")


# ─────────────────────── the declaration, and the gate ───────────────────────


def test_rules_are_declared_in_one_module():
    """The reasons live in tools/character_loadout_rules.py, not inline; the
    checker and its tests must read the same table (task-666)."""
    import character_loadout_rules as rules

    assert clc.CHECKS is rules.CHECKS
    assert clc.ERROR == rules.ERROR
    assert clc.WARN == rules.WARN


def test_the_shipped_library_has_no_new_loadout_findings(monkeypatch):
    """This is the pre-commit path: pytest is what runs before a commit here, so
    a bad entry cannot be committed without the gate being consulted. Baseline
    entries are accepted debt; a NEW finding fails right here. Point the scanner
    at absolute paths so the assertion cannot pass vacuously from the wrong cwd.
    """
    root = Path(__file__).resolve().parent.parent
    monkeypatch.setattr(clc, "CHAR_DIR", root / "data" / "library" / "characters")
    monkeypatch.setattr(clc, "ITEM_DIR", root / "data" / "library" / "items")

    result = clc.scan()
    assert result["scanned"] > 0, "the shipped character library was not found"

    all_sigs = {
        clc._signature(cid, fname)
        for cid, entries in result["findings"].items()
        for fname, _detail in entries
    }
    new = sorted(all_sigs - clc._read_baseline())
    assert not new, (
        f"new character-loadout findings not in {clc.BASELINE_PATH}: {new}. "
        "Run --report for detail; --update-baseline only if the debt is deliberate."
    )