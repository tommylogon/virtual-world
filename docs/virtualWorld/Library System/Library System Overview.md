# Library System Overview

The Library system is a persistent, file-based registry for reusable game content. It allows world authors to create, store, and import entities (items, characters, areas, traits, conditions, behaviours) across different scenarios without duplication.

## Directory Structure

All library data lives under `data/library/`, organised by entity type:

```
data/library/
├── items/          # Item templates (282 JSON files across all types)
├── characters/     # Character/player templates
├── areas/          # Area templates (often contain embedded players + items)
├── traits/         # Trait definitions (e.g. allergic, blind, cleanfreak)
├── tags/           # Tag definitions (id-keyed; see [[Library System/Tags System]])
├── conditions/     # (defined but directory may not exist yet)
├── behaviours/     # (defined but directory may not exist yet)
├── areas/          # (defined but directory may not exist yet)
└── ways/           # (defined but directory may not exist yet)
```

The full list of supported types is defined in `routes/library_routes.py:19`:

```python
REGISTRY_TYPES = ['items', 'characters', 'areas', 'traits', 'conditions', 'behaviours']
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
  "hidden": false,
  "action_costs": {},
  "skill_check": {},
  "effect_target": null,
  "effect_stat": null,
  "effect_amount": 0,
  "tags": [],
  "triggers": [],
  "contents": []
}
```

### Character Example (`data/library/characters/Kaelen Voss.json`)

Characters include full player data: `stats`, `vitals`, `skills`, `traits`, `state`, `current_area`, `inventory` (array of item names/IDs), `emotion`, `memories`, `relationships`, `behaviors`, `npc_behavior`, `npc_action_interval`, `simple_npc` flag, and `world_knowledge`.

### Area Example (`data/library/areas/mansion.json`)

Area library files are **full world snapshots** containing embedded `players`, `areas`, and `graph` data. They include the complete room definitions with environments, exits, and items.

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

### `load_registry(data_dir, filename)` (line 50)

Reads every `.json` file from `data/library/<name>/` where `name` is derived from `filename` (e.g. `items.json` → `data/library/items/`). Returns a dict keyed by filename (without extension).

```python
def load_registry(data_dir, filename):
    subdir = _registry_subdir(data_dir, filename)  # data/library/<name>/
    result = {}
    for entry in os.listdir(subdir):
        if not entry.endswith('.json'): continue
        key = entry[:-5]
        with open(os.path.join(subdir, entry), 'r') as f:
            result[key] = json.load(f)
    return result
```

### `save_registry(data_dir, filename, data)` (line 74)

Writes one file per dict key into `data/library/<name>/`. Deletes files whose keys are no longer present in the dict — this is a full sync, not an append.

```python
def save_registry(data_dir, filename, data):
    subdir = _registry_subdir(data_dir, filename)
    # Remove stale entries
    for key in existing - current:
        os.remove(os.path.join(subdir, f"{key}.json"))
    # Write current entries
    for key, value in data.items():
        with open(os.path.join(subdir, f"{key}.json"), 'w') as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
```

### `_registry_subdir(data_dir, filename)` (line 42)

Maps `items.json` → `data/library/items/`, creating the directory if it doesn't exist.

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

## Importing from Library (Copies, Not References)

Importing creates **independent copies** of library data in the world graph. There is no live link — modifying the imported entity does not modify the library entry, and vice versa.

### Item Import (`routes/library_routes.py`)

`POST /api/build/item-from-library` copies item properties (`description`, `actions`, `uses`, `weight`, `action_costs`, `skill_check`, `hidden`, `locked`, `equip_slots`, `tags`, `current_state`) from the library entry into a new graph `Node`. It also:
- Creates `logic_trigger` nodes for each entry in the item's `triggers` array
- Adds `location`, `contains`, or `carried_by` edges for placement

### Character Import (`library_routes.py:91-172`)

`POST /api/library/import/character/<id>` creates a `Player` object from library data, copies stats/vitals/skills/traits/personality/memories/behaviors, and optionally imports inventory items from the library.

### Area Import (`library_routes.py:176-226`)

`POST /api/library/import/room/<id>` creates a `Area` object from library data and imports referenced items.

## Library Browser UI

The UI is implemented in `static/js/library-browser.js`. It provides:
- **Tabbed interface** across all 6 entity types (`items`, `characters`, `areas`, `traits`, `conditions`, `behaviours`)
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
