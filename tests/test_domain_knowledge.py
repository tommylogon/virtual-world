"""Tests for task-968: Domain knowledge, explicit blind spots, and semantic school/life knowledge integration."""

from app import create_app
from engine.character_appearance import (
    DOMAIN_COMPETENCE_LEVELS,
    StructuredError,
    compile_record,
    normalize_domains,
    schema_for_llm,
    validate_before_compile,
)
from engine.character_store import apply_node_properties, to_node_properties
from engine.items.examine_actions import mask_jargon_for_listener, resolve_domain_examine_note
from engine.memory_dynamics import (
    EPISODIC,
    PROCEDURAL,
    SEMANTIC,
    apply_decay,
    category_for,
    mark_procedural_used,
)
from engine.memory_retrieval import retrieve_associative_memories, score_memory
from graph import Node
from player import Player
import pytest


def test_domain_schema_normalization_and_validation():
    assert DOMAIN_COMPETENCE_LEVELS == ("ignorant", "novice", "familiar", "expert")
    schema = schema_for_llm()
    cap_props = schema["properties"]["capabilities"]["properties"]
    assert "domains" in cap_props
    assert cap_props["domains"]["items"]["properties"]["level"]["enum"] == list(DOMAIN_COMPETENCE_LEVELS)

    doms = normalize_domains([
        {"domain": "Silicone Molding", "level": "expert", "notes": "Platinum-cure casting", "jargon_terms": ["shore_hardness", "platinum_cure"]},
        {"domain": "sports", "level": "ignorant", "notes": "No clue about rules or teams"},
        "first_aid",
    ])
    assert len(doms) == 3
    assert doms[0] == {
        "domain": "silicone_molding",
        "level": "expert",
        "notes": "Platinum-cure casting",
        "jargon_terms": ["shore_hardness", "platinum_cure"],
    }
    assert doms[1]["domain"] == "sports"
    assert doms[1]["level"] == "ignorant"
    assert doms[2] == {"domain": "first_aid", "level": "familiar", "notes": "", "jargon_terms": []}

    ok, errs = validate_before_compile({"capabilities": {"domains": doms}})
    assert ok and not errs

    ok_bad, errs_bad = validate_before_compile({"capabilities": {"domains": [{"domain": "law", "level": "godlike"}]}})
    assert not ok_bad
    assert any("level must be one of" in e for e in errs_bad)

    with pytest.raises(StructuredError):
        normalize_domains([{"domain": "", "level": "expert"}])

    compiled = compile_record({
        "identity": {"pronouns": "she/her"},
        "capabilities": {"domains": doms},
    })
    assert compiled["domains"] == doms


def test_character_store_and_serialization_single_source_roundtrip():
    app = create_app({"TESTING": True})
    zoe = Player("Zoe")
    zoe.domains = normalize_domains([
        {"domain": "silicone_molding", "level": "expert", "notes": "Knows sulfur inhibition", "jargon_terms": ["platinum_cure"]},
        {"domain": "sports", "level": "ignorant", "notes": "Knows nothing about sports"},
    ])
    assert zoe.get_domain_level("silicone_molding") == "expert"
    assert zoe.has_domain_level("silicone_molding", "familiar")
    assert not zoe.has_domain_level("sports", "novice")

    records = zoe.get_knowledge_records()
    assert any(r["type"] == "domain" and r["data"]["domain"] == "silicone_molding" for r in records)
    assert any(r["type"] == "blind_spot" and r["data"]["domain"] == "sports" for r in records)

    node = Node("char_zoe", "character", "Zoe")
    node.properties = to_node_properties(zoe, node.properties)
    node.properties["narrative"] = {
        "knowledge_seeds": [
            {"text": "Learned basic mold making in art school studio", "source_kind": "school", "domain": "silicone_molding"},
            {"text": "Father taught how to fix leaky faucets", "source_kind": "parent", "tags": ["plumbing"]},
        ]
    }

    rehydrated = Player("Zoe")
    apply_node_properties(rehydrated, node.properties)
    assert len(rehydrated.domains) == 2
    assert rehydrated.get_domain_level("silicone_molding") == "expert"
    seed_mems = [m for m in rehydrated.memories if "knowledge_seed" in (m.get("tags") or [])]
    assert len(seed_mems) == 2
    assert all(m.get("category") == "semantic" and m.get("kind") == "semantic" for m in seed_mems)
    assert any("school" in (m.get("tags") or []) for m in seed_mems)
    assert any("parent" in (m.get("tags") or []) for m in seed_mems)

    # Serialization: live payload publishes domains + knowledge_records; scenario dict strips duplicate players copy
    app.world.graph.add_node(node)
    app.world.players["Zoe"] = rehydrated
    live_player = app.world.to_dict()["players"]["Zoe"]
    assert len(live_player["domains"]) == 2
    assert len(live_player["knowledge_records"]) >= 2

    scenario = app.world.to_scenario_dict()
    assert "domains" not in scenario["players"]["Zoe"]
    assert "knowledge_records" not in scenario["players"]["Zoe"]
    saved_node = scenario["graph"]["nodes"]["char_zoe"]
    assert len(saved_node["properties"]["domains"]) == 2


def test_memory_dynamics_semantic_stability_and_procedural_disuse_decay():
    p = Player("Zoe")
    ep = p.add_memory("Saw a stray cat near the bench", tick=10, importance=4, memory_type="observation", source="auto")
    sem_school = p.add_memory(
        "Learned contract tort basics in first-year law school",
        tick=10,
        importance=5,
        memory_type="semantic",
        tags=["school", "law"],
        source="backstory",
    )
    proc_recipe = p.add_memory(
        "Knows recipe: platinum_silicone_cast",
        tick=10,
        importance=6,
        memory_type="recipe",
        source="crafting",
        category="procedural",
        kind="procedural",
    )
    ep["activation"] = 1.0
    sem_school["activation"] = 1.0
    proc_recipe["activation"] = 1.0

    assert category_for(sem_school) == SEMANTIC
    assert category_for(proc_recipe) == PROCEDURAL
    assert category_for(ep) == EPISODIC

    # Within procedural grace period (tick=30, grace=50): episodic decays, semantic & procedural hold
    apply_decay(p, rate=0.2, tick=30)
    assert ep["activation"] < 1.0
    assert sem_school["activation"] == 1.0
    assert proc_recipe["activation"] == 1.0

    # Prolonged disuse past grace period (tick=120): procedural decays via disuse, semantic stays 1.0
    apply_decay(p, rate=0.2, tick=120)
    assert proc_recipe["activation"] < 1.0
    assert sem_school["activation"] == 1.0

    # Using the procedural skill resets disuse_ticks and reinforces activation
    mark_procedural_used(proc_recipe, tick=125)
    assert proc_recipe["disuse_ticks"] == 0
    assert proc_recipe["last_used_tick"] == 125


def test_memory_retrieval_domain_boost():
    zoe = Player("Zoe")
    zoe.domains = normalize_domains([
        {"domain": "silicone_molding", "level": "expert", "jargon_terms": ["platinum_cure"]},
        {"domain": "sports", "level": "ignorant"},
    ])
    m_domain = zoe.add_memory(
        "Always degas platinum_cure silicone in a vacuum chamber",
        tick=10,
        importance=5,
        memory_type="semantic",
        tags=["silicone_molding", "school"],
        source="backstory",
    )
    m_other = zoe.add_memory(
        "Watched a local game at the stadium",
        tick=10,
        importance=5,
        memory_type="semantic",
        tags=["sports"],
        source="backstory",
    )

    s_dom, bd_dom = score_memory(m_domain, {"domain_tags": {"silicone_molding"}}, current_tick=20)
    s_other, bd_other = score_memory(m_other, {"domain_tags": {"silicone_molding"}}, current_tick=20)
    assert bd_dom["domain_score"] > 0
    assert bd_other["domain_score"] == 0
    assert s_dom > s_other

    recalled = retrieve_associative_memories(zoe, {"dialogue": ""}, world=None, tick=20, max_results=2, min_score=0.5)
    assert recalled["memories"][0]["id"] == m_domain["id"]


def test_examine_actions_domain_gated_notes_and_jargon_opacity():
    zoe = Player("Zoe")
    zoe.domains = normalize_domains([
        {"domain": "silicone_molding", "level": "expert", "jargon_terms": ["platinum_cure", "sulfur_inhibition"]},
    ])
    kayla = Player("Kayla")
    kayla.domains = normalize_domains([
        {"domain": "silicone_molding", "level": "ignorant"},
    ])

    item_props = {
        "domain_notes": {
            "silicone_molding": {
                "min_level": "familiar",
                "expert": "Diagnostics: platinum_cure elastomer showing tacky sulfur_inhibition along the seam.",
                "familiar": "Two-part silicone mold kit, slightly tacky near the clay.",
                "ignorant": "Two unlabeled bottles of thick, slightly sticky clear goop.",
            }
        }
    }

    zoe_note = resolve_domain_examine_note(item_props, zoe)
    kayla_note = resolve_domain_examine_note(item_props, kayla)
    assert "platinum_cure" in zoe_note
    assert "sulfur_inhibition" in zoe_note
    assert "sticky clear goop" in kayla_note
    assert "platinum_cure" not in kayla_note

    masked = mask_jargon_for_listener(zoe_note, ["platinum_cure", "sulfur_inhibition"], listener=kayla, domain="silicone_molding")
    unmasked = mask_jargon_for_listener(zoe_note, ["platinum_cure", "sulfur_inhibition"], listener=zoe, domain="silicone_molding")
    assert "[unfamiliar jargon]" in masked
    assert "platinum_cure" not in masked
    assert unmasked == zoe_note
