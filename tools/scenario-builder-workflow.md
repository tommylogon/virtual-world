# Kraktooth Goblin Camp — Scenario Builder Workflow

## Problem

One-shot JSON generation produces invalid scenarios because:
- Way nodes need `pass_message`
- Weapons need `damage` in addition to `damage_dice`
- Armor needs `equip_slots`
- Container items need `max_weight_capacity`
- Trigger edges must point from item → trigger, not trigger → item
- Area node IDs must match engine conventions (`area_<name>`)

## Solution

A scripted component workflow that:
1. Creates areas with validated node IDs and properties
2. Creates ways with `pass_message` and proper connection edges
3. Creates items with complete mechanical properties
4. Creates characters with full LLM-agent state
5. Wires triggers correctly (item → trigger)
6. Assembles and validates before writing

## Scripts

### `tools/build_scenario.py`

Main entry point. Reads component JSON files, validates, assembles, writes scenario.

### `tools/scenario_components/areas/`

Individual area JSON files. Each area gets:
- Validated `id` matching `area_<name>` convention
- `name`, `description`
- `environment` (light, temperature, air, smell, noise)
- `human_description`, `goblin_description`
- `goblin_knowledge` (known_as, importance, common_activities)
- `features`, `possible_items`, `possible_encounters`
- `tags`, `floor`, `central_gravity_enabled`

### `tools/scenario_components/ways/`

Individual way JSON files. Each way gets:
- Validated `id` matching `way_<name>` convention
- `name`, `description`
- `pass_message` (required by engine)
- `area_from`, `area_to`
- `current_state`, `hidden`, `tags`
- `cost` (time, energy)
- `requires` (skill/condition if needed)

### `tools/scenario_components/items/`

Individual item JSON files. Each item gets:
- Validated `id` matching `item_<name>` convention
- `name`, `description`
- `actions` (comma-separated or array)
- `weight`, `uses`, `current_state`, `hidden`
- `tags` with mechanical implications:
  - `weapon` → requires `damage` and `damage_type`
  - `armor` → requires `equip_slots`
  - `container` → requires `max_weight_capacity`
  - `light_source` → requires `light_level`
  - `heat_source` → requires `heating_rate`
  - `food` → should have `adjust_vital` for hunger
  - `drink` → should have `adjust_vital` for thirst
  - `magic` → may have `mana_cost`
- Mechanical properties filled based on tags

### `tools/scenario_components/characters/`

Individual character JSON files. Each character gets:
- Validated `id` matching `character_<name>` or player convention
- `name`, `personality`, `description`, `base_description`
- `stats` (STR, DEX, CON, INT, WIS, CHA)
- `skills` (Acrobatics, Athletics, Perception, Persuasion, Stealth, Survival)
- `vitals` (Bladder, Energy, Entertainment, HP, Hunger, Hygiene, Max_HP, Sanity, Social, Thirst, Temperature)
- `tags` (species, role, etc.)
- `emotion` (current, description, intensity)
- `traits`, `interest_tags`
- `current_area` (must reference valid area)
- `autonomy`, `simple_npc`
- `memories`, `relationships`
- `decay_rates`

### `tools/scenario_components/triggers/`

Individual trigger JSON files. Each trigger gets:
- Validated `id` matching `logic_trigger_<name>` convention
- `name`, `trigger_type` (on_examine, on_take, on_use, etc.)
- `target` (the item/area this trigger attaches to)
- `conditions`, `conditions_logic`
- `effects` array with typed effects
- `once` flag

### `tools/scenario_components/world/`

World-level JSON files:
- `world_lore.json` — lore entries
- `world_state.json` — season, day, weather, etc.
- `population.json` — tribe/village populations
- `knowledge.json` — known locations, routes, dangers, resources
- `schedules.json` — character daily schedules
- `world_events.json` — queued events

## Assembly Flow

```
1. Load all areas → validate IDs, names, descriptions
2. Load all ways → validate pass_message, area_from/to exist
3. Load all items → validate mechanical properties match tags
4. Load all characters → validate current_area exists, full state blocks
5. Load all triggers → validate trigger_type, target exists
6. Assemble graph:
   - Add all area nodes
   - Add all way nodes
   - Add all item nodes
   - Add all character nodes
   - Add all trigger nodes
   - Create connection edges (area ↔ way ↔ area)
   - Create in edges (character → area, item → area)
   - Create triggers edges (item → trigger)
   - Create carrying edges (player → item)
7. Add world_lore, world_state, population, knowledge, schedules, events
8. Validate entire scenario:
   - All current_area references resolve
   - All trigger targets resolve
   - All way area_from/to resolve
   - All items have required properties for their tags
   - JSON is valid
9. Write scenario file
```

## Validation Rules

### Areas
- `id` must match `area_<name>` convention
- `name` must be non-empty
- `description` must be non-empty
- `environment` must have light, temperature, air, smell, noise

### Ways
- `id` must match `way_<name>` convention
- `pass_message` must be non-empty
- `area_from` and `area_to` must reference existing areas
- `current_state` must be "open" or "closed"

### Items
- `id` must match `item_<name>` convention
- `actions` must be non-empty
- If tag `weapon` present → must have `damage` and `damage_type`
- If tag `armor` present → must have `equip_slots`
- If tag `container` present → must have `max_weight_capacity`
- If tag `light_source` present → must have `light_level`
- If `damage_dice` present → should also have `damage`

### Characters
- `id` must match naming convention
- `current_area` must reference existing area
- Must have `personality`, `stats`, `vitals`, `tags`
- `simple_npc` must be boolean
- If `simple_npc: false` → must have full agent state

### Triggers
- `id` must match `logic_trigger_<name>` convention
- `trigger_type` must be valid event type
- `target` must reference existing item or area
- Edge must go from target → trigger (not reverse)

## Usage

```bash
# Build from components
python tools/build_scenario.py --components tools/scenario_components --output data/scenarios/kraktooth_goblin_camp.json

# Validate existing scenario
python tools/validate_scenario.py --input data/scenarios/kraktooth_goblin_camp.json

# Load via API
python tools/load_scenario.py --file data/scenarios/kraktooth_goblin_camp.json
```

## Benefits

1. **Reusability**: Areas, items, characters can be reused across scenarios
2. **Validation**: Each component is validated before assembly
3. **Version control**: Component files are easy to diff and merge
4. **Procedural generation**: Components can be generated by LLM or scripts
5. **Library integration**: Components can be imported from the library
6. **Editor parity**: Follows the same conventions as the NL editor
