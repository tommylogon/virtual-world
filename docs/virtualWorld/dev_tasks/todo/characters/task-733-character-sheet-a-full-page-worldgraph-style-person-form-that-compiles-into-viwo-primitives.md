---
type: task
status: todo
area: characters
priority: medium
---

# task-733: Character sheet: a full-page WorldGraph-style person form that compiles into ViWo primitives

**Filed:** 2026-10-08
**Related:** task-507, task-673, task-675, task-690, task-724, task-404, task-447

## Goal

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

## Design

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
