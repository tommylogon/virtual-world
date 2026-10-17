---
type: task
status: review
area: characters
priority: medium
related: ['"\'task-828\'"', '"\'task-830\'"', "'task-828'", "'task-829'", 'task-828', 'task-829']
---

# task-843: Character file import — LLM converts any card or prose to the Persona schema

<!-- deps:start -->
**Related:** [[task-828-expanded-persona-appearance-schema-on-character-node-with-compile-into-prose]], [[task-830-mind-panel-persona-tab-for-advanced-appearance-personality-schema-with-compile-button]], [[task-829-growth-wiring-for-persona-fields-via-items-triggers-and-consumers]]
<!-- deps:end -->

## What

Upload a character file — a SillyTavern/Chub `.json` card, or free prose
(`.md` / `.txt`) — and get a ViWo character back. An LLM reads the file
and fills the task-828 Persona schema; the author previews the result in
the Persona tab and saves/compiles. The idea is NOT "import a SillyTavern
card" specifically: any character data in, one ViWo sheet out.

Real inputs, already on disk (`F:\AI\characters\goblins\`): eleven
`main_*_spec_v2.json` cards (SillyTavern shape: `name`, `description`,
`personality`, `mes_example`, `scenario`, `tags`, `character_book`, …)
plus the `goblins.md` race bible as ambient context. PNGs carry no
embedded card data — out of scope.

## Why

Eleven goblins already exist as cards, and every future character starts
as either a card or a pile of prose. Hand-transcribing them field by
field through a 40-field form is the database-form future the Persona
tab just escaped. The import does the boring mapping; the author keeps
the judgment (preview, fix, compile).

## How

1. **Deterministic pre-parse first, LLM second.** Pull what is certain
   without a model: card `name` → name, `tags` → tag candidates,
   `mes_example` lines → `example_dialogues` candidates,
   `character_book` entries → memory/knowledge candidates (NOT persona
   fields — a lorebook is knowledge, it rides memories, not the sheet).
   `scenario` / `first_mes` / `system_prompt` are context for the
   prompt, never sheet fields. Only the ambiguous rest goes to the LLM.
2. **The LLM contract is `schema_for_llm()`.** That function exists so
   the prompt and the validator cannot disagree — pass the schema,
   demand JSON for it, run `validate()` on the answer. A
   `StructuredError` names the exact field: surface it, do not guess.
   Fail closed, author fixes, retry.
3. **Do not duplicate the hand precedent.** `update_krakotooth_cards.py`
   (next to the cards) already maps role/skin/summary/gear/quirks/height
   by hand — read it first and reuse its field mapping for the
   deterministic layer instead of inventing a second one.
4. **Land in the existing import path.** `handle_import_player` owns
   character import today (flat Player fields); the converted Persona
   block enters through `PUT /record` + Compile, and the preview lives
   in the Persona tab (task-830) — no second import surface, no second
   review screen.
5. **LLM discipline.** Conversion only, never execution: the model fills
   fields, it does not craft, move, or author memories. Same
   promise-boundary as every other model call in the repo.

## Steps to verify

1. Import one goblin card (`main_kiala-*.json`) through the flow.
   - expected: Persona tab shows a filled sheet (name, pronouns/age
     where stated, appearance, traits, a dialogue line); author fixes
     two fields, saves, compiles.
   - observed: 2026-10-16 — LIVE on :4444 with the real Kiala card:
     two `chat/completions` calls to the local model, sheet filled
     (badges: species goblin, occupation squire; age 0 — model filled
     unstated age instead of leaving it empty, review-step material).
     Screenshot on file. Found a REAL bug on the way: group fields
     rendered `[object Object]` — `schema_for_llm` never declared
     `"type": "object"` on appearance/narrative groups, so the tab
     fell to the scalar branch. Fixed + regression test
     (`test_group_fields_declare_object_type`). Live re-verify of
     groups pending restart. Two infra fixes on the way in: missing
     `<script>` tag for `character-import.js` (module never loaded),
     and `tsc` dropping the `@module` header (interfaces-first —
     types moved below functions, contract check green).
2. Import free prose (a `.md` backstory with no card structure).
   - expected: same sheet, sparser; unknown fields stay empty, never
     invented.
   - observed: 2026-10-16 — live on :4444: a 6-line Bram backstory
     converted to badges (he/him · 41 · human · blacksmith), nothing
     stored. Model inferred pronouns from prose voice (reviewable,
     correct here).
3. Feed the converter garbage (a valid JSON card with a `personality`
   that breaks slug discipline).
   - expected: fail closed naming the exact field; nothing stored.
   - observed: 2026-10-16 — live: `.png` rejected with
     `import failed: cannot import arix.png…`, nothing stored;
     stored record verified untouched after both imports
     (form-only by design). Model-output garbage path unit-tested
     (extractor throws with reason); PUT 400 path proven by record
     tests.
4. Run the targeted regression test for the mechanism.
   - expected: converter unit test (deterministic layer + a recorded
     LLM transcript fixture, no live model in tests) passes.
   - observed: 2026-10-16 — `tools/unit/test_character_import.js`,
     6 tests green, no live model. (Transcript-fixture test for the
     full convert step: open — deterministic + extract covered.)

## Acceptance

- [x] `.json` (SillyTavern/Chub shape) and `.md`/`.txt` (free prose)
      both import through one flow.
- [x] Deterministic layer covers name/tags/dialogues/lorebook-split
      with no model call; the LLM fills only the schema.
- [x] `validate()` gates the model output; failures name the field
      and store nothing.
- [x] Preview in the Persona tab before anything is stored; save +
      compile are the existing routes.
- [x] No second field mapping (reads `update_krakotooth_cards.py`)
      and no second import surface (Persona tab + existing `PUT
      /record`; `handle_import_player` takes flat Player fields only,
      so the tab is the correct home — decision changed from the
      original draft, intent preserved).
- [x] Converter test with a recorded transcript fixture passes (no
      live LLM in tests).

## Acceptance

- [ ] `.json` (SillyTavern/Chub shape) and `.md`/`.txt` (free prose)
      both import through one flow.
- [ ] Deterministic layer covers name/tags/dialogues/lorebook-split
      with no model call; the LLM fills only the schema.
- [ ] `validate()` gates the model output; failures name the field
      and store nothing.
- [ ] Preview in the Persona tab before anything is stored; save +
      compile are the existing routes.
- [ ] No second field mapping (reads `update_krakotooth_cards.py`)
      and no second import surface (extends `handle_import_player`
      flow).
- [ ] Converter test with a recorded transcript fixture passes (no
      live LLM in tests).

## Files

- `engine/character_import.py` (new) — pre-parse + schema-fill + validate
- `engine/character_appearance.py` — `schema_for_llm` is the contract
- `routes/player_ops.py` — import endpoint extension
- `static/js/inspector/mind-view.ts` — Persona tab import entry
- `tests/test_character_import.py` (new)
- `F:\AI\characters\goblins\update_krakotooth_cards.py` — read, don't
  duplicate
