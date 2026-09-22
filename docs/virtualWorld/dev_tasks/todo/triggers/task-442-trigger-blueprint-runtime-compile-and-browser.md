---
type: task
status: todo
area: triggers
priority: high
---

# task-442: Trigger blueprint runtime compile + blueprint browser

**Filed:** 2026-09-21
**Supersedes:** task-351 Phases 2–3 (Phase 1 shipped; that task is closed)
**Related:** task-388 (trigger graph editor overhaul — defects #9–#11 are the compile-honesty findings to fix here)

## Goal

Make a saved trigger **blueprint** something the engine can actually run, and give
blueprints a real browser. Today a blueprint is a JSON document the editor can load and
compile to a graph patch, but **no Python code has ever heard of a blueprint** — nothing
materialises a blueprint into `logic_trigger` nodes + `triggers` edges at runtime.

## Verified state (2026-09-21)

- Phase 1 (node renderer, sockets, wires, inline editing, blueprint save/load/export/
  import, compile-to-engine, inspector + library integration) is **done** in
  `static/js/shared/trigger-graph.js` — `_serializeGraph` `:1622`, `compileToEngine`
  `:1984`, `compileToBehaviors` `:1832`, blueprint I/O `:1667-1765`.
- Blueprint storage is real: `POST /api/library/triggers`
  (`routes/library_routes.py:48-60`, `triggers` in `REGISTRY_TYPES`
  `routes/library_ops.py:16`) writes per-entry files under `data/library/triggers/`.
- **`grep blueprint *.py` → 0 hits.** Phase 3 is unstarted.
- Phase 2's two unticked boxes (directory exists, templates seeded) are actually
  satisfied — nine files in `data/library/triggers/`. What is missing is the **browser**:
  today only the in-editor `_loadBlueprint` picker (`trigger-graph.js:1714-1750`), a raw
  floating div.

## Slice 1 — blueprint → engine nodes (the point of the task)

Define the compile as a documented JSON contract plus a runtime materialiser, so
attaching a blueprint to a node creates ordinary `logic_trigger` nodes and `triggers`
edges — no parallel format, same as task-398's `GenerationPatch` principle.

## Slice 2 — condition branching must stop losing data

Two known dishonest compiles to fix (also tracked as task-388 defects #9–#11):

- `_traceGraph` (`trigger-graph.js:2082-2113`) **AND-folds every condition and keeps only
  a NO-branch message as `fail_message`**, dropping every other NO-branch effect.
- `compileToEngine` (`:1996`) **always emits `{operator:'and'}`** — there is no OR/NOT.

A branch's NO path must compile to engine conditions / effects, or the editor must refuse
to save it rather than silently discard it.

## Slice 3 — blueprint browser

A searchable picker over `data/library/triggers/` (the six seeded templates plus
user-saved ones), in the shape the item library already uses — not a floating div.

## Acceptance

- A blueprint with a condition branch round-trips into `logic_trigger` nodes + `triggers`
  edges and behaves correctly in the engine.
- No effect is silently dropped on save or compile: a NO branch with two effects produces
  two effects (or a visible refusal).
- OR/NOT conditions survive the round trip.
- The browser lists and searches `data/library/triggers/*.json`, and attaching a
  blueprint from it materialises the nodes.
- `node --check` clean on touched JS; `python -m pytest tests/ -q -k "not mcp and not emote"` green.

## Non-goals

- The editor's UI/UX overhaul (pan/zoom, wire deletion, undo) — that is task-388, and
  pan/zoom already exists (`trigger-graph.js:1113-1219`).
- Re-introducing `reduce_uses`: it does not exist in the effect registry
  (`engine/effect_handlers/equipment.py:182` has `adjust_uses`, which accepts a negative
  delta). Task-351's Phase-1 checkbox claiming it was added is false and has been
  corrected there.
