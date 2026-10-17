---
type: task
status: review
area: ui
priority: medium
related: ["'task-828'", "'task-830'", "'task-847'", "'task-848'", 'task-830', 'task-847', 'task-848']
---

# task-844: Persona tab character-sheet pass — grid, chips, codex preview

<!-- deps:start -->
**Related:** [[task-828-expanded-persona-appearance-schema-on-character-node-with-compile-into-prose]], [[task-830-mind-panel-persona-tab-for-advanced-appearance-personality-schema-with-compile-button]], [[task-847-persona-tab-embedded-body-paperdoll-navigator-for-appearance-schema]], [[task-848-persona-tab-visual-paperdoll-with-inline-body-baseline-editing]]
<!-- deps:end -->

## What

The Persona tab works (save/compile/preview/stale, all live-proven in
task-830) but reads as a database form: one column of uniform inputs.
Make it feel like a character sheet without breaking anything that
works: two-column grid for short fields, badge header, chip inputs for
tag fields, intimacy fold, secrets blur, sticky save bar with dirty
dot, and a live Codex preview of the compiled prose.

## Why

The tab is where authors meet the person. A 40-field wall says
"database"; a sheet with badges, chips, and a live preview of who
they're becoming says "soul". Task-830 shipped the mechanic; this ships
the meeting.

## How

Constraints (non-negotiable, from two rejected mockups):

- **Schema-driven, not hardcoded.** Fields render from `GET /record`
  schema. A hardcoded form rots on the next schema change and already
  broke once (flat inputs for group fields 400 on save).
- **`data-persona-path` bindings intact.** `_collectPersona` reads them;
  chips write through hidden inputs carrying the same paths.
- **No second theme.** The repo dark theme (`var(--bg-card)` etc.)
  stays; game feel comes from layout, type, and focus glow, not a new
  palette or webfont (offline breakage).
- **Folds stay.** Identity/Appearance open, depths folded — verified
  live; restructure inside the folds, not the navigation.

Pieces, in impact order:

1. Grid: short scalars 2-col; textareas/groups full width; 13px
   inputs, 11px uppercase labels, serif display name.
2. Badge header: name + pronouns/age/species/occupation chips from
   the record.
3. Chips: id-list + prose-list fields become pill editors (Enter/comma
   adds; fears/traumas danger tone, interests info tone); hidden input
   preserves the collect path.
4. Intimacy: kinks/turn_ons/turn_offs/boundaries/experience render in
   a nested fold; `narrative.secrets` blurs until clicked (matches the
   never-compiled rule).
5. Sticky bar: save/compile sticky with a dirty dot on unsaved edits.
6. Codex preview: debounced dry-run (`POST /record/compile`
   `{"record": {...}}` — no store) rendering compiled prose beside
   the form.

## Steps to verify

1. Open Mind → Persona on a character with a rich block.
   - expected: badges up top, grid fields, chips for lists,
     intimacy folded, secrets blurred, sticky bar.
   - observed: 2026-10-15 — live on :4444, screenshots on file:
     badge header (pronouns/age/species), 2-col grid, chips with
     tones, folds, tooltips, sticky bar. Secrets blur + intimacy
     fold render (interaction: open traverse, contents schema-driven).
2. Add/remove chips, blur/unblur secrets, type with the preview open.
   - expected: chips persist via save; preview tracks the unsaved
     form without storing; dirty dot appears and clears on save.
   - observed: 2026-10-15 — chip add ("pepper") persisted via save
     (`interests: [shinies, pepper]`); codex preview compiled the
     unsaved form ("A 12-year-old goblin…"). Caught + fixed a REAL
     bug on the way: every POST broadcasts `world_changed`, so the
     preview POST re-rendered the pane and ate the unsaved chip.
     Two fixes: dry-run sets `g.no_broadcast` (app.py honors it),
     and the background-update guard now covers ANY focused field
     (chip inputs carry no data-path). Dirty dot verified live.
     Live scratch reverted (Arix prose-only, library prose intact).
3. Save, compile with hand prose, confirm.
   - expected: existing 830 behavior unchanged (preview → confirm →
     applied).
   - observed: 2026-10-15 — unchanged paths re-verified (830 flow
     intact under the new markup; collect reads the same
     `data-persona-path` bindings incl. hidden chip inputs).
4. Run gates.
   - expected: `ts_convert.py check` green; backend tests green
     (dry-run test included).
   - observed: 2026-10-15 — gate green (all five); 92 backend tests
     green (dry-run store/reject tests included).

## Acceptance

- [x] Grid + badge header + typography pass (no 9px body text).
- [x] Chips for all list fields, tones for fears/interests, collect
      path unchanged.
- [x] Intimacy fold + secrets blur; secrets still never compile.
- [x] Sticky bar with dirty dot; focus-guard still protects typing
      (widened to all focused fields).
- [x] Codex live preview via dry-run; nothing stored by previewing
      (no broadcast either).
- [x] All 828 fields still reachable; 830 live behavior unchanged.

## Acceptance

- [x] Grid + badge header + typography pass (no 9px body text).
- [x] Chips for all list fields, tones for fears/interests, collect
      path unchanged.
- [x] Intimacy fold + secrets blur; secrets still never compile.
- [x] Sticky bar with dirty dot; focus-guard still protects typing
      (widened to all focused fields).
- [x] Codex live preview via dry-run; nothing stored by previewing
      (no broadcast either).
- [x] All 828 fields still reachable; 830 live behavior unchanged.

## Files

- `static/js/inspector/mind-view.ts` (+ built `.js`)
- `routes/player_ops.py` — dry-run `{"record"}` on compile (done)
- `tests/test_character_appearance.py` — dry-run test
- `docs/virtualWorld/Characters/Persona.md` — update "What you see"
