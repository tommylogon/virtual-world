---
type: task
status: todo
area: characters
priority: medium
related: ['"\'task-507\'"', '"\'task-828\'"', '"\'task-830\'"', '"\'task-844\'"', '\'"\\'task-507\\'"\'', '\'"\\'task-828\\'"\'', '\'"\\'task-829\\'"\'', '\'"\\'task-830\\'"\'', '\'"\\'task-844\\'"\'', '\'"\\'task-849\\'"\'', "'task-507'", "'task-828'", "'task-830'", "'task-844'", 'task-850']
blocked_by: [task-457]
---

# task-733: Character sheet: a full-page WorldGraph-style person form that compiles into ViWo primitives

**Filed:** 2026-10-08
**Related:** task-507, task-673, task-675, task-690, task-724, task-404, task-447

<!-- deps:start -->
**Blocked by:** [[task-457-character-nodes-are-the-canonical-character-record-human-agent-simple-npc]]
**Related:** [[task-507-structured-appearance-personality-fields-for-characters-optional-llm-fillable]], [[task-828-expanded-persona-appearance-schema-on-character-node-with-compile-into-prose]], [[task-830-mind-panel-persona-tab-for-advanced-appearance-personality-schema-with-compile-button]], [[task-844-persona-tab-character-sheet-pass-grid-chips-codex-preview]], [[task-829-growth-wiring-for-persona-fields-via-items-triggers-and-consumers]], [[task-849-narrative-authoring-should-feed-memories-and-goals-not-duplicate-them]], [[task-850-identity-additions-mbti-alignment-birthday-each-with-a-named-reader]]
<!-- deps:end -->

## What

Give a character one rich authoring surface (a full-page editor over the WorldGraph person schema shape) that projects into the primitives the simulation already reads: personality prose/structured, appearance/base_description, interest_tags/fear_tags, traits, skills, memories, known, relationships. Author once as a structured sheet; compile it into the fields the engine and prompts consume, so the richer form is usable data rather than dead authoring metadata.

## Source model

`F:\AI\code\graph-editor` (WorldGraph) stores a deeply nested **person schema**
(`js/storage.js:203-299`):

```
appearance            overview height build skin hair eyes face body genitalia style scent voice
personality           traits mbti alignment likes dislikes fears aspirations quirks habits speech_pattern
biography             early_life adulthood current_situation
relationships         family{parents,siblings,children,other} connections friends enemies rivals mentors protégés
secrets               deepest_secret hidden_facts known_by
capabilities          skills languages weaknesses
kinks_and_sexuality   orientation experience preferences turn_ons turn_offs curiosities boundaries
narrative             arc potential_storylines role_in_town
example_dialogues
media                 favorite_movies favorite_music favorite_books
```

task-507 already aligned a curated subset to ViWo and reused the WorldGraph names
where they overlap ("so authored persons import cleanly"), and deliberately
excluded `media` / `mbti` / `alignment` (`engine/character_appearance.py` docstring).

## The projection — every form field has exactly one ViWo primitive

| WorldGraph field | ViWo primitive | consumer today |
|---|---|---|
| `appearance.*` | structured `appearance` block → rendered `base_description`/`description` | task-507 |
| `personality.traits`, `quirks`, `habits`, `aspirations`, `speech_pattern` | structured `personality` block → prose `personality` | prompt voice |
| `personality.likes` / `dislikes` | `interest_tags` | gift/dialogue targeting |
| `personality.fears` | `fear_tags` | `engine/fear` |
| `kinks_and_sexuality.turn_ons` / `turn_offs` | structured `personality.kinks`/`turn_offs` | affect map (652) |
| `capabilities.skills`, `languages`, `weaknesses` | `skills`, `traits` | skills/traits |
| `biography.*` | **memories** with `source: manual` | task-404 |
| `secrets.*`, `known_by` | `known`, knowledge | task-366 |
| `relationships.*` | `relationships` (label + closeness), `rel:` memories | task-447 / 724 |
| `narrative.role_in_town`, `arc` | plans/goals | task-702/704 |
| `example_dialogues`, `voice`, `scent` | prompt voice / perception | prompts |
| `mbti`, `alignment`, `media` | **none — left out** | — |

## New fields needed

Two of the fields the prose work depends on do **not exist** on a ViWo character:

- **`pronouns`** — for prose generation ("she/they/he"). Today only the `female`
  tag hints at it. Add a field; prompts read it.
- **`age`** (and `species` already exists) — for time-related growth/aging. Add a
  field; an aging mechanic is separate (compare task-537 `age_effect`).
- `sexuality`/`orientation` is also absent (only `kinks`/`turn_offs` exist).

## How

- **Author once, on the node.** The rich `sheet` is authored definition on the
  character node (like task-507's structured block, and per task-724's decision
  that authored definition lives on the node). A **projector** compiles it into
  the primitives: prose (`personality`, `base_description`), id lists
  (`interest_tags`, `fear_tags`), `traits`/`skills`, and authored content
  (`memories`, `known`, `relationships`).
- **One source of truth.** Either the sheet is authored and the primitives are
  derived (one-way — editing the sheet re-projects), or the primitives are
  authored directly and the sheet is just a form over the subset. Do **not** let
  both be independently editable or they drift (the task-724 failure). Recommendation:
  structured sheet is authoritative where present; prose/id lists are a rendered
  projection; memories/known/relationships are authored **writes** the compile
  step performs once.
- **UI**: a full-page editor. The host frame is **task-673** (EntityEditor) and
  the character layout is **task-675**; this task is the *rich form + projector*,
  not another frame. "Fill the full thing, or free-form into `personality`" — both
  modes must work (task-507's requirement).
- Same endpoints (`updateNode`/`updateCharacter`); no new persistence model, no
  second copy in a save.

## Phases

1. `sheet` model + projector for the **already-mechanic-backed** fields
   (appearance, personality, likes/dislikes/fears, traits, skills) — extends 507.
2. Add `pronouns` + `age` fields and wire them into prose/prompts.
3. Compile `biography → memories(source=manual)` (shares task-404).
4. Compile `secrets → known/knowledge` (task-366) and `narrative → plans` (702/704).

## Open questions

- Does `age` ever *change* (aging over sim time) or is it authoring-only? Decides
  whether it is a sheet field or a runtime field with a mechanic.
- `pronouns` as a field vs derived from `tags`/`gender`. Deriving is fragile;
  a field is explicit.
- Where `mbti`/`alignment` go: nowhere (507's call) unless a mechanic appears.

## Acceptance

- [ ] A character can be authored from the rich form; the projector writes
      `personality`, `base_description`, `interest_tags`, `fear_tags`, `traits`,
      `skills` and an editor can see them.
- [ ] Free-form-only characters (prose) still work; the sheet is optional.
- [ ] No field is added without a consumer (mbti/alignment/media stay out).
- [ ] `pronouns`/`age` exist and are read where prose/time needs them.
- [ ] Live: author a character from the sheet, save, reload, prompt contains the
      projected personality + appearance; `npm run build:ts` and the unit runner
      pass.

## Why

TODO

## Steps to verify

1. Create a scratch character from the character sheet and enter distinct
   values for pronouns, age, appearance, personality, interests, fears, traits,
   and skills. Save and reopen the character.
   - expected: the form restores the authored values and projects them into the
     existing ViWo fields listed in the projection table; it does not create a
     parallel unconsumed WorldGraph blob.
2. Inspect the character's saved definition and runtime prompt after reload.
   - expected: personality and appearance are present in the prompt, while
     interest/fear tags, traits, skills, and memories remain in their existing
     consumers. `mbti`, `alignment`, and `media` are not added as fields.
3. Load a free-form-only character that has no structured sheet data.
   - expected: its existing prose still loads and drives the prompt without
     requiring a visit to the sheet or a migration.
4. Edit one appearance field and one personality field, save, and reload.
   - expected: only the corresponding projected primitives change; unrelated
     authored fields and runtime memory remain intact.

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: select a character → Character Inspector → Bio → open the
full-page **Character Sheet** authoring form. This is the proposed entry point
for one coherent authoring surface; it writes to the existing character
definition and the primitives the simulation already consumes.

Current availability: the full-page structured sheet is planned. Existing
character Bio and advanced fields are separate surfaces; this card does not
claim the WorldGraph-style form or projection workflow is available today.

Live steps when available:
1. Open a character's Bio in the Inspector and open **Character Sheet**. Enter
   `they` for pronouns, `31` for age, a distinctive appearance detail, one
   personality habit, one interest tag, one fear tag, one trait, and one skill.
   Save the character and close the sheet.
   - expected: the save succeeds and the Inspector shows the character's
     updated authored definition.
2. Reopen the sheet and reload the scenario. Compare the restored form values
   with the character node's `properties` and the projected fields in
   `/api/state`.
   - expected: the same values survive reload in `personality`,
     `base_description`/`description`, `interest_tags`, `fear_tags`, `traits`,
     and `skills`; no duplicate sheet-only record is persisted.
3. Open the character's prompt preview or run a character turn and inspect the
   generated prompt context.
   - expected: the distinctive personality and appearance are available to the
     prompt. The character's existing prose-only authoring still works for a
     second character with no sheet data.
4. Inspect the sheet's available fields.
   - expected: every offered field has a ViWo consumer; `mbti`, `alignment`,
     and `media` are not presented as persisted character mechanics.

These steps define the intended authoring path and round-trip behavior; the
full-page sheet remains planned.

This section is not a claim that planned UI exists or works today.
