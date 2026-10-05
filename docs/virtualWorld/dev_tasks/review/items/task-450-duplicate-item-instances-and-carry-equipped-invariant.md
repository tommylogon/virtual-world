---
type: task
status: review
area: items
priority: medium
---

# task-450: Duplicate item instances and the carried+equipped invariant

**Filed:** 2026-09-22, split out of bug-25. (Renumbered from 445 to avoid the
id collision with `done/emotions/task-445-character-expression-packs.md`.)

## Why

bug-25 (take/wear no-op messaging) was closed by the engine-side wording fix, but
its live repro only happens when one character holds **two same-named item
instances** (one carried, one worn) — or a single instance carries both a
`CARRYING` and an `EQUIPPED` edge. The messages are then technically correct
(`take` → "already carrying", `equip` → "already wearing") yet read as a
contradiction, and the LLM spirals.

Evidence: playtest "John two / Jane three" (2026-08-30), plus the original
taco_bell case where miki spawned wearing one Blue Butterfly Earring and carrying
a second. Scenario names suggest population/dressing duplication; `equip_item`
removes the `CARRYING` edge, so a single node normally cannot hold both — the
both-edge state comes from load/legacy/test paths that add `CARRYING` without
removing `EQUIPPED` (`serialization_legacy.py`, `routes/library_ops.py`,
`engine/dressing.py` + `equip_item` when seeding).

## Goal

1. **Find the duplication source.** Identify where a character can end up with
   two same-named item nodes (dressing, library population, scenario assembly,
   or the `kraktooth` character duplication tracked in task-408) and stop it at
   the source rather than deleting copies after the fact.
2. **Enforce the invariant at the engine boundary.** An item node must never
   hold both `EDGE_CARRYING` and `EDGE_EQUIPPED` to the same character. Audit
   every `EDGE_CARRYING` add site (grep `type=EDGE_CARRYING`) and make
   equip/transfer/load converge on exactly one edge per item→owner; add a
   load-time normalizer/validator warning when both are present in a save or
   scenario.
3. **Expose the state, don't paper over it.** With the invariant enforced, the
   bug-25-class confusion disappears; no new user-facing string is needed.

## Acceptance

- A save or scenario that contains an item with both edges loads with exactly
  one (equipped wins) and logs a single warning.
- Dressing/population a character who already wears an item does not create a
  second same-named node; a test asserts one node per equipped item.
- `take`/`equip` on any legitimate state never produce the carrying-vs-wearing
  contradiction.

## Non-goals

- Changing the bug-25 take/equip wording (already shipped).
- Character-node dedup (tracked separately in task-408).

## Resolution (2026-10-02)

**Duplication source found: `auto_dress` did not check worn names before
hydrating.** `_hydrate_item(always_fresh=True)` mints a new node per call;
`equip_item` then refuses an already-worn name, and the except block drops the
freshly-minted node into the room. So dressing an already-dressed character a
second time left a second same-named item on the floor (the taco_bell "one worn,
one carried" shape). Fixed by collecting the character's worn names first and
skipping any candidate whose name matches — the module docstring already claimed
this idempotence, but the code did not implement it.

**Invariant enforced at the load boundary.** `WorldGraph.normalize_item_hold_state()`
removes a `carrying` edge whenever the same item→character pair also has an
`equipped` edge (equipped wins, since demoting would make a worn item leave the
body), and logs exactly one aggregated warning. It runs inside
`WorldGraph.load_from_dict()` and again in `Serialization.load_from_dict()` so
both the graph shape and the legacy loader are covered.

**Audited add sites:** `equip_item` already removes `carrying` after adding
`equipped`; `transfer_actions` retarget edges; `library_ops` import/population
adds only `carrying` (it does not create equipped edges), so no both-edge state
arises there. The remaining sources are save/scenario data written by older
paths, which the load normalizer repairs.

**Acceptance:**
- [x] A save/scenario with both edges loads with exactly one (equipped) and logs
      one warning (`tests/test_carry_equip_invariant.py`).
- [x] Dressing a character who already wears an item creates no second node
      (same test file; asserts node count is unchanged and the room gains
      nothing).
- [x] `take`/`equip` on a legitimate state cannot reach the contradiction,
      because the state is repaired before any verb runs.
