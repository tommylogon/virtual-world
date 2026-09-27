"""WorldPainter biome/feature taxonomy (task-497).

The shipped taxonomy must validate clean, map to the foraging vocabulary the
engine already uses, and stay extendable by data alone.
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import biomes, foraging


def _is_wild(biome_id):
    """A biome that has to satisfy the *wild-country* contract.

    Three kinds do not, for three different reasons: a **building** is a made
    place (task-561) — the inside of a smithy has no berries and no wildlife; a
    **structure** cell is not a place at all (task-562): a void has no ground to
    name a material for, and a wall is never walked on; and an **indoor room**
    (task-568) is made for the first of those reasons — a bedroom is not
    wilderness, and asking a `hallway` for a forage tag would mean writing
    fiction to satisfy a linter. Everything else is wilderness and owes a forage
    tag and distribution rules.
    """
    tags = {str(t).lower() for t in biomes.area_tags(biome_id)}
    return ("building" not in tags and biomes.NOT_A_PLACE_TAG not in tags
            and biomes.INDOOR_TAG not in tags)


def test_shipped_taxonomy_validates_clean():
    assert biomes.validate() == []


def test_every_wild_biome_has_a_tag_foraging_recognises():
    """Wild country must be forageable, or an area painted with it is barren."""
    recognized = {str(t).lower() for t in foraging.AREA_SKILL_BONUS}
    for bid in biomes.biomes():
        if not _is_wild(bid):
            continue
        tags = set(biomes.area_tags(bid))
        assert tags & recognized, f"{bid} would be barren: {sorted(tags)}"


def test_every_biome_names_known_forage_skills():
    for bid, rec in biomes.biomes().items():
        for skill in (rec.get("forage_skills") or []):
            assert str(skill).lower() in foraging.SKILL_TABLES, (bid, skill)


def test_resource_tags_come_from_the_foraging_vocabulary():
    vocab = set()
    for entries in foraging.SKILL_TABLES.values():
        for entry in entries:
            vocab |= {str(t).lower() for t in (entry.get("tags") or [])}
    for bid, entries in biomes.resource_distribution().items():
        for entry in entries:
            assert {str(t).lower() for t in entry["tags"]} <= vocab, (bid, entry)


def test_forage_bonus_is_derived_from_foraging():
    # A painted forest is foragable exactly as a hand-authored one is.
    assert biomes.forage_skill_bonus("dense_forest").get("survival", 0) > 0


def test_every_place_declares_a_surface_and_no_record_uses_floor_for_it():
    """`surface` is the ground material; `floor` is a storey index (see
    `engine/world_grid.PAINT_LAYERS`), so a taxonomy record must not use it.

    A structure cell is exempt from the surface: a void has no ground to name a
    material for, and a wall is not walked on (task-562)."""
    for bid, rec in biomes.biomes().items():
        if not _is_wild(bid) and biomes.NOT_A_PLACE_TAG in {
                str(t).lower() for t in (rec.get("tags") or [])}:
            continue
        assert rec.get("surface"), f"{bid} has no ground material"
        assert "floor" not in rec, (
            f"{bid} uses 'floor' for a material; it means the storey index")


def test_ground_surface_falls_back_and_tolerates_the_legacy_key():
    """The material falls back: a road with none stands on the biome's ground,
    and a pre-rename record that still says `floor` is still understood."""
    assert biomes.ground_surface({"surface": "stone"}) == "stone"
    assert biomes.ground_surface(None, {"surface": "sand"}) == "sand"
    assert biomes.ground_surface({}, {"surface": "sand"}) == "sand"
    assert biomes.ground_surface({"floor": "mud"}) == "mud"      # legacy
    assert biomes.ground_surface({}, {}) == biomes.DEFAULT_SURFACE
    assert biomes.forage_skill_bonus("farmland").get("survival", 0) > 0


def test_every_wild_biome_has_resource_and_hostile_rules():
    """Only wild country owes distribution rules (see `_is_wild`). A building is a
    made place and a structure cell is not a place at all; both are exempt, and the
    exemption is written down rather than an omission."""
    wild = {b for b in biomes.biomes() if _is_wild(b)}
    assert len(wild) >= 12, "the taxonomy still has wilderness in it"
    assert set(biomes.resource_distribution()) == wild
    assert set(biomes.hostile_distribution()) == wild
    # The exemptions are the validator's too, so nothing is reported.
    assert not [p for p in biomes.validate() if p.startswith("biome ")]


def test_cell_kind_reads_the_vocabulary_not_a_hardcoded_list():
    """The vocabulary decides what a cell is to movement, so a modder can add a
    `hedge` or a `turnstile` without touching the compiler (task-562)."""
    assert biomes.cell_kind("sparse_forest") == "place", "wild country is a place"
    assert biomes.cell_kind("tavern") == "place", "so is a building"
    assert biomes.cell_kind("wall") == "solid"
    assert biomes.cell_kind("void") == "solid"
    assert biomes.cell_kind("window") == "see_through"
    assert biomes.cell_kind("door") == "passable"
    # An unknown id is a *place*, not a hole: deleting the author's cell over a typo
    # would be far worse than an area that reads thin (and the compile report names
    # the unknown ids).
    assert biomes.cell_kind("no_such_biome") == "place"


def test_features_reference_known_biomes():
    for fid, rec in biomes.features().items():
        for ref in (rec.get("biomes") or []):
            assert ref in biomes.biomes(), (fid, ref)


def test_hostile_bands_are_sane():
    for bid, entries in biomes.hostile_distribution().items():
        for entry in entries:
            assert entry["kind"] in biomes.HOSTILE_KINDS, (bid, entry)
            assert 0 <= entry["base_chance"] <= 1
            assert entry["per_area_from_settlement"] >= 0
            assert entry["max_chance"] >= entry["base_chance"]


def test_adding_a_biome_is_data_only():
    data = copy.deepcopy(biomes.load())
    data["biomes"]["marsh"] = {
        "name": "Marsh", "terrain": "water", "tags": ["stream", "water"],
        "forage_skills": ["survival"], "surface": "mud",
        "descriptions": ["Standing water and tufted reeds."],
    }
    data["resource_distribution"]["marsh"] = [{"tags": ["herb"], "weight": 2}]
    data["hostile_distribution"]["marsh"] = [
        {"kind": "predator", "base_chance": 0.02,
         "per_area_from_settlement": 0.01, "max_chance": 0.2},
    ]
    assert biomes.validate(data) == []


def test_a_bad_biome_is_rejected():
    data = copy.deepcopy(biomes.load())
    data["biomes"]["bad"] = {
        "name": "Bad", "terrain": "rock", "tags": ["nowhere"],
        "forage_skills": ["alchemy"], "surface": "stone", "descriptions": [],
    }
    data["resource_distribution"]["bad"] = [{"tags": ["unicorn"], "weight": 1}]
    data["hostile_distribution"]["bad"] = [
        {"kind": "dragon", "base_chance": 2, "per_area_from_settlement": -1,
         "max_chance": 0},
    ]
    problems = biomes.validate(data)
    joined = " ".join(problems)
    assert "bad: no area tag foraging recognises" in joined
    assert "unknown forage skill 'alchemy'" in joined
    assert "not in the foraging vocabulary" in joined
    assert "unknown kind 'dragon'" in joined
    assert "max_chance < base_chance" in joined


def test_missing_rules_are_flagged():
    data = copy.deepcopy(biomes.load())
    del data["resource_distribution"]["lake"]
    del data["hostile_distribution"]["ocean"]
    problems = biomes.validate(data)
    assert any("biome 'lake' has no rules" in p for p in problems)
    assert any("biome 'ocean' has no rules" in p for p in problems)


def test_area_tags_are_lowercased():
    assert biomes.area_tags("dense_forest") == ["forest", "woods", "dense"]
