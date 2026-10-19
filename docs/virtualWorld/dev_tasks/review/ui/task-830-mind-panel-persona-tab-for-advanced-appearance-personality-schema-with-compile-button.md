---
type: task
status: review
area: ui
priority: high
related: ["'task-828'", "'task-844'", "'task-847'", "'task-848'", "'task-852'", 'task-820', 'task-821', 'task-844', 'task-847', 'task-848', 'task-852']
wiki: "[[Feature Map]]"
---

# task-828: Mind panel Persona tab for advanced appearance-personality schema with compile button

**Filed:** 2026-10-15
**Related:** task-733

<!-- deps:start -->
**Related:** [[task-828-expanded-persona-appearance-schema-on-character-node-with-compile-into-prose]], [[task-844-persona-tab-character-sheet-pass-grid-chips-codex-preview]], [[task-847-persona-tab-embedded-body-paperdoll-navigator-for-appearance-schema]], [[task-848-persona-tab-visual-paperdoll-with-inline-body-baseline-editing]], [[task-852-persona-ui-improvement-plan-workspace-doll-navigation-markings-state-integration]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]], [[task-821-mind-panel-relocate-the-gimp-goal-editor-out-of-the-bio-tab]]
<!-- deps:end -->

## What

A new **Persona** tab in the Mind panel: the full WorldGraph-flavoured
advanced schema (task-828's fields) nested UNDER Appearance and
Personality sections, all editable, with ONE **Compile** button that
projects the block into `base_description` / `description` /
`personality` + tags/traits.

Layout: `Mind | Persona | Memories | People | Goals`. Persona holds:

- Identity: pronouns, age, gender, species, occupation,
  sexuality/orientation
- Appearance: overview, height/build/weight, hair{color,length,style},
  eyes{color,shape,special}, skin{tone,condition,features}, face,
  body+modifications (tattoo/scar/piercing/prosthetic), voice, scent,
  style
- Personality: traits, likes/dislikes/interests, fears, kinks +
  turn_ons/offs, traumas, quirks/habits/aspirations, speech_pattern,
  boundaries, experience
- Narrative: biography, secrets (+known_by), example_dialogues,
  role_in_town, arc

Every field shows its consumer as hint text ("→ fear engine",
"→ prompt voice", "→ affect"). The Compile button calls
`POST /record/compile` (explicit; never auto-clobbers hand prose -
shows a diff/preview first when prose exists).

## Why

task-733's sheet has no home; the Bio tab is definition, the Mind
panel is the person. The user decision: advanced schema lives in a
new Mind tab, new fields UNDER appearance/personality, compiled on a
button press into the prose fields.

## How

- `static/js/inspector/mind-view.ts`: new `persona` tab renderer +
  form state; reads `GET /record`, writes `PUT /record`
  (`render:false` while editing), compiles via `POST
  /record/compile`. Follows existing tab + TagMultiselect patterns.
- `.ts` first, then `npm run build:ts` (never hand-edit `.js`).
- Preview: when compiled prose differs from hand prose, show both
  and require confirm.

## Steps to verify

1. Open a character → Mind → Persona. Edit pronouns, age, a tattoo,
   a kink, a trauma, a secret, a dialogue line. Save.
    - expected: `GET /record` returns them; reload restores.
    - observed: 2026-10-15 - full round-trip live on :4444, verified
      by screenshot: tab (42 controls, folds, hints), typed age 29 →
      Save → `GET /record` returns 29. Live scratch reverted
      afterwards (original library prose restored via update route +
      `DELETE /record`; Arix prose-only again).
2. Press Compile with empty hand prose.
    - expected: `base_description`/`personality` fill; tags/traits
      project; no parallel blob.
    - observed: 2026-10-15 - live compile on the fresh server wrote
      `A 29-year-old.` into `/api/state` (node-shadowing fix
      verified live), stale flag cleared. Screenshots on file.
3. Press Compile with hand prose present.
    - expected: preview shows both; confirm required; cancel keeps
      hand prose.
    - observed: 2026-10-15 - preview screenshot live (BASE NOW vs
      BASE COMPILED + PERSONALITY pair, replace/keep buttons);
      confirm click applied, banner cleared, state updated.
4. `python tools/ts_convert.py check` + unit runner pass.
    - expected: clean.
    - observed: 2026-10-15 - gate green (build/typecheck/lint/
      module:check/unit). Background state pushes skip re-render while
      a persona input has focus, so typing is never wiped.

## Acceptance

- [x] Persona tab exists in the Mind panel with all 828 fields under
  Appearance/Personality (+ Identity/Narrative).
- [x] Edit → save → reload round-trips via `record` routes.
- [x] Compile projects to prose + tags/traits; hand prose protected
  by preview/confirm.
- [x] Every field hints its consumer; mbti/alignment/media absent.
- [x] `ts_convert.py check` + unit runner pass.

## Files

- static/js/inspector/mind-view.ts
- 
outes/players.py
- 
outes/player_ops.py
