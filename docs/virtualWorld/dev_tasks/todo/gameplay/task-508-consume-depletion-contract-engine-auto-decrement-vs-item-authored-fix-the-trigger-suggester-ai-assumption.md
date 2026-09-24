---
type: task
status: todo
area: gameplay
priority: medium
---

# task-508: Consume depletion contract — engine auto-decrement vs item-authored

**Filed:** 2026-09-24
**Related:** 424, 506, 155, 196
**Blocks:** 506 (the library-wide consumable pass cannot be authored correctly until the depletion model is fixed)

## Goal

Decide, implement, and document **one** rule for how an item's `uses` (`uses` =
charges/durability, task-155) is spent on `eat`/`drink`, so the engine and the
trigger-authoring layer agree. Today they don't, and the disagreement silently
creates infinite food.

## The mismatch (measured 2026-09-24)

Two mechanisms exist and only one fires for consume:

- **`use` action auto-decrements.** `engine/items/use_actions.py:160-170`:
  every `use` does `uses -= 1` and detaches the item at 0, regardless of triggers.
- **`eat`/`drink` never auto-decrement.** `engine/items/consume_actions.py` has no
  decrement; `_deplete_if_spent` (`:132`) only *reacts* to a count that a trigger
  already drove to 0. So consume depletion must be hand-authored via
  `adjust_uses` / `remove_item` / persistent `set_state`.

Now the authoring layer. The trigger suggester and its AI prompt were built on the
opposite assumption:

- `static/js/shared/trigger-suggest-ai.js:122` tells the model: *"The engine
  auto-decrements uses and removes the item at 0 — do NOT hand-add
  `adjust_uses`/`destroy_item`."*
- `static/js/item-library/consumable-triggers.js:298-301` emits a `uses_above 0`
  condition + an "empty" fail message, but **no** `adjust_uses`.

So a finite consumable produced by "⚡ Suggest" / "✨ Suggest (AI)" has a guard that
can never become false: the guard asks "are there uses left?", nothing ever spends
one, and the item is **infinite**. This is exactly why `rations_of_dried_meat`
(`uses: 3`) and `apple` (`uses: 1`) never deplete once the authored path is live
(see task-424 / task-506).

It also means task-424's chosen model (item-authored `adjust_uses`, hand-written
into the camp's five consumables) directly contradicts the contract the authoring
tools assume — one of the two is wrong and the difference is invisible until
someone soaks it.

## The fork

**A — engine auto-decrement for consume (recommended).**
Make `eat`/`drink` spend `uses` exactly as `use` does, so the AI prompt's
statement becomes true. Consequences:
- Consume triggers author only `adjust_vital` (+ conditions/messages); they never
  touch `uses`. The `uses_above 0` guard becomes meaningful.
- The persistent-empty hook (`on_depleted`, `set_state empty`) attaches to the
  engine decrement (`uses_before > 0 → 0`) instead of to a hand-authored
  `adjust_uses`.
- The camp's five consumables drop their hand `adjust_uses`
  (`tools/author_camp_consumables.py` is a one-line change) — no double-decrement.
- One decrement path for both verbs; the "forgot `adjust_uses` → infinite" bug
  class disappears.
- Risk: any existing trigger that *also* hand-authors `adjust_uses` on consume
  would double-decrement and must be found and cleaned (audit `data/`).

**B — item-authored depletion stays.**
Keep task-424's model and instead fix the tools: update the AI prompt and the
heuristic suggester to emit `adjust_uses`, and batch-run them. Consequences:
- No engine change; the `use` path and the consume path stay different rules.
- Every consumable, forever, must remember to deplete itself; the failure mode is
  silent and only a soak catches it.

Recommendation: **A** — it is the contract the authoring layer already assumes,
it removes a silent-infinite failure class, and it matches the one place the
engine already auto-spends `uses`.

## Design questions to settle

- Does auto-decrement apply when `uses == -1`? (No — "no charge model"; keep
  permanent items permanent, as `use` already does.)
- Does a consume trigger that wants the item to *survive* (the water skin that
  empties) rely on `set_state` + a persistent empty state, not on skipping the
  decrement? (Yes.)
- Ordering: decrement before or after the item's triggers fire? `use` decrements
  *after* its triggers (`use_actions.py:160` is past the trigger exec); match that
  so a trigger can read the pre-spend count.
- Migration: find every consume trigger in `data/` that hand-authors `adjust_uses`
  or `remove_item` and remove the now-redundant spend (keep `remove_item` only
  where "destroy, don't persist" is genuinely intended and distinct from
  `uses: 1`).

## Acceptance

- `eat`/`drink` on an item with `uses > 0` decrements `uses` and, at 0, runs the
  existing persistent-empty / removal behaviour — with no `adjust_uses` in the
  trigger.
- An item with `uses: -1` is never spent or destroyed by consume.
- The water-skin acceptance from task-424 still holds (drinks down, empties,
  persists, refillable).
- `trigger-suggest-ai.js` no longer contains a claim the engine contradicts; the
  suggester's `uses_above 0` guard is meaningful.
- Camp week soak stays 23/23 at 1 and 15 min/tick.
- Data audit: no consume trigger double-spends `uses`.

## Non-goals

- Per-item nutrition/restore amounts (that is task-506).
- Changing what counts as food/drink (`FOOD_TAGS`/`DRINK_TAGS`).
- The `use` path's existing auto-decrement (it is already correct).

## Verification

- Unit: `eat` an authored item with `uses: 2`, no `adjust_uses` → after one eat
  `uses == 1`, item present; after two, removed.
- Unit: permanent (`uses: -1`) authored item survives any number of eats.
- Unit: persistent-empty (`set_state empty`) item stops at 0 and stays.
- Regression: a "suggested" item (heuristic output) is finite, not infinite.
- Soak: camp 23/23 at 1 and 15 min/tick; graph node growth bounded.
