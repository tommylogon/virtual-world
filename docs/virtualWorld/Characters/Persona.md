---
type: doc
tags: [system/characters, surface/in-editor]
---

# Persona

A character's person - who they are, what they look like, how they speak, what they carry unseen - kept in one place and projected into everything that reads them.

## What it is

Every character has a structured block on their node (`properties["appearance"]`, four sections: identity, appearance, personality, narrative). Prose-only stays the default: no block, normal character. The block is the **state**; the description, the tags, the voice are **projections** of it, refreshed by one explicit Compile. Nothing is stored twice and nothing is guessed.

## What you see

Mind → Persona tab. Folds, not a wall: Identity and Appearance open (who they are, what you'd notice meeting them), Personality and Narrative one click away (the depths). A badge header names them (pronouns · age · species · occupation); short fields sit in a two-column grid; tag fields are chips (fears red-ish, interests teal); intimacy fields fold separately and secrets stay blurred until clicked. Every field carries its reader as a ⓘ tooltip - never inline clutter.

Two buttons ride a sticky bar with a dirty dot, so the payoff is always visible:

- **Save block** stores the sheet. Nothing else moves.
- **Compile** projects it into `base_description` / `personality` + interest/fear tags. Empty prose fills silently; hand prose gets a side-by-side preview and a choice - replace or keep mine. Compile never clobbers quietly.

A Codex entry fold shows the compiled prose live as you type - a dry-run that stores and broadcasts nothing. When the block moves on without the prose (a lens changed an eye, a year passed), the tab says so: *"block changed since the last compile - prose is stale."*

The Appearance fold opens with the 🩺 body doll: the equipment paperdoll
figure in navigate mode (one template, two readers - Inventory equips
through it, Persona reads through it). Clicking a slot shows that
bodypart's live status (sensitivity, injury, coverage - the same data as
the 🩺 modal) beside what the sheet says about it (linked fields,
markings), with a ⤴ jump to each real input - plus a sensitivity slider
per region, writing the authorable baseline (`PUT /body`). Hurt slots
glow red, hot ones warm, the selection rings blue. Areas with no schema
field say so honestly instead of inventing one. Injury is never editable
here: wounds are sim state owned by combat and medicine, and a form must
not bypass them.

## How it works

- **One block.** Identity, appearance, personality, narrative nested under a single node key. No parallel blob, no second store. A character with no block is prose-only, not broken.
- **Explicit compile.** `POST /api/players/<name>/record/compile` returns the projection; `force: true` (or `compile: true` on PUT) applies it. Preview-before-clobber is the rule, not a courtesy.
- **Secrets never compile.** A secret in prose is a leak. Secrets live in the record for the Mind panel and the known system, and stay out of every projection.
- **Growth is the feature.** `set_persona_field` / `add_persona_id` / `remove_persona_id` / `advance_age` change any field at runtime through ordinary trigger effects - a lens item, a tattoo kit, a passing year. Tag mirrors (`fear_tags`, `interest_tags`) update additively, so a tag from another source is never silently dropped.
- **Every field names its reader.** `mbti` / `alignment` / `media` are absent because nothing reads them. A field nobody reads is a field that rots - it doesn't ship. The full map is served by `GET /record` as `hints`, so the tab and the engine can never disagree about what exists.
- **Birthday is canonical (`dd.mm.yyyy`) and gates earliest memories.** `identity.birthday` validates and normalizes to `dd.mm.yyyy` (`01..31` day, `01..12` month, `0001..9999` year). `engine/lifecycle.py:ensure_birth_tick` reads `identity.birthday` and `identity.age` to resolve `Player.birth_tick`, which both the Persona lifecycle and the Memory Weaver / memory routes enforce as the earliest valid tick for any character memory.

## Usability bar

Nothing here is decoration. A Persona field must be **reachable** (editable in the tab), **read** (some engine path consumes it - prompts, fear, affect, dress, lifecycle), and **round-trippable** (save, reload, identical). `exists ≠ wired`: a schema entry with no consumer is a draft, not a feature, and the tests enforce it - every schema field must render or project somewhere, and every field must carry a consumer hint.

## Where it lives

- `engine/character_appearance.py` - schema, validators, `compile_persona`, mutators
- `engine/effect_handlers/persona.py` - the four growth effects
- `engine/pronouns.py` - explicit `identity.pronouns` first, tags fallback
- `routes/player_ops.py` - `GET`/`PUT /record`, `POST /record/compile`
 - `static/js/inspector/mind-view.ts` - the Persona tab
   (`InspectorPaperdoll.AREA_TO_REGIONS` in `paperdoll-view.ts` is the
   region map the body navigator reads - one map, two readers)
- Tests: `tests/test_character_appearance.py`, `tests/test_persona_growth.py`

## Personality field map

Every personality field names its reader. Id-list fields hold tag slugs
(`^[a-z0-9][a-z0-9_-]*$`); prose fields hold free text or structured groups.

| Field | Kind | Consumer |
|-------|------|----------|
| likes | id-list | gifts and dialogue targeting |
| dislikes | id-list | gifts and dialogue targeting |
| fears | id-list | `engine.fear` fear_tags |
| interests | id-list | attention / interest_tags |
| kinks | id-list | `affect_for_stimulus` -> arousal |
| turn_ons | id-list | `affect_for_stimulus` -> arousal (WorldGraph names) |
| turn_offs | id-list | `affect_for_stimulus` -> disgust / negative arousal |
| traumas | id-list | fear_tags + frightened condition; backstory wounds |
| boundaries | id-list | consent gate for intimacy prompts |
| traits | id-list | personality traits (tag slugs) |
| aspirations | id-list | goals / plans projection (tag slugs) |
| quirks | id-list | prompt voice colour (tag slugs) |
| habits | id-list | background behaviour (tag slugs) |
| speech_pattern | group (prose) | prompt voice (style / dialect / catchphrases) |
| experience | text (prose) | intimacy prompt context (WorldGraph experience) |

**Media is not identity.** Media (movies, games, books, music) is a prose list
under `narrative` that feeds memory / knowledge generation - lorebook entries and
memory records - not identity, not GIMP, not MOSIAC.

**Id-list discipline:** display names are rejected. `likes` holds
`monster_energy`, not `"Monster energy drink"`. The compile fails closed
on unknown ids - it never guesses.

## See also

- [[Characters Overview]]
- [[Traits System]]
- [[Emotion & Affect System]]
- [[Inspector Panels]]

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` - relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** - [[Activities & States]], [[Background Simulation]], [[Character Images & Expression Packs]], [[Characters Overview]], [[Emotion & Affect System]], [[GIMP]]

<!-- connected:end -->
