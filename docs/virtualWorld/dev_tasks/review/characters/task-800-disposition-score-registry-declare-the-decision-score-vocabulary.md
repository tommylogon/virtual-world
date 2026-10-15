---
type: task
status: review
area: characters
priority: high
wiki: "[[Character Pursuits]]"
related: [task-704, task-691, task-714, task-801, task-802, task-803, task-804, task-805, task-806]
blocked_by: [task-799]
---

# task-800: Disposition score registry: declare the decision-score vocabulary

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-799-disposition-spike-do-three-unrelated-soak-decisions-fit-one-score-registry]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-801-disposition-action-features-verb-score-contributions]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-803-disposition-value-gates-traits-and-morality-as-hard-exclusions]], [[task-804-disposition-pick-argmax-with-a-stable-tie-break]], [[task-805-disposition-whispers-render-the-score-registry-as-words-for-the-llm]], [[task-806-split-traits-capabilities-from-personality-decision-dials]]
<!-- deps:end -->

## What

One module, `engine/disposition.py`, declares every decision score the disposition reads: its name, kind, base value and range. The kind vocabulary is the union proven by the task-799 spike - **utility, weight, multiplier, gate, threshold, salience** - not the card's original four. It also declares, per decision, the **combine** (add / multiply / threshold) and **pick** (argmin / argmax / weighted-draw / threshold-then-utility), because the spike showed one pick rule cannot serve all three decisions (task-804 owns the pick *implementation*).

This is the shared currency that traits, needs, emotion, memories, obligations and GIMP's goal all write into. The gate `tools/disposition_index.py --check` fails when a score's declared base drifts from the engine constant that reads it, when a decision names an undeclared score, and when a personality/modifier file references an undeclared score.

## Why

The 200-modifier catalogue named scores that do not exist in the code. Until each score declares a kind, base and range, 'add_delta' is ambiguous and 'clamp to the declared range' is undefined.

## How

Create engine/disposition.py owning the registry as a single declaration, in the manner of tools/way_properties.py. Add a --check gate (tools/disposition_index.py) so a card referencing an unknown score fails. Seed from task-799's spike.

## Steps to verify

1. Registry gate: a modifier names a score that is not declared.
   - expected: `python tools/disposition_index.py --check` fails, naming the unknown score.
   - observed: PASS 2026-10-13. With a probe file naming `choice.utility.forceful_action`, the gate exits 1: "references undeclared score". On the clean tree it reports "35 scores across 4 decisions, no drift".
2. In the app, open the 🧠 Mind panel for a character.
   - expected: the character's decision scores are listed, each with its kind, base and range from the registry.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. The "Disposition - what they weigh" block lists the character's weighted scores, each labelled with its registry kind and, on hover, its base and range, e.g. "survive.utility.need_relief utility" (title "base 0 range [0, 100]"). It lists the scores the character *moves*, not all 35; the full vocabulary is `python tools/disposition_index.py --report`.

## Acceptance

- [x] Every score has a declared kind, base and range (24 scores, checked by `check_registry`).
- [x] A `--check` tool flags references to undeclared scores (demonstrated live, exit 1).
- [x] The registry declares per-decision combine and pick, so task-804's modes have a source.
- [x] `tests/test_disposition.py` proves the mechanism and both gate directions — 9 passed.
- [x] The declared bases equal the engine constants (`relief.PRIVACY_WEIGHTS`, `background_social.BASE_WEIGHTS` / `BASE_IGNORE_WEIGHT` / `AFFECT_TILT`); the gate fails if either side drifts.
- [x] `python tools/feature_index.py --check` passes.

## Files

- `engine/disposition.py` (new — the registry)
- `tools/disposition_index.py` (new — the gate)
- `tests/test_disposition.py` (new — the mechanism test)

## Browser UI and intended live verification

Intended UI home: Not applicable — this card declares the engine's decision-score vocabulary and static checks; the registry itself has no browser authoring surface.

Current availability: the card records 24 declared scores, six score kinds, per-decision combine/pick modes, a `check_registry` guard, and passing `tests/test_disposition.py` evidence. The browser does not expose the registry directly.

Why no browser UI: completeness and base/range agreement are properties of the source registry and its readers; a rendered game outcome cannot show every declared score or detect a missing declaration.

Alternative verification steps:
1. Run `python -m pytest tests/test_disposition.py` and inspect the registry test output.
   - expected: `check_registry` validates all declared score kinds, bases, ranges, and per-decision modes; the test fails if a referenced score is undeclared.
2. Change a test-only score reference to an undeclared name and run the same focused test.
   - expected: the guard reports the exact unknown score and fails; restoring the declared name passes.
3. Compare declared bases with the source constants named in the card (privacy and background-social weights).
   - expected: every registry base matches its engine constant, with no second hand-maintained base value.

This section is not a claim that planned registry UI exists or works today.
