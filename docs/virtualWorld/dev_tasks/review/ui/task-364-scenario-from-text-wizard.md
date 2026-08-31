---
type: task
status: review
area: ui
priority: high
---

# task-364: Scenario from Text wizard

**Filed**: 2026-08-30
**Status**: In Review — implemented 2026-08-30; E2E-verified with a stubbed LLM
(full draft→review→apply→undo round trip against the live server); real-LLM
run + user playtest pending.

## What was built

- GUI entry: 🎮 Game ▾ → "✨ Scenario from Text…" (`templates/index.html`).
- Wizard `static/js/ui/scenario-wizard.js`: premise → LLM draft (client-side
  `AIGenerator.generate`) in world-TEMPLATE format → review cards (accept /
  per-room ✨ Regen / item checkboxes / characters / lore) → Apply.
- Apply rides the existing `POST /api/load`: undo snapshot, scenario file,
  `TemplateLoader` build. No new backend route.
- Backend extensions in `engine/serialization_template.py`:
  - item `tags` + `light_level` / heat / sound props now survive
    (previously silently dropped — light_source items lost their tag).
  - `characters` list → multiple players (protagonist stays active).
- Tests: `tests/test_template_loader.py` (5). Full suite 1286 passed.

## Known follow-ups

- Real-LLM quality pass (model from Settings; gpt-4.1-mini-class ok for
  3–8 rooms).
- Append-to-existing-world mode (currently replaces; undo restores).
- Room-template palette + draw-a-door flow (filed separately / idea).
