---
type: task
status: review
area: characters
priority: high
wiki: "[[Character Pursuits]]"
related: [task-704]
---

# task-799: Disposition spike: do three unrelated soak decisions fit one score registry

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]]
<!-- deps:end -->

## What

Declare the decision scores three unrelated soak decisions need - Gribba choosing who to feed, the road captain at a crossing, the wolf deciding to hunt - and test whether ONE score registry covers all three.

## Why

The score vocabulary is upstream of every coefficient and of the missing action-feature table. Get it wrong and all of it inherits the mistake. This is the cheapest way to falsify the whole disposition direction before a line of code.

## How

No code. For each of the three decisions, name the scores it turns on and the kind of each (utility, multiplier, threshold, salience). Diff the three sets. If one vocabulary covers all three, hand it to task-800; if each needs its own, say so and stop.

## Steps to verify

1. In docs/virtualWorld/design/Character Pursuits.md the three decisions and their scores are written out.
   - expected: three declared score sets, and either one proposed registry that covers all three or a named reason the model fails.
   - observed: DONE 2026-10-13. The `### The disposition spike: do three unrelated decisions fit one registry?` section names the three decisions (relieve, the social pass, the wolf hunt), their score kinds, the diff table, and both conclusions.

## Findings

- **One registry covers all three: yes.** The union of the kinds they need is {utility, weight, multiplier, gate, threshold, salience}; nothing falls outside it. Task-800 proceeds as written.
- **One pick rule does not.** The three resolve differently: relieve is an additive utility chosen by **argmin** (deterministic); the social pass is **multiplicative weights chosen by a seeded draw**; the hunt is **threshold-then-utility**. A registry that declared a single `argmax` (task-804 as written) would fail the social pass - a draw is not the maximum.
- **Consequence for task-804:** it is "the pick modes", not "the pick". Amended there.

## Acceptance

- [x] Three decisions and their scores are documented.
- [x] One registry is proposed (the kinds union), and the place the model as written fails (a single pick rule) is named.
- [x] The output is handed to the registry task (task-800).

## Files

- `docs/virtualWorld/design/Character Pursuits.md`

## Progress (2026-10-13)

- Grounded the first two decisions in the live engine: `engine/relief.score_privacy` (additive utility, argmin) and `engine/background_social.py` (seeded weighted draw with `AFFECT_TILT` and trait gates). The third is proposed.
- Wrote the diff and the pick-mode finding into the design doc; task-804 rewritten to carry it.

## Browser UI and intended live verification

Intended UI home: Not applicable — this is a completed design spike documenting three distinct decision-score shapes, not a player-facing control or shipped resolver.

Current availability: acceptance records Gribba choosing who to feed, a road captain at a crossing, and a wolf deciding to hunt; one universal pick rule was rejected and the score-kind union was handed to task-800.

Why no browser UI: the spike's deliverable is the documented decision model and its counterexample to a single pick rule. A browser action would exercise later consumers rather than validate this design handoff.

Alternative verification steps:
1. Read the spike's three decision traces and compare their score roles and selection rules.
   - expected: feeding, crossing, and hunting each have their own described score/decision shape; the note does not claim a single resolver mode covers them.
2. Compare the declared score-kind union and the failure case with task-800's registry design.
   - expected: task-800 carries the six kinds and the per-decision combine/pick requirement forward without losing the spike's caveat.
3. Inspect task-800's linked implementation/evidence after it lands.
   - expected: this spike remains the design source for the handoff, not an independent runtime score registry.

This section is not a claim that planned UI exists or works today.
