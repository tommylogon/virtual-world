---
type: task
status: todo
area: world
priority: high
---

# task-585: allow_regenerate overwrites a hand edit on a generated node

**Filed:** 2026-09-28
**Related:** task-398, task-400

## Goal

Decide and implement what an explicit allow_regenerate re-run may overwrite on a node that carries generation provenance. Today apply_patch re-stamps the incoming node in place, so a re-run silently reverts a hand edit; the opposite requirement also exists, namely that a legitimate recipe change must reach nodes the recipe already emitted.

## Why this is needed

Found by the task-400 end-to-end test
(`tests/test_pines_slice.py::test_a_hand_edit_is_not_erased_by_a_second_invocation`)
while wiring the recipe into the generate endpoint.

`engine/generation.py::apply_patch` has two requirements pulling in opposite
directions, and today the second one wins silently:

- **task-398's acceptance:** "a later manual edit to a generated item survives
  reload and cannot be erased by a second generator invocation." The *default*
  path honours this — a second call is refused with 409 and the edit survives.
- **the re-stamp intent in `apply_patch`:** a re-run that only *adds* missing
  nodes leaves every existing one with stale data, so a recipe change (new
  properties, a revised description) must reach the nodes the recipe already
  emitted. Hence `graph.replace_node(node)` under `allow_regenerate`.

The result is that `allow_regenerate: True` reverts a hand edit, and the operator
gets no signal. The comment in the code says it is deliberate, so the ambiguity
is in the *contract*, not the code: "generated is a provenance flag, not an
ownership claim" cannot also mean "an explicit re-run overwrites whatever you did
by hand".

## Requirements

- One rule, stated once, covering both directions. Candidates to weigh:
  - re-stamp only keys the existing node does **not** have, so a recipe can add
    but never rewrite (breaks a deliberate recipe revision);
  - re-stamp everything but preserve a recorded set of **author-edited** keys
    (needs a marker for "the author touched this");
  - make `allow_regenerate` a *diff preview* rather than a silent overwrite, so
    the author is shown what would change and confirms it.
- Whatever the rule, the endpoint must not report success while reverting an
  edit the author did not ask it to revert. A `report` field naming reverted
  properties would satisfy this cheaply.
- The default path keeps its current behaviour: 409, nothing touched.

## Acceptance

- A hand edit survives an `allow_regenerate` re-run, **or** the re-run reports
  exactly which properties it is about to revert and the author confirms.
- A genuine recipe revision still reaches existing generated nodes.
- A test pins both halves; today only the refused path is pinned
  (`tests/test_apartment_recipe.py`, `test_apartment_recipe.py` line ~250).

## Non-goals

- Making recipes version-migrate old output (a separate, larger question).
- The `Generate` button and preview surface (task-580).
