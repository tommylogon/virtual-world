---
type: task
status: todo
area: characters
priority: high
---

# task-707: Memory: decay reduces activation only, never deletes (actor, trigger, or consolidation only)

**Filed:** 2026-10-05
**Related:** task-685,task-687,task-688

## Goal

Decay fades a memory's activation toward zero. Removal requires an actor, an explicit trigger effect, or deliberate reflection consolidation - never a falling number.

## Acceptance

- **The principle:** decay reduces `activation`. Removal requires an actor, an
  explicit trigger effect, or deliberate reflection consolidation. It is never
  a side effect of a number going down.
- **Wiring:** `apply_decay` calls no `memories.remove`. It still returns the
  removed count so `tick_manager`'s existing consumption is unchanged, and that
  count is now always 0 from the decay path.
- A memory driven to `activation <= ACTIVATION_FLOOR` stays in the roster and
  stays findable. It is simply not surfaced — a later contextual match
  (keyword, semantic, tag) can still raise it.
- Recall cost is unchanged: `MAX_RECALL = 10` (memory-context.ts:341) caps what
  reaches a prompt regardless of stored count, so storing more does not grow the
  context. Measure stored-memory growth over one soak before setting any cap.

## Why deletion is not justified

The original argument here was context budget, and it is the weaker of the two.
Both are recorded.

**Context budget does not justify it.** Recall is **already** capped
independently of storage — `MAX_RECALL = 10` (memory-context.ts:341) applied
after scoring, so only ten memories reach a prompt no matter how many are
stored. Deletion buys storage, not context.

**The stronger argument: activation is inert, so deletion is the only mechanism
in this system that makes anything permanently unforgettable.** Every reader of
`activation` in the whole codebase:

```
memory_dynamics.py:164   written (boost)
memory_dynamics.py:240   written (decay)
memory-view.ts:87        displayed in the inspector
mind-view.ts:69          displayed in the inspector
```

**Nothing reads it to decide anything** — not retrieval, not scoring, not
selection. task-687's docstring says memories "fade toward irrelevance"; they do
not. They decay a number that is displayed and then tested for deletion at line
241.

Meanwhile the **retrieval layer already implements the behaviour we want.**
Recall is keyword match + semantic vector + recency, with no strength threshold
anywhere in the pipeline. A memory's chance of returning depends entirely on
whether the moment resembles it — which is exactly the designed case ("walk into
the kitchen and it comes back whole"). Decay does not participate in that. So the
system forgets the way a person forgets *by default*, and deletion is the single
exception that breaks it: for a memory that scored low, nothing comes back —
not because the character forgot, but because it is no longer there to be reminded.

## Invariant this task must not break later

**Recall must stay purely contextual.** Nobody may "optimise" retrieval by
ranking on `activation`, or by filtering recall at an activation threshold. That
would rebuild permanent forgetting from the other side while appearing to be a
quality improvement to recall. Any future change that makes `activation`
retrieval-visible is a regression against this task, not an enhancement.

## The principle, in full

> Decay changes how loudly a memory answers a cue. It never decides whether the
> memory still exists.
>
> A character who never perceived something has no memory of it, and that is the
> only kind of absence the world contains.

The second line is the design statement: the distinction between *losing*
knowledge and *never acquiring* it. Nothing needs a forgetting mechanism for
what was never learned.

## Current behaviour this reverses

`engine/memory_dynamics.py:241` deletes today:

```python
if memory["activation"] <= ACTIVATION_FLOOR and _removable(memory):
    player.memories.remove(memory)
    _forget_index(player, memory.get("id"))
```

`_removable` (line 206) permits removal for anything that is not
`manual`/`preconceived`, under importance 6, and unreinforced. So a plain,
unrepeated, low-importance memory is currently deleted permanently, index
entry included. task-687's acceptance ("the plain one is removed first") asserts
this behaviour and **must be rewritten**, not merely relaxed — see below.

## The gap in the rule, stated rather than hidden

Two deletion paths are *not* decay and must stay, or an actor can be erased by
the back door:

- **Reflection consolidation** (task-688) writes "memories folded; originals
  removed". Deliberate, opt-in, and the summary survives — a different thing from
  a memory quietly evaporating.
- **Any future retention cap** must be an authored, visible decision, never a
  silent default.

Both are named here so that "decay never deletes" does not become "nothing ever
deletes" by omission.

## task-687 knock-on

task-687's first acceptance criterion asserts the opposite ("the plain one is
removed first"). It cannot be weakened — the honest move is to replace it with an
activation-ordering assertion (the important memory's activation stays strictly
higher) and drop the deletion claim. Flagged for whoever picks up 687; task-707
blocks it.
