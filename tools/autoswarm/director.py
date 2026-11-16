"""tools/autoswarm/director.py - Super-agent orchestrator for ViWo AutoSwarm.

Coordinates:
- Planning: DeepSeek / Gemini high-level cognitive decomposition.
- Authoring: Cartographer (areas, ways, scopes) & Lore (props, keys, characters).
- Auditing: Automated invariant checks (zero em-dashes, key-lock reachability).
- Playtesting: Local LM Studio actor swarm (qwen3.5-2b).
- Persistence: Writing compliant scenario to disk (data/scenarios/).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.autoswarm.llm import call_tier
from tools.autoswarm.cartographer import make_area_node, make_way_node, make_environment
from tools.autoswarm.lore import make_item_node, make_character_definition
from tools.autoswarm.auditor import audit_scenario
from tools.autoswarm.actor import run_playtest_session


def build_autonomous_scenario(
    scenario_id: str = "science_annex_investigation",
    scenario_title: str = "Millwood Science Annex - Hazardous Reagents",
) -> Tuple[Dict[str, Any], Path]:
    """Construct an authored scenario with locked door, hidden key, and props."""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Define Areas
    # Area 1: Chemistry Lab Main
    lab_env = make_environment(
        light=85,
        temperature=18.5,
        air="faint smell of ethanol and copper sulphate",
        smell="isopropyl alcohol and old cardboard",
        noise="faint ventilation drone",
    )
    a_lab = make_area_node(
        area_id="area_chem_lab_main",
        name="Chemistry Lab Main Floor",
        description="A spacious high school laboratory fitted with black chemical-resistant bench tops, stainless sinks, and gas jet valves. Tall glassware drying racks stand against the north wall.",
        cell=(0, 0),
        environment=lab_env,
        tags=["interior", "school", "science_lab"],
    )
    nodes.append(a_lab)

    # Area 2: Teacher Prep Room (where the key is located)
    prep_env = make_environment(
        light=75,
        temperature=21.0,
        air="smell of roasted coffee and pencil shavings",
        smell="fresh coffee and dry paper",
        noise="quiet clock ticking on the wall",
    )
    a_prep = make_area_node(
        area_id="area_chem_prep_office",
        name="Teacher Science Prep Office",
        description="A cluttered staff office tucked behind the main lab. Shelves are crammed with safety goggles, acid-spill kits, and student attendance binders.",
        cell=(1, 0),
        environment=prep_env,
        tags=["interior", "school", "office"],
    )
    nodes.append(a_prep)

    # Area 3: Hazardous Reagents Vault (locked door required)
    vault_env = make_environment(
        light=40,
        temperature=14.0,
        air="heavy, cold air with faint acetic acid sting",
        smell="acetic acid and sealed rubber",
        noise="audible suction from dedicated exhaust vent",
    )
    a_vault = make_area_node(
        area_id="area_hazardous_reagents_vault",
        name="Hazardous Reagents Vault",
        description="A reinforced steel storage vault with grounded spark-proof shelving, holding amber bottles of concentrated acids and sealed canisters of magnesium ribbon.",
        cell=(-1, 0),
        environment=vault_env,
        tags=["interior", "school", "secure_vault"],
    )
    nodes.append(a_vault)

    # 2. Define Ways
    # Way 1: Lab <-> Prep Office (unlocked, east)
    w_prep, e_prep = make_way_node(
        way_id="way_lab_to_prep",
        name="Prep Office Wooden Door",
        area_from="area_chem_lab_main",
        area_to="area_chem_prep_office",
        pass_message="You turn the brass handle and push through the half-glazed wooden door into the prep office.",
        door=True,
        locked=False,
        direction="east",
        reverse_direction="west",
    )
    nodes.append(w_prep)
    edges.extend(e_prep)

    # Way 2: Lab <-> Reagents Vault (LOCKED with reagents_vault_key, west)
    w_vault, e_vault = make_way_node(
        way_id="way_lab_to_vault",
        name="Heavy Steel Reagents Door",
        area_from="area_chem_lab_main",
        area_to="area_hazardous_reagents_vault",
        pass_message="You unlock the steel latch and pull open the heavy fire-rated door into the cold storage vault.",
        door=True,
        locked=True,
        key_id="reagents_vault_key",
        lock_description="A sturdy Yale cylinder lock reinforced with a warning placard: AUTHORIZED SCIENCE FACULTY ONLY.",
        direction="west",
        reverse_direction="east",
    )
    nodes.append(w_vault)
    edges.extend(e_vault)

    # 3. Define Items
    # Key placed in Prep Office
    i_key, e_key = make_item_node(
        item_id="item_vault_brass_key",
        name="Brass Vault Key",
        description="A heavy notched brass key stamped with the code CHEM-VAULT-01.",
        location_id="area_chem_prep_office",
        weight=0.1,
        key_id="reagents_vault_key",
        tags=["key", "brass", "essential"],
    )
    nodes.append(i_key)
    edges.append(e_key)

    # Lab Prop: Bunsen Burner in Main Lab
    i_burner, e_burner = make_item_node(
        item_id="item_bunsen_burner",
        name="Heavy Base Bunsen Burner",
        description="A cast-iron Bunsen burner connected to a corrugated rubber gas hose with an adjustable collar.",
        location_id="area_chem_lab_main",
        weight=1.2,
        tags=["lab_equipment", "metal"],
    )
    nodes.append(i_burner)
    edges.append(e_burner)

    # Vault Prop: Amber Acid Bottle inside the Vault
    i_acid, e_acid = make_item_node(
        item_id="item_amber_acid_bottle",
        name="Sealed Amber Reagent Bottle",
        description="A thick brown glass bottle with a Teflon seal, labelled Concentrated Nitric Acid 68 percent - Corrosive.",
        location_id="area_hazardous_reagents_vault",
        weight=2.0,
        tags=["hazardous", "chemical", "glass"],
    )
    nodes.append(i_acid)
    edges.append(e_acid)

    # 4. Define Characters
    char1_node, char1_edge, player1 = make_character_definition(
        char_id="char_jake_halloway",
        name="Jake Halloway",
        base_description="A lanky high school junior with ink-stained fingers and a skeptical expression.",
        persona_prompt="You are Jake Halloway, an inquisitive student trying to find the missing reagents before detention ends.",
        location_id="area_chem_lab_main",
        traits=["analytical", "cautious"],
    )
    char2_node, char2_edge, player2 = make_character_definition(
        char_id="char_sammy_lopez",
        name="Sammy Lopez",
        base_description="An energetic student carrying a cracked stopwatch and an oversized hoodie.",
        persona_prompt="You are Sammy Lopez, loyal, quick-witted, and always looking for shortcuts.",
        location_id="area_chem_lab_main",
        traits=["energetic", "impulsive"],
    )
    nodes.extend([char1_node, char2_node])
    edges.extend([char1_edge, char2_edge])

    # Assemble Scenario Dict
    scenario_dict = {
        "_scenario_name": scenario_id,
        "_description": scenario_title,
        "current_area": "area_chem_lab_main",
        "active_player": "Jake Halloway",
        "clock_start_hour": 15,
        "clock_start_minute": 30,
        "time_ticks": 0,
        "turn_number": 0,
        "graph": {
            "nodes": {n["id"]: n for n in nodes},
            "edges": edges,
        },
        "players": {
            player1["name"]: player1,
            player2["name"]: player2,
        },
        "areas": {
            "area_chem_lab_main": {
                "name": "Chemistry Lab Main Floor",
                "description": a_lab["properties"]["description"],
                "environment": lab_env,
                "items": ["item_bunsen_burner"],
                "exits": ["way_lab_to_prep", "way_lab_to_vault"],
            },
            "area_chem_prep_office": {
                "name": "Teacher Science Prep Office",
                "description": a_prep["properties"]["description"],
                "environment": prep_env,
                "items": ["item_vault_brass_key"],
                "exits": ["way_lab_to_prep"],
            },
            "area_hazardous_reagents_vault": {
                "name": "Hazardous Reagents Vault",
                "description": a_vault["properties"]["description"],
                "environment": vault_env,
                "items": ["item_amber_acid_bottle"],
                "exits": ["way_lab_to_vault"],
            },
        },
    }

    output_path = REPO_ROOT / "data" / "scenarios" / f"{scenario_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scenario_dict, f, indent=2)

    return scenario_dict, output_path


def run_full_swarm_mission(scenario_id: str = "science_annex_investigation", cycles: int = 3) -> Dict[str, Any]:
    """Run autonomous end-to-end mission: Build -> Pre-Audit -> Playtest -> Post-Audit."""
    start_time = time.time()
    print("=" * 60)
    print(" [AUTOSWARM] STARTING AUTONOMOUS MISSION")
    print(f" Target Scenario: {scenario_id}")
    print("=" * 60)

    # 1. Cartographer & Lore phase
    print("\n[Phase 1]: Cartographer & Lore Authoring...")
    scenario_dict, scenario_path = build_autonomous_scenario(scenario_id)
    print(f" -> Scenario assembled with {len(scenario_dict['graph']['nodes'])} nodes, {len(scenario_dict['graph']['edges'])} edges.")
    print(f" -> Persisted to: {scenario_path}")

    # 2. Pre-Audit phase
    print("\n[Phase 2]: Automated Pre-Audit...")
    pre_report = audit_scenario(scenario_dict, scenario_path)
    print(pre_report.summary())
    if not pre_report.passed:
        raise RuntimeError(f"Pre-Audit FAILED:\n{pre_report.summary()}")

    # 3. Cognitive Playtest Swarm phase
    print("\n[Phase 3]: Cognitive Playtest Swarm (Local LLMs)...")
    from app import create_app
    app = create_app()

    # Load our created scenario into the app world via official /api/load
    client = app.test_client()
    load_resp = client.post("/api/load", json=scenario_dict)
    if load_resp.status_code != 200:
        raise RuntimeError(f"Engine failed to load scenario: {load_resp.get_json()}")
    print(f" -> Loaded into app.world: {len(app.world.graph.nodes)} nodes, {len(app.world.players)} players.")

    playtest_results = run_playtest_session(
        app=app,
        character_names=["Jake Halloway", "Sammy Lopez"],
        cycles=cycles,
    )

    # 4. Post-Audit & Telemetry phase
    print("\n[Phase 4]: Post-Playtest Audit & Verification...")
    post_report = audit_scenario(scenario_dict, scenario_path)
    print(post_report.summary())

    duration = time.time() - start_time
    print("\n" + "=" * 60)
    print(f" [AUTOSWARM] MISSION COMPLETE IN {duration:.2f}s")
    print("=" * 60)

    return {
        "scenario_id": scenario_id,
        "scenario_path": str(scenario_path),
        "pre_audit_passed": pre_report.passed,
        "post_audit_passed": post_report.passed,
        "playtest_results": playtest_results,
        "duration_seconds": duration,
    }


if __name__ == "__main__":
    res = run_full_swarm_mission()
    print(json.dumps(res, indent=2))
