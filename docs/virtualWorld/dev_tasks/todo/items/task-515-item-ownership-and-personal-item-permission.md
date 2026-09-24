---
type: task
status: todo
area: items
priority: medium
---

# task-515: Item ownership and personal-item permission

**Filed:** 2026-09-24
**Related:** task-20, task-450

## Goal

Let an item be personally owned so others cannot casually take or use it —
Gribba's treasured Good Knife "nobody else may touch" — while keeping an
explicit, contested steal path.

## Context

- No owner/permission field exists on items. `steal_item`
  (`engine/items/transfer_actions.py:96`) resolves any carried or worn item in
  the target's inventory and contests Sleight of Hand vs Perception;
  `give_item` (line 16) transfers unconditionally.
- `locked`/`current_state` (task-20, task-97) is a key-lock, not ownership.
  `bound` is a player state, not an item binding.
- Motivating cases: Gribba's Good Knife; likely also Vekka's folded map,
  Krikka's hidden cove finds and Zikka's trophy leather strips.

## Proposal

- An item-level ownership marker (`owner` = character id/name, or tag
  `personal` plus `owner`), set at authoring or spawn.
- A non-owner `take`/`give`/`use` refuses with a clear message; the owner is
  always allowed. Decide whether an absent/incapacitated owner or a successful
  Social/Intimidation check lifts the refusal.
- Keep `steal_item` as the contested override (ownership may raise the
  difficulty or add a "you would be caught" gate) rather than blocking it
  outright.
- Reveal the owner on examine only when known (task-339 stranger naming).

## Acceptance

- A node marked owned cannot be taken/given/used by a non-owner through the
  normal verbs; tested with a clear refusal message.
- The owner can always take/use/give it away.
- `steal` still functions as the override and is tested.
- Gribba's Good Knife is the worked example.
- Implemented as a node property rather than a new edge type, or the new edge
  is justified.

## Non-goals

- A full property/faction law system.
- Locked containers and keys (task-20).
