# Life Experience Authoring & Import

This document describes the offline life experience generator and Aura/Diary importer for VirtualWorld characters.

## Architecture

VirtualWorld treats character backstory as authored first-person experience rather than decorative prose:
- Starting memories are loaded into `Player.preconceived_knowledge.memories` and injected into the character's live `Player.memories` store via `AgentMind.load_preconceived()`.
- Authored motivations stemming from life events are represented exclusively through existing GIMP goal structures in `Player.goals`.
- No parallel memory store, shadow simulation, or diary-entry database is added to the running simulation.

## Generator (`engine.life_experience`)

The generator (`generate_life_experience`) creates deterministic first-person memories across distinct life stages (childhood, youth, adulthood, recent):
- **Determinism:** The same character name, background archetype, and integer seed always produce identical memory payloads.
- **Reference Resolution:** When a scenario dictionary is provided, location and entity references are validated against existing graph nodes. If a location or entity cannot be verified in the scenario, the reference is omitted from the memory entry and logged in the authoring report rather than inventing non-existent nodes.

## Aura / Diary Importer

The importer (`import_diary_export`) parses offline life simulation exports (such as Aura/Diary JSON):
- Converts `raw_memory` and event choices into first-person episodic memories.
- Scales `emotional_impact` to an integer importance rating (1-10).
- Verifies `location_id` and `involved_persons` against real nodes in the target scenario.
- Captures unsupported fields (such as emotional trajectory data) in an authoring report so creators can review differences.

## CLI Usage

```bash
# Generate deterministic wanderer backstory for Arix and print report
python tools/import_life_experience.py --generate --character "Arix" --seed 42 --background wanderer --report

# Import an Aura/Diary export and inject into scenario
python tools/import_life_experience.py --import-diary "path/to/diary_export.json" --character "Arix" --scenario "data/scenarios/world_template.json" --output "data/scenarios/world_template.json" --report
```
