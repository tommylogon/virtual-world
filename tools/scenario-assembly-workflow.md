# Scenario Assembly Workflow

## Goal

Turn a short prompt — plus optional image, area/character/item/way counts, and constraints — into a playable scenario by mixing:
- procedural generation,
- library imports,
- natural-language agentic editing,
- editor-compatible validation/assembly.

This should feel like:
1. give a goal/spec,
2. get a draft world,
3. iterate with NL edits,
4. export a valid scenario file.

## Inputs

- `goal`: text prompt describing the scenario
- `image`: optional reference image path/URL
- `constraints`: optional counts/limits, e.g.
  - `areas: 8-12`
  - `ways: 10-15`
  - `characters: 5-8`
  - `items_per_area: 2-6`
- `seed_scenario`: optional existing scenario to extend/modify
- `library_sync`: optional library IDs to force into the world

## Pipeline

### Stage 1 — Seed / bootstrap

Options:
- blank world
- load existing scenario via `POST /api/load`
- import selected library entities via library APIs

Output: stable starting graph with runtime state.

### Stage 2 — Procedural draft

Use the existing generators to create bulk content:
- area drafts from goal/image
- item drafts for each area
- character drafts from goal/image
- way drafts connecting areas

This stage should:
- prefer library templates when available
- generate missing components with valid schemas
- create `pass_message` for every way
- add `damage`/`equip_slots`/`max_weight_capacity` as needed

### Stage 3 — NL editor refinement

Drive the existing NL editor loop (`NLEditorAgent`) with the goal as the first turn:
- multi-turn tool-calling edits
- library search/reuse
- staging + apply through `/api/graph/batch`
- clarification when ambiguous

This stage is interactive, but can also be scripted by sending prompts into the agent loop programmatically.

### Stage 4 — Assembly & validation

Run the scenario validator against:
- area/way/item/character/trigger counts
- required fields (`pass_message`, `damage`, `equip_slots`, etc.)
- reference integrity (`current_area`, trigger targets, way endpoints)

Export a single scenario JSON ready for `POST /api/load`.

## Implementation Plan

### A. CLI workflow driver

`tools/assemble_scenario.py`
- accepts goal/image/constraints
- calls stage 1-4 in order
- writes final scenario JSON

### B. Procedural draft generators

Reuse/extend:
- `static/js/item-library/ai-generation.js`
- `static/js/inspector/area-view.js` system prompt
- `static/js/inspector/item-view.js` system prompt
- `static/js/inspector/way-view.js` system prompt
- `static/js/shared/ai-generator.js`

Add:
- area batch generator from goal/image
- character batch generator from goal/image
- way batch generator from adjacency plan

### C. NL editor controller

Drive `NLEditorAgent` from Python via the existing APIs:
- `POST /api/graph/batch` for staged ops
- `GET /api/graph` / node endpoints for reads
- `POST /api/load` for final assembly

Or run it in-browser via the existing side panel once the world is loaded.

### D. Validator + exporter

Reuse `tools/validate_scenario.py`.
Add exporter that:
- loads the live world
- calls `to_scenario_dict()` if available
- normalizes missing required fields
- writes `data/scenarios/<name>.json`

## Minimal Viable Flow

```
goal → stage1(load/blank) → stage2(procedural draft) → stage3(NL refine) → stage4(validate/export)
```

Where:
- stage1 is one API call
- stage2 is batch generation via existing prompts
- stage3 is the existing NL editor, either manual or scripted
- stage4 is validation + scenario write

## Open Questions

1. Should this be a Python CLI, a browser flow, or both?
2. Do you want the procedural pass to run server-side via API, or client-side in the editor?
3. Should the NL stage be fully automated from the goal, or interactive?
4. Do you want image analysis in stage 2, or is text goal enough for now?
