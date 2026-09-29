# Library System Overview

> **Corrected 2026-09-29.** Several claims below were verified against the code and fixed; each correction is marked inline. This file is still a partial rewrite — see [Library 2.0 - Unified Library Design](<Library 2.0 - Unified Library Design.md>) §1.4 for the remaining falsehoods, and **task-291** for the rewrite. Do not add to the type list here without reading `routes/library_ops.py:17`.

The Library system is a persistent, file-based registry for reusable game content. It allows world authors to create, store, and import entities (items, characters, areas, ways, traits, conditions, behaviours, tags, triggers, structures) across different scenarios without duplication.

## Directory Structure

All library data lives under `data/library/`, **one JSON file per entry**, in a directory per type. File counts as of 2026-09-29:

```
data/library/
├── items/          # 532 item templates
├── tags/           # 588 tag definitions (id-keyed; see [[Library System/Tags System]])
├── areas/          # 90 area templates
├── ways/           # 85 way templates
├── traits/         # 71 trait definitions (e.g. allergic, blind, cleanfreak)
├── characters/     # 68 character/player templates
├── conditions/     # 39 data-driven conditions (task-291)
├── triggers/       # 9 trigger blueprints — used by the trigger graph editor, no browser tab
├── behaviours/     # authored from the Behaviours tab; the engine does not read these yet (task-590)
├── structures/     # structure templates; engine + API exist, no UI yet (task-591)
├── rooms/          # LEGACY, a stale alias of `areas`. Delete — see task-291 Phase 3
├── behaviours.json # ✗ does not exist and is never read — see "one storage shape" below
└── structures.json # ✗ same
```

**There is one storage shape, not two.** A registry *filename* is only a name: `load_registry(data_dir, 'items.json')` strips the extension and reads the **directory** `data/library/items/` (`routes/helpers.py:201-206`). Nothing reads a `data/library/<type>.json` file, so "is `behaviours.json` missing?" is the wrong question — the directory is what matters, and it is created on demand.

The full list of supported types is defined in **`routes/library_ops.py:17`** (re-exported by `library_routes.py:10` — the list is not defined there):

```python
REGISTRY_TYPES = ['items', 'characters', 'areas', 'ways', 'traits', 'conditions',
                  'behaviours', 'tags', 'triggers', 'structures']
```

## Per-File Format

Each entity is stored as an **individual JSON file** — one file per entry. There are no cross-file references; each file is self-contained. The filename (minus `.json`) becomes the entry's key.

### Item Example (`data/library/items/altar.json`)

```json
{
  "name": "altar",
  "description": "A stone altar draped in dusty black cloth...",
  "actions": "examine",
  "uses": -1,
  "weight": 200,
  "current_state": "normal",
  "light_level": "dim",
  "defense": 0,
  "damage": 0,
  "insulation": 0,
  "tags": ["altar", "ritual", "occult", "stone", "furniture", "display", "shrine"],
  "triggers": [ { "trigger_type": ["on_examine"], "effects": [ ... ] } ],
  "contents": []
}
```

*Corrected 2026-09-29 against the real `data/library/items/altar.json`.* The previous sample showed
`hidden`, `action_costs`, `skill_check` and `effect_target` / `effect_stat` / `effect_amount`. The `effect_*`
trio is **gone** — do not copy it into new content. `action_costs` and `skill_check` are still honoured on
materialisation but are not stored on this entry, and `hidden` is a legacy input that
`library_item_properties` (`engine/library_nodes.py:74-75`) folds into `current_state`. The full set of
properties a materialised node carries is that one function — read it rather than copying any list.

### Character Example (`data/library/characters/Kaelen Voss.json`)

Characters include full player data: `stats`, `vitals`, `skills`, `traits`, `state`, `current_area`, `inventory` (array of item names/IDs), `emotion`, `memories`, `relationships`, `behaviors`, `npc_behavior`, `npc_action_interval`, `simple_npc` flag, and `world_knowledge`.

### Area Example (`data/library/areas/*.json`)

*Corrected 2026-09-29.* Area library files are **flat templates**, not world snapshots. This section
previously claimed they are "full world snapshots containing embedded `players`, `areas`, and `graph` data",
and pointed at a `data/library/areas/mansion.json` that does not exist. Census of all **90** files in
`data/library/areas/`, 2026-09-29 — every key, and how many files carry it:

| Key | Files |
|---|---|
| `name` | 90 |
| `description` | 90 |
| `tags` | 90 |
| `environment` | 90 |
| `items` | 89 |
| `exits` | 81 |
| `triggers` | 89 |

No `players`, no `areas`, no `graph`, anywhere. `_buildAreaPayload` produces exactly this shape, and a
**multi-area** world (a mansion with 40 rooms) is not one area entry — it is a scenario, or a structure
template (see **task-591** for the capture path that produces those).

### Trait Example (`data/library/traits/allergic.json`)

```json
{
  "id": "allergic",
  "name": "Allergic",
  "description": "Takes damage or gains a condition when near items/areas with a matching tag.",
  "category": "physical",
  "params": {
    "type": "string",
    "label": "Allergen tag",
    "placeholder": "e.g. pollen, dust"
  }
}
```

## Load/Save Registry Helpers

Found in `routes/helpers.py`.

### `load_registry(data_dir, filename)` (line 209)

Reads every `.json` file from `data/library/<name>/`, where `name` is `filename` minus `.json` (`items.json` → `data/library/items/`). Returns a dict keyed by filename without extension. Opens each file as `utf-8-sig`; an unreadable entry is logged and skipped, and a missing directory yields `{}` rather than raising.

```python
def load_registry(data_dir, filename):
    subdir = _registry_subdir(data_dir, filename)  # data/library/<name>/
    result = {}
    try:
        for entry in os.listdir(subdir):
            if not entry.endswith('.json'):
                continue
            path = os.path.join(subdir, entry)
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    result[entry[:-5]] = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load library entry {entry}: {e}")
    except FileNotFoundError:
        return result
    return result
```

### `save_registry(data_dir, filename, data)` (line 233)

Writes one file per dict key into `data/library/<name>/`. **It never deletes.** A caller that passes a partial dict — a single test entry, say — must not silently wipe the rest of the registry, so removal is the caller's explicit job via `delete_registry_entry`. *Corrected 2026-09-29: this file previously claimed a full sync with a "remove stale entries" loop. That loop is not in the code; the sample below is the real one.*

```python
def save_registry(data_dir, filename, data):
    """... **Never deletes files** ..."""
    subdir = _registry_subdir(data_dir, filename)
    for key, value in data.items():
        path = os.path.join(subdir, f"{key}.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(value, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Could not save library entry {key}: {e}")
```

**Consequence:** a rename writes a new file and leaves the old one behind forever. Renames go through the backend rename endpoint, which writes the new id *and* removes the old file; `save_registry` will not do it for you.

### `_registry_subdir(data_dir, filename)` (line 201)

Maps `items.json` → `data/library/items/`, creating the directory if it does not exist. Note it is called from **`load_registry` as well as the save path**, so a plain `GET /api/library/behaviours` creates an empty `data/library/behaviours/` directory in the working tree. Harmless for git (empty directories are untracked) but surprising if you are watching for a clean tree.

## API Endpoints

### Item/Character/Trait Registry (legacy)

> **Note:** The old `routes/items_registry.py` (the `/api/registry/*` and `/api/build/item-from-library` endpoints) has been folded into the unified library API. Use the **Unified Library CRUD** endpoints below — `/api/library/<type>`.

### Unified Library CRUD (`routes/library_routes.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/library/entities` | Summary of all entity types + counts |
| GET | `/api/library/<type>` | List all entries of a type |
| POST | `/api/library/<type>` | Create or update an entry |
| DELETE | `/api/library/<type>/<id>` | Delete an entry |
| POST | `/api/library/import/character/<id>` | Import character as player |
| POST | `/api/library/import/area/<id>` | Import area into world graph |

## Importing from Library

*Corrected 2026-09-29: this section previously said importing creates "independent copies … there is no live link", which is only half true and is the more dangerous half to leave standing.*

Importing is a **copy into the world**, but the copy is **linked back**: items and ways carry a `library_id` property, and a **refresh-from-library** path applies changes in either direction. So a world entity derived from a library entry is not an independent snapshot — it can be pushed back and pulled again, and the DiffModal is what resolves a conflict. The two statements are not in tension: the graph node is a copy, and the copy remembers where it came from.

### Item Import (`routes/library_routes.py`)

`POST /api/build/item-from-library` copies item properties (`description`, `actions`, `uses`, `weight`, `action_costs`, `skill_check`, `hidden`, `locked`, `equip_slots`, `tags`, `current_state`) from the library entry into a new graph `Node`. It also:
- Creates `logic_trigger` nodes for each entry in the item's `triggers` array
- Adds `location`, `contains`, or `carried_by` edges for placement

### Character Import (`library_routes.py:91-172`)

`POST /api/library/import/character/<id>` creates a `Player` object from library data, copies stats/vitals/skills/traits/personality/memories/behaviors, and optionally imports inventory items from the library.

### Area Import (`library_routes.py:176-226`)

`POST /api/library/import/room/<id>` creates a `Area` object from library data and imports referenced items.

## Library Browser UI

The UI is implemented in `static/js/library-browser.js`, with panes in `templates/index.html`. It provides:
- **Tabbed interface** across 8 entity types — `items`, `characters`, `areas`, `ways`, `traits`, `conditions`, `behaviours`, `tags` (corrected 2026-09-29: this said 6 and omitted ways and tags). `triggers` and `structures` are registered types with **no tab**: triggers is a blueprint store for the trigger graph editor, structures has no UI at all yet (task-591)
- **Search/filter** for each type
- **Editor forms** generated from field configs in `_getEditorConfigs()`
- **Save to library** from the browser UI
- **Save world character to library** via `saveWorldToCharacter()` — uses DiffModal for conflict resolution
- **Sync all world items to library** via `syncAllWorldItems()` — conflict-aware batch sync with per-item DiffModal prompts
- **Sync all world characters to library** via `syncAllWorldCharacters()` — iterates all players with per-character DiffModal prompts
- **Save world area to library** via `saveWorldToArea()` and `syncAllWorldAreas()` — builds area entry from graph data with items, exits (as templates with `target_room_hint`), and triggers
- **Import** characters/areas directly into the active world

The `LibraryBrowser` singleton is exposed as `window.libraryBrowser` and delegated from `VW.libraryBrowser`.

## Adding New Items to Library

Two paths:
1. **UI**: Open the Library Browser → select type → click "New" → fill form → "Save"
2. **API**: `POST /api/library/items` with `{"id": "my_item", "data": {...}}` or flat JSON

The generic registry handler at `library_routes.py:58` accepts either nested `{id, data}` or flat `{id, name, description, ...}` payloads.

## Character Registry vs Item Registry

- **Items Registry** (`items.json`): Simple item templates — name, description, actions, uses, weight, triggers. Used for world objects.
- **Characters Registry** (`characters.json`): Full character data — stats, vitals, skills, personality, emotions, memories, behaviors, inventory references. Imported characters become playable `Player` objects with full LLM agent capability.
- **Traits Registry** (`traits.json`): Trait definitions with category, description, and parameter schema. Traits are applied to characters to modify behavior or capabilities.

## Related tasks

- [[dev_tasks/review/ui/task-13-unify_item_inspector_and_library|task-13: Unify item inspector and library]]
- [[dev_tasks/done/items/task-95-idempotent-sync-to-library|task-95: Idempotent sync to library]]
- [[dev_tasks/inprogress/items/task-106-tag-library-and-multiselect|task-106: Tag library and multiselect]]
- [[dev_tasks/review/items/task-44-remove_add_from_library|task-44: Remove add from library]]
- [[bug_3-library-slow-open 1|bug-3: Library slow open]]
