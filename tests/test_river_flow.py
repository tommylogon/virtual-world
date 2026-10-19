"""Tests for hydrological gradient flow and river linting (task-745)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import biomes, world_grid
from tools import river_flow_lint


def test_biome_hazard_defaults_and_archetypes():
    """Biomes declare default hazard couplings and register water archetypes."""
    assert biomes.biome_hazard("river") == "river"
    assert biomes.biome_hazard("cliff") == "cliff"
    assert biomes.biome_hazard("river_calm") is None
    assert biomes.biome_hazard("river_swift") == "river"
    assert biomes.biome_hazard("river_rapids") == "rapids"
    assert biomes.biome_hazard("waterfall") == "fall"
    assert biomes.biome_hazard("grass") is None


def test_derive_water_current_slope_ladder():
    """Current strength auto-derives from floor storey gradient across cells."""
    record = {
        "grid": {"w": 10, "h": 10},
        "layers": {
            "biome": {
                "1,1": "grass",
                "2,1": "river_calm",
                "3,1": "river",
                "4,1": "river",
                "5,1": "river",
                "6,1": "waterfall",
                "7,1": "deep_water",
            },
            "floor": {
                "2,1": 0,
                "3,1": 0,    # 0 drop from (2,1)
                "4,1": -1,   # 1 storey drop from (3,1)
                "5,1": -3,   # 2 storey drop from (4,1)
                "6,1": -7,   # 4 storey drop from (5,1)
                "7,1": -8,   # 1 storey drop into lake/basin
            },
        },
    }

    # 1. Non-water cell returns None
    assert world_grid.derive_water_current(record, 1, 1) is None

    # 2. 0 storeys drop (meander / flat reach): strength 1
    flat = world_grid.derive_water_current(record, 2, 1)
    assert flat is not None
    assert flat["strength"] == 1
    assert flat["drop"] == 0
    assert flat["slope_percent"] == 0.0

    # 3. 1 storey drop (3m drop over 80m ≈ 3.75% slope): strength 5 (swift current)
    swift = world_grid.derive_water_current(record, 3, 1)
    assert swift is not None
    assert swift["strength"] == 5
    assert swift["drop"] == 1
    assert swift["bearing"] == "e"
    assert swift["hazard_id"] == "river"
    assert 3.5 <= swift["slope_percent"] <= 3.8

    # 4. 2 storeys drop (6m drop over 80m = 7.5% slope): strength 10 (rapids)
    rapids = world_grid.derive_water_current(record, 4, 1)
    assert rapids is not None
    assert rapids["strength"] == 10
    assert rapids["drop"] == 2
    assert rapids["hazard_id"] == "rapids"
    assert 7.0 <= rapids["slope_percent"] <= 8.0

    # 5. 4 storeys drop (12m drop over 80m = 15% slope): strength 20 (waterfall)
    fall = world_grid.derive_water_current(record, 5, 1)
    assert fall is not None
    assert fall["strength"] == 20
    assert fall["drop"] == 4
    assert fall["hazard_id"] == "fall"
    assert fall["slope_percent"] >= 15.0


def test_derive_water_current_manual_override():
    """Authored current layer takes precedence over gravity gradient."""
    record = {
        "grid": {"w": 5, "h": 5},
        "layers": {
            "biome": {"2,2": "river"},
            "floor": {"2,2": 0, "3,2": -2},
            "current": {
                "2,2": {"strength": 16, "direction": 4},  # West
            },
        },
    }
    res = world_grid.derive_water_current(record, 2, 2)
    assert res is not None
    assert res["manual_override"] is True
    assert res["strength"] == 16
    assert res["direction"] == 4
    assert res["bearing"] == "w"


def test_river_flow_lint_detects_errors():
    """Validator catches uphill flow, unclassified drops, and inland dead-ends."""
    bad_record = {
        "grid": {"w": 10, "h": 10},
        "layers": {
            "biome": {
                "2,2": "river",
                "3,2": "river",
                "4,2": "river",
                "5,5": "river",  # Inland dead end
            },
            "floor": {
                "2,2": 0,
                "3,2": 5,   # Uphill from 2,2
                "4,2": -1,  # 6 storey drop from 3,2 lacking waterfall classification
                "5,5": 0,
            },
            "current": {
                "2,2": {"strength": 10, "direction": 0},  # Points East towards higher (3,2)
            },
        },
    }

    problems = river_flow_lint.lint_grid_river_flow(bad_record, "test_scope")
    types = {p["type"] for p in problems}
    assert "uphill_flow" in types
    assert "unclassified_cataract" in types
    assert "dead_end_outflow" in types

    # Clean record returns no problems
    clean_record = {
        "grid": {"w": 10, "h": 10},
        "layers": {
            "biome": {
                "0,5": "river",
                "1,5": "river_swift",
                "2,5": "waterfall",
                "3,5": "deep_water",
            },
            "floor": {
                "0,5": 5,
                "1,5": 4,   # 1 drop
                "2,5": 4,
                "3,5": 0,   # 4 drop into classified waterfall / deep water
            },
        },
    }
    assert river_flow_lint.lint_grid_river_flow(clean_record, "clean") == []
