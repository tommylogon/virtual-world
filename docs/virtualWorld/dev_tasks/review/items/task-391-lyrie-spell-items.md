---
type: task
status: review
area: items
priority: medium
---

# task-391: Lyrie's Spellbook — Life-Bonded Spell Items

**Filed**: 2026-09-02 
**Implemented**: 2026-09-27 
**Source**: Character backstory from `data/library/characters/Lyrie.json` — memories, personality, and current Frozen Thicket situation.

## Status — implemented (2026-09-27)

All 15 spells are in `data/library/items/`, assigned to Lyrie, and backed by five
new effect handlers. See **Implementation record** at the bottom of this file for
what actually differs from the original proposal.

> Note: the original spec said "12 spell items" and then listed 15. All 15 were
> authored.

## Summary

Create 12 spell items for Lyrie, each tied to a specific life memory or enduring situation. Spells should reflect her personality: well-intentioned, slightly chaotic, deeply kind, and occasionally catastrophic. Some should be implementable with existing engine effects; others should propose new trigger/effect types that would meaningfully expand the engine.

Each spell below includes a full item JSON spec (library-ready), suggested trigger wiring, and a note on whether it uses existing engine machinery or proposes a new effect.

## Spells

### 1. Hearth Ember
**Life memory**: *The Present* (Age 79) — freezing in the Frozen Thicket. 
**Trigger**: `on_use` 
**Effect tier**: Existing engine effects only.

```json
{
 "name": "Hearth Ember",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "A pocket of warmth Lyrie learned out of necessity. She cups her hands and a soft heat blooms between her palms, curling up her arms and toes. It's the only spell that behaves exactly like she wants — probably because she's cast it a thousand times in the snow.",
 "tags": ["spell", "magic", "fire", "warmth"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "remove_condition",
 "params": {
 "condition": "hypothermia",
 "target": "self",
 "message": "The deep cold lets go."
 }
 },
 {
 "type": "heal",
 "params": {
 "amount": 20,
 "stat": "Temperature",
 "target": "self",
 "message": "Warmth spreads all the way to your toes."
 }
 },
 {
 "type": "adjust_environment",
 "params": {
 "temperature": 5,
 "target_node": "self",
 "message": "The air around Lyrie turns comfortably warm."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

### 2. Tongue of the Little Folk
**Life memory**: *The Squirrel Incident* (Age 31) — tried to comfort a squirrel in animal tongue; it screamed for twenty minutes. 
**Trigger**: `on_use` 
**Effect tier**: Existing + `llm_respond` for animal dialogue.

```json
{
 "name": "Tongue of the Little Folk",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "The elven tongue for beasts. Lyrie knows it well — she learned it the hard way. Animals still don't quite understand her, but she never stops trying. She leaves acorns out as apologies.",
 "tags": ["spell", "magic", "beast", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "add_tag",
 "params": {
 "node_id": "self",
 "tag": "animal_tongue",
 "message": "Your ears crackle and pop in a way beasts seem to recognize."
 }
 },
 {
 "type": "llm_respond",
 "params": {
 "instructions": "You are a small forest creature (bird, squirrel, rabbit, or fox) that has been addressed in animal tongue by Lyrie. Reply in a single short sentence of animal-speak: chitters, chirps, huffs, or clicks. Never full sentences. Sometimes you are annoyed, sometimes curious, sometimes indifferent.",
 "fallback_message": "*A small creature stares at Lyrie, then darts away.*"
 }
 },
 {
 "type": "message",
 "params": {
 "message": "Lyrie chirrups a wumbling greeting. Something small and alive considers her seriously from the underbrush."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

### 3. Whisper of Green
**Life memory**: *The Grapevine* (Age 45) — talked to a grapevine named Vincent for three days. "He never talked back, but he listened." 
**Trigger**: `on_use` 
**Effect tier**: Existing + proposed `plant_whisper` effect (plants can `llm_respond` as slow, patient speakers).

```json
{
 "name": "Whisper of Green",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "Named for Vincent the grapevine. Plants speak slowly, in rustles and sap, and they remember everything. This spell lets her ask them small questions — where water hides, which way is safe, whether a storm is coming.",
 "tags": ["spell", "magic", "plant", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "surface_memory",
 "params": {
 "text": "Vincent the grapevine. You talked for three days. He never talked back, but he listened.",
 "importance": 5,
 "message": "A slow, green warmth rises in your chest. You can almost hear leaves rustling."
 }
 },
 {
 "type": "heal",
 "params": {
 "amount": 5,
 "stat": "Sanity",
 "target": "self",
 "message": "The forest feels like an old friend."
 }
 },
 {
 "type": "llm_respond",
 "params": {
 "instructions": "You are a nearby plant (bush, vine, tree, or flower) addressed by Lyrie through plant-whisper magic. Reply in one short, slow, earthy sentence full of rustle, sap, root, and leaf imagery. Be patient. Be ancient. Be kind.",
 "fallback_message": "*A branch brushes your arm. The plant has nothing important to say right now.*"
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

### 4. Bloom of the Well
**Life memory**: *The Exile Scare* (Age 62) — tried to make the well prettier with flowers. Turned it into a fountain of blossoms; water unusable for a week. This is the incident that got her almost exiled. 
**Trigger**: `on_use` 
**Effect tier**: Existing + proposed `area_transformation` visual state.

```json
{
 "name": "Bloom of the Well",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "What the Exile Scare taught her: beauty has consequences. This spell makes flowers bloom from almost anything, but the result is always a little too much. The well ran for a week. Her hands still shake when she thinks about it.",
 "tags": ["spell", "magic", "flower", "plant", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "spawn_item",
 "params": {
 "item_id": "flowers",
 "into": "area",
 "message": "Blossoms erupt from the ground in a glorious, messy cascade."
 }
 },
 {
 "type": "adjust_environment",
 "params": {
 "light": 10,
 "air": "sweet",
 "target_node": "self",
 "message": "The air turns sweet and the light softens."
 }
 },
 {
 "type": "message",
 "params": {
 "message": "Lyrie watches the flowers bloom and smiles, then winces. 'Not too much... not too much...'"
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

### 5. Transfigure: Poultry
**Life memory**: *The Chicken Cart* (Age 22) — tried to fix a cart wheel with magic. "I made it better — it turned into a chicken." 
**Trigger**: `on_use_on` (cast on an object) 
**Effect tier**: **Proposes new effect**: `polymorph_target` — transforms a target item/NPC into another template for a duration.

```json
{
 "name": "Transfigure: Poultry",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "The Chicken Cart. She tried to fix a wheel and made it into a chicken. She still apologizes to poultry. The spell is theoretically about transmutation, but in practice it just turns things into birds.",
 "tags": ["spell", "magic", "transmutation", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use_on",
 "effects": [
 {
 "type": "message",
 "params": {
 "message": "Lyrie squints, mutters a word that sounds like 'chicken,' and —"
 }
 },
 {
 "type": "polymorph_target",
 "params": {
 "target_template": "chicken",
 "duration": 50,
 "message": "The object clucks, feathers bursting from its surface, and struts away."
 }
 },
 {
 "type": "apply_condition",
 "params": {
 "condition": "amused",
 "target": "self",
 "duration": 5,
 "message": "Well. That was embarrassing."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `polymorph_target` — takes `target_template` (library item/NPC id), `duration` in ticks, optional `revert_after`. Should work on items and simple NPCs. Reverts automatically after duration.

### 6. Conjure Fluffy
**Life memory**: *The Lost Sheep* (Age 70) — found a rock that looked like a sheep. Convinced herself it was Fluffy. "It never moved. I still visit sometimes." 
**Trigger**: `on_use` 
**Effect tier**: **Proposes new effect**: `create_illusory_companion` — spawns a temporary, interactable NPC with custom dialogue and behavior.

```json
{
 "name": "Conjure Fluffy",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "A rock that looks like a sheep. Lyrie named him Fluffy. He never moved, but he was good company in the snow. This spell conjures something that isn't quite real but feels true — useful when you're lost and the trees all look the same.",
 "tags": ["spell", "magic", "illusion", "companion", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "message",
 "params": {
 "message": "Lyrie closes her eyes and holds out her hands. When she opens them, there's a small, fuzzy shape sitting in her palms. It looks like a sheep made of down and wishful thinking. It blinks at her."
 }
 },
 {
 "type": "create_illusory_companion",
 "params": {
 "name": "Fluffy",
 "description": "A small, fuzzy sheep made of down and wishful thinking. It has kind eyes and no discernible mass. It does not move unless you believe very hard.",
 "duration": 100,
 "dialogue": [
 "Fluffy blinks slowly. You feel strangely comforted.",
 "Fluffy chews on nothing. It is a very peaceful nothing."
 ],
 "message": "Fluffy materializes. He is very quiet and very warm."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `create_illusory_companion` — spawns an NPC with a limited lifespan, custom dialogue snippets, and no collision/physics. Vanishes after duration or if the caster stops concentrating (e.g., moves to a new area).

### 7. Siren's Lullaby
**Life memory**: *The Singing Fish* (Age 75) — sang to a sad fish for two hours. It died. She doesn't sing near water anymore. 
**Trigger**: `on_use` 
**Effect tier**: **Proposes new effect**: `broadcast_emotion` — shifts the `emotion` state of all characters within an area radius.

```json
{
 "name": "Siren's Lullaby",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "The Singing Fish. She sang to cheer it up. It died. She hasn't sung near water since. The lullaby still soothes, but there's something about it that unnerves living things just a little.",
 "tags": ["spell", "magic", "song", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "message",
 "params": {
 "message": "Lyrie hums a soft, wordless tune. The tension in the air eases. A bird nearby tilts its head, then flies away a little faster than before."
 }
 },
 {
 "type": "broadcast_emotion",
 "params": {
 "emotion": "soothed",
 "intensity": 0.3,
 "radius_areas": 1,
 "duration": 5,
 "message": "Your song drifts through the area. Living things feel strangely comforted, then vaguely unsettled."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `broadcast_emotion` — shifts `emotion.current` for all characters in range. Could also `adjust_vital` for Social or Sanity as a secondary effect.

### 8. Spark of the Baking Incident
**Life memory**: *The Great Baking Incident* (Age 14) — used fire salts instead of flour. Kitchen exploded. Elder Caelum's eyebrows never grew back. 
**Trigger**: `on_use` 
**Effect tier**: Existing + proposed `spawn_fire_source` persistent hazard.

```json
{
 "name": "Spark of the Baking Incident",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "Fire salts instead of flour. The kitchen exploded. Elder Caelum's eyebrows never grew back. This spell creates a sudden burst of flame — not a controlled one, but a passionate, enthusiastic one. She still bakes him a cake every year. She buys it now.",
 "tags": ["spell", "magic", "fire", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "spawn_item",
 "params": {
 "item_id": "candle",
 "into": "area",
 "current_state": "lit",
 "message": "A shower of sparks erupts from Lyrie's hands. One candle ignites. The curtains are fine. Probably."
 }
 },
 {
 "type": "adjust_environment",
 "params": {
 "temperature": 8,
 "light": 40,
 "target_node": "self",
 "message": "The room brightens and warms rapidly."
 }
 },
 {
 "type": "surface_memory",
 "params": {
 "text": "The Great Baking Incident. Elder Caelum's eyebrows. The kitchen.",
 "importance": 5,
 "message": "For a moment, you smell burnt sugar and regret."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

### 9. Apology to Chickens
**Life memory**: *The Chicken Cart* (Age 22) — the aftermath. She apologizes to chickens. This spell makes skittish creatures calm down around her. 
**Trigger**: `on_use_on` (cast on a character/NPC) 
**Effect tier**: Existing, but extends `apply_condition` to non-self targets in a spell-item context.

```json
{
 "name": "Apology to Chickens",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "The Chicken Cart incident left her with a lifelong habit: she apologizes to chickens. This spell extends that apology into a subtle pacification — fowl (and sometimes other skittish creatures) calm down around her.",
 "tags": ["spell", "magic", "beast", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use_on",
 "effects": [
 {
 "type": "apply_condition",
 "params": {
 "condition": "charmed",
 "target": "target",
 "duration": 5,
 "message": "Lyrie looks at the creature with big, earnest eyes. It seems to relax."
 }
 },
 {
 "type": "message",
 "params": {
 "message": "'I'm sorry about the cart,' she whispers."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**Dev note**: `on_use_on` with `target: "target"` already exists for items; validating it works from spell items with `target: "target"` is the main QA task here.

### 10. Vincent's Embrace
**Life memory**: *The Grapevine* (Age 45) — three days of talking to a vine. "I named him Vincent. He never talked back, but he listened." 
**Trigger**: `on_use` 
**Effect tier**: Existing + proposed `reveal_hidden` effect (nature exposes what is concealed).

```json
{
 "name": "Vincent's Embrace",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "Named for a grapevine who listened for three days. This spell lets her ask the green world for small favors — a hidden path, a safe resting place, something to eat. Plants oblige, slowly.",
 "tags": ["spell", "magic", "plant", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "surface_memory",
 "params": {
 "text": "Vincent the grapevine. The forest keeps secrets if you ask nicely.",
 "importance": 4,
 "message": "The leaves rustle. A path reveals itself, half-hidden by brambles."
 }
 },
 {
 "type": "heal",
 "params": {
 "amount": 10,
 "stat": "Sanity",
 "target": "self",
 "message": "The forest seems to lean in, protective."
 }
 },
 {
 "type": "reveal_hidden",
 "params": {
 "radius_areas": 1,
 "duration": 20,
 "message": "Through the undergrowth, you see what was hidden: a narrow trail, a cache of berries, a safe place to rest."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `reveal_hidden` — temporarily sets `hidden: false` on items/NPCs/ways within an area radius. Re-hides after duration.

### 11. Fountain of Blossoms
**Life memory**: *The Exile Scare* (Age 62) — turned the village well into a fountain of blossoms. Water unusable for a week. 
**Trigger**: `on_use` 
**Effect tier**: Existing + proposed `transform_area_theme` (area appearance override).

```json
{
 "name": "Fountain of Blossoms",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "The spell that almost got her exiled. Turns any water source into a geyser of blossoms. Beautiful, fragrant, and absolutely catastrophic for water quality. She casts it only when she's very sure the water doesn't matter.",
 "tags": ["spell", "magic", "flower", "water", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "spawn_item",
 "params": {
 "item_id": "flowers",
 "into": "area",
 "message": "A fountain of blossoms erupts from the ground, glorious and overwhelming."
 }
 },
 {
 "type": "adjust_environment",
 "params": {
 "light": 15,
 "temperature": 2,
 "air": "sweet",
 "target_node": "self",
 "message": "The area is drenched in floral sweetness and soft light."
 }
 },
 {
 "type": "transform_area_theme",
 "params": {
 "theme": "blossoming",
 "duration": 100,
 "message": "The world turns pink and white. The elders are definitely going to notice."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `transform_area_theme` — applies a temporary visual/audio/smell overlay to the current area. Themes could include `blossoming`, `frost`, `autumn`, `starlight`. Duration-based revert.

### 12. Ember Companion
**Life memory**: *The Present* (Age 79) — she talks to the little flame like a friend. "oh, please stay lit... i need you to keep me warm." 
**Trigger**: `on_use` 
**Effect tier**: Existing + proposed `bind_companion` (persistent summoned entity that follows caster).

```json
{
 "name": "Ember Companion",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "The little ember she talks to in the Frozen Thicket. She learned to give it a shape, a voice, a tiny flickering personality. It follows her, keeps her warm, and never argues.",
 "tags": ["spell", "magic", "fire", "companion", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "spawn_item",
 "params": {
 "item_id": "everflame_ember",
 "into": "inventory",
 "current_state": "lit",
 "message": "A tiny ember wakens in your palm. It hums contentedly and hovers near your shoulder."
 }
 },
 {
 "type": "bind_companion",
 "params": {
 "item_id": "everflame_ember",
 "follow_distance": 1,
 "duration": 300,
 "message": "The ember settles beside you, a quiet warm presence."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `bind_companion` — marks a spawned item/NPC as a persistent companion of the caster. It follows the caster across area transitions within duration, retains its own triggers/behaviors, and can be interacted with by other characters. Vanishes if caster dies or duration expires.

### 13. Mending Touch
**Life memory**: *The Chicken Cart* (Age 22) — the original intent was fixing the wheel. 
**Trigger**: `on_use` 
**Effect tier**: **Proposes new effect**: `repair_item` — restores durability/uses to a broken item in inventory or on the ground.

```json
{
 "name": "Mending Touch",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "The spell she tried to use on the chicken cart. She wanted to fix the wheel. It turned the cart into a chicken. But the principle was right — mending. If she concentrates very hard, she can make broken things whole again. Mostly.",
 "tags": ["spell", "magic", "mending", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use_on",
 "effects": [
 {
 "type": "message",
 "params": {
 "message": "Lyrie presses her hands to the broken thing and closes her eyes. Her brow furrows with effort. For a moment nothing happens. Then — a soft green glow. The cracks knit together."
 }
 },
 {
 "type": "repair_item",
 "params": {
 "target": "target",
 "repair_amount": 5,
 "message": "The item feels stronger in your hands."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `repair_item` — restores `uses` or a new `durability` field on a target item. If no durability system exists yet, this effect seeds the schema discussion for one.

### 14. Glimpse of the Lost Path
**Life memory**: *The Present* (Age 79) — three days lost in the woods. "I think I'm going the right way. I'm probably not." 
**Trigger**: `on_use` 
**Effect tier**: Existing (`scry`) + proposed `set_way_hint` (way metadata update).

```json
{
 "name": "Glimpse of the Lost Path",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "Three days lost in the woods. She learned to ask the forest for directions. Not a map — just a feeling, a pull, a sense of which way leads home. It's not always right, but it's always hopeful.",
 "tags": ["spell", "magic", "navigation", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "scry",
 "params": {
 "target": "nearest_way_out",
 "message": "You catch a glimpse of a familiar landmark — the village, the well, the tree with the low branch. You think you know which way to go."
 }
 },
 {
 "type": "set_way_hint",
 "params": {
 "way_id": "nearest_way_out",
 "hint": "This way feels like it leads toward something familiar.",
 "duration": 30,
 "message": "An exit nearby seems to hum with a faint, welcoming pull."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `set_way_hint` — adds a temporary narrative hint to a way/node. Displayed in look/examine outputs and way tooltips for `duration` ticks.

### 15. Hearth Ward
**Life memory**: *The Exile Scare* (Age 62) aftermath — she did chores for everyone to make amends. Learned that protection is quieter than beauty. 
**Trigger**: `on_use` 
**Effect tier**: **Proposes new effect**: `ward_area` — grants a defensive bonus or condition resistance within an area for a duration.

```json
{
 "name": "Hearth Ward",
 "actions": "examine,use",
 "current_state": "normal",
 "description": "A protective blessing learned from watching the village elders. Lyrie doesn't have the precision for grand wards, but she can make a small, wobbling circle of safety around herself. It's not much, but it's home.",
 "tags": ["spell", "magic", "ward", "protection", "elven"],
 "triggers": [
 {
 "trigger_type": "on_use",
 "effects": [
 {
 "type": "ward_area",
 "params": {
 "radius_areas": 1,
 "duration": 50,
 "defense_bonus": 2,
 "resistance": "cold",
 "message": "A warm, fuzzy feeling settles around you. The cold softens at the edges of your senses."
 }
 },
 {
 "type": "adjust_environment",
 "params": {
 "temperature": 3,
 "light": 10,
 "target_node": "self",
 "message": "A small, warm circle of light surrounds you."
 }
 }
 ]
 }
 ],
 "uses": -1,
 "weight": 0.1
}
```

**New feature proposal**: `ward_area` — grants a buff to all friendly characters within `radius_areas`. Supports `defense_bonus`, `resistance` (element/status), and `auto_fail_saves` suppression.

## Companion Items / NPCs Needed

| Name | Type | Purpose | Source |
|------|------|---------|--------|
| `fluffy` | Item or simple NPC | The rock sheep from *The Lost Sheep*. Conjured by *Conjure Fluffy*. | New |
| `vincent` | Environmental NPC | The grapevine from *The Grapevine*. Responds to *Whisper of Green*. | New |
| `chicken` | Simple NPC | Transmutation target for *Transfigure: Poultry*. | New |
| `everflame_ember` | Item (existing) | Persistent flame companion for *Ember Companion*. | `data/library/items/everflame_ember.json` |
| `flowers` | Item (existing) | Spawned by *Bloom of the Well* and *Fountain of Blossoms*. | `data/library/items/flowers.json` |
| `white_feather` | Item (existing) | Comedy residue from failed *Transfigure: Poultry*. | `data/library/items/white_feather.json` |

## New Feature Proposals (Summary)

| Effect | Spells | Description |
|--------|--------|-------------|
| `polymorph_target` | Transfigure: Poultry | Transform a target item/NPC into another library template for `duration` ticks, then revert. |
| `create_illusory_companion` | Conjure Fluffy | Spawn a temporary NPC with custom dialogue, follows caster, vanishes on duration/area leave. |
| `broadcast_emotion` | Siren's Lullaby | Shift `emotion.current` for all characters within `radius_areas`. |
| `repair_item` | Mending Touch | Restore `uses` or `durability` on a target item. Seeds durability schema if absent. |
| `reveal_hidden` | Vincent's Embrace | Temporarily set `hidden: false` on nearby items/NPCs/ways. |
| `transform_area_theme` | Fountain of Blossoms | Temporary area overlay (visual/scent/sound theme) with auto-revert. |
| `bind_companion` | Ember Companion | Persistent summoned entity that follows caster across areas, retains its own triggers. |
| `set_way_hint` | Glimpse of the Lost Path | Temporary narrative hint on an exit, shown in look/examine outputs. |
| `ward_area` | Hearth Ward | Area-of-effect buff: defense bonus, elemental resistance, duration-based. |
| `plant_whisper` | Whisper of Green | Plants can `llm_respond` as slow, patient entities with memory of prior interactions. |

## Implementation Plan

1. **Implement new effects** in `engine/trigger_system.py` (or new `engine/spell_effects.py` if volume warrants) — prioritize by spell count: `polymorph_target`, `repair_item`, and `ward_area` are the highest-value because they unlock entire gameplay loops.
2. **Create companion items/NPCs**: `fluffy`, `vincent`, `chicken` in `data/library/items/` and `data/library/characters/`.
3. **Create spell item JSONs** in `data/library/items/` using the specs above.
4. **Assign spells to Lyrie**: add the completed item `library_id`s to `inventory` in `data/library/characters/Lyrie.json`.
5. **QA**: run `python -m pytest tests/ -q -k "trigger"` and manual playtest of each spell in a test scenario.

## Verification

- All 15 spells import cleanly from the library browser.
- Existing-effect spells fire correctly on first manual test.
- New-effect spells compile through the trigger validator and fail gracefully if the effect is not yet implemented.
- Lyrie's character file loads without JSON errors after spell inventory assignment.

## Implementation record (2026-09-27)

### What was added

**Five effect handlers** — `engine/effect_handlers/spells.py`, registered via
`engine/effects.py`, declared in `engine/triggers/constants.py`:

| Effect | What it does | Built from |
|--------|--------------|-----------|
| `polymorph_target` | Swap a node onto a library template, and revert it | snapshot + `schedule_trigger`/`on_delayed` |
| `create_illusory_companion` | Summon a temporary, inert companion | `spawn_character` hydration |
| `broadcast_emotion` | Spike the affect map within a radius | task-96 affect map |
| `bind_companion` | Mark a node as a follower of its caster | new turn sweep |
| `reveal_hidden` | Unhide things in a radius, re-hide on duration | `set_hidden` semantics |

Durations are in **ticks**, and the passage of time is handled in a new
`engine/companions.py` (`process_companions`), called once per turn from
`engine/tick_manager.py`. The effect handlers mark the world and get out of the
way, so a spell author never reasons about the tick loop — and the sweep sits
*outside* the `skip_npcs` guard deliberately, so a fast-forward still lets a
conjuration expire.

**Fifteen library items** in `data/library/items/hearth_ember`,
`tongue_of_the_little_folk`, `whisper_of_green`, `bloom_of_the_well`,
`transfigure_poultry`, `conjure_fluffy`, `sirens_lullaby`,
`spark_of_the_baking_incident`, `apology_to_chickens`, `vincents_embrace`,
`fountain_of_blossoms`, `ember_companion`, `mending_touch`,
`glimpse_of_the_lost_path`, `hearth_ward`.

**Two companion entities**: `data/library/characters/fluffy.json` and
`data/library/items/chicken.json`. All four items the spec assumed already
existed did (`everflame_ember`, `flowers`, `white_feather`, `candle`).
`vincent` was **not** created — Whisper of Green uses `llm_respond`, which
generates the plant's voice from instructions and needs no library entity.

**Lyrie** now carries the spellbook: 15 entries added to `inventory` in
`data/library/characters/Lyrie.json` (22 items total), in the same entry shape as
the existing `create_flame` reference.

**Tests**: `tests/test_spell_effects.py`, 11 tests.

### Corrections to the original spec

The spec's JSON was not library-schema-accurate. Real library items use
`"trigger_type"` as a **list** and carry `target_name` / `target_state` /
`conditions` / `success_message` / `fail_message` on every trigger. Authored
against the real schema instead.

Several effect params in the spec did not match the handlers:

- `heal` **ignores `target`** (`vitals.py` always uses `game_state.player`) and
 clamps to 100. Hearth Ember's `heal: {stat: Temperature}` would have been a
 37 -> 57 body-temperature swing, so it uses `adjust_vital` with a gentle +2 and
 leans on `remove_condition: hypothermia` for the actual effect.
- `surface_memory` takes `tags` / `keywords` / `salience_boost`, not
 `text` / `importance`. It only surfaces a memory that **already exists**; all
 nine of Lyrie's memories carry the right phrases (`Grapevine`,
 `Baking Incident`, `The Present`), so the keywords match.
- `spawn_item` supports `into: "area"` or `"container"` — **not** `"inventory"`.
 Ember Companion spawns into the area and `bind_companion` then carries it.
- `set_emotion` allows only 7 emotions, so Siren's Lullaby's `"soothed"` would
 have raised. It targets the task-96 affect map instead (`calm`/`peaceful` up,
 `anxious`/`uneasy` down), which is also a better fit for the description.

Two proposals were substituted rather than invented:

- `repair_item` -> `adjust_uses`. **Known limitation:** `adjust_uses` no-ops on
 items with `uses: -1` (it only adjusts when `current_uses >= 0`), so Mending
 Touch is a no-op on indestructible items. Real durability is a schema change —
 filed as the seed of that discussion in task-537.
- `transform_area_theme` -> `adjust_environment` + `append_description`.
- `ward_area` -> `apply_area_status: blessed` (the one existing ward-like status;
 it grants +5 light/tick). The `defense_bonus` and `resistance` halves of the
 proposal were **dropped**, not faked — see task-537.
- `plant_whisper` needed nothing new; it is `llm_respond`.

### Gaps and follow-ups

- **Hearth Ward is the weakest of the fifteen.** The design wanted a defensive
 bonus and cold resistance; what ships is a light and temperature nudge plus the
 `blessed` area status. It is a ward in flavour only.
- **`Ember Companion` overlaps `create_flame`**, which Lyrie already carried:
 both spawn an `everflame_ember`. `create_flame` drops a lit ember in the area;
 Ember Companion does that *and* binds it as a follower. Worth deciding whether
 Create Flame is now redundant.
- **Fluffy's `dialogue` is stored but never spoken.** `create_illusory_companion`
 keeps the lines on the instance and folds `greeting` into the description, but
 there is no `speak`-to-a-character path that reads them. Surfacing the dialogue
 needs a talk handler and is not done.
- **Glimpse of the Lost Path lost its way-hint.** The spec paired `scry` with
 `set_way_hint`; `scry` resolves an *area name* and `set_way_view` needs a
 concrete `way_id`, so there is no "nearest way out" resolution. The spell
 surfaces the memory and attempts the scry (which fails its own `fail_message`).
 `set_way_hint` is in task-537.
- **`reveal_hidden` re-hides to `hidden`.** `_reveal_previous_state` records the
 prior state per node so a future hiding mechanism that preserves state reverts
 correctly, but today `set_hidden` overwrites `current_state` outright, so the
 recorded value is always `hidden`. The bookkeeping is correct but currently
 redundant.
- **`broadcast_emotion` names specific affect keys** (`calm`, `peaceful`,
 `anxious`, `uneasy`) and the emotion vocabulary is slated for a reword pass.
 The handler skips unknown keys per character rather than failing the cast, so
 a rename degrades to "half the effect" rather than "broken spell" — but Siren's
 Lullaby will need revisiting.

### Not done

- The **new-feature proposals table** in the middle of this file is the original
 proposal and is now historical. See task-537 for the reviewed, consolidated
 list of missing effects.
- `Fluffy` is `autonomy: false` / `simple_npc: false`, so it never draws an LLM
 turn and never soaks. That is deliberate — a conjured object is not an actor —
 but it does mean it is a static prop, not a companion you can talk to.
