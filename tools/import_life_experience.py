#!/usr/bin/env python3
"""CLI tool for generating or importing character life experience into scenarios.

@docs docs/virtualWorld/Characters/Life Experience.md
"""

import argparse
import json
import os
import sys

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.life_experience import (
    apply_experience_to_scenario,
    generate_life_experience,
    import_diary_export,
)


def main():
    parser = argparse.ArgumentParser(description="Author and import character life experiences.")
    parser.add_argument("--character", required=True, help="Character name to author experience for.")
    parser.add_argument("--generate", action="store_true", help="Generate life experience deterministically.")
    parser.add_argument("--seed", type=int, default=42, help="Seed for deterministic generator.")
    parser.add_argument("--background", default="wanderer", help="Background archetype (wanderer, scholar, soldier).")
    parser.add_argument("--stages", type=int, default=4, help="Number of life stages to generate.")
    parser.add_argument("--import-diary", help="Path to Aura/Diary JSON export file.")
    parser.add_argument("--scenario", help="Path to scenario JSON file to resolve against and optionally update.")
    parser.add_argument("--output", help="Path to write modified scenario JSON.")
    parser.add_argument("--report", action="store_true", help="Print full authoring/validation report.")

    args = parser.parse_args()

    scenario_dict = None
    if args.scenario:
        if not os.path.exists(args.scenario):
            print(f"Error: Scenario file '{args.scenario}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(args.scenario, "r", encoding="utf-8") as f:
            scenario_dict = json.load(f)

    result = None
    if args.import_diary:
        if not os.path.exists(args.import_diary):
            print(f"Error: Diary file '{args.import_diary}' not found.", file=sys.stderr)
            sys.exit(1)
        result = import_diary_export(args.import_diary, args.character, scenario_dict=scenario_dict)
    elif args.generate:
        result = generate_life_experience(
            args.character,
            seed=args.seed,
            background=args.background,
            stages=args.stages,
            scenario_dict=scenario_dict,
        )
    else:
        print("Error: Specify either --generate or --import-diary <path>.", file=sys.stderr)
        sys.exit(1)

    # Print summary
    print(f"Processed {len(result.memories)} memories and {len(result.goals)} goals for '{args.character}'.")

    if args.report or not args.output:
        print("\n--- Authoring Report ---")
        rep = result.report
        print(f"Source: {rep.get('generator') or rep.get('importer')}")
        if "seed" in rep:
            print(f"Seed: {rep['seed']}")
        if rep.get("unresolved_locations"):
            print(f"Unresolved locations ({len(rep['unresolved_locations'])}):")
            for item in rep["unresolved_locations"]:
                print(f"  - {item.get('message')}")
        if rep.get("unresolved_entities"):
            print(f"Unresolved entities ({len(rep['unresolved_entities'])}):")
            for item in rep["unresolved_entities"]:
                print(f"  - {item.get('message')}")
        if rep.get("unsupported_fields"):
            print(f"Unsupported Aura/Diary fields ({len(rep['unsupported_fields'])}):")
            for item in rep["unsupported_fields"]:
                print(f"  - {item}")

    if args.output:
        if not scenario_dict:
            scenario_dict = {"players": {}, "graph": {"nodes": []}}
        updated = apply_experience_to_scenario(scenario_dict, args.character, result)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2)
        print(f"\nSaved updated scenario to '{args.output}'.")


if __name__ == "__main__":
    main()
