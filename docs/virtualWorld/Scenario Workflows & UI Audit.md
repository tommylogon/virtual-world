# Scenario Workflows & UI Audit

**Status**: Design document — audit of every current world/scenario function, how it works, and suggested improvements.
**Date**: 2026-08-30
**Scope**: world creation, authoring, maintenance, playtest, and hand-off flows (GUI + the endpoints they drive). Not a code walkthrough; a workflow audit.

---

## 1. The data map (what lives where)

| File / location | What it is | Written by |
|---|---|---|
| `data/autosave.json` | Boot-restore world (full live state + `_autosave_meta`). Loaded on server start. | every world mutation (`save_autosave`) |
| `saves/autosave.json` | The AUTO slot in the Save/Load modal (keeps `_save_metadata`, `autosave: true`; pinned top of list). | every mutation, plus manual save |
| `saves/<name>_<timestamp>.json` | Manual save games (full state + `_save_metadata`: name, scenario, tick, turn, player, version, autosave flag). | `💾 Save Game` / slot overwrite |
| `data/scenarios/<name>.json` | **Scenario source** — the authoring template for a world. Created by `POST /api/load` when the payload has no `_save_metadata` (it also sets `_scenario_source`). | `Load JSON…`, New Scenario, wizard apply (via `/api/load`) |
| `data/library/{items,areas,characters,tags,conditions,ways,behaviours,triggers}/` | Reusable catalogs (data-driven). Items/characters/tags/conditions have full sync+diff machinery; **areas dir is wired but relies on manual JSONs; ways/triggers/behaviours partial**. | editor "Save to Library", `seed_condition_library` |
| `world_template.json` (app root) | Legacy fallback for Restart when no `_scenario_source` exists. | legacy tooling |

**Key insight — the divergence problem:** `data/scenarios/<name>.json` is the *source*, `data/autosave.json` is the *live copy*. Editing the world only mutates the live copy. Nothing (except `/api/load`, which replaces the whole world) writes back to the source. Restart = discard everything since the last load. **There is currently no way to commit live edits into the scenario source.**

---

## 2. Scenario lifecycle — current functions

### 2.1 Create

| Function | How it works today | Friction / notes |
|---|---|---|
| 🆕 **New Scenario** (`main.js → POST /api/load` with a void world) | Clears everything (undo snapshot pushed). Empty graph, heroes? none. Banner name = `unnamed` until next load. | You get a blank canvas with no scaffold; no checklist, no hint of what to build next. |
| ✨ **Scenario from Text…** (wizard, `scenario-wizard.js`) | Premise → LLM draft (client `AIGenerator`) in TEMPLATE format → review cards (tick rooms/items, per-room ✨ Regen, chars, lore) → Apply via `/api/load` (undo-safe, becomes scenario source). | Draft quality tied to Settings model. Only replace-mode (no append/merge). No integration with the area library yet. |
| 📂 **Load JSON…** (`uploadWorld` → `api.loadWorld` → `/api/load`) | File picker → parse → apply directly. Name from filename. No preview, no validation, no counts. | **Blind import** — only reachable by Undo if it was wrong. |
| 🏠 **Add Area / Add Item / 🚪 Way / 📚 Library create buttons** (graph toolbar) | `create-modal` single-node forms (area gets light/temp; item gets actions/tags; way minimal) + library browser for catalog spawns. | One node at a time. No room template palette, no copy/duplicate, no multi-create. |

### 2.2 Author (in-session tools)

| Function | How it works | Friction / notes |
|---|---|---|
| **Graph canvas** (drag/connect, edge types, gravity per node, filters, overlays light/heat/sound, labels, floor filter, fit, physics toggle) | Full node-graph editor. Connection edges carry direction/cardinal/view; ways are separate nodes with their own properties; connect flow asks edge type only. | Two door models (raw `connection` edges vs way nodes). Way creation needs the Way node in advance; **no draw-a-door wizard** (auto way + both directions + defaults). |
| **Area inspector** (description, environment light/temp/air/smell/noise, items list, exits list, image, tags, aliases, triggers, template sync, gravity, **Known by removed** → knowledge managed char-side) | Direct PATCHes per field; ✨ Improve = `AIGenerator` description+env proposal (one area at a time); template sync row (refresh/save area). | Env entries are raw number/string fields; no presets, no zone copy ("make all these rooms arctic"), no bulk. |
| **Item inspector** (actions grid, properties, params, tags, image, aliases, triggers incl. contents, move-to picker, library save/refresh, template sync, auto-inverse actions) | Rich single-item editor; library refresh/save with diff modal (task-115/127/204); actions toggling auto-creates base triggers on enable. | Still one item at a time; no "duplicate item + contents"; container contents editing is a JSON blob in some paths. |
| **Way inspector** (state, description, pass message, see-through, size/requires/cost, cardinal/view, prevent-close, tags, triggers, save-to-library) | Direct PATCHes; trigger editor shared. | Cardinal/view live on edges — editing an edge with the way open requires the edge inspector; **way "flip" exists?** (task-318 in review: graph editor flip edge). |
| **Character inspector** (tabs Inventory/Bio/Advanced: vitals, stats, skills, traits, personality, appearance, relationships, tags, aliases, interests, What-I-See preview, memories editor, conditions, knowledge section + 🎛 Knowledge modal, behaviors, timeline, gravity, library sync) | Very complete. Knowledge manager modal groups Items/Chars/Areas/Ways with search/all-none/stale cleanup, saves immediately. | Long panel; tab structure reviewed in task-251. Relationship UI present. |
| **Trigger editor** (per-node trigger rows: type, conditions (treemap), effects (param forms), graph editor (task-351 in progress), validate button, generic PARAMETERS key/value) | Shared across item/way/area/character; trigger graph editor is Phase-1 complete but not shipped (inprogress 351). | Effects need hand-authored param keys; **no snippet palette** for "chest/examine", "torch/light", "whisper door" patterns. |
| **Outline panel** (19 rooms… copy-to-clipboard, per-room expand: description/exits/items/players; click → focus+inspect; temp/light/air badges) | Read-only tree; copy exports plain text. | Read-only: no inline edit, no checkboxes, no drag reorder. |
| **Issues panel** (validator: trigger wiring, way authoring fields, mechanical tags with ⚙ quick-fix, library drift) | Live-world validation, auto-refresh, jump buttons. | Validates the live graph, not scenario files; no "before loading" audit. |
| **Agents / Lens / Event stream** | Agent roster, initiative, per-agent lens of what they see, stream filters/persistence. | — |
| **World Lore modal** (browser modal, `lore-view`) | CRUD over `world_lore`; lore injected into system prompt. | — |

### 2.3 Maintain / Update

| Function | How it works | Friction / notes |
|---|---|---|
| 💾 **Save / Load modal** (Game menu) | Lists `saves/` with stats (time, turn, player, scenario, PCs, areas, size, version), AUTO slot pinned, overwrite slot, rename (label+file), delete. | **Save-game, not scenario.** This is runtime snapshots. |
| 📝 **Save Scenario…** (`saveScenarioToFile` → `/api/save-scenario`) | Returns `to_scenario_dict()` **and downloads a JSON via Save-As dialog — it does NOT write `data/scenarios/<name>.json`**. | **Misleading + broken workflow:** authors think they updated the scenario; Restart still reverts. The scenario source is only updated by `/api/load` (whole-world replacement). |
| 🌀 **Restart** (`restartScenario` → `/api/reset`) | Reload from `_scenario_source` (or `world_template.json`); clears logs/ticks; deletes boot autosave. Undo-safe. | The trap: with no Commit path, "Restart" silently destroys uncommitted authoring. |
| **Live-edit push** (EventSource `/api/events`, `world_changed`) | Refetches state on any mutation; logs "World edited by <editor> — POST /path". | Log line only; no per-edit undo binding, no edit feed. |
| **Undo/Redo** (graph toolbar; `/api/undo`, `/api/redo`) | 10-deep full-world snapshots pushed on load/reset and (some) ops. | **Invisible** (two small buttons), **unlabeled** (no "before: moved 12 items"), and only reset/load push snapshots — most single edits don't get their own undo entry. |
| **Template sync / diff** (save-to-library, refresh-from-library, field locks, drift warnings) | Per-node library round-trip with diff modal; Issues flags drift. | Per-node only. No "sync this whole area's items", no scenario-level diff. |
| **Scenario from Text — Apply** | Replaces world; undo restores. Scenario file written by `/api/load`. | OK. |

### 2.4 Playtest & hand-off

| Function | How it works | Friction / notes |
|---|---|---|
| **Play** (▶/⏭/steps), Turn queue, Spectate | Browser agent loop; tick manager; stream. | Turn-based toggle is separate; max-steps guard exists. |
| **World export** (`world-export.js` text/file), **copy outline**, **save file** | Plain text outlines / JSON dumps. | No scenario pack (world+library+tags) export; no zip. |
| **Import** | See 2.1 Load JSON. | No preview. |
| **MCP tools** (build_area/item, connect_areas, import/export, lore, memories…) | Full programmatic surface; external agents author. | No GUI twin for bulk-authored changes (no "review MCP batch" view). |

---

## 3. Suggested improvements (prioritized)

### P0 — fix the workflow breakers
1. **Scenario status chip + Commit** (top bar): `📦 <scenario> · source <age> · ● N changes` with **[💾 Commit]** (writes live world into `data/scenarios/<name>.json`, undo-safe) and **[🌀 Restart]**. Detects drift server-side (`to_dict()` vs source hash) or at least shows the chip after any mutation.
2. **Make "Save Scenario…" honest**: menu becomes [💾 Commit to Scenario] (server write, no download) + [📤 Export Scenario File] (the current download behavior).
3. **Import preview**: `Load JSON…` → parse → show counts (rooms/players/ways/items), source file name, big sanity line (missing areas referenced by exits, etc.) → [Apply with Undo] / [Cancel].

### P1 — UI glue (pervasive speed)
4. **Command palette (Ctrl+K)**: fuzzy jump to any node (focus+inspect), any menu action, any panel/tab. One index built from graph + a static action table.
5. **Undo history dropdown**: expose the 10-deep stack with labels (push sites add a short label: "before: reset", "before: loaded scenario X", "before: editor batch"). Click = restore.
6. **Recently-edited rail**: last ~10 nodes touched in this session (frontend records its own PATCHes; jump-back on click).

### P2 — maintain intelligently
7. **Changes-since-source panel**: server diff (`to_dict()` vs source) grouped by +rooms/−rooms/changed-env/items/ways; per-group Commit/Discard; "Open diff" reuses the sync-diff modal per node.
8. **Scenario Manager modal**: list `data/scenarios/*` (stats, age); open with preview; **Audit** (run the validator against a fresh load of that file — offline issues count); rename/duplicate/delete; "Clone current world into new scenario".
9. **Audit-check on import** (same validator pass as #8, pre-apply).

### P3 — authoring acceleration
10. **Draw-a-door wizard**: select two areas → `connect_areas` flow in the GUI (way node + 4 edges + defaults), with name/cardinal/hidden/one-way options.
11. **Duplicate room (+contents/items/triggers)**; duplicate item with contents.
12. **Bulk selection mode** (shift-click) + action bar: tag / state / env preset / delete / move.
13. **Env presets & zone apply** ("Arctic: -12°, bright, fresh" → apply to selection).
14. **Trigger snippet palette** (chest, torch, whispering door, capture-recorder template with param placeholders).
15. **Room template palette** — reuse the existing library areas pipeline (Save Area → New Room from Template) with pre-seeded starter templates.
16. **World-building onboarding checklist** for New Scenario (premise → map → cast → props → hooks, each links to the right tool).

### P4 — visibility
17. **Scenario-from-text append mode** (draft merges into current world; per-room accept mapped onto existing nodes).
18. **"World edited" feed with per-edit undo** (bind EventSource entries to undo snapshots).
19. **Scenario health dashboard** (per-file audit reports; "issues: 3 high, 1 block").
20. **Keyboard map** (Ctrl+S commit, Ctrl+K palette, Ctrl+Z undo — currently only toolbar).

---

## 4. Dependencies / sequencing notes

- P0 items 1-3 need no new storage format; Commit uses `to_scenario_dict()` (already exists) + a small write route (mirrors `/api/load`'s scenario write but from live state, with `_push_undo_snapshot`).
- #5 (undo labels) touches every `_push_undo_snapshot` call site (small, mechanical).
- #7 requires a stable diff identity (node ids; the sync-diff machinery already computes property diffs per node — reuse).
- #8/#9 reuse `TriggerValidator` on a throwaway `VirtualWorld().load_from_dict(...)` — safe (no side effects beyond the object).
- #15 dovetails with the area library wiring already present (`InspectorTemplateSync.populateSelector('area')`).
- The trigger editor (task-351), behavior state-machine editor (task-226), event-stream v2 (task-340/341), and inspector tab restructure (task-251) are already underway in the task vault — this document is meant to complement them, not duplicate.
