---
type: task
status: todo
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
   - observed: TODO

## Acceptance

- [ ] Three decisions and their scores are documented.
- [ ] Either one registry is proposed, or the linear-currency model is declared wrong with the reason.
- [ ] The output is handed to the registry task (task-800).

## Files

- `docs/virtualWorld/design/Character Pursuits.md`
