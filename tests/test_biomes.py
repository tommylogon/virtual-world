"""WorldPainter biome/feature taxonomy (task-497).

The shipped taxonomy must validate clean, map to the foraging vocabulary the
engine already uses, and stay extendable by data alone.
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import biomes, foraging


def test_shipped_taxonomy_validates_clean():
    assert biomes.validate() == []


def test_every_biome_has_a_tag_foraging_recognises():
    recognized = {str(t).lower() for t in foraging.AREA_SKILL_BONUS}
    for bid in biomes.biomes():
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
    assert biomes.forage_skill_bonus("farmland").get("survival", 0) > 0


def test_every_biome_has_resource_and_hostile_rules():
    assert set(biomes.resource_distribution()) == set(biomes.biomes())
    assert set(biomes.hostile_distribution()) == set(biomes.biomes())


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
        "forage_skills": ["survival"], "floor": "mud",
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
        "forage_skills": ["alchemy"], "floor": "stone", "descriptions": [],
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
