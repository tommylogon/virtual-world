# Characters Overview

VirtualWorld has three character types, all stored as `Player` objects (`player.py:273`). They are differentiated by the `simple_npc` flag and how they are driven (human, LLM agent, or scripted behavior).

## Three Character Types

| Type | `simple_npc` | Driven By | Use Case |
|------|-------------|-----------|----------|
| **Active Player (Human)** | `False` | Human user via UI commands | The player controlling the game |
| **LLM-Driven Agent** | `False` | Agent engine (LLM reasoning) | AI characters with full personality simulation |
| **Simple NPC** | `True` | Scripted behaviors in `npc_behaviors.py` | Background characters, wandering animals, guards |

All three types share the same `Player` class. The engine does not distinguish between "PC" and "NPC" at the data level — only by which player is currently "active" (see `player_manager.py:19`).

## Player Class (`player.py:273`)

```python
class Player:
    def __init__(self, name="Traveler"):
```

### Core Identity Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `name` | `str` | `"Traveler"` | Character name |
| `personality` | `str` | `""` | Free-form personality description/prompt text |
| `base_description` | `str` | `""` | Naked/baseline appearance — what they look like with nothing on |
| `description` | `str` | `""` | Current outward-facing description (auto-generated from base + equipment) |

Personality is the primary prompt text used by the LLM agent engine. In character library files, this is written in second person ("You are...").

See `routes/players.py:139` for the update API fields.

### D&D Core Stats (`player.py:298-301`)

Six standard D&D attributes, range 1-20 (default 10):

```python
self.stats = {
    "STR": 10, "DEX": 10, "CON": 10,
    "INT": 10, "WIS": 10, "CHA": 10
}
```

Stats are used in:
- **Combat**: STR for attack rolls, target's DEX/equipment defense for the defense roll (`combat.py:117`, `combat.py:57-60`)
- **Skill checks**: not directly used by the skill system (only skill values are checked)
- **Damage calculation**: STR bonus from `max(0, (attacker.stats.get("STR", 10) - 10) // 2)` (`combat.py:198`)
- **Item action costs**: traits can modify action costs

### Vitals & Needs (`player.py:304-311`)

All vitals range 0-100 (except `Temperature` which is 25-45):

```python
self.vitals = {
    "HP": 100, "Max_HP": 100,
    "Hunger": 100, "Thirst": 100,
    "Hygiene": 100, "Energy": 100,
    "Social": 100,
    "Bladder": 0, "Sanity": 100,
    "Entertainment": 100, "Temperature": 37.0
}
```

See **Vitals System.md** for full details.

### Decay Rates (`player.py:314-317`)

Per-character override for baseline decay rates:

```python
self.decay_rates = {
    "Hunger": 1, "Thirst": 1, "Energy": 1, "Social": 1,
    "Hygiene": 1, "Bladder": 1, "Sanity": 1, "Entertainment": 1
}
```

If a character does not specify decay rates, the engine's baseline decay values are used (`tick_manager.py:110-114`).

### Skills (`player.py:320-324`)

```python
self.skills = {
    "Athletics": 1, "Acrobatics": 1,
    "Stealth": 1, "Perception": 1,
    "Survival": 1, "Persuasion": 1
}
```

Skills are not fixed — characters can have any skill name. Values typically range -20 to +20. Character library examples show custom skills like `"Performance": 5`, `"Investigation": 3`.

See **Skills System.md** for full details.

### Traits & Tags (`player.py:325-336`)

```python
self.traits = {}      # trait_id -> param_value (True for booleans)
self.tags = []        # identity markers: ["vampire", "faction:guard"]
self.interest_tags = []  # what the character pays attention to: ["magic", "documents"]
```

Traits are defined in the trait library (`engine/traits.py`) and assigned via the Inspector UI. Tags are free-form identity markers checked by items, triggers, and conditions.

**Interest tags** drive the agent prompt's "Items that catch your attention" list: items whose tags (or name keywords) match an `interest_tags` entry surface first, ordered by weight (bigger = easier to see), capped at 15. Examined/taken items drop off the list automatically — their facts live in the agent's investigation notes. Set in the Inspector → agent Bio tab (✨ Interest Tags).

See **Traits System.md** for full details.

### Conditions (`player.py:337-342`)

```python
self.conditions = {"awake": [{"duration": None, "source": None, "level": 0}]}
```

Conditions are a **multi-instance system**: `player.conditions` maps `condition_id → [instance, ...]`, so a character can hold several concurrent instances of the same condition (5 vials of poison = 5 stacked `poisoned` instances; drains sum, gates/mods are presence-based). Each instance is `{duration, source, level}` plus optional overrides (`periodic`, `ends_on`, `symptoms`, `known`, and gate overrides like `blocks_speech` / `drops_held_items`).

The single source of truth is `CONDITION_DEFINITIONS` in `player.py:30-215`. The catalog's `stack` field controls re-application:

- `"accumulate"` (`poisoned`/`sick`): re-apply appends an instance — drains sum
- `"refresh"` (`stunned`/`exhausted`): re-apply extends the duration / bumps `level`
- `"noop"` (`grappled`/`restrained`/`blind`/...): re-apply does nothing

Use `has_condition()` / `add_condition()` / `remove_condition()` / `end_instances(action)` — never raw list math. `add_condition()` resolves catalog exclusions and can attach `extra_conditions` bundles, `source_type` (`"way"`/`"area"`/`"item"`/`"character"`, used by `frightened` gates), and arbitrary gate `overrides`. `end_instances()` removes every instance whose effective `ends_on` includes the action (per-instance override wins over the catalog default).

Standard conditions in the catalog:

| Condition | Blocks Action? | Periodic Effect | Notes |
|-----------|---------------|-----------------|-------|
| `awake` | No | — | Default state |
| `dead` | Yes | — | Auto-fails STR/DEX/CON saves |
| `unconscious` | Yes | — | Defense -5; `ends_on` wake/damage/timer; `sleep` applies this with `source: "sleep"`, `blocks_speech: False` |
| `paralysed` | Yes | — | Defense -5, duration 3 |
| `stunned` | Yes | — | Defense -5, `refresh` stack, duration 2 |
| `grappled` | Yes | — | Speed 0, attack -2; held by someone — WHO is tracked via a `grappled` graph edge (grappler → target), the `grappled_by` API field is derived from it |
| `restrained` | Yes | — | Defense -2, attack -2 |
| `prone` | No | — | Speed ×0.5, movement `crawl`, attack/defense -2 |
| `busy` | No | — | Occupied (rest/meditate/wait/sit/lie/bathe), `ends_on` stop |
| `exhausted` | No | Energy -3/tick | Levels 1-6, `refresh` stack, speed ×0.5→0 |
| `sick` | No | Hunger -2, Thirst -2/tick | Hidden (`known: False`), `accumulate`, duration 8 |
| `poisoned` | No | HP -5/tick | Hidden, `accumulate`, duration 10 |
| `blind` | No | — | Auto-fails sight checks, attack/defense -2 |
| `deaf` | No | — | Auto-fails hearing checks |
| `mute` | No | — | `blocks_speech` |
| `frightened` | No | — | Blocks re-entering/touching/attacking its `source` |
| `charmed` | No | — | Hidden (`known: False`) |

**`sleeping` is gone** — `sleep` is an activity (task-131) that applies an `unconscious` instance. See **Activities & States.md** and **Conditions System.md**.

Condition hierarchy (most significant first, `player.py:218-226`): `dead > unconscious > paralysed > stunned > grappled > restrained > prone > busy > exhausted > sick > poisoned > blind > deaf > frightened > charmed > awake`.

The `state` property (`player.py:399-405`) is a **derived read-only view** — it returns the most significant condition for backward compatibility (UI shows it as a label, not a selector). Its setter **adds** the condition without wiping others (conflicts resolved by catalog exclusions); the inspector edits conditions directly via the add/remove controls. `state_timer` (`player.py:540-546`) is a compat property returning the longest finite duration across the state condition's instances.

### Inventory

Items are graph nodes connected to the character via a `carrying` edge (task-105 edge refactor; legacy `carried_by`/`location` edges are migrated on load). Containers/nesting use the spatial edge types (`in`, `on`, `under`, `behind`, `beside`, `at`). See **Graph System.md** for the full edge list.

### Equipment / Paperdoll (`player.py:383-390`)

```python
self.equipped = {
    "head": [], "neck": [], "torso": [], "arms": [],
    "hands": [], "legs": [], "feet": [], "back": [],
    "waist": [], "accessory": [],
    "hand_left": [], "hand_right": []
}
```

Each slot is a list (stack order = innermost to outermost). Managed by `engine/equipment.py`. The equipment system integrates with the LLM for auto-generating appearance descriptions when items are equipped/unequipped.

### Emotion System (`player.py:369-375`)

```python
self.emotion = "neutral"        # neutral, happy, sad, angry, afraid, surprised, disgusted
self.emotion_intensity = 0.0    # 0.0 to 1.0
```

Emotion is set via `set_emotion()` (`player.py:596-602`) or auto-updated from action outcome text via `update_emotion_from_outcome()` (`player.py:621-654`). The `get_emotion_nl()` method (`player.py:604-619`) returns a natural language description.

### Relationships (`player.py:377-380`)

```python
self.relationships = {
    "other_name": {
        "closeness": 0,         # -100 to +100
        "last_interaction_tick": int,
        "interaction_count": int
    }
}
```

- `-100`: sworn enemy, `-50`: rival, `0`: neutral, `50`: friend, `100`: inseparable (`player.py:773-797`)
- Updated via `update_relationship()` (`player.py:754-771`); first meetings are tracked by `register_first_meeting()` (`player.py:656-677`), which stamps `first_sighting: True` so strangers stay anonymized until the next shared-area encounter

### Memories (`player.py:392-394`)

```python
self.memories = []  # {id, text, tick, timestamp, importance (1-10), type}
```

Managed by `add_memory()` (`player.py:799`, max 200 memories) and retrieved by `get_relevant_memories()` (`player.py:813`). Memory is the **unified store** (task-178) — the agent engine, inspector editor, and MCP tools all operate on this list. The old `agent_memory.py` key-value store and `world_knowledge` blob were deleted. See [[AI & Narration/Memory System]].

### NPC Fields (`player.py:352-359`)

```python
self.simple_npc = False
self.npc_behavior = "wander"   # wander, flee, stationary
self.npc_action_interval = 3   # act every N ticks
self.npc_state = "idle"        # behavior state machine
self.state_enter_tick = 0      # tick when npc_state was entered
self.behaviors = []            # list of behavior definitions
```

See **NPC Behavior System.md** for full details.

### Other Properties

- `activity`: current multi-turn activity (task-131) — `None` or `{type, started_at_tick, target_item, duration_ticks, elapsed_ticks, visible}`; types: sleeping, resting, waiting, meditating, bathing, sitting, lying down. See **Activities & States.md**
- `unknown_name`: explicit stranger label used until another character meets this one (falls back to description/tag-derived labels, `player.py:683-736`)
- `discovered_exits`: set of `(area_name, direction)` tuples tracked during exploration
- `visited_areas`: set of area names the character has entered (used for Entertainment novelty bonus)
- `discovered_items`: set of item IDs the character has encountered (used for Entertainment novelty bonus)
- `recent_hearing`: list of `{speaker, text, tick, timestamp}` for recent speech heard
- `interest_tags`: what the character pays attention to (see Traits & Tags above)
- Removed: `item_statuses`, `world_knowledge`, `knowledge` (legacy fields deleted with the memory rework, task-178)

### Serialization

`to_dict()` (`player.py:846-889`) produces a complete serializable dict — including `conditions` (list of condition ids), `condition_instances` (full `{cid: [instance, ...]}` data), `activity`, `interest_tags`, and `unknown_name`. Used by API responses.

## Character Registry and Library

### Registry Files

Characters are stored in two locations:

1. **Runtime registry**: `data/characters.json` — legacy flat JSON file
2. **Library files**: `data/library/characters/*.json` — one file per character (current system)

The `load_registry()` helper (`routes/helpers.py:124-147`) reads all `.json` files from `data/library/characters/` and returns them as a dict keyed by filename (without extension). The `save_registry()` helper (`routes/helpers.py:148-174`) writes one file per key.

### Library File Format

Each character library file is self-contained JSON. Example from `Miki.json`:

```json
{
  "name": "Miki",
  "personality": "You are Miki, a chaotic ASMR artist...",
  "stats": { "CHA": 12, "CON": 10, "DEX": 12, "INT": 14, "STR": 8, "WIS": 8 },
  "vitals": { "Energy": 100, "HP": 100, "Hunger": 80, ... },
  "skills": { "Investigation": 2, "Perception": 3, "Performance": 5, "Stealth": 4 },
  "traits": {},
  "state": "awake",
  "current_area": "Foyer",
  "inventory": ["phone", "granola_bar", "water_bottle", ...]
}
```

Extended format (from `jake.json`) also includes:
- `description`: rendered appearance text
- `emotion`: `{current, intensity}` object
- `relationships`: dict of relationship objects
- `simple_npc`, `npc_behavior`, `npc_state`, `behaviors`: NPC configuration
- `decay_rates`: per-character decay overrides

Legacy keys (`item_statuses`, `world_knowledge`, `memory_store`, `agent_history`) may still appear in older library files but are no longer read or written by the engine (memory rework, task-178).

### Inventory Items in Library Files

Inventory can be specified as a list of strings (item names, matched by `library_id` in the items registry) or a list of dicts (inline item definitions). The import process creates graph nodes for each item (`routes/library_routes.py:134-167`).

### Character Import

Characters can be imported into the world via:

1. **API**: `POST /api/library/import/character/<id>` (`routes/library_routes.py`)
2. **API**: `POST /api/library/import/character/<char_id>` with `{active, room}` (`routes/library_routes.py:92`)
3. **API**: `POST /api/players/import` with full player data (`routes/players.py:241`)
4. **UI**: Import button in the Character Library browser

The import process:
1. Creates a `Player` object with stats, vitals, skills, traits, tags
2. Sets personality, description, emotion, memories
3. Places the character in the specified room (or falls back to first available room)
4. Creates graph nodes for all inventory items
5. Adds the player to the engine via `add_player()`

### Character Creation via API

`POST /api/players` creates a new player from scratch (`routes/players.py:21-37`):

```python
player = Player(name)
player.stats = data.get('stats', player.stats)
player.vitals = data.get('vitals', player.vitals)
player.skills = data.get('skills', player.skills)
player.traits = data.get('traits', player.traits)
player.tags = data.get('tags', player.tags)
player.interest_tags = data.get('interest_tags', player.interest_tags)
app.world.add_player(player)
```

### Character Updates via API

`POST /api/players/<name>` (`routes/players.py:139`) supports updating all player fields:
- `state`, `current_area`, `new_name` (with graph node migration)
- `emotion`, `emotion_intensity`
- `personality`, `description`, `base_description`
- `stats`, `skills`
- `traits`, `tags`, `equipped`, `interest_tags`
- `behaviors`, `npc_state`, `npc_behavior`, `npc_action_interval`, `simple_npc`
- `conditions` (via `load_conditions()`), `relationships`

### Player Manager (`engine/player_manager.py`)

The `PlayerManager` class:
- **Registration**: `add_player()` creates a graph node and registers the player (`player_manager.py:30-49`)
- **Active player**: `set_active_player()` switches focus (`player_manager.py:51-60`)
- **Area queries**: `get_players_in_area()` lists players in a room, excluding ghosts when appropriate (`player_manager.py:168-191`)
- **Death tracking**: `get_all_dead_players()`, `get_all_alive_players()` (`player_manager.py:193-205`)
- **Trait checks**: `is_slasher()` delegates to `TraitSystem.has_effect()` (`player_manager.py:209-215`)
- **Item lookup**: `find_item_node()` searches inventory, room, and containers (`player_manager.py:110-163`)

### Graph Integration

Each player has a graph node with ID `player_<name>` (type `character`). An `in` edge connects the player to their current room. Items are connected via `carrying` edges (inventory) or `equipped` edges (worn/held, slot in edge props).

## Death System

A character dies when HP reaches 0. This can happen from:
- Combat damage (`combat.py:201`, death at `combat.py:218-224`)
- Starvation/dehydration/madness (vitals at 0 cause HP loss per tick, `tick_manager.py:182-190`)
- Hypothermia/heat stroke (core Temperature < 30 or > 42, `tick_manager.py:215-218`)
- Exhaustion (Energy at 0 three times, `tick_manager.py:165-180`)
- Toxic air (HP damage from `toxic` air, `tick_manager.py:229-240`)

On death:
1. State is set to `"dead"`
2. A body item is spawned via `spawn_body_item()`
3. Ghost mode can be enabled to allow dead characters to continue acting
4. Immortal trait prevents HP from dropping below 1

## Character Library Examples

The library contains 8 characters as of writing:

| File | Name | Type | Setting |
|------|------|------|---------|
| `Miki.json` | Miki | LLM agent | Paranormal mansion (modern) |
| `jake.json` | Jake Halloway | LLM agent | Haunted mansion (Chaos teen) |
| `kyrie.json` | Kyrie Johansen | LLM agent | Haunted mansion (Wrestler/mechanic) |
| `sammy.json` | Sammy Lopez | LLM agent | Haunted mansion (Anxious observer) |
| `kayla.json` | Kayla Jenkins | LLM agent | Haunted mansion (Sharp-tongued) |
| `Kaelen Voss.json` | Kaelen Voss | LLM agent | Fantasy steampunk setting |
| `Viktor.json` | Viktor | LLM agent | Fighting pit (pit fighter) |
| `Gromm.json` | Gromm | LLM agent | Fighting pit (heavy bruiser) |

## Related tasks

- [[dev_tasks/review/characters/task-17-editable_characters|task-17: Editable characters]]
- [[dev_tasks/review/characters/task-27-character_import_from_file|task-27: Character import from file]]
- [[dev_tasks/review/characters/task-28-character_needs_system|task-28: Character needs system]]
- [[dev_tasks/review/items/task-32-enhanced_item_creation|task-32: Enhanced item creation]]
- [[task-89-character_inspector_polish|task-89: Character inspector polish]]
- [[dev_tasks/review/characters/task-38-npc_behavior_go_command|task-38: NPC behavior go command]]
