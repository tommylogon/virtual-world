---
type: task
status: done
area: triggers
priority: high
---

# task-396: ai-trigger-prompt-examples

## Outcome (verified 2026-09-22) — complete

The prompt was already the deliverable; what was missing was anything verifying it.

**Landed this pass:**
- **`tools/unit/test_trigger_suggest_ai.js` — 16 tests** over the prompt's contract: the
  five hard rules must be stated, and every WORKED EXAMPLE embedded in the prompt is
  parsed and validated against those rules (non-empty `effects`; no `on_light` +
  `on_toggle_on` pair; no `on_use` + consume pair; top-level `success_message` honest;
  every effect type documented and carrying a `params` object; nested `save` branches
  non-empty). `buildPrompt`'s plan / no-plan paths and node-context rendering are
  covered too. This is the missing piece: a rule-violating example is the real
  regression risk, because the model pattern-matches the examples, not the prose rules.
- Four item/area-relevant trigger types the prompt omitted were added: `on_look`,
  `on_search`, `on_spoil`, `on_use_progressive`.
- **`tools/unit/run.js` → `tools/unit/run.cjs`.** The repo's `package.json` sets
  `"type": "module"`, which broke the CommonJS runner outright (`ReferenceError: require
  is not defined`). Node's own guidance is the `.cjs` extension. References in
  `task-322` updated.
- **Decision on the catalog question: document the deliberate subset** (Part 5 rewritten
  below) rather than embedding every type/condition/effect. Rationale: what fixed the
  empty-`effects` failure was the hard rules plus worked examples, not catalog
  completeness, and this prompt targets a small local model where a larger prompt
  degrades instruction-following. Expanding the catalogs stays available as a follow-up
  if generations under-perform.

**Verified:**
- `node tools/unit/run.cjs` → **67 passed, 2 failed**; all 16 new tests pass. The 2
  failures are pre-existing and unrelated: `test_describe_vital.js` expects
  "Your stomach feels empty." / "Your throat feels dry." while `describeVital` now emits
  the urgency form ("FIND SOMETHING TO EAT NOW.") — the same class of stale expectation
  task-322 R6 already recorded once.

**Deliberately out of scope:**
- The LLM's *output* still cannot be unit-tested without a live model. The output
  assertions in the old Verification section remain a manual check; their prompt-side
  equivalents are now automated.
- No server route and no shared JSON catalog of examples — the examples stay in the
  module so they version with the prompt they anchor.

### Prior state (2026-09-21) — partial, not closable

**Note on the file's nature:** Parts 1-4 (lines 56-367) are a reference catalog of
trigger types, conditions and effects with worked JSON examples. It is a
**reference document first and a spec second** — the only verification text is the
prose checklist at 383-388, and there are no acceptance criteria or test commands.

**Landed:**
- The generator's system prompt is no longer a bare schema. It is now a
  descriptive catalog with trigger types, conditions, effects, hard rules, a
  category instinct and **three worked examples** (food, tainted drink, haunted
  take) — `static/js/shared/trigger-suggest-ai.js:32-146`; examples at `:136-144`
  match Parts 4.4/4.5/4.8.
- It is genuinely wired into trigger generation: `AIGenerator.generate(buildPrompt(...), buildSystem(kind), ...)`
  at `:188`, consumed by `static/js/item-library/ai-generation.js:344` and
  `static/js/inspector/trigger-helpers.js:430`.
- The ground rule about `on_light` is real, not just documented: it fires as a
  companion to `on_toggle_on` in `engine/toggleable_items.py:72-77`, registered at
  `engine/triggers/constants.py:20`.

**Residual items — resolved 2026-09-22 (see Outcome above):**
- *The condensed subset:* Part 5 now documents it as deliberate, and the four
  item/area-relevant types it lacked (`on_look`, `on_search`, `on_spoil`,
  `on_use_progressive`) were added to the prompt.
- *No tests:* `tools/unit/test_trigger_suggest_ai.js` now covers the prompt contract
  (16 tests).
- *No server route / shared JSON catalog:* accepted — the examples live in the module
  so they version with the prompt they anchor.

**Premise corrected:** the section above is now marked historical. It described the
pre-fix prompt; the current prompt mandates non-empty effects, puts prose in
`params.message`, and ships three worked examples.

**Filed**: 2026-09-07
**Status**: In Progress — this is the *reference catalog* the trigger AI prompt
must embed: every trigger type, condition, and effect with a plain-language
description AND a concrete example. Plus corrected archetypes (light/heat/sound/
container) verified against the engine.

## Why the prompt previously failed (historical — fixed 2026-09-07)

> Kept for context only. This describes the prompt *before* the fix. The current prompt
> mandates non-empty `effects`, sends prose into `effects[].params.message`, and ships
> three worked examples — see the Outcome section above.

The generator's system prompt dumps a **schema** (key names + param labels)
with a single empty example (`effects: []`, `conditions: []`). A local 9B model
pattern-matches to the only example it sees → dumps prose into inert top-level
`success_message` and leaves `effects` empty. The model also inflated trigger
counts (`on_toggle_*`) because the plan told it to. The fix:
- full descriptive catalog (this file),
- hard rules (effects mandatory; prose lives in `effects[].params.message`),
- corrected archetypes.

## Ground rules (verified in engine code)

- **Engine executes `effects[]`.** `success_message`/`fail_message` at trigger
  top level are inert. Prose → `effects[].params.message` /
  `params.success_message`. `effects: []` = does nothing.
- **`conditions[]` gate the whole trigger**; `[]`/`{}` = always fire.
- **`target: "self"`** = active player; `"other"` + `character_name` = another
  character in the area; `"target"` = the used-on node (for `on_use_on`).
- **Toggleables**: `use` on a `toggleable`-tagged item routes to
  `toggle_item_status` (flips `lit`/`unlit`, fires `on_toggle_on`/`on_toggle_off`,
  handles `uses` drain + `on_depleted`). Authors do **NOT** add set_state lit.
- **`on_light` IS fired** (task-396 fix): it was registered but had no caller.
  It now fires as a **companion to `on_toggle_on`** when a toggleable turns on —
  the semantic "this got lit" hook. `on_toggle_off` remains the off-side.
  Suggest `on_light` for lighting flavor; never both `on_light` AND `on_toggle_on`
  (redundant — both fire together).
- **Heat sources are properties, not triggers** (`environment_propagation.py:174-180`):
  a `lit` `heat_source` pulls the room toward `target_temperature` at
  `heating_rate` each tick. No set/adjust_environment trigger needed.
- **Finite uses**: engine auto-decrements + removes at 0 (fires `on_depleted`).
  Add a `uses_above: 0` condition + empty `fail_message`; do NOT hand-add
  `adjust_uses`/`destroy_self`.
- **Consume**: ONE of `on_eat`/`on_drink`/`on_use` (they co-fire) — never both.
- **`spawn_item` is for things that *produce* items** (vending machine, fabricator,
  spell that conjures). NOT for "stuff inside a chest" — that's the container's
  `contents` / a spawn gated by a condition so it can't be farmed infinitely.

---

# PART 1 — TRIGGER TYPES (catalog)

Each trigger fires on a specific event. `conditions` gate *whether* it runs;
`effects[]` say *what happens*.

## Item interaction

| type | fires when | notes / example |
|---|---|---|
| `on_take` | player picks the item up | best for whispers/weight/magic reaction |
| `on_drop` | player drops it | "it thuds to the ground" |
| `on_examine` | player examines it | ideal for save-gated reveals |
| `on_inspect` | upgraded examine | "you study it closely" |
| `on_use` | player uses it | the generic action; also co-fires on_eat/drink |
| `on_use_progressive` | every use (fires *alongside* on_use) | charges/ramps. Gate w/ `uses_reached`/`uses_above` |
| `on_use_on` | used ON a target (item/way/character) | unlocks, keys, use-on-door |
| `on_look` | player looks at it in room | ambient flavor |
| `on_search` | player searches it/area | hidden finds |
| `on_eat` / `on_drink` | consume it | food/drink; already co-fires on_use |
| `on_read` | read it | books/notes — write the excerpt |
| `on_light` | a toggleable turns **on** (companion to `on_toggle_on`; both fire) | lighting flavor — "the beam carves through the dark" |
| `on_activate` | activate it | mechanism, switch |
| `on_equip` / `on_unequip` | equip/unequip | weapon threats, curses |
| `on_throw` | throw it | breaking, distance effects |
| `on_break` | it breaks | shards, "the blade snaps" |
| `on_depleted` | `uses` reaches 0 | "it runs out / burns out" (fires after the system flips unlit) |
| `on_toggle_on` / `on_toggle_off` | toggleable flip ON / OFF | the REAL trigger for turning a light on |
| `on_spoil` | food spoils on a tick | rot/poison |
| `on_speech` | someone speaks near it | "it reacts to the word X" |

## Movement / doors / areas

| type | fires when | notes / example |
|---|---|---|
| `on_enter` | player enters an **area** | arrival flavor, traps, ambience |
| `on_open` / `on_close` | a door/container opens/closes | creaks, "the lid groans open" |
| `on_auto_open` | auto-opens (see_through/auto_open) | |
| `on_state_enter` / `on_state_exit` | node's `current_state` changes | recursive — fires on the node itself |
| `on_fail_jump` / `on_fail_climb` | a jump/climb attempt fails | "you slip and fall" |

## Time / environment (fired by the engine on area/way/character nodes)

| type | fires when |
|---|---|
| `on_tick` | every time tick (carried items also fire) |
| `on_turn_start` / `on_turn_end` | start-end of a turn |
| `on_dawn` / `on_dusk` / `on_day` / `on_night` | clock phases |
| `on_full_moon` / `on_blood_moon` | moon phases |
| `on_delayed` | a `schedule_trigger` effect fires N ticks later (on the target node) |

---

# PART 2 — CONDITIONS (catalog)

Gate the trigger. Simple leaf = `{"type": "<t>", ...}`. Combine with
`{"operator": "and"|"or"|"not", "conditions": [...]}`.

| type | meaning | example |
|---|---|---|
| `uses_above` | item's `uses` is above **value** | `{"type":"uses_above","value":0}` — "not empty yet" |
| `uses_reached` | `uses` ≤ **value** | `{"type":"uses_reached","value":0}` — "just ran out" |
| `has_item` | player carries **item** | `{"type":"has_item","item":"rusty_key", "target":"player"}` |
| `has_items` | player carries ALL in list | `{"type":"has_items","value":["a","b"]}` |
| `is_equipped` | player has **item** equipped | `{"type":"is_equipped","item":"lantern"}` |
| `skill_check` | roll a **skill** vs DC (success = gate open) | `{"type":"skill_check","skill":"Investigation","dc":14}` — the *condition* way to gate on a skill |
| `save_throw` | unified save condition (task-159) | `{"type":"save_throw","stat":"CON","dc":12,"target":"self"}` |
| `state_equals` | a node's `current_state` equals value | `{"type":"state_equals","target":"self","value":"lit"}` / `"door_x=open"` |
| `random_chance` | X% chance. `value`=0–100 (item) or `chance`=0–1 (NPC) | `{"type":"random_chance","value":25}` |
| `sound_heard` | player has heard a sound **pattern** recently | `{"type":"sound_heard","pattern":"glass"}` |
| `speech_matches` | spoken text matches a phrase | `{"type":"speech_matches","phrase":"help","mode":"contains"}` |
| `temperature_below` / `temperature_above` | current-area temp vs threshold | `{"type":"temperature_below","value":5}` |
| `area_temp` | area temp compared (op lt/gt/eq…) | `{"type":"area_temp","value":30,"operator":"gt"}` |
| `vital` / `vital_above` / `vital_below` | player vital vs threshold | `{"type":"vital","stat":"HP","value":15,"operator":"lt"}` |
| `time_of_day` | clock HH:MM matches | `{"type":"time_of_day","value":"03:00"}` |
| `weather` | current-area weather == value | `{"type":"weather","value":"fog"}` |
| `area_has_status` | area has dynamic status (poison_gas…) | `{"type":"area_has_status","status_type":"poison_gas"}` |
| `has_tag` | target has a tag (target=used-on node for use_on) | `{"type":"has_tag","value":"occult","target":"target"}` |
| `target_has_tag` | used-on node has tag (alias) | `{"type":"target_has_tag","value":"rusted"}` |
| `has_trait` | player has trait | `{"type":"has_trait","value":"loner"}` |
| `item_relationship` | this item has an edge of relation | `{"type":"item_relationship","relation":"in"}` — "has contents inside" |
| `in_area` / `proximity` | NPC/player location | NPC behaviors |
| `eq` | context key == value | NPC behaviors |
| `tick_since_state` | ticks since state_enter ≥ min | NPC behaviors |
| `npc_emotion_is` / `npc_is_hidden` / `character_has_tag` | NPC state | NPC behaviors |

---

# PART 3 — EFFECTS (catalog)

Each effect = `{"type": "<t>", "params": {...}}`. Prose lives in
`params.message`/`params.success_message`. A trigger can have MULTIPLE effects,
run in order.

## Narrative / state
| type | what it does | example |
|---|---|---|
| `message` | prints narratATION (the workhorse) | `{"type":"message","params":{"message":"The doll's head turns to face you."}}` |
| `set_state` | set `current_state` (fires on_state_exit/enter) | `{"type":"set_state","params":{"node_id":"self","state":"lit","message":"…"}}` |
| `set_hidden` | reveal/hide a node | `{"type":"set_hidden","params":{"hidden":false,"message":"…"}}` |
| `add_tag` / `remove_tag` | tag a node | `{"type":"add_tag","params":{"node_id":"self","tag":"examined"}}` |
| `rename` | rename a node | `{"type":"rename","params":{"node_id":"self","name":"The Warden's Key"}}` |
| `set_parameter` / `adjust_parameter` | set/increment a `parameters` key | `{"type":"set_parameter","params":{"node_id":"self","parameter_name":"charges","value":3}}` |
| `set_description` / `append_description` | (re)write a node's description | `{"type":"append_description","params":{"node_id":"self","text":" It is warmer now."}}` |

## Vitals / conditions
| type | what it does | example |
|---|---|---|
| `adjust_vital` | add/subtract a vital | `{"type":"adjust_vital","params":{"stat":"Hunger","amount":-30,"target":"self","success_message":"…"}}` |
| `heal` | restore HP/stat | `{"type":"heal","params":{"amount":15,"target":"self"}}` |
| `damage` | deal damage (optionally save-resisted) | `{"type":"damage","params":{"amount":10,"target":"self","save":{"stat":"DEX","dc":14,"on_success":"half"}}}` |
| `save` | roll a save, run `on_success`/`on_fail` branches | `{"type":"save","params":{"stat":"CON","dc":13,"target":"self","on_success":[{"type":"message","params":{"message":"…"}}],"on_fail":[{"type":"apply_condition","params":{"condition":"poisoned","duration":8,"target":"self"}},{"type":"damage","params":{"amount":6,"target":"self"}}]}}` |
| `apply_condition` / `remove_condition` | add/remove a condition | `{"type":"apply_condition","params":{"condition":"poisoned","duration":8,"target":"self","source_type":"item"}}` |
| `apply_trait` / `remove_trait` | add/remove a trait | `{"type":"apply_trait","params":{"trait":"clumsy","target":"self"}}` |
| `drain` | deplete a source (uses/charge) | `{"type":"drain","params":{"amount":1,"target":"self"}}` |
| `adjust_uses` | change item uses | `{"type":"adjust_uses","params":{"amount":-1}}` |
| `consume_item` | remove an item from the player | `{"type":"consume_item","params":{"item_id":"bread_loaf","target":"self"}}` |

## Env / area / way
| type | what it does | example |
|---|---|---|
| `set_environment` | override full env keys (light/temp/air/smell/noise…) on an area | `{"type":"set_environment","params":{"light":40,"smell":"woodsmoke","message":"…"}}` |
| `adjust_environment` | increment temp/light, or set air/smell/noise | `{"type":"adjust_environment","params":{"temperature":2,"noise":"quiet"}}` — used for *instant* shifts |
| `apply_area_status` / `clear_area_status` | dynamic area status (on_fire, poison_gas, flooded) | `{"type":"apply_area_status","params":{"target":"","status_type":"poison_gas","severity":2,"message":"…"}}` |
| `unlock_way` | unlock a way | `{"type":"unlock_way","params":{"way_id":"way_attic_door","message":"The key turns with a click."}}` |
| `set_way_target` / `set_way_view` / `spawn_way` / `spawn_area` | rewire / rebuild geography | GM-style |
| `teleport` | move player to an area | `{"type":"teleport","params":{"area":"cellar"}}` |
| `spawn_item` | produce a brand-new item (vending machine / fabricator / conjure). **Needs a gating condition** or it's farmable | `{"type":"spawn_item","params":{"item_id":"water_bottle","into":"area"}}` |
| `give_item` | put a library item into a character | `{"type":"give_item","params":{"item_id":"note","target":"self"}}` |
| `remove_item` | remove an item node from the world | |
| `set_wet` | wet/dry clothing | `{"type":"set_wet","params":{"wet":true,"target":"self","message":"…"}}` |

## Spawn / memory / meta (GM + NPC)
| type | what it does |
|---|---|
| `spawn_character` | spawn a character |
| `surface_memory` / `suppress_memory` / `unblock_memory` | memory recall control |
| `set_time` / `set_date` | game clock/calendar |
| `set_weather` / `forecast_override` / `adjust_forecast` | weather & forecast |
| `llm_respond` | the node/entity speaks via the LLM (best for speechy items) |
| `scry` | view a distant area |
| `schedule_trigger` | queue `on_delayed` N ticks later on the target node | `{"type":"schedule_trigger","params":{"delay_ticks":5,"target":"self"}}` |
| `destroy_self` / `end_scenario` / `restart_scenario` | meta/end-game |

---

# PART 4 — CORRECTED ARCHETYPES

> The earlier draft had three wrong patterns (light, heat, container). Corrected
> per engine verification + user review.

## 1. Light source — a lantern / flashlight

**System auto-lights via `use`.** `use` → `toggle_item_status()` flips
`current_state` between `lit`/`unlit`, drains `uses`, fires
`on_toggle_on` (AND its companion `on_light`) or `on_toggle_off`, and
`on_depleted` when it runs out. So:

- **Base (what makes it work):** tag `toggleable` + `light_level`; `current_state`
  starts `unlit`. That's it — the engine lights/douses, drains `uses`, fires
  `on_depleted`. **No set_state lit trigger needed, ever.**
- **on_light** (optional, preferred): flavor *when it comes on* — "The beam
  carves through the dark." (Companion to `on_toggle_on`; both fire — pick ONE.)
- **on_toggle_off** (optional): flavor when doused.
- **on_use** (optional): if a non-toggleable lights-on-use (a match), a
  `set_state lit` + message is fine.
- **Flashlight example (what you asked for):**
  - `on_examine` → reveals `uses` count: "The battery reads **~{#uses} %**. It looks standard."
  - `on_throw` → breaks: `set_state broken` + "It shatters on the flagstones."
  - `on_use` → message (it's toggleable — system handles the flip, this just
    narrates): "You thumb the switch. *click*."
  - `on_depleted` → "The light dies. Dead batteries."

```json
{ "trigger_type": "on_toggle_on", "conditions": [],
  "effects": [ { "type": "message", "params": { "message": "You click the flashlight on — a hard white cone throws the dust into stark relief." } } ],
  "success_message": "", "fail_message": "" }
```
```json
{ "trigger_type": "on_throw", "conditions": [],
  "effects": [ { "type": "set_state", "params": { "node_id": "self", "state": "broken", "message": "The flashlight bursts on the flagstones. The casing splinters." } } ],
  "success_message": "", "fail_message": "" }
```
```json
{ "trigger_type": "on_examine", "conditions": [ { "type": "uses_above", "value": -1 } ],
  "effects": [ { "type": "message", "params": { "message": "Standard plastic flashlight. Battery's at {uses}%." } } ],
  "success_message": "", "fail_message": "" }
```

## 2. Heat source — a brazier / stove / glowing rune

**System:** a `lit` item tagged `heat_source` pulls the area toward
`target_temperature` at `heating_rate` per tick (a *property*, not a trigger!).
So heat sources need **no** set/adjust_environment trigger.

```jsonc
// item properties (NOT triggers):
{ "tags": ["heat_source", "fireplace"], "current_state": "lit",
  "target_temperature": 32, "heating_rate": 0.5 }
```
- `on_toggle_on` → "You bank fresh coals; the warmth begins to spread."
- `on_examine` → "This one puts out a steady, dry heat."
- (The stone tablet with rune is *correct* to have NO temp trigger — it just
  needs `target_temperature`/`heating_rate`, which it currently lacks, so its
  heating is non-functional as authored.)

## 3. Sound source — a music box / radio / wind chimes

**Base:** tag `sound_source` + `sound_level` + `sound_pattern` on the item;
system plays it when `current_state` in `(lit, on, active, ringing, playing)`.
A one-shot use can also push `noise` via `set_environment`.

- **on_use** → wind it: "You wind the key… a sad lullaby creaks out." +
  optionally `set_state active` / `set_environment noise`.
- For a speech-y artifact, **`llm_respond`** is better than a canned message.

```json
{ "trigger_type": "on_use", "conditions": [],
  "effects": [
    { "type": "message", "params": { "message": "You wind the key. A sad, tinny lullaby creaks out — and the whispers in the hallway fall quiet." } },
    { "type": "set_environment", "params": { "noise": "haunting music" } }
  ],
  "success_message": "", "fail_message": "" }
```

## 4. Food / drink

- Food → `on_eat`, `Hunger` −; drink → `on_drink`, `Thirst` −.
- Finite uses → `uses_above: 0` condition + empty fail message.
- Prose → `adjust_vital.params.success_message`.

```json
{ "trigger_type": "on_eat", "conditions": [ { "type": "uses_above", "value": 0 } ],
  "effects": [ { "type": "adjust_vital",
      "params": { "stat": "Hunger", "amount": -35, "target": "self",
                  "success_message": "You tear off a hunk of dark rye. Coarse and a little stale, but it fills the hollow in your stomach." } } ],
  "success_message": "", "fail_message": "The bread is all gone — just crumbs." }
```

## 5. Poison / tainted item

Skill gate goes in the **condition** (as you said), reveal in the effect:

```json
{ "trigger_type": "on_examine",
  "conditions": [ { "type": "skill_check", "skill": "Investigation", "dc": 14 } ],
  "effects": [ { "type": "message",
      "params": { "message": "It's poisoned. That should NOT go in anyone's mouth." } } ],
  "success_message": "", "fail_message": "" }
```
```json
{ "trigger_type": "on_examine",
  "conditions": [ { "type": "skill_check", "skill": "Investigation", "dc": 14, "operator": "not" } ],
  "effects": [ { "type": "message", "params": { "message": "Looks safe enough to eat." } } ],
  "success_message": "", "fail_message": "" }
```
```json
{ "trigger_type": "on_drink", "conditions": [ { "type": "uses_above", "value": 0 } ],
  "effects": [
    { "type": "adjust_vital", "params": { "stat": "Thirst", "amount": -20, "target": "self", "success_message": "You take a sour sip." } },
    { "type": "save", "params": { "stat": "CON", "dc": 13, "target": "self",
        "on_success": [ { "type": "message", "params": { "message": "It's bitter and wrong, but you keep it down." } } ],
        "on_fail": [ { "type": "apply_condition", "params": { "condition": "poisoned", "duration": 8, "target": "self", "source_type": "item" } },
                     { "type": "damage", "params": { "amount": 6, "target": "self" } },
                     { "type": "message", "params": { "message": "Your stomach lurches violently — the wine was poisoned." } } ] } }
  ],
  "success_message": "", "fail_message": "The bottle is empty." }
```

## 6. Trap

```json
{ "trigger_type": "on_enter", "conditions": [],
  "effects": [ { "type": "damage", "params": { "amount": 10, "target": "self",
      "save": { "stat": "DEX", "dc": 14, "on_success": "half" },
      "message": "The floor gives way! Spikes jab up at you." } } ],
  "success_message": "", "fail_message": "" }
```

## 7. Container / locked chest

**`spawn_item` is NOT for "what's in the chest"** — it creates brand-new items
(constant Rusty Key spawner = farmed keys). A chest opens if you have the key:

```json
{ "trigger_type": "on_use", "conditions": [ { "type": "has_item", "item": "rusty_key", "target": "player" } ],
  "effects": [ { "type": "set_state", "params": { "node_id": "self", "state": "open",
      "message": "The key slides in. A click, and the lid swings open." } } ],
  "success_message": "", "fail_message": "Locked. It wants a key." }
```
- Pre-placed contents live in the node's `contents` / placement — no spawn needed.
- A **genuine** spawner (vending machine) DOES use `spawn_item`, but gate it so it
  can't be farmed infinitely (per-use cost, a `uses` count, etc.).

## 8. Weapon / cursed tool / haunted object / key / medicine

```json
// haunted take-whisper + scheduled dread:
{ "trigger_type": "on_take", "conditions": [],
  "effects": [ { "type": "message", "params": { "message": "The doll's head turns, just a fraction, to face you. Its painted eyes are wet." } },
               { "type": "schedule_trigger", "params": { "delay_ticks": 5, "target": "self" } } ],
  "success_message": "", "fail_message": "" }
// key on a door:
{ "trigger_type": "on_use_on", "conditions": [],
  "effects": [ { "type": "unlock_way", "params": { "way_id": "way_attic_hidden_door", "message": "The old key turns with a heavy click. The hidden door swings free." } } ],
  "success_message": "", "fail_message": "The key doesn't fit." }
// medicine:
{ "trigger_type": "on_use", "conditions": [],
  "effects": [ { "type": "heal", "params": { "amount": 15, "target": "self" } },
               { "type": "remove_condition", "params": { "condition": "poisoned", "target": "self" } },
               { "type": "message", "params": { "message": "The bitter tincture stings, then settles. The nausea drains away." } } ],
  "success_message": "", "fail_message": "" }
```

---

# PART 5 — What the code prompt embeds (as shipped)

**Decision (2026-09-22): the prompt embeds a deliberate subset, not the full catalogs**
— see the Outcome section for why. What actually ships in
`static/js/shared/trigger-suggest-ai.js`:

1. **Trigger types** — the full item-interaction set plus the movement and time families
   an item/way/area can use. Excluded as engine-only / NPC-behaviour surfaces:
   `on_auto_open`, `on_fail_jump` / `on_fail_climb`, `on_turn_start` / `on_turn_end`.
   Parts 1–3 above remain the complete reference.
2. **Conditions** — the fifteen an author needs: `uses_above`, `uses_reached`, `has_item`,
   `has_items`, `is_equipped`, `skill_check`, `state_equals`, `random_chance`,
   `sound_heard`, `speech_matches`, `temperature_below` / `_above`, `weather`, `vital`,
   plus the `and` / `or` combiner. Engine-side ones (`save_throw`, `area_temp`,
   `time_of_day`, `item_relationship`, …) stay out.
3. **Effects** — the authoring set: `message`, `adjust_vital`, `heal`, `damage`, `save`,
   `set_state`, `set_environment`, `unlock_way`, `spawn_item`, `give_item`,
   `remove_item` / `consume_item`, `add_tag` / `remove_tag`, `set_parameter` /
   `adjust_parameter`, `schedule_trigger`, `surface_memory`, `teleport`, `set_time`,
   `set_weather`, `destroy_self`.
4. **Hard rules** — effects ≥1 per trigger; prose in `effects[].params.message` /
   `adjust_vital.success_message`; top-level `success_message` / `fail_message` stay
   `""`; never pair `on_light` with `on_toggle_on`; never pair `on_use` with
   `on_eat`/`on_drink`; heat sources are properties, not triggers; finite uses get
   `uses_above: 0` plus a fail message.
5. **Three worked examples** (food, tainted drink with a CON save, haunted take) as
   style anchors, closing with "Match the style of the examples".

**Expanding to the full catalogs is a deliberate, reversible choice** — do it only if
generations under-perform, and re-run the prompt tests afterwards.

## Verification

- **Prompt side — automated.** `node tools/unit/run.cjs` →
  `tools/unit/test_trigger_suggest_ai.js` (16 tests): the hard rules are stated, and
  every embedded example is validated against them.
- **Output side — manual, needs a live model.** Generate for a candlestick, poisoned
  wine and a fireplace; assert every trigger has non-empty `effects[]`, prose lives in
  `params[].message` and not the top-level strings, no `on_light` + `on_toggle_on` pair
  on one item, and the heat source yields zero env triggers.