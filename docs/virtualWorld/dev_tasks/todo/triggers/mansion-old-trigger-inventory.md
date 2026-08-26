# Mansion — old-style trigger inventory

Extracted from `virtual_world/data/scenarios/mansion.json` on 2026-08-09.

> The same 64 old trigger pairs exist **identically** in `data/scenarios/mansion2.json` and `data/library/rooms/mansion.json` — one inventory covers all three copies. Convert one, propagate (or re-extract) to the others.

These triggers still use the LEGACY flat format (`effect_type` + `effect_params`) and are **silently dead** in the current engine — `engine/trigger_system.py` only reads `effects[]`, so they fire as empty messages. Convert each to the new format:

```json
"trigger_type": ["on_examine"],
"conditions": {},
"effects": [{"type": "message", "params": {"success_message": "...", "fail_message": ""}}]
```

Total: 64 trigger edges across 53 source nodes. Old effect types seen: `message`, `damage`, `heal`, `spawn_item`. No old trigger has conditions.

> Note: each trigger appears in BOTH the `triggers` edge properties and the `logic_trigger` node properties (duplicated). The edge copy is what the engine reads. When converting, write the new `effects[]` to both, or drop the stale old fields.

---

## flashlight (`inv_Elena Vance_flashlight`)

### 1. `trigger_inv_Elena Vance_flashlight_on_depleted_0` — on_depleted → message

effect_params:
```json
{
  "message": "The flashlight flickers and dies."
}
```

## altar (`item_altar`)

### 1. `trigger_item_altar_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You lift the dusty cloth. The skull-shaped depression is lined with symbols that pulse with a faint, dying light. The runes around the edge read: 'Return what was taken. Free what is bound. Eleanor waits.'"
}
```

## boarded_window (`item_boarded_window`)

### 1. `trigger_item_boarded_window_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "Through a gap in the boards, you can see the garden and the graveyard beyond. Scratched into the wood of one of the boards, faint but legible: 'I'm still here. Help me.'"
}
```

## brass_key (`item_brass_key`)

### 1. `trigger_item_brass_key_on_take_0` — on_take → message

effect_params:
```json
{
  "message": "As you take the key, the temperature drops sharply. A whisper, so faint you might have imagined it: 'Thank you...'"
}
```

## broken_key (`item_broken_key`)

### 1. `trigger_item_broken_key_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "The heat-seal cracks as you examine the joined halves. The key is whole again. It feels powerful — and sad. This key was meant to keep something locked away forever."
}
```

## candle (`item_candle`)

### 1. `trigger_item_candle_on_depleted_3` — on_depleted → message

effect_params:
```json
{
  "message": "The black candle sputters and goes out, its last wisp of smoke curling upward like a question."
}
```

### 2. `trigger_item_candle_on_toggle_off_2` — on_toggle_off → message

effect_params:
```json
{
  "message": "You extinguish the black candle. The room darkens."
}
```

### 3. `trigger_item_candle_on_toggle_on_1` — on_toggle_on → message

effect_params:
```json
{
  "message": "You light the black candle. A strange blue-white flame flickers to life."
}
```

### 4. `trigger_item_candle_on_use_0` — on_use → message

effect_params:
```json
{
  "message": "The black candle burns with a strange blue-white flame. As it burns, the runes carved into the wax seem to writhe. The shadows in the room elongate and dance."
}
```

## child_dress_item (`item_child_dress_item`)

### 1. `trigger_item_child_dress_item_on_take_0` — on_take → message

effect_params:
```json
{
  "message": "As you lift the dress, a lullaby plays faintly from somewhere in the room. It stops when you set the dress down. The dress is cold and damp, as if recently washed but not dried."
}
```

## coat_rack (`item_coat_rack`)

### 1. `trigger_item_coat_rack_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You search the coat pockets and find an old train ticket stub for a journey from London, dated October 31st, 1891. The last train out of Blackwood station. Whoever wore this coat never made it home."
}
```

## crate (`item_crate`)

### 1. `trigger_item_crate_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "Through a gap in the crate's slats, you can see moldy burlap sacks. But something glints beneath them — a bottle of something expensive."
}
```

## crystal_skull (`item_crystal_skull`)

### 1. `trigger_item_crystal_skull_on_drop_3` — on_drop → message

effect_params:
```json
{
  "message": "The skull clatters to the floor but does not break. The whispering stops. The room feels lighter."
}
```

### 2. `trigger_item_crystal_skull_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You peer into the crystal skull's eye sockets. For just a moment, you see a reflection that isn't yours — a young girl with dark hair and sad eyes, standing behind you. You spin around. There's no one there."
}
```

### 3. `trigger_item_crystal_skull_on_take_1` — on_take → damage

effect_params:
```json
{
  "amount": 8,
  "message": "A searing cold shoots up your arm as you lift the skull. Your vision blurs and you feel a splitting headache. The whispers grow louder in your mind.",
  "target": "self"
}
```

### 4. `trigger_item_crystal_skull_on_take_2` — on_take → message

effect_params:
```json
{
  "message": "The room darkens as you lift the skull from its pedestal. The green glow from the walls flickers. A woman's voice whispers clearly: 'Now you've done it. He knows you're here.' The bookcase behind you SLAMS shut with a deafening crack."
}
```

## dead_vine (`item_dead_vine`)

### 1. `trigger_item_dead_vine_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "The vine twitches at your touch. You pull your hand back, startled. Wrapped around the vine's base, almost invisible, is the other half of a broken brass key."
}
```

## doll (`item_doll`)

### 1. `trigger_item_doll_on_drop_1` — on_drop → spawn_item

effect_params:
```json
{
  "description": "A tiny scrap of paper that falls from the doll's hollow arm: 'The skull is in the study. Take it to Mother's grave. She'll know what to do. — E.'",
  "item_id": "item_hidden_note_doll",
  "name": "hidden_note"
}
```

### 2. `trigger_item_doll_on_take_0` — on_take → damage

effect_params:
```json
{
  "amount": 8,
  "message": "A piercing headache lances through your skull as you pick up the doll. You feel a presence — angry, trapped, desperate.",
  "target": "self"
}
```

## family_photo (`item_family_photo`)

### 1. `trigger_item_family_photo_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You hold the photograph closer. The youngest child's face isn't blurred by movement — it's been deliberately scratched out. But beneath the scratches, you can just make out a small, sad face. The name on the back: 'Eleanor the Younger, age 3. Taken October 1890.'"
}
```

## family_plot (`item_family_plot`)

### 1. `trigger_item_family_plot_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You kneel to examine the smallest headstone — Eleanor the Younger's. The earth at its base has settled unevenly, as if something was buried here recently. A small handful of wilted rose petals — from the red rose bush in the garden — are scattered on the ground."
}
```

## fireplace (`item_fireplace`)

### 1. `trigger_item_fireplace_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You search the fireplace thoroughly. Beneath a loose brick at the back of the hearth, you find a small compartment containing a bundle of letters tied with a faded ribbon. They're love letters between Augustus Blackwood and a woman who isn't his wife."
}
```

## flowers (`item_flowers`)

### 1. `trigger_item_flowers_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "The single red rose bush seems out of place in this garden of decay. As you lean closer, you notice a small brass plaque at its base, nearly hidden by thorns: 'For our Eleanor, who loved roses. Gone but never forgotten. — Mother and Father.' This is a grave."
}
```

## fountain (`item_fountain`)

### 1. `trigger_item_fountain_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You peer into the murky water. At the bottom of the fountain basin, half-buried in sediment, lies a small silver crucifix. It must have been thrown in deliberately."
}
```

## ghostly_figure (`item_ghostly_figure`)

### 1. `trigger_item_ghostly_figure_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "Where the figure stood, you find a small, cold spot on the floor. A single white feather lies there, untouched by dust. You pick it up — it's real."
}
```

## glasses_case (`item_glasses_case`)

### 1. `trigger_item_glasses_case_on_take_0` — on_take → spawn_item

effect_params:
```json
{
  "description": "A crumpled note that was stuck to the glasses case: 'Augustus — I've found what you requested. The crystal skull is not a legend. It is in the catacombs beneath Prague. I will bring it to the manor on All Hallows Eve. Your servant, Prof. Aldridge.'",
  "item_id": "item_professors_note",
  "name": "professor's_note"
}
```

## hidden_shelf (`item_hidden_shelf`)

### 1. `trigger_item_hidden_shelf_on_examine_0` — on_examine → spawn_item

effect_params:
```json
{
  "description": "A leather-bound grimoire titled 'Rituals of Binding and Release'. The book falls open to a marked page: 'The Ritual of the Firstborn — To release a spirit bound to an object, the object must be returned to the place of death and the following incantation spoken at the hour of the binding...'",
  "item_id": "item_ritual_book",
  "name": "ritual_book"
}
```

## iron_key (`item_iron_key`)

### 1. `trigger_item_iron_key_on_take_0` — on_take → message

effect_params:
```json
{
  "message": "The key is cold and heavy. It looks like it belongs to the garden door."
}
```

## jewelry_box (`item_jewelry_box`)

### 1. `trigger_item_jewelry_box_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "The jewelry box is locked, but the keyhole is tiny. A key no larger than your thumb would fit — like the one from the foyer vase."
}
```

## key_fragment_2 (`item_key_fragment_2`)

### 1. `trigger_item_key_fragment_2_on_take_0` — on_take → message

effect_params:
```json
{
  "message": "As you pick up the second fragment, both halves grow warm in your hands, as if drawn to each other. They fit together perfectly — the heat-seal is an occult binding, not a physical break."
}
```

## lullaby_box (`item_lullaby_box`)

### 1. `trigger_item_lullaby_box_on_use_0` — on_use → heal

effect_params:
```json
{
  "amount": 5,
  "target": "self"
}
```

### 2. `trigger_item_lullaby_box_on_use_1` — on_use → message

effect_params:
```json
{
  "message": "The lullaby fills the room. For a moment, the cold recedes, and you feel an overwhelming sense of peace — and profound sadness."
}
```

## mirror_bath (`item_mirror_bath`)

### 1. `trigger_item_mirror_bath_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You stare at the mirror, focusing on the fragment that doesn't match your movement. It's not a reflection — it's something behind the mirror, watching you. You see the outline of a small handprint on the other side of the glass."
}
```

## mouse_nest (`item_mouse_nest`)

### 1. `trigger_item_mouse_nest_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "Hidden beneath the mouse nest, you find a small silver locket. It's tarnished but opens with a click. Inside: a miniature portrait of a young woman with sad eyes, and a lock of dark hair."
}
```

## music_box (`item_music_box`)

### 1. `trigger_item_music_box_on_use_0` — on_use → heal

effect_params:
```json
{
  "amount": 10,
  "target": "self"
}
```

### 2. `trigger_item_music_box_on_use_1` — on_use → message

effect_params:
```json
{
  "message": "The music box plays its haunting lullaby. As it plays, the temperature in the room seems to warm slightly. The whispers from the hallway fall silent."
}
```

## plant (`item_plant`)

### 1. `trigger_item_plant_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "As the fern crumbles, you see a small garnet ring buried in the dry soil. It's a woman's ring, delicate and old. The inside is engraved: 'Forever, A.B.'"
}
```

## pocket_watch (`item_pocket_watch`)

### 1. `trigger_item_pocket_watch_on_take_0` — on_take → message

effect_params:
```json
{
  "message": "The watch is ice cold. As you hold it, the second hand twitches once, then begins ticking backward."
}
```

## portrait (`item_portrait`)

### 1. `trigger_item_portrait_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "As you study the portrait, you notice the eyes are painted with an unsettling attention to detail. They seem to follow you. But more importantly — there's a faint line around the frame. It's a door. The portrait is a door."
}
```

## portrait_f665a200 (`item_portrait_f665a200`)

### 1. `trigger_item_portrait_f665a200_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "The crack in the painting seems to form the shape of a '7'. You study Eleanor's face more closely. Her expression is stern, but her eyes hold a deep sadness — and something else. Recognition? As if she knows why you're here."
}
```

## portrait_hall (`item_portrait_hall`)

### 1. `trigger_item_portrait_hall_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You touch the crack in the canvas. Behind the painting, taped to the back, you find a small photograph. It shows Augustus with a woman who is NOT his wife — the same woman from the love letters in the library. They're holding hands. On the back: 'My dearest Margaret. Someday we'll be free.'"
}
```

## railing (`item_railing`)

### 1. `trigger_item_railing_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "The blue silk ribbon tied to the railing is old but well-preserved. It's tied in a complex knot — a lover's knot. Someone stood here, looking out at the garden, waiting for someone who never came."
}
```

## remains (`item_remains`)

### 1. `trigger_item_remains_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You sift through the remains of The Butcher's past victims. The most recent belongings are from the 1990s. This thing has been here longer than the Blackwood family. It was here before the mansion was built."
}
```

## rocking_horse (`item_rocking_horse`)

### 1. `trigger_item_rocking_horse_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "As you approach the rocking horse, it stops moving. Beneath it, scratched into the wooden floor: 'ELLIE WAS HERE' in a child's handwriting. The scratches are fresh."
}
```

## root (`item_root`)

### 1. `trigger_item_root_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You follow the root with your hand. It leads to a corner of the cellar where the earth has been disturbed. Something was buried here. The root grows through the mound like a grave marker."
}
```

## rug (`item_rug`)

### 1. `trigger_item_rug_on_examine_0` — on_examine → message

**ALREADY has new `effects[]`** — old fields are stale leftovers, safe to delete.

effect_params:
```json
{
  "message": "As you lift the rug, you notice faint scratch marks on the marble tile beneath. Something was dragged here recently — and left scratches pointing toward the library."
}
```

## sarcophagus (`item_sarcophagus`)

### 1. `trigger_item_sarcophagus_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You peer inside the sarcophagus. It's empty. But at the bottom, nestled in a corner, lies a single object: a pair of wire-rimmed spectacles, crushed. And a folded letter, yellowed with age."
}
```

## secret_drawer (`item_secret_drawer`)

### 1. `trigger_item_secret_drawer_on_examine_0` — on_examine → spawn_item

effect_params:
```json
{
  "description": "A bundle of letters from Margaret Holloway to James Blackwood. 'Dear James, I know we cannot be together in this house. But I watch for you at the garden gate every evening. Meet me by the oak tree. I have news I can only share in person. — Yours, forever, M.'",
  "item_id": "item_margaret_letters",
  "name": "margaret_letters"
}
```

## stove (`item_stove`)

### 1. `trigger_item_stove_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You open the stove door. Inside, you find a charred fragment of a photograph. It shows a woman in a dark dress — her face has been burned away. On the back, in shaky handwriting: 'Forgive me, Eleanor. I couldn't protect you.'"
}
```

## strange_compass (`item_strange_compass`)

### 1. `trigger_item_strange_compass_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "The needle spins erratically for a moment, then settles pointing directly at the fireplace. When you hold it near the mantel, it vibrates."
}
```

## stuffed_rabbit (`item_stuffed_rabbit`)

### 1. `trigger_item_stuffed_rabbit_on_drop_1` — on_drop → message

effect_params:
```json
{
  "message": "The rabbit lands on the floor with a soft thump. For just a moment, you could swear you heard a child sob."
}
```

### 2. `trigger_item_stuffed_rabbit_on_take_0` — on_take → damage

effect_params:
```json
{
  "amount": 5,
  "message": "A wave of sadness washes over you as you pick up the rabbit. The room temperature drops sharply.",
  "target": "self"
}
```

## table (`item_table`)

### 1. `trigger_item_table_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You count the place settings carefully. Seven. But there are eight chairs. The eighth chair — at the far end of the table — is pushed slightly away from the table, as if an invisible guest is seated there. A dusty plate sits before it, completely clean. No dust on this one."
}
```

## tainted_wine (`item_tainted_wine`)

### 1. `trigger_item_tainted_wine_on_take_0` — on_take → message

effect_params:
```json
{
  "message": "As you lift the bottle, you hear a faint whisper: 'Don't drink that, dear.' The voice sounds like an old woman."
}
```

## tiny_key (`item_tiny_key`)

### 1. `trigger_item_tiny_key_on_take_0` — on_take → message

effect_params:
```json
{
  "message": "The key feels strangely warm in your palm, as if it was recently held."
}
```

## toy_box (`item_toy_box`)

### 1. `trigger_item_toy_box_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "At the very bottom of the toy box, beneath all the broken toys, you find a small music box. It's dented but intact. When you wind it, it plays a haunting, tinny lullaby — the same melody as the one in the nursery."
}
```

## trunk (`item_trunk`)

### 1. `trigger_item_trunk_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You press your ear to the trunk. The tapping stops. Then a voice — a child's whisper, muffled by the wood: 'Let me out. She's not who she says she is.'"
}
```

## tub (`item_tub`)

### 1. `trigger_item_tub_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You lean closer to the tub. Beneath the grimy water, something glints. You reach in — it's cold, colder than the water should be — and pull out a small silver locket. Identical to the one in the pantry, but this one contains a tiny photograph of a woman with sad eyes."
}
```

## unlabeled_vial (`item_unlabeled_vial`)

### 1. `trigger_item_unlabeled_vial_on_use_0` — on_use → heal

effect_params:
```json
{
  "amount": 25,
  "target": "self"
}
```

### 2. `trigger_item_unlabeled_vial_on_use_1` — on_use → message

effect_params:
```json
{
  "message": "The liquid burns going down, but warmth spreads through your body. Your aches fade. Whatever this is, it works."
}
```

## vanity (`item_vanity`)

### 1. `trigger_item_vanity_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You stare at your reflection in the cracked mirror. For just a moment, the reflection isn't you. A woman in a dark Victorian dress stares back, her hand pressed against the glass from the other side. Then your own reflection returns."
}
```

## vase (`item_vase`)

### 1. `trigger_item_vase_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "Inside the vase, you find a tiny key — no larger than your thumb — taped to the inner wall. It's a jewelry box key."
}
```

## watering_can (`item_watering_can`)

### 1. `trigger_item_watering_can_on_take_0` — on_take → spawn_item

effect_params:
```json
{
  "description": "Half of a broken brass key, snapped cleanly in two. The teeth are intricate — this was a finely made key. Without the other half, it's useless.",
  "item_id": "item_key_fragment",
  "name": "key_fragment"
}
```

## wilting_lilies (`item_wilting_lilies`)

### 1. `trigger_item_wilting_lilies_on_examine_0` — on_examine → message

effect_params:
```json
{
  "message": "You pick up the lilies. They're real, still moist at the stems. Beneath them, you find a small card. 'Welcome home, little one. — Mother.' The handwriting is elegant, old-fashioned. Fresh."
}
```
