---
type: task
status: cancelled
area: characters
priority: medium
horizon: next
goal: Every paperdoll region can carry a description, edited from the doll and rendered into the looks prose by Compile.
wiki: "[[Persona]]"
related: [task-848, task-847, task-852, task-744]
blocked_by: [task-865]
---

# task-867: Per-region body descriptions edited from the paperdoll

**Filed:** 2026-10-18
**Related:** task-848, task-847, task-852, task-744

<!-- deps:start -->
**Blocked by:** [[task-865-rename-the-persona-block-key-from-appearance-to-persona]]
**Related:** [[task-848-persona-tab-visual-paperdoll-with-inline-body-baseline-editing]], [[task-847-persona-tab-embedded-body-paperdoll-navigator-for-appearance-schema]], [[task-852-persona-ui-improvement-plan-workspace-doll-navigation-markings-state-integration]], [[task-744-equipment-and-body-one-edge-truth-for-worn-gear-layered-coverage-body-marks-body-centric-ui]]
<!-- deps:end -->

## What

The paperdoll already knows the body regions (`InspectorPaperdoll.AREA_TO_REGIONS`), the Persona tab already reads region status there, and `body.modifications` is already region-linked as `area::text` (`static/js/inspector/mind-view.ts:1288`). But no region can carry a description, so the source's genitalia / body-part descriptions have nowhere to go.

This card adds a per-region description field to the block and edits it from the doll.

## Why

Intimate and regional detail is intrinsic appearance. It belongs in the structured block, and the region map is already the natural editor. If it is typed straight into `base_description` prose, the next Compile treats it as stale and clobbers it. The block is state; the prose is its projection.

## How

1. Add a `body.regions` group to the appearance schema (region id -> text), beside the existing `body.modifications[]`, mirroring the region-linked shape (`area::text`).
2. Open a text field on a paperdoll region click; write the region's text to `body.regions[<region>]`.
3. Compile: `render_record_prose` (`engine/character_appearance.py`) renders each region's text into the looks prose.
4. Do not write region text directly into `base_description` / `description`.
5. Serve the new group in `schema_for_llm` so import / LLM fill can populate it.

## Browser UI and intended live verification

The paperdoll is the surface. Live steps: open a character's Persona tab, click a body region, type a description, save, run Compile, confirm the prose includes it; reload and confirm the region text round-trips.

## Steps to verify

1. Click a paperdoll region and add text, then save.
   - expected: `body.regions[<region>]` holds the text.
   - observed: TODO
2. Run Compile.
   - expected: the rendered looks prose includes the region text.
   - observed: TODO
3. Save the scenario and reload.
   - expected: the region text survives; no direct write landed in `description`.
   - observed: TODO

## Acceptance

- [ ] Each paperdoll region can carry a description.
- [ ] Compile includes region descriptions in the looks prose.
- [ ] Nothing writes region text directly into `description` / `base_description`.
- [ ] The region text round-trips a scenario save / load.
- [ ] The field is served in `schema_for_llm`.

## Files

- `engine/character_appearance.py`
- `static/js/inspector/mind-view.ts`
- `static/js/inspector/paperdoll-view.ts`
- `tests/test_character_appearance.py`

## Retracted 2026-10-18

Duplicate. Per-region authored data is already `task-733` (`appearance` includes `genitalia`), `task-848` (region selection and inline body editing on the doll) and `task-744` slice 4 (per-region authored data whose description composes into appearance prose).

The one delta survives and is folded into `task-733`: region prose must be rendered by `render_record_prose`, never typed straight into `base_description`, or the next Compile treats it as stale.
