---
id: 288
title: Condition Editor Modal + /api/conditions (inspector tooling)
status: done
priority: medium
created: 2026-08-17
tags: [ui, inspector, conditions, tooling]
type: task
area: ui
---

# Condition Editor Modal + `/api/conditions`

## What

Inspector tooling for authoring conditions on a character, split out of the blind sensory work
(task-287) so the two stay separable. Replaces the old select+➕ flow (which could only add a
default instance) with a **modal** that mirrors the trigger editor, backed by a catalog endpoint
and a full-payload `add_condition` API that matches the multi-instance conditions system.

## How

- **`GET /api/conditions`** returns the `CONDITION_DEFINITIONS` catalog for the editor: `value`,
  `label`, `description`, `default_duration`, and the `blocks_actions`/`blocks_movement`/
  `blocks_speech`/`known` flags (sorted with blocking conditions first).
- **`add_condition` accepts a full payload** — `condition, duration, source, level, periodic,
  ends_on, symptoms, extra_conditions, source_type, overrides` — so the editor can author
  leveled/periodic/bundled conditions, not just a bare default instance. This matches the
  multi-instance model (`player.conditions` maps `condition_id → [instance, ...]`).
- **Modal** (`agent-view.js`) mirrors the trigger editor: grouped condition dropdown, duration /
  level / source / ends-on fields, and an advanced section for `periodic` + `overrides` JSON.
  The old select+➕ button is replaced by a single "➕ Add Condition" button.

## Files

- `routes/players.py` — `GET /api/conditions` endpoint; `add_condition` accepts the full payload dict.
- `static/js/api.js` — `get()` helper + `conditionsCatalog()`.
- `static/js/inspector/agent-view.js` — `_openConditionEditor()` modal, `_applyCondition()`,
  replaced select+➕ with "➕ Add Condition".

## Steps to verify

- expected: GET /api/conditions catalog + an Add Condition modal in the character inspector.
- observed (2026-10-10 live): /api/conditions -> 200, 40 conditions, blocking first (dead, grappled, paralysed...); 'Add Condition' opens 'Add Condition - Arix' with the grouped dropdown (Dead..Satiated) and Duration/Level/Source/Ends/Periodic/Overrides/Advanced.

## Status

**In Review — implemented 2026-08-17, static checks + live API smoke pass**; pending a browser pass of
the modal. Split from task-287 (blind sensory system) so the tooling and the design stay separable.

## Why

TODO

## Acceptance

- [ ] TODO
