"""Tests for Markov biome adjacency matrix and transition gradients (task-884).

Verifies transition validity, intermediate gradient buffers, and seam feathering.
"""

from engine import world_adjacencies


def test_load_adjacency_data():
    data = world_adjacencies.load_adjacency_data(fresh=True)
    assert isinstance(data, dict)
    assert "gradients" in data
    assert "affinities" in data
    assert "prohibited" in data
    assert "water_to_land" in data["gradients"]
    assert "dwarven_civic_to_mine" in data["gradients"]


def test_is_valid_transition():
    # Valid transitions
    assert world_adjacencies.is_valid_transition("deep_water", "shallow_water")
    assert world_adjacencies.is_valid_transition("river", "shallow_water")
    assert world_adjacencies.is_valid_transition("clearing", "sparse_forest")
    assert world_adjacencies.is_valid_transition("same_biome", "same_biome")

    # Prohibited transitions defined in adjacency.json
    assert not world_adjacencies.is_valid_transition("deep_water", "dense_forest")
    assert not world_adjacencies.is_valid_transition("dense_forest", "deep_water")
    assert not world_adjacencies.is_valid_transition("deep_water", "sand_desert")
    assert not world_adjacencies.is_valid_transition("cliff", "deep_water")
    assert not world_adjacencies.is_valid_transition("dwarven_magma_forge", "deep_water")


def test_suggest_buffer_linear_gradient():
    # water_to_land gradient: deep_water -> shallow_water -> beach -> clearing -> sparse_forest -> dense_forest
    buf = world_adjacencies.suggest_buffer("deep_water", "dense_forest", count=4)
    assert buf == ["shallow_water", "beach", "clearing", "sparse_forest"]

    # Reversed direction
    rev_buf = world_adjacencies.suggest_buffer("dense_forest", "deep_water", count=4)
    assert rev_buf == ["sparse_forest", "clearing", "beach", "shallow_water"]

    # Single intermediate step sampling
    buf_single = world_adjacencies.suggest_buffer("deep_water", "dense_forest", count=1)
    assert len(buf_single) == 1
    assert buf_single[0] in ["shallow_water", "beach", "clearing", "sparse_forest"]

    # Subterranean dwarven civic to mine gradient
    dwarven_buf = world_adjacencies.suggest_buffer("dwarven_thane_throne", "dwarven_deep_mine", count=3)
    assert dwarven_buf == ["dwarven_colonnade", "dwarven_archway", "dwarven_mechanists_guild"]


def test_suggest_buffer_affinity_and_fallback():
    # Fallback when identical
    assert world_adjacencies.suggest_buffer("clearing", "clearing") == []

    # Fallback when generic
    fb_water = world_adjacencies.suggest_buffer("deep_water", "unknown_biome", count=2)
    assert "shallow_water" in fb_water


def test_feather_seam():
    # Feather across steps
    feather = world_adjacencies.feather_seam("deep_water", "dense_forest", steps=4)
    assert len(feather) == 4
    assert feather == ["shallow_water", "beach", "clearing", "sparse_forest"]

    # Zero or negative steps
    assert world_adjacencies.feather_seam("a", "b", steps=0) == []
