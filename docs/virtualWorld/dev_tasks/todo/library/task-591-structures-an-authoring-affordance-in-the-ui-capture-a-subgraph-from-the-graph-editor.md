---
type: task
status: todo
area: library
priority: high
related: [task-357, task-291]
---

# task-591: Structures — an authoring affordance (capture a subgraph from the graph editor)

**Filed:** 2026-09-29
**Related:** task-357, task-291

## Goal

`engine/structures.py` already implements a structure as a portable, internally-wired subgraph — **areas + ways + items + residents** — and `routes/structures.py` registers five endpoints including `save` and `materialize`. Nothing in `static/` or `templates/` mentions a structure template, so the entire feature is reachable by curl only, `data/library/structures/` is empty, and no structure has ever been captured. Give it a way in from the graph editor.

## Verified state (2026-09-29)

- **Engine, complete.** `collect_structure` (`structures.py:153`) captures from a live graph with a fixpoint that pulls in items reachable through area / surface / container and any residents inside. `materialize_structure` (`:309`) instantiates it, remapping every reference (`_remap_refs:73`, `_unique_id:94`, `_deterministic_suffix:89`) so two instances cannot collide. `summarize_structure` (`:291`) reports `{areas, ways, items, residents}`.
- **API, complete.** `/api/structures` (list), `/preview`, `/save`, `/<id>/materialize`, `/<id>` (delete).
- **Storage, already per-entry.** `save_registry` writes `data/library/structures/<id>.json` — no shape decision is outstanding here, contrary to what a first reading of `STRUCTURES_REGISTRY = "structures.json"` suggests.
- **UI, absent.** The library has eight panes (`areas, behaviours, characters, conditions, items, tags, traits, ways`). `triggers` has no pane by design — it is a blueprint store for the trigger graph editor. `structures` has no pane and no other affordance: a repo-wide grep of `static/` and `templates/` for "structure" returns only `ACTION STRUCTURE` prompt prose.
- **No content.** `data/library/structures/` is empty, so `list` returns nothing and `materialize` can only ever 404.

## The gap

Capture is the interesting direction and it needs the graph editor: the author has a subgraph in front of them — a tavern with its tap room, a shrine with its courtyard, a bandit camp — and wants it reusable. Today the only way to get one is to hand-build the JSON, which is the thing the library exists to stop.

## Open questions

1. **Where does capture start?** A context-menu action on selected area nodes in the graph canvas, or a button in the area inspector that captures the area and everything reachable? The engine's boundary rule (no far-side area node, or far side outside the selection) is the interesting part and the UI has to express it before the author presses the button, not after.
2. **Preview before saving.** `/api/structures/preview` exists. Does the flow show `{areas, ways, items, residents}` and the boundary before it writes, given that `save_registry` never deletes and a wrong capture lingers?
3. **Which pane?** A `structures` library pane would make them browsable, but triggers set the precedent that a type used only by one tool needs no pane — the trigger graph editor's blueprint picker. Structures is captured in the graph editor, so a picker there may be the honest answer.
4. **Does `task-357` already own part of this?** It is in review and covers capture + materialize end to end. If its acceptance is met by the engine alone, this task is the UI half; if it never claimed a UI affordance, say so in its file rather than leaving two tasks implying the same work.

## Acceptance

- An author can capture a subgraph from the graph editor and see the `{areas, ways, items, residents}` summary and the boundary **before** anything is written.
- The capture is a `data/library/structures/<id>.json` file that `list` and `preview` serve, with no other write path.
- A structure can be materialized twice into the same world with **no id collision**, proved by a test that exercises `_deterministic_suffix` (`structures.py:89`) — the second instance's names and ids must both differ while the wiring stays intact.
- Deleting a template from the UI removes the file via `delete_registry_entry` and leaves existing materialized instances in the world alone.
- A first real template is captured and committed, so `data/library/structures/` is not empty on `master`.
