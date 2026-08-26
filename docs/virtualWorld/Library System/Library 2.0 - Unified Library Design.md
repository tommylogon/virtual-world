# Unified Library — Redesign Proposal ("Library 2.0")

> Status: **Design proposal** — 2026-08-17. Audited against current code.
> Implementation progress (see task-291): **Phase 1 done** — one `/api/library/*` API (registry
> routes folded/deleted, MCP migrated, `rename`/`place`/`refresh-to-world` live), and **conditions +
> traits are now data-driven** (`data/library/conditions/*.json`, `data/library/traits/*.json` load at
> import; hardcoded dicts are fallback; full suite green + live smoke pass).
> Companion task docs: task-287 (blind sensory — touchpoint for the condition editor),
> task-288 (condition editor modal + `/api/conditions`), task-266 (condition catalog),
> task-291 (this consolidation).
> See also the stale `Library System Overview.md` — **it disagrees with the code in several places** (Section 1.4).

---

## 0. TL;DR

One library, one paradigm. Today there are **three frontend tiers**, **two backend API families**,
**four save paths**, and a handful of **ghost types** that write files nothing ever reads. The worst
consequence is silent data loss — the ways incident (`task_18_vent_shaft_1.json` truncated to 6 of its
16 fields, filename not renamed) was not an edge case, it's the normal behavior of the generic editor.

The goal: every entity type gets the same three powers —

1. **Full-schema editing** (saving never truncates),
2. **World ↔ library sync** through the DiffModal (update/duplicate per section),
3. **Import / placement** into the world.

Plus: real renames (with file GC), custom modals (no native `prompt`/`confirm`), and the dead weight
removed.

---

## 1. Audit — what is actually broken

### 1.1 Two parallel backend APIs

Two route modules serve the *same* entity types with *different* contracts:

| Concern | `routes/items_registry.py` (`/api/registry/*`) | `routes/library_routes.py` (`/api/library/*`) |
|---|---|---|
| Items CRUD | GET/POST/DELETE `/api/registry/items[/<id>]` | GET/POST/DELETE `/api/library/items[/<id>]` |
| Characters CRUD | GET/POST `/api/registry/characters` | GET/POST/DELETE `/api/library/characters` |
| Traits CRUD | GET/POST `/api/registry/traits` | GET/POST/DELETE `/api/library/traits` |
| Character import | POST `/api/registry/characters/import` (`items_registry.py:313`) | POST `/api/library/import/character/<id>` (`library_routes.py:93`) |
| Build/place item | POST `/api/build/item-from-library` (`items_registry.py:57`) | — (frontend calls the registry one) |
| Refresh world from lib | POST `/api/items/<id>/refresh-from-library` (`items_registry.py:178`) | POST `/api/ways/<id>/refresh-from-library` (`library_routes.py:290`) |
| Way/area/tag/condition/behaviour/trigger CRUD | — | generic `/api/library/<type>` |

**Problems:**
- **Character import is implemented twice** with drifting behavior (`items_registry.py:313` vs
  `library_routes.py:93` — the library one additionally imports inventory & re-links equipment).
- **Payload contract differs:** `/api/registry/items` accepts `{id, data}` *or* flat; the generic
  `/api/library/<type>` POST accepts `{id, data}` *or* flat-with-`id`. Two parsers to keep in sync.
- Items GET/POST/DELETE exist on both; a bug fixed in one silently diverges from the other.

### 1.2 Three frontend tiers — the same "save" behaves totally differently per tab

`static/js/library-browser.js` + `static/js/item-library.js` implement three different paradigms:

| Tier | Types | Editor | World→lib save | DiffModal | Import | Rename |
|---|---|---|---|---|---|---|
| **A** | items | Rich full-schema editor (`item-library.js`, 1144 lines: actions, equip slots, tag-driven conditional fields, triggers w/ graph editor, contents, AI gen, export JSON, duplicate) | `saveWorldItem` + `syncAllWorldItems` with DiffModal | ✅ | Placement ("Place in Area", multi-select) | Duplicate + auto-id-from-name |
| **B** | characters, areas | Generic form + world-payload builders (`_buildCharacterCard`, `_buildAreaPayload`) | `saveWorldToCharacter/Area` + `syncAllWorld*` with DiffModal | ✅ | ✅ "Import to World" | ❌ (readonly ID) |
| **C** | **ways**, traits, conditions, behaviours, tags | Generic 6-field config editor (`_getEditorConfigs()`, `library-browser.js:176-248`) | ❌ none | ❌ | ❌ | ❌ (readonly ID) |

**Tier C is the broken tier.** `saveEntry()` (`library-browser.js:340`) rebuilds the payload from only
the config's declared fields and **overwrites the whole entry** — so ways lose `pass_message`,
`requires`, `max_size`, `needs_open`, `one_way`, `prevent_close`, `edge_length`, `parameters`,
`triggers`. Traits/conditions/behaviours/tags truncate the same way. The ID input is `readonly` for
existing entries (`library-browser.js:297`), so a rename is *impossible* from the UI — the filename
can never follow the name.

> This is exactly the reported bug: a way saved from the library tab dropped 10 fields and kept the
> old filename. Confirmed root cause — not a mystery, the normal path.

### 1.3 Ghost types & dead code

**Verified 2026-08-17** — not all "ghosts" are ghosts; three things that looked dead are actually
alive in unexpected places:

| Item | Where | Reality |
|---|---|---|
| **Conditions tab** | `library-browser.js` + `lib-pane-conditions` (index.html:502) | `data/library/conditions/` is **empty**; `conditions.json` is never loaded by any engine/route logic. The real conditions live in `player.py:CONDITION_DEFINITIONS` and are edited via the inspector's condition **modal** (`/api/conditions`, task-288). The tab's editor uses a **legacy schema** (`duration, severity, effects`) that nothing consumes. **Decision (§4): keep, but make the catalog data-driven so the tab edits the real thing.** |
| **Traits — the divergence trap** | `data/library/traits/` (52 files) vs `engine/traits.py` `TRAIT_DEFINITIONS` (hardcoded) | The **engine only reads `TRAIT_DEFINITIONS`** (effects-based). The library files (`{id, name, description, category, params}` — a *different* schema) are read **only by UI pickers** (`agent-view.js:118` trait selector, `trigger-editor.js:212`). So the Traits tab can create traits the engine **silently ignores**, and the pickers can offer traits that don't exist in the engine. Two sources, diverged. **Decision (§4): unify — load `data/library/traits/*.json` into the engine at startup; one source feeds engine + pickers + tab.** |
| **Behaviours tab** | `lib-pane-behaviours` (index.html:529) | `data/library/behaviours/` is empty; `behaviours.json` never loaded. Behaviours are **per-character data** — `engine/npc_behaviors.py` evaluates `player.behaviors[]` arrays (trigger/interval/conditions/actions) attached to each character. No blueprint registry exists. **Remove the tab/type.** |
| **Triggers — NOT dead** | `data/library/triggers/` (7 files) + `REGISTRY_TYPES` | Used as a **blueprint store by the trigger graph editor**: `trigger-graph.js` saves (`_saveBlueprint`), loads (`_loadBlueprint`), and picks (`_pickBlueprint`) blueprints via `/api/library/triggers`. **Keep the type + files; there's just no browser tab** (authored inline, stored as blueprints). |
| **`rooms` dir** | `data/library/rooms/` (3 files) | Legacy alias of `areas`. Only referenced by `tools/migrate_legacy_triggers.py`. **Delete.** |
| **IndexedDB `item_library` store** | `storage.js` (`getLibraryItem`, `setLibraryItem`, `getAllLibraryItems`, `deleteLibraryItem`, store creation) | Browser-side legacy item library. **Nothing calls it.** Dead code + dead data in user DBs. |
| **Inline save path** | `main.js:132` | Auto-saves a **reduced** item payload on some flow (`name, description, actions, uses, weight, current_state, equip_slots, tags`) — a fourth save path that truncates by design. Should be consolidated into the item editor's builder. |

### 1.4 The overview doc disagrees with the code

`docs/virtualWorld/Library System/Library System Overview.md` is stale:

- **Says** `save_registry` deletes stale files ("full sync, not an append") — **the code never deletes**
  (`routes/helpers.py:148-163`, with an explicit "Never deletes files" comment). Renames therefore leave
  orphaned `<old_id>.json` files forever.
- Lists `REGISTRY_TYPES` as 6 types — it's **9** today (`tags`, `triggers` added).
- Describes areas as "full world snapshots (embedded players/areas/graph)" — current `_buildAreaPayload`
  produces a **flat template** (items/exits/triggers).
- Says imports are "independent copies, **no live link**" — but items/ways get a `library_id` property and
  there is a whole **refresh-from-library** path (bidirectional sync).
- Item example shows removed legacy fields (`effect_target`, `effect_stat`, `effect_amount`).
- Omits ways, tags, DiffModal, refresh-from-library, build-item-from-library, the condition catalog.

### 1.5 Bugs (confirmed, in priority order)

1. **Tier-C `saveEntry` truncates entries on save** — data loss (the ways incident). `library-browser.js:340`.
2. **Existing-entry IDs are readonly** — renames impossible; filename can't follow name. `library-browser.js:297`.
3. **`save_registry` never GCs** — renaming/duplicating leaves orphan `<old_id>.json` files. `helpers.py:148`.
4. **DiffModal duplicate naming uses native `prompt()`** (`diff-modal.js:126`) — violates the project rule
   that destructive/input flows use **custom modals** (see the delete-confirmation decision & the
   task-288 modal). Also no validation on the new id.
5. **Tag validation is only wired on graph node updates** (`routes/graph.py:64`), not on library saves —
   library entries can silently store tags that don't exist in the tag library.
6. **Two character imports** — drift risk. `items_registry.py:313` vs `library_routes.py:93`.

### 1.6 What's genuinely good (keep these)

- **DiffModal** — per-section update/duplicate/cancel is the right pattern; it just needs a custom modal for naming.
- **Item editor** — richest editor in the app; the template every other tab should grow toward.
- **World→library sync with skip-unchanged** (`_itemsDiffer`, `syncAllWorld*`) — fast, conflict-aware.
- **Per-file JSON storage** — git-friendly diffs per entry; keep it.
- **`library_id` + locked_fields** — the refresh/lock machinery on items/ways is exactly the right sync primitive; generalize it.
- **`/api/conditions` catalog + modal (task-288)** — the model for how "catalog-driven data" should be edited.

---

## 2. Target architecture

### 2.1 One backend: `routes/library_routes.py` becomes the only library API

Fold `items_registry.py` into it (keep file build/import/refresh logic, migrate routes). Final surface:

```
# CRUD
GET    /api/library/<type>                 # list
POST   /api/library/<type>                 # create/update  (accepts flat OR {id, data})
DELETE /api/library/<type>/<id>            # delete

# Verbs
POST   /api/library/<type>/<id>/rename     # { new_id } → write new file, GC old, return {old, new}
POST   /api/library/items/<id>/place       # (was /api/build/item-from-library) area|container|character
POST   /api/library/<type>/<id>/import     # character & area import (single implementation!)
POST   /api/library/<type>/<id>/refresh-to-world  # unify item + way refresh (node_id, sections)

# Catalog / metadata
GET    /api/library/entities               # counts (keep)
GET    /api/library/schema                 # per-type field schemas → drives a schema-driven editor
GET    /api/conditions                     # condition catalog (keep, task-288)
```

- Delete `/api/registry/*` and `/api/build/item-from-library` after migrating callers:
  `item-library.js` (`getLibraryItems`, `saveLibraryItem`, `deleteLibraryItem`),
  `agent-view.js:1313-1317` (character registry), `main.js:132` (inline reduced save → replace with the real builder).
- One character-import implementation (the richer `library_routes.py` one).

### 2.2 One frontend paradigm: schema-driven tabs

Replace Tier C's hardcoded field arrays with a **schema-driven editor** (field spec from
`GET /api/library/schema`, same shape per type). Every tab gets the full stack:

1. **List + search** (+ per-type badges like the items tab's tag/trigger/contents chips).
2. **Full-schema editor** — every field the type supports; *no* field is silently dropped on save
   (save = send the whole schema payload, backend merges, never wipes).
3. **Editable ID** — rename action (with id-from-name suggestion, like items' `_autoIdFromName`),
   routed through the backend rename endpoint so the file is renamed and the old one GC'd.
4. **Save from World** — per-type world→library payload builder (characters/areas/items already exist;
   **ways needs one** — extract `way-view.js:_saveToLibrary`'s payload builder so the tab and the
   inspector share it).
5. **Sync All from World** — per-type, DiffModal per changed entry, skip unchanged.
6. **Import to World / Place** — every type gets it (items place, chars/areas import, ways → connect
   between two areas).
7. **Delete & rename & duplicate via custom modals** — no native `confirm`/`prompt`.

The **items tab keeps its rich editor** (AI gen, contents, triggers, equip) — it's Tier A; the goal is
to raise the others *up to it*, not flatten it down.

### 2.3 Per-type schema coverage (the "never truncate" contract)

| Type | Fields (must round-trip) |
|---|---|
| **items** | name, description, actions, uses, weight, current_state, light_level, equip_slots, defense, damage, damage_skill, damage_type, stun_chance, stun_duration, insulation, resistances, action_costs, skill_check, contents, aliases, tags, triggers |
| **characters** | everything `_buildCharacterCard` emits (stats, vitals, skills, traits, conditions, equipped, activity, inventory, memories, relationships, behaviors, npc_*… ) |
| **areas** | name, description, tags, environment, items, exits, triggers |
| **ways** | name, description, current_state, pass_message, edge_length, needs_open, auto_close, see_through, one_way, requires, max_size, prevent_close, jump_dc, climb_dc, tags, parameters, triggers |
| **tags** | name, description, category, color, icon, applies_to, examples |
| **traits** | the **engine** `TRAIT_DEFINITIONS` schema (`id, name, description, category, effects, grants_conditions, conflicts, behavior_prompt`, + `params` for parameterized traits) — this becomes the single source after unification; the current 52-file library format (params-only) is migrated |
| **conditions** | the `CONDITION_DEFINITIONS` catalog fields (name, description, gates, auto_fail_checks, mods, speed_mult, periodic, ends_on, known, symptoms, stack, default_duration, excludes) once data-driven |
| **behaviours** | — (tab removed; behaviours are per-character data on character entries) |
| **triggers** | blueprint store for the trigger graph editor (`{name, description, graph}`) — keep, no browser tab |

Backend-side, each type gets an optional **validate/coerce** hook (unknown keys warned, required keys
checked) so typos surface instead of silently persisting.

### 2.4 Sync model (world ↔ library)

- **Keep `library_id` + `locked_fields`** as the link primitive; generalize to all types.
- **library → world:** place/import/refresh. Refresh is per-section and lock-aware (exists for items
  & ways; one unified endpoint).
- **world → library:** save-from-world / sync-all, per-section DiffModal on conflict, short-circuit when
  identical.
- **Rename propagation (decision, §4):** whether renaming a library entry rewrites `library_id` on
  placed nodes.

### 2.5 Data integrity & hygiene

- **Backend rename endpoint** writes the new file, deletes the old one (the GC `save_registry` refuses to do).
- **Orphan sweep:** optional "prune orphans" (files on disk not returned by the index) exposed as a
  maintenance action, since existing repos already contain orphans.
- **`validate_tags_on_save` on library saves**, not just graph updates.
- **Custom modals everywhere** (rename, duplicate naming, delete) — matches the project rule.

### 2.6 Migration & docs

- Delete `data/library/rooms/`; drop the **behaviours** tab/type; keep **triggers** (blueprint store) and
  the **conditions**/**traits** tabs (now backed by the data-driven catalogs). Remove the IndexedDB
  `item_library` store; retire `main.js:132`'s inline save.
- **Conditions → data-driven:** move `CONDITION_DEFINITIONS` out of `player.py` into
  `data/library/conditions/*.json` (one file per condition), loaded at startup with the catalog as
  fallback. `/api/conditions` + the task-288 modal then serve/edit the same files the tab shows.
- **Traits → unified:** load `data/library/traits/*.json` into the engine at startup, merged over /
  overriding `TRAIT_DEFINITIONS`, and migrate the 52 existing files to the engine schema so the tab,
  the pickers, and the engine agree on one source.
- Rewrite `Library System Overview.md` to match reality (per-file format, one API, sync model, schema
  tables). Add short docs: `Sync & DiffModal.md`, `Library Schema.md`, `Migration 2.0.md`.
- Touch `AGENTS.md` Known Gotchas: "the library browser's generic editor truncates" → after Phase 2,
  remove that gotcha; note the unified save contract.

---

## 3. Phased plan (small, verifiable steps)

**Phase 0 — stop the bleeding (1 session)**
- Restore the truncated `task_18_vent_shaft_1.json` (done).
- Ways tab: full field set + editable ID + save via DiffModal (the fix already scoped earlier).
- Add `jump_dc`/`climb_dc` to the way schema (they exist in the inspector but were missing from the payload).

**Phase 1 — backend consolidation**
- Fold `items_registry.py` into `library_routes.py`; delete `/api/registry/*` + `/api/build/item-from-library`;
  migrate JS callers.
- Add `/rename` (write + GC), `/refresh-to-world` (unify item/way), `/schema`, single character import.
- Wire `validate_tags_on_save` into library POST.
- **Conditions & traits become data-driven:** load `data/library/conditions/*.json` + `data/library/traits/*.json`
  at startup (merged over `CONDITION_DEFINITIONS` / `TRAIT_DEFINITIONS`), migrate the 52 trait files to the
  engine schema, seed `data/library/conditions/` from the catalog.

**Phase 2 — frontend unification**
- Schema-driven editor for Tier C tabs (full fields, editable ID, rename). Conditions/traits tabs now edit
  the real data-driven catalogs.
- Extract shared world→library builders (ways from `way-view.js:_saveToLibrary`; traits from the trait editor).
- Custom modals for duplicate naming / rename / delete (reuse task-288 modal styling).
- Save-from-World + Sync-All + Import for every tab.

**Phase 3 — cleanup & docs**
- Remove the behaviours tab/type, the `rooms` dir, the IndexedDB store, the `main.js:132` path.
- Orphan sweep action. Rewrite `Library System Overview.md` + add the sub-docs.

**Phase 4 — polish (optional, fun)**
- Library-wide search + favorites/last-used; bulk export/import of a whole library dir (zip/json);
  AI "polish" for ways/areas like items' ✨ Improve; "place way between two areas" wizard from the tab.

---

## 4. Open decisions (user's call)

1. **Conditions & traits — keep, and make them the single source of truth.** Verified: the engine
   ignores both library dirs today (`CONDITION_DEFINITIONS` / `TRAIT_DEFINITIONS` are hardcoded in
   Python). The plan is to move them to `data/library/conditions/` + `data/library/traits/` (loaded at
   startup) so the tabs, the pickers, and the engine all read one source. **Decided: do it.** (User:
   "I'd still like to see conditions and traits.")
2. **Behaviours — remove** (verified: per-character data, no blueprint store). **Decided: remove tab/type.**
3. **Triggers — keep as blueprint store** (verified: `trigger-graph.js` save/load/pick). **Decided: keep
   type + files, no browser tab.**
4. **Rename propagation** — when a library entry is renamed, should placed nodes' `library_id` be
   rewritten (recommended: yes, same session) or left stale for the refresh flow to catch?
5. **Area format** — keep flat templates (current) or restore full snapshot format (old Overview docs)?
6. **Ways "Save from World" scope** — the tab gets the full world→library save with DiffModal
   (recommended), reusing `way-view.js`'s payload builder.

---

## 5. Success criteria

- Saving *any* library entry from *any* tab round-trips **every** field of that type (fuzz: save →
  reload → save → diff is empty).
- Renaming a library entry renames the file, removes the old one, and never orphans data.
- One API, one editor paradigm, zero native `prompt`/`confirm` in library flows.
- `Library System Overview.md` matches the code line-by-line.
