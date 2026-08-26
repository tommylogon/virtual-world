# Conditions System

## Overview

The Conditions System manages temporary status effects on characters. Conditions are identified by a canonical id (`"poisoned"`, `"blind"`, `"asleep"`, etc.) and modify a character's capabilities, apply periodic effects, and gate actions.

The system lives in `engine/conditions.py` (class `ConditionsSystem`). The **editable source of truth is the data-driven library**: `data/library/conditions/*.json`, loaded into the in-memory catalog at import with a **merge-over-fallback** strategy — the hardcoded `CONDITION_DEFINITIONS` dict in `player.py` is only the fallback, so a truncated or corrupt library file can never wipe definitions. Edit conditions via the Library Browser's conditions section; each library file is one condition entry.

Conditions are stored as **multi-instance lists**: `{condition_id: [instance, instance, ...]}`. Five vials of poison are five `poisoned` instances. Each instance carries optional overrides (`periodic`, `ends_on`, `symptoms`, `known`, gate fields). Drains sum across instances; gates and modifiers are presence-based.

```python
# Example: player with two poisoned instances and one prone instance
{
    "poisoned": [
        {"duration": 8, "source": "rat_bite", "level": 0, "periodic": {"HP": -5}},
        {"duration": 5, "source": "cloud", "level": 0}
    ],
    "prone": [
        {"duration": None, "source": "grapple", "level": 0,
         "movement_mode": "crawl", "speed_mult": 0.5}
    ]
}
```

## Condition Catalog

### Definition Schema

Each entry in the condition catalog (library file or `player.py` fallback, `CONDITION_DEFINITIONS`) shares this schema:

```python
{
    "id": "poisoned",
    "name": "Poisoned",
    "description": "Toxin in the blood. You're losing HP.",
    "blocks_actions": False,    # hard gate — cannot act
    "blocks_movement": False,   # hard gate — cannot move
    "blocks_speech": False,     # hard gate — cannot speak
    "auto_fail_checks": [],     # sense checks that auto-fail: ["sight", "hearing"]
    "auto_fail_saves": [],      # ability saves that auto-fail: ["STR", "DEX", "CON"]
    "attack_mod": 0,            # modifier on the bearer's own attack rolls
    "defense_mod": 0,           # modifier on the bearer's defense (target defense_mod is subtracted from incoming attacks; negative = easier to hit)
    "speed_mult": 1.0,          # movement speed multiplier
    "movement_mode": None,      # "crawl" forces crawl movement (prone)
    "drops_held_items": False,  # drop hand items into the area when applied
    "periodic": {},             # per-tick vital drains {stat: amount}; summed across instances
    "level_periodic": {},       # level-scaled drains {level: {stat: amount}} (exhausted)
    "level_speed_mult": {},     # level-scaled speed multiplier {level: float} (exhausted)
    "ends_on": [],              # actions/triggers that end this condition: ["stand"], ["wake", "damage"]
    "known": True,              # True = self-evident (agent sees description); False = hidden (agent sees symptoms only)
    "symptoms": {},             # {min_remaining: line} — agent perceives highest threshold reached; keyed by `level` for leveled diseases
    "stack": "noop",            # "accumulate" (poisoned/sick: append instance, drains sum)
                               # "refresh" (stunned/exhausted: extend duration / bump level)
                               # "noop" (grappled/restrained/blind/...: re-apply does nothing)
    "default_duration": None,   # ticks; None = permanent until countered/removed
    "excludes": [],             # condition ids removed when this one is applied (dead = set() removes everything)
}
```

### Current Catalog

| Condition | Key Effects | Default Duration | Stack |
|-----------|-------------|------------------|-------|
| `awake` | Default state; excludes `unconscious` | None | `noop` |
| `dead` | `blocks_actions`, `blocks_movement`, `drops_held_items`; auto-fail STR/DEX/CON; speed 0 | None | `noop` |
| `unconscious` | `blocks_actions`, `blocks_movement`, `blocks_speech`; `defense_mod` -5; `drops_held_items`; ends on `wake`/`damage`/`timer` | None | `refresh` |
| `paralysed` | `blocks_actions`, `blocks_movement`, `blocks_speech`; auto-fail STR/DEX; `defense_mod` -5 | 3 | `noop` |
| `stunned` | `blocks_actions`, `blocks_movement`; auto-fail STR/DEX; `defense_mod` -5 | 2 | `refresh` |
| `grappled` | `blocks_actions`, `blocks_movement`; `attack_mod` -2; `drops_held_items` on death | None | `noop` |
| `restrained` | `blocks_actions`, `blocks_movement`; `attack_mod`/`defense_mod` -2; auto-fail DEX | None | `noop` |
| `prone` | `movement_mode: "crawl"`; `speed_mult` 0.5; `attack_mod`/`defense_mod` -2 | None | `noop` |
| `busy` | Occupied with something; interruptible | None | `noop` |
| `exhausted` | `speed_mult` 0.5 at L1, decreasing; periodic Energy drain; levels 1-6 accumulate | 5 | `refresh` |
| `sick` | periodic Hunger/Thirst drain; `known: False`; symptoms at 5/3/1 ticks | 8 | `accumulate` |
| `poisoned` | periodic HP drain; `known: False`; symptoms at 6/3/1 ticks | 10 | `accumulate` |
| `blind` | auto-fail sight checks; `attack_mod`/`defense_mod` -2 | 5 | `noop` |
| `deaf` | auto-fail hearing checks | 5 | `noop` |
| `mute` | `blocks_speech` | None | `noop` |
| `frightened` | `attack_mod` -2; source-type gates (`way`/`area`/`item`/`character`) | None | `noop` |
| `charmed` | `known: False`; can't attack charmer | None | `noop` |

### Derived Constants

These are computed from the catalog in `player.py:228-250` — do not hardcode them elsewhere:

```python
CONDITION_HIERARCHY = ["dead", "unconscious", "paralysed", "stunned",
    "grappled", "restrained", "prone", "busy", "exhausted",
    "sick", "poisoned", "blind", "deaf", "frightened", "charmed", "awake"]

BLOCKING_CONDITIONS = frozenset(cid for cid, d in CONDITION_DEFINITIONS.items() if d["blocks_actions"])

PERIODIC_CONDITIONS = {cid: d["periodic"] for cid, d in CONDITION_DEFINITIONS.items() if d["periodic"]}

CONDITION_EXCLUSIONS = {cid: set(d["excludes"]) for cid, d in CONDITION_DEFINITIONS.items()}

CONDITION_DEFAULT_TIMERS = {cid: d["default_duration"] for cid, d in CONDITION_DEFINITIONS.items() if d["default_duration"] is not None}
```

## Player Methods

All condition management on the `Player` class (`player.py`).

### `state` property (`player.py:400-412`)

Read-only backward-compatible accessor: returns the most significant active condition from `CONDITION_HIERARCHY`, or `"awake"` if none.

The setter **adds** the condition without wiping others. Conflicts are resolved by the catalog `excludes` field. This means waking or ending an activity no longer clears unrelated conditions like `poisoned` or `blind`.

### `state_timer` property (`player.py:541-554`)

Backward-compat: returns the longest finite `duration` across instances of the current state condition, or `0` when permanent. The setter writes the countdown duration onto the primary (longest-finite) instance.

### `has_condition(condition)` (`player.py:414`)

Returns `True` if any instance of the condition is present.

### `add_condition(condition, duration, source, level, periodic, extra_conditions, ends_on, symptoms, known, source_type, overrides)` (`player.py:417-505`)

Apply a condition instance (or a bundle via `extra_conditions`).

**Stacking behavior** (catalog `stack` field):
- `"accumulate"` (poisoned, sick): appends a new instance — periodic drains sum across all instances.
- `"refresh"` (stunned, exhausted): extends the existing primary instance — a fresh stun extends the countdown; re-exhaustion bumps `level` toward 6.
- `"noop"` (grappled, restrained, blind, ...): does nothing when already present.

**Exclusions**: applying a condition automatically removes all instances of every condition listed in its `excludes` field.

**`overrides`**: a dict of arbitrary catalog gate fields to merge onto the instance (`blocks_speech`, `drops_held_items`, `blocks_actions`, ...).

**`source_type`**: classifies the source (`"way"`/`"area"`/`"item"`/`"character"`) so `frightened_block` knows what to gate.

### `remove_condition(condition)` (`player.py:507-510`)

Removes all instances of the condition. If no conditions remain, adds a default `awake` instance.

### `end_instances(action)` (`player.py:512-538`)

Removes every instance whose effective `ends_on` includes `action`. Resolved **per-instance**: an instance override wins, else the catalog default. So `fix` ends only the broken-leg `prone` instance while `stand` ends only a knock-down one. Returns the removed `(condition_id, source)` pairs.

## ConditionsSystem API (`engine/conditions.py`)

### `apply_condition(player_name, condition, duration, source, level, periodic, extra_conditions, ends_on, symptoms, known, source_type)` (line 239)

Applies a condition instance. If `duration` is `None`, uses `CONDITION_DEFAULT_TIMERS` if available. After application, checks `drops_held_items` — if any active instance (or catalog default) has it, calls `ItemActions.drop_held_items`.

### `remove_condition(player_name, condition)` (line 270)

Removes all instances of the condition.

### `has_condition(player_name, condition)` (line 277)

Returns `True` if any instance is present.

### `can_act(player_name)` (line 291)

Returns `True` if no blocking condition is active. Uses the derived `BLOCKING_CONDITIONS` set.

### `can_speak(player_name)` (line 298)

Returns `True` if no active condition has `blocks_speech: True` (presence-based, per-instance override wins).

### `get_condition_instances(player_name, condition)` (line 284)

Returns the raw list of instance dicts for one condition.

### `get_active_conditions(player_name)` (line 308)

Returns a list of dicts with keys `condition`, `ticks_remaining` (when finite), and `source` (when present), ordered by `CONDITION_HIERARCHY`.

### `end_conditions(player_name, action)` (line 329)

Calls `Player.end_instances(action)`. Returns removed `(condition_id, source)` pairs.

### `process_tick()` (line 341)

Called each turn from `TickManager.tick_turn()`.

1. **Periodic effects**: for each condition, sums periodic drains across every instance (instance override → level-scaled → catalog default). Applies to `player.vitals`. `unconscious` is engine-managed (skipped here; its countdown is owned by `tick_manager`).
2. **Duration decrement**: each timed instance counts down independently. Expired instances are removed. When the last instance of a condition is removed, the condition key is deleted from `player.conditions`. If `player.conditions` becomes empty, a default `awake` instance is added.

## Instance Field Resolution

The system uses per-instance overrides with catalog fallbacks. Helper functions in `engine/conditions.py`:

- `effective_periodic(condition, instance)` — instance override → catalog default
- `effective_periodic_for(condition, instance)` — instance override → `level_periodic` by level → catalog default
- `effective_ends_on(condition, instance)` — instance override → catalog default
- `effective_known(condition, instance)` — instance override → catalog default (defaults to `True`)
- `effective_symptoms(condition, instance)` — instance override → catalog default
- `effective_speed_mult(condition, instances)` — instance override → `level_speed_mult` by level → catalog default
- `symptom_for(condition, instance)` — picks the highest threshold reached based on remaining duration or level

## Combat Modifiers

`get_condition_mods(player)` (`engine/conditions.py:190-204`) aggregates combat modifiers from all active conditions:

```python
# combat applies: attack_roll + attack_mod - target.defense_mod
# so a target with defense_mod -5 (helpless) gives the attacker +5
attack_mod = sum of all conditions' attack_mod
defense_mod = sum of all conditions' defense_mod
```

Modifiers are presence-based per condition id: one mod per condition regardless of how many instances it has.

### Auto-Fail Checks and Saves

- `auto_fails_checks(player, sense)` (`engine/conditions.py:207-212`): `True` if any active condition auto-fails checks requiring `sense` (`"sight"`, `"hearing"`, ...).
- `auto_fails_saves(player, stat)` (`engine/conditions.py:215-220`): `True` if any active condition auto-fails saves on ability `stat` (`"STR"`, `"DEX"`, `"CON"`, ...).

## Movement Integration

Conditions hook into movement via `effective_speed(player)` (`engine/conditions.py:223-229`) and `movement_mode`:

- `speed_mult`: product across all active conditions (e.g. exhausted L3 → 0.25, prone → 0.5)
- `movement_mode: "crawl"`: forces `go` → crawl; climb/jump are refused in `move_to_area`
- `drops_held_items`: drops hand items into the area (hooked at energy-collapse, sleep start, combat death)

`frightened_block(player, source_type, source_id, source_name)` (`engine/conditions.py:123-147`) gates movement/actions based on the frightened instance's `source` and `source_type`:

| `source_type` | Gate |
|---------------|------|
| `way` | Won't use that passage again |
| `area` | Won't re-enter the area |
| `item` | Won't touch the item |
| `character` | Won't approach or attack the character |

`save` trigger effect (`{"type": "save", "params": {"stat": "WIS", "dc": 12, ...}}`) can apply `frightened` with the source node's name and `source_type`.

## Agent Perception

Agents never see raw condition ids for hidden conditions. The prompt renders `symptoms` (for `known: False`) or a physical description (for `known: True`).

`perceived_conditions(player)` (`engine/conditions.py:150-179`) builds the perception lines:

- Known conditions: `description` (or instance override), personalized with source — e.g. `"Poisoned (from rat_bite)"`
- Hidden conditions: the `symptom_for` line for the current stage, or nothing yet (e.g. freshly-applied poison with no thresholds reached)
- `frightened` with a source: `"Terrified of {source}."`
- Lines are deduped across stacked instances

Raw condition ids are never exposed to the agent. Stacked instances each contribute a line; identical lines are deduped.

## Integration with Tick Manager

Conditions are processed in `TickManager.tick_turn()` (`tick_manager.py`):

```python
self.gs.conditions.process_tick()
```

Called before vital decay and environmental effects, so condition damage happens first each turn.

### Unconscious State Transitions

Owned by `tick_manager`, not `ConditionsSystem.process_tick`:
- If `state == "unconscious"` and `state_timer > 0`, the player recovers Energy and counts down
- When `state_timer == 0`, state transitions back to `"awake"`
- `unconscious` is in `engine_managed = {"unconscious"}` in `process_tick` — it is skipped by the conditions tick

## Integration with Effects (Triggers)

The Effects system (`engine/effects.py`) provides two effect handlers:

- `handle_apply_condition` (line 638): params `{condition, target, duration, source, level, ...}`
- `handle_remove_condition` (line 658): params `{condition, target}`

Registered as `EFFECT_TYPES` in `trigger_system.py`:
```python
"apply_condition",
"remove_condition",
```

Triggers can check for conditions via `"has_condition"` condition type (`trigger_system.py`).

### End Conditions via Triggers

The `end_condition` effect type calls `ConditionsSystem.end_conditions(player_name, action)`, which resolves per-instance `ends_on`. A trigger author can specify an action like `"fix"` or `"stand"` to end specific instances.

## Integration with Traits

Traits can grant conditions via `grants_conditions` in the trait definition. The trait system applies them at creation and they behave like any other condition instance (stacking, ticking, ending).

## UI Integration

### Condition Badges in Inspector

The Inspector UI (`static/js/inspector/`) displays condition badges on player entities. Conditions are shown as colored badges with their name and ticks remaining when finite. Stacked instances of the same condition each render a separate badge.

### Condition Library UI

The Library Browser has a conditions section (`data/library/conditions/`). Conditions can be created and managed through the UI, saved as JSON files in the library format. Each library entry corresponds to one `CONDITION_DEFINITIONS` entry.

## Busy State

`busy` is a non-blocking condition (`blocks_actions: False`) used for persistent multi-turn activities (`rest`, `sleep`, `wait`, `bathe`, `meditate`, `sit`, `lie down`). It is interruptible and ends on `"stop"`.

## Sleep → Unconscious

`sleeping` is no longer a condition. The `sleep` activity applies an `unconscious` instance with `source: "sleep"` and `blocks_speech: False`. The unconscious countdown is engine-managed by `tick_manager` (Energy recovery + wake).

## Diseases & Contagion

Diseases are **not a special system** — they're composed from triggers, the `give_item`/`apply_condition` effects, and the condition catalog. This is the authoring pattern:

### 1. Infection (giving the carrier)

Use the `give_item` effect (`handle_give_item`, `engine/effects.py`) to place a hidden disease carrier directly into a character's inventory — typically gated behind a failed check:

```json
{"type": "save", "params": {
  "stat": "Medicine", "dc": 12,
  "on_success": [{"type": "message", "params": {"message": "You recognize the signs — you keep your distance."}}],
  "on_fail": [
    {"type": "give_item", "params": {
      "item_id": "plague_miasma", "target": "self",
      "message": "An invisible miasma clings to you."}}
  ]
}}
```

- `item_id` — library item to hydrate (or existing node id)
- `target` — `"self"` (active player), `"target"` (the `on_use_on` target), or a character name
- `message` — supports `{target_name}` template rendering

A diseased corpse (`on_examine` → Medicine save → `give_item`), a poison poured into wine (`use poison on wine` via `on_use_on`), or a cursed amulet (`on_equip`) are all the same pattern.

### 2. The carrier item

`data/library/items/plague_miasma.json` is the reference contagion item:

- `hidden: true` — invisible in inventory, weight 0, uses -1 (never consumed)
- `on_tick` trigger → `apply_condition sick` with `target_by: "all_in_area"` — spreads to everyone in the room
- `random_chance` condition gates the spread (30% per tick)
- `on_examine` trigger gives a hint so the carrier can discover they're sick

### 3. Spread (carried items tick)

`TickManager.tick_turn()` fires `on_tick` for **every carried/equipped item with the trigger** (`tick_manager.py`, per-player pass) — not just `"lit"` ones. A hidden carrier in someone's pocket ticks each turn. (Lit items additionally burn `uses` and fire `on_depleted` at 0.)

The spread effect uses unified targeting, so one effect hits every character in the area:

```json
{"type": "apply_condition", "params": {
  "condition": "sick", "target_by": "all_in_area",
  "duration": 8, "source": "plague miasma"}}
```

### 4. Cures

The condition library has a matching **cure item per condition** (e.g. `bitterweed_tonic.json` → `remove_condition sick`, `neutralizing_draught.json` → `remove_condition poisoned`). Cure items targeting incapacitating conditions (`dead`, `unconscious`) are **ally-administered**: `target: "target"` + an `on_use_on` trigger, so a companion does `use heartseed elixir on <name>`.

### Composition notes

- **Werewolf curse** = `apply_trait hostile` + `set_description` (character node) + `adjust_vital` + a trait with a `behavior_prompt` for the personality change
- **Radioactivity** = poisoned + sick + periodic vital drains
- **Hallucinations** = already driven by low Sanity in `tick_manager`

## Related Files

- `player.py:30-215` — `CONDITION_DEFINITIONS` catalog
- `player.py:228-250` — derived constants
- `player.py:400-554` — `Player.state`, `state_timer`, condition methods
- `engine/conditions.py` — `ConditionsSystem`, helpers, perception, combat mods
- `engine/effects.py:638,658` — trigger effect handlers (`handle_give_item` near `handle_spawn_item`)
- `tick_manager.py` — tick integration, unconscious state machine, carried-item `on_tick`
- `data/library/items/plague_miasma.json` — reference contagion carrier item

## Related tasks

- [[dev_tasks/review/characters/task-24-traits_conditions_emotions_editor|task-24: Traits conditions emotions editor]]
- [[dev_tasks/review/triggers/task-50-trigger_condition_has_item_dropdown|task-50: Trigger condition has_item dropdown]]
- [[dev_tasks/review/triggers/task-51-trigger_multi_effect_conditions|task-51: Trigger multi effect conditions]]
- [[dev_tasks/done/characters/task-163-condition-system-redesign|task-163: Condition system redesign]]
