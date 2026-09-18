# Kraktooth Goblin Camp — Sandbox Scenario Plan (v3)

## 1. Premise

A living, breathing goblin camp embedded in a contested borderland. The session is not a story with an ending; it is an ongoing D&D-style sandbox slice of life centered on the KrakoTooth tribe and the individuals orbiting them.

The tone is grounded fantasy with respectable worldbuilding — survival hardship, small politics, resource scarcity, personal grudges, rituals, petty theft, traps, bad food, and occasional violence. Nothing is railroading toward a finale; events emerge from the environment, relationships, and immediate needs.

The player is a human in the forest, free to move anywhere in the territory and watch the world evolve.

## 2. Core Themes

- Survival vs. comfort
- Tribe loyalty vs. personal ambition
- Usefulness vs. status
- Scarcity and improvisation
- Attention as currency
- Territory, routes, and secrets
- Civilization as opportunity, not safety

## 3. Viwo Scenario Shape

Per `ScenarioCreationGuide.md`, the engine reads:
- `graph.nodes` for areas, ways, items, characters, logic triggers
- `graph.edges` for connections, `in`, `triggers`, `equipped`, `carrying`
- `players` as authoritative character state
- `world_lore` injected into every agent prompt
- Runtime state: `active_player`, `time_ticks`, `clock_start_*`, `turn_number`, `narration_mode`, `ghost_mode`

This plan is therefore organized around: areas/ways graph, character roster, item/trigger tables, lore blocks, and runtime config.

## 4. Time and Weather

- Timescale: **1 minute per turn**
- Initial simulation: **1 week** (10,080 turns)
- `time_per_tick_minutes`: 1
- `clock_start_hour` / `clock_start_minute`: TBD
- Days and nights cycle
- Weather shifts: rain, cold, heat, fog
- Seasons change resource availability
- Some areas become inaccessible during bad weather
- Goblin activity patterns shift with light and weather

## 5. Map and Graph Plan

### 5.1 Camp Areas (nodes)
These become `area_*` nodes.

1. `area_camp_entrance` — main entrance, traps, smells of smoke
2. `area_chiefs_pit` — central fire, meetings, feasting
3. `area_chiefs_den` — leader room, trophies, war plans
4. `area_sleeping_halls` — hammocks, furs, personal belongings
5. `area_nursery` — young goblins, caretakers, basic supplies
6. `area_cooking_area` — fires, meat racks, pots, spices
7. `area_food_storage` — dried meat, mushrooms, barrels, spice shelves
8. `area_workshop` — repairs, crafting, tinkering
9. `area_scrap_pile` — junk, stolen goods, parts, valuables in trash
10. `area_training_pit` — sparring, weapon practice, cages
11. `area_prison_pens` — slaves, captives, trade goods
12. `area_shaman_lair` — rituals, herbs, strange artifacts
13. `area_healing_area` — basic medicine, bandages, potions
14. `area_scouting_rooms` — maps, reports, tracking info
15. `area_mine_access` — tunnels to lower caves, stone, ore
16. `area_storage_caves` — wood, stone, clay, spare supplies
17. `area_animal_pens` — wolves, captured beasts, livestock
18. `area_water_source` — underground lake, fishing, water storage
19. `area_waste_disposal` — refuse, bones, latrine downstream
20. `area_side_tunnels` — expansion, exploration, unknown routes

### 5.2 Surrounding Areas
21. `area_deep_forest`
22. `area_raven_river`
23. `area_murk_lake`
24. `area_blackmarsh`
25. `area_old_dwarven_ruins`
26. `area_abandoned_farm`
27. `area_eldenford_village`
28. `area_human_road`
29. `area_northern_hills`
30. `area_camp_entrance_trail` — forest approach to camp

### 5.3 Ways (edges)
Each connection is a bidirectional `way_*` node with `connection` edges.

Examples:
- `way_camp_entrance_to_forest` between entrance and trail
- `way_forest_to_raven_river`
- `way_forest_to_blackmarsh`
- `way_forest_to_old_dwarven_ruins`
- `way_forest_to_abandoned_farm`
- `way_forest_to_eldenford_edge`
- `way_raven_river_to_camp_tunnel`
- `way_side_tunnels_to_mine_access`
- Internal camp ways between numbered areas

Some ways should have:
- `hidden`: true for secret routes
- `needs_open.enabled`: true for blocked passages
- `requires`: climb, crawl, jump
- `cost.time` and `cost.energy`: travel cost in minutes and energy

## 6. Runtime Config

- `active_player`: human explorer
- `clock_start_hour`: TBD
- `clock_start_minute`: TBD
- `time_per_tick_minutes`: 1
- `turn_number`: 0
- `ghost_mode`: false
- `narration_mode`: none
- `current_area`: starting forest area
- `game_time`: derived from clock start

## 7. Character Roster

All characters go in `players`. Each needs:
- `personality`
- `description` / `base_description`
- `stats`
- `vitals`
- `skills`
- `traits`
- `tags`
- `emotion`
- `current_area`
- `autonomy`, `simple_npc`, `npc_behavior`, `npc_state`, `npc_action_interval`
- `relationships`
- `memories`
- `decay_rates`
- `interest_tags`

### 7.1 Human Player
- `simple_npc`: false
- `autonomy`: false
- `current_area`: `area_camp_entrance_trail`
- Starting vitals, skills, equipment TBD

### 7.2 LLM-Agent Goblins
These should be `simple_npc: false` to use the full agent engine:
- Thrazz
- Zikka
- Vekka
- Mikka
- Gribba
- Rikka
- Krikka

### 7.3 Additional Goblin Characters
These can be `simple_npc: true` or LLM agents depending on desired simulation cost:
- Arix
- Kiala
- Belne
- Leslie (optional)

### 7.4 Human Villagers (Eldenford)
- Village Elder
- Blacksmith
- Merchant
- Road Guard Captain
- Farmer

### 7.5 Animals / Creatures
These should almost certainly be `simple_npc: true` with `npc_behavior` patterns:
- Rag-Tail (wolf pack alpha)
- Old Iron-Back (bear)
- Tusker (boar)
- Shadow-Pelt (worg leader)
- Silver-Talon (raven)
- Croak-Mother (frog)

`simple_npc: true` characters skip LLM calls and act via backend `tick_turn`, which is appropriate for animals and background villagers.

## 8. Items and Triggers

Items are `item_*` nodes with properties including:
- `actions`
- `description`
- `current_state`
- `uses`
- `weight`
- `hidden`
- `tags`
- `action_costs`
- `skill_check`
- `contents` (for containers)
- `equip_slots`
- `light_level`
- `damage_dice`
- `damage_type`
- `defense`
- `heating_rate`
- `insulation`
- `target_temperature`
- `temp_range`

### 8.1 Item Placement
Items are placed via `in` edges to areas or other items:
- `item_rusty_hatchet` → `area_training_pit`
- `item_bread` → `area_cooking_area`
- `item_backpack` → `area_sleeping_halls`
- `item_healing_herbs` → `area_healing_area`

### 8.2 Triggers
Triggers are `logic_trigger` nodes with `triggers` edges from items, areas, or ways.

Key trigger types to use:
- `on_examine` / `on_search` for discovery
- `on_take` / `on_drop` for inventory events
- `on_eat` / `on_drink` for consumables
- `on_use` / `on_activate` for magic items and tools
- `on_light` / `on_toggle_off` for light sources
- `on_enter` for area events
- `on_tick` for periodic effects
- `on_open` / `on_close` for containers and ways
- `on_speech` for social reactions

### 8.3 Example Items to Build First
- Basic weapons: rusty hatchet, spear, club, bow
- Tools: hammer, saw, pry bar, torch
- Food: dried meat, bread, mushrooms, berries
- Drink: water skin, mushroom tea
- Light: torch, lantern
- Containers: backpack, chest, basket
- Keys and locked containers
- Scrap items for the workshop
- Shamanic items: herbs, bones, charms
- Traps

## 9. Magic System (Viwo-shaped)

In Viwo, magic is modeled as:
- Items with `magic` tag
- `on_activate` / `on_use` triggers that consume `Mana` or limited `uses`
- `adjust_vital` effects for costs
- `damage`, `apply_condition`, `heal`, `teleport`, etc. for effects
- Spells can be learned from scrolls via `on_read` → `spawn_item`

Goblin magic in this scenario:
- **Create Flame**: spell-item with `on_activate` damage/fire + light
- **Spark**: cheaper ignition variant
- **Snuff**: extinguishes light sources in area
- **Find Water**: reveals hidden water source or adjusts environment
- **Warn**: applies `frightened` condition or adds sensory message
- **Blight**: withers plants/food in area
- **Grow**: accelerates plant growth
- **Fool**: minor illusion — message-based sensory effect
- **Stick**: applies `stuck` condition to target
- **Break**: weakens item/way, sets state to `jammed` or broken

## 10. World Lore

`world_lore` is injected into every agent prompt. Key lore blocks:

### 10.1 Tribe Lore
- Kraktooth tribe history and reputation
- Current leadership structure
- Recent events affecting the camp

### 10.2 Region Lore
- Geography: forest, river, marsh, hills, ruins
- Human village: Eldenford attitudes and defenses
- Dwarven ruins: what remains and what dangers
- Trade routes and patrol patterns

### 10.3 Magic Lore
- Goblin shamanic practices
- Known magical sites or residual magic
- Human attitudes toward goblin magic

### 10.4 Threat Lore
- Known predators and their patterns
- Human patrol schedules and routes
- Rival tribes or dangers

## 11. Starting State

### 11.1 Time
- Start at dawn: `clock_start_hour: 6`, `clock_start_minute: 0`
- `game_time`: "06:00:00"
- `turn_number`: 0
- `time_ticks`: 0

### 11.2 Player Spawn
- `current_area`: `area_camp_entrance_trail`
- Basic survival gear: torch, knife, water skin, bread
- knows general region, not specific locations

### 11.3 Camp State
- Normal operations
- Food reserves: moderate
- Tools: functional but worn
- No immediate threats
- Weather: clear

### 11.4 Relationships
- Tribal relationships at baseline
- Outsiders have default attitudes
- Player unknown to most

## 12. What Makes This Sandbox Work in Viwo

- No main quest, no victory condition
- LLM agents have personal drives, not plot hooks
- Simple NPCs provide ambient life via backend behaviors
- The camp is a graph system with interdependent needs
- Triggers create emergent events from item use, area entry, and time
- World lore keeps all agents grounded in shared context
- Outside pressure changes priorities
- Small events compound via triggers and relationships
- The player can intervene, observe, or ignore
- Characters respond to behavior through relationship shifts and memories

## 13. Open Questions for Viwo Implementation

1. **Agent vs Simple NPC split**: Which goblins should be full LLM agents, and which are `simple_npc: true`? I suggest the 7 core goblins as LLM agents, others/animals/villagers as simple NPCs. Agree?
2. **Player spawn area**: Is `area_camp_entrance_trail` the right start, or somewhere else in the forest?
3. **Starting clock**: Dawn at 06:00, or something else?
4. **Starting inventory**: Basic explorer kit, or something more specific?
5. **Initial relationships**: Any pre-existing relationships among NPCs at spawn, or all neutral/unknown?
6. **Trigger density**: Should the opening area have many discovery triggers, or sparse and revealed through play?
7. **Simple NPC behavior**: Should villagers have `wander`/`guard`/`patrol` patterns, or mostly `stationary`?
8. **Animal behaviors**: Which animals should `hunt`, `flee`, or `wander`?
9. **Magic availability**: Are there spell items in the world at start, or only improvised magic via shamanic items?
10. **Content boundaries**: Any content the scenario should avoid or tone down?

## 14. Implementation Order

1. Finalize agent/simple-NPC split and starting clock
2. Build graph skeleton: all area nodes and way edges
3. Define starting areas and player spawn
4. Create player character JSON block
5. Create all NPC/animal character blocks
6. Write world_lore blocks
7. Place core items in starting areas
8. Write discovery triggers for starting area
9. Add 5–10 opening triggers for emergent first-turn events
10. Validate against `ScenarioCreationGuide.md` shape
11. Load in engine and verify area connections, turn queue, and basic movement
