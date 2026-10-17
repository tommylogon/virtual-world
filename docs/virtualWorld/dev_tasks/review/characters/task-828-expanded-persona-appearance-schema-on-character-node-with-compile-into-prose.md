---
type: task
status: review
area: characters
priority: high
related: ['"\'task-507\'"', '"\'task-733\'"', '"\'task-830\'"', '"\'task-843\'"', '"\'task-844\'"', "'task-829'", "'task-843'", 'task-829', 'task-843']
wiki: "[[Feature Map]]"
---

# task-828: Expanded persona-appearance schema on character node with compile into prose

**Filed:** 2026-10-15
**Related:** task-733

<!-- deps:start -->
**Related:** [[task-507-structured-appearance-personality-fields-for-characters-optional-llm-fillable]], [[task-733-character-sheet-a-full-page-worldgraph-style-person-form-that-compiles-into-viwo-primitives]], [[task-830-mind-panel-persona-tab-for-advanced-appearance-personality-schema-with-compile-button]], [[task-843-character-file-import-llm-converts-any-card-or-prose-to-the-persona-schema]], [[task-844-persona-tab-character-sheet-pass-grid-chips-codex-preview]], [[task-829-growth-wiring-for-persona-fields-via-items-triggers-and-consumers]]
<!-- deps:end -->

## What

Expand the task-507 curated slice into the full WorldGraph-flavoured
persona/appearance schema, still stored as ONE block on the character
graph node (`properties["appearance"]`), with the new fields nested
UNDER `appearance` and `personality`, and add one explicit **compile**
step that renders the new fields into the prose the sim already reads
(`base_description` / `description` / `personality`).

New fields (all optional, prose-only stays the default):

- identity: `pronouns` (explicit she/he/they/xe… — replaces the
  female-tag hint), `age` (authored years; birth-tick clock is task-735),
  `species` mirror, `gender`, `occupation`, `sexuality`/`orientation`
- appearance: `overview`, `face{shape,features,makeup}`,
  `body{chest,waist,hips,legs,butt,modifications[]}` (tattoo, scar,
  piercing, prosthetic), `voice{pitch,accent,mannerisms}`, `scent`,
  `style{clothing[],accessories[],footwear[]}`,
  `eyes{color,shape,special}` (lenses change color),
  `hair{color,length,style,accessories[]}` (grows / cut),
  `skin{tone,condition,distinguishing_features[]}`
- personality: `traits[]` (prose tags), `aspirations[]`, `quirks[]`,
  `habits[]`, `speech_pattern{style,dialect,catchphrases[]}`,
  `interests[]`, `turn_ons[]`/`turn_offs[]` (keep id discipline),
  `traumas[]`, `boundaries[]`, `experience`
- narrative: `biography{early_life,adulthood,current_situation}`,
  `secrets{deepest_secret,hidden_facts[],known_by[]}`,
  `example_dialogues[]`, `role_in_town`, `arc`

`mbti` / `alignment` / `media` stay OUT — no consumer.

## Why

task-507 proved the slice; task-733 wants the full sheet compiled into
ViWo primitives. The user decision: new fields live UNDER appearance
and personality on the node (no parallel blob, no second store), and a
button compiles them into description / appearance / personality prose.
And the question is not what works today but what must change so every
field is growable: age → old age / child→adult, lenses → eye color,
hair → grow/cut, tattoo given, leg → prosthetic, kinks/turnoffs/trauma/
interests/likes/dislikes/fears addable and removable so characters
become more than they started.

## How

- `engine/character_appearance.py`: extend `APPEARANCE_FIELDS` /
  `PERSONALITY_FIELDS` (+ `IDENTITY_FIELDS`, `NARRATIVE_FIELDS`),
  validators, `compile_persona(node)` → `{base_description,
  description, personality, interest_tags, fear_tags, traits}`.
  Compile is explicit (button + PUT `record` with `compile:true`),
  never silent, never clobbers hand prose unless forced.
- `routes/player_ops.py` + `routes/players.py`: `PUT record` accepts
  `compile:true`; new `POST /record/compile` returns the projection.
- Consumers: pronouns → `engine/pronouns.py` (explicit field first,
  tags fallback); age → task-735 clock; sexuality/dialogue/secrets →
  prompt context; turn_ons/offs → affect (already); fears →
  fear_tags; likes/dislikes/interests → interest_tags; traumas →
  fear_tags + conditions; modifications → prose + equipment prose.
- Tests: `tests/test_character_appearance.py` extended — every new
  field renders or projects somewhere; no dead fields.

## Steps to verify

1. Author a scratch character with pronouns, age, a tattoo, a kink,
   a trauma, a secret, a dialogue line. Save, reload.
    - expected: form restores; node holds ONE `appearance` block; no
      parallel blob.
    - observed: 2026-10-15 — engine round-trip proven in
      `tests/test_character_appearance.py::TestExpandedSchema` (RICH
      fixture covers all of the above; `validate`/`set_record`/`get_record`
      preserve ONE block). Browser form is task-830's Persona tab.
2. Press Compile.
    - expected: `base_description`/`personality` gain the new prose;
      interest/fear tags, traits projected; hand prose kept unless
      forced.
    - observed: 2026-10-15 — proven via `POST /record/compile` +
      `PUT record {compile:true}` (`TestCompileRoutes`, 5 tests):
      projection applies to empty prose, `needs_confirm` + preview over
      hand prose, `force:true` applies. `player.traits` dict untouched
      (mechanical traits, not prose).
3. Run the targeted regression test for the mechanism.
    - expected: `python -m pytest tests/test_character_appearance.py`
      passes.
    - observed: 2026-10-15 — 76 passed (59 existing + 17 new/extended).
      The 2 obsolete task-507 pins were updated to the 828 contract.
4. Live: open Mind → Persona, edit one appearance + one personality
   field, Compile, reload, inspect `/api/state` + prompt.
    - expected: only the projected primitives change; runtime memory
      intact.
    - observed: TODO — tab live-verified rendering (task-830); compile
      round-trip pending server restart (backend serves new routes,
      running server predates `player_ops.py` reload).

## Acceptance

- [x] New WorldGraph-flavoured fields exist UNDER `appearance` /
  `personality` on the node; prose-only still default.
- [x] One explicit compile renders into `base_description` /
  `description` / `personality` + tags/traits; no silent clobber.
- [x] `pronouns`/`age`/`sexuality` readable by prompts/time.
  (`pronouns_for` explicit-first; `lifecycle.status()` — age, stage,
  lifespan — served on `GET /record`; sexuality/dialogues in compile
  prose. 735 clock landed.)
- [x] Every new field names its consumer; mbti/alignment/media absent.
  (`CONSUMER_HINTS` + `test_every_field_names_its_consumer`.)
- [x] `tests/test_character_appearance.py` extended and passing.

## Acceptance

- [ ] New WorldGraph-flavoured fields exist UNDER `appearance` /
  `personality` on the node; prose-only still default.
- [ ] One explicit compile renders into `base_description` /
  `description` / `personality` + tags/traits; no silent clobber.
- [ ] `pronouns`/`age`/`sexuality` readable by prompts/time.
- [ ] Every new field names its consumer; mbti/alignment/media absent.
- [ ] `tests/test_character_appearance.py` extended and passing.

## Files

- `engine/character_appearance.py`
- `routes/player_ops.py`, `routes/players.py`
- `tests/test_character_appearance.py`
- `engine/pronouns.py` (explicit field first)

## Why

TODO

## How

TODO

## Browser UI and intended live verification

Intended UI home: TODO — name the page, panel, tab, or control where this behavior belongs. If no browser UI is appropriate, write 'Not applicable' here, explain why below, and give an observable alternative.

Current availability: TODO — for example, planned/not implemented, present but not live-checked, or live-checked with date and evidence.

Live steps when available:
1. TODO — describe how to reach the surface and the interaction to perform.
   - expected: TODO — describe what the user can see or do.

Why no browser UI: (only when Intended UI home is Not applicable) TODO — explain why browser interaction is not appropriate.

Alternative verification steps: (only when Intended UI home is Not applicable)
1. TODO — describe an observable alternative.
   - expected: TODO — describe the result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
