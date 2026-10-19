---
type: task
status: review
area: characters
priority: high
related: ['task-828', 'task-849', 'task-843']
wiki: "[[Feature Map]]"
---

# task-828: Growth wiring for persona fields via items triggers and consumers

**Filed:** 2026-10-15
**Related:** task-733

<!-- deps:start -->
**Related:** [[task-828-expanded-persona-appearance-schema-on-character-node-with-compile-into-prose]], [[task-849-narrative-authoring-should-feed-memories-and-goals-not-duplicate-them]], [[task-843-character-file-import-llm-converts-any-card-or-prose-to-the-persona-schema]]
<!-- deps:end -->

## What

Wire every 828 field so it can CHANGE at runtime - via items,
triggers, and the engine - so a character grows: age advances to old
age / child→adult, lenses change eye color, hair grows and is cut,
tattoos/scars/piercings are given, a leg becomes a prosthetic, and
kinks / turn_offs / traumas / interests / likes / dislikes / fears
are added AND removed. All still ONE block on the node; the block is
the state, the compile is the prose.

## Why

The ask is explicit: the question is not what works today but what
must change to take full use of the new fields. A static sheet is
dead authoring. Growth is the feature: characters become more than
they started.

## How

New trigger effects (all target a character node, all mirror to the
node block AND re-compile or mark prose stale):

- `set_persona_field {path, value}` - generic: `appearance.hair.color`,
  `personality.traumas[]`, `identity.age`, `narrative.secrets…`.
  One handler, dotted path, so lenses/haircut/tattoo/prosthetic need
  no bespoke effect each.
- `add_persona_id {field, id}` / `remove_persona_id {field, id}` -
  for every id-list: likes, dislikes, fears, interests, kinks,
  turn_ons/offs, traumas, boundaries, quirks, habits, aspirations.
  fear/interest adds ALSO mirror to `Player.fear_tags` /
  `interest_tags` so `engine/fear.py` + attention read them today.
- `advance_age {years}` - bumps authored age; when task-735's clock
  lands it becomes elapsed-derived, this stays as author override.
- Item hooks: `on_use` / `on_use_on` carry these effects, so lenses,
  scissors, tattoo kit, prosthetic leg, diary (secret), letter
  (dialogue example) are content, not code.
- Consumers: sexuality/orientation + example_dialogues + voice/scent
  → prompt context (`engine/dressing.py`, `engine/narration.py`);
  secrets/known_by → `known`; age → life-stage gate (735);
  traumas → fear_tags + `frightened`; turn_ons/offs → affect
  (already); modifications → `base_description` via compile.

## Steps to verify

1. Give a character lenses via an item `on_use` with
   `set_persona_field appearance.eyes.color`.
    - expected: node block changes; after Compile the prose shows it.
    - observed: 2026-10-15 - mechanism proven end to end at the
      dispatch layer (`test_lenses_change_eye_color_through_an_effect`
      runs `world.effects.execute("set_persona_field", ...)` and the
      prose recompiles with the change). `on_use` dispatches through
      the same trigger registry (`effects.py`), so a lens item carrying
      this effect needs no new code; authoring one is content work.
2. Add + remove a kink, a fear, a trauma via trigger effects.
    - expected: lists change; fear/interest mirror on Player; affect
      + fear engine read the new value.
    - observed: 2026-10-15 - proven (`TestEffectDispatch` + round-trip
      test, 13 tests in `tests/test_persona_growth.py`). Mirroring is
      additive-only on `set` so foreign tags survive.
3. Advance age across a life-stage threshold (scratch clock).
    - expected: stage changes; old-age death path reachable (735).
    - observed: 2026-10-15 - `advance_age` bumps authored age and shifts birth tick (proven in `test_advance_age_moves_the_clock_too`); threshold gate wired via task-735.
4. Run the targeted regression test.
    - expected: new `tests/test_persona_growth.py` passes.
    - observed: 2026-10-15 - 13 passed.

## Acceptance

- [x] `set_persona_field` / `add_persona_id` / `remove_persona_id` /
  `advance_age` exist, target characters, persist on the node.
- [x] Lenses / haircut / tattoo / prosthetic achievable as content.
  (`data/library/items/template_set_persona_field.json` + `on_use`
  trigger + `test_template_item_grows_through_on_use`: use the item,
  the sheet changes. A lens/scissors/kit item is authoring from here.)
- [x] Every id-list growable both directions; fear/interest mirror live.
- [x] Sexuality, dialogue examples, secrets, voice/scent reach prompts;
  age reaches the lifecycle gate. (Sexuality/dialogues/voice/scent
  proven in compile prose; secrets DELIBERATELY excluded from prose -
  served via GET /record for the Mind panel + `known` system;
  `advance_age` now shifts the 735 birth tick too - proven in
  `test_advance_age_moves_the_clock_too`.)
- [x] `tests/test_persona_growth.py` proves add/remove/compile round-trip.

## Acceptance

- [ ] `set_persona_field` / `add_persona_id` / `remove_persona_id` /
  `advance_age` exist, target characters, persist on the node.
- [ ] Lenses / haircut / tattoo / prosthetic achievable as content.
- [ ] Every id-list growable both directions; fear/interest mirror live.
- [ ] Sexuality, dialogue examples, secrets, voice/scent reach prompts;
  age reaches the lifecycle gate.
- [ ] `tests/test_persona_growth.py` proves add/remove/compile round-trip.

## Files

- `engine/effect_handlers/persona.py` (new)
- `engine/triggers/constants.py` (`EFFECT_TYPES` + `SAFE_EFFECT_TYPES`)
- `engine/effects.py` (registry)
- `engine/character_appearance.py` (mutators + compile)
- `engine/dressing.py`, `engine/narration.py` (prompt consumers)
- `tests/test_persona_growth.py` (new)
