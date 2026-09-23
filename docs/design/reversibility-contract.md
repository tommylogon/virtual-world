# Reversibility Contract

How a backgrounded character can be *promoted* to full cognition, and *demoted*
back, without ever becoming a different person. This is the rule that makes
"same characters, two fidelities" safe instead of a source of retcons.

Related: [[trace-format]], and tasks 397 (scopes), 399 (background sim),
403 (unified memory).

## Principle

**One state model, two decision policies.** There is exactly one `Player`, one
graph, one clock, one set of vitals. Background and foreground differ *only* in
where decisions come from:

- **Background:** deterministic/probabilistic rules over schedule + needs +
  traits. No LLM.
- **Foreground:** the LLM proposes goals/plans; the deterministic layer
  validates and executes.

Promotion is "start asking the character instead of their rulebook."
Demotion is the reverse. Nothing is materialized, re-rolled, or recreated —
so nothing can contradict.

## What must stay continuously true (both fidelities)

While a character is backgrounded, the rule layer must keep updating the same
fields the foreground layer reads. If a field is frozen during background, it is
a reversibility violation.

| Field | Why it must stay live |
|---|---|
| `current_area` + position | Promotion at a stale location is teleportation |
| `vitals` (all) | Hunger/thirst/energy/HP must be the real, decayed values |
| `conditions` | A backgrounded character can be wounded, ill, asleep |
| `inventory` / `equipped` | Objects must not duplicate or vanish across the seam |
| `relationships` | Coarse deltas are enough, but they must accrue |
| `memories` / trace | The history of what they did must survive |
| `activity` / `state` | "Asleep in the Sleeping Halls" is real state |
| `traits` | Acquired slowly; must not reset |
| `goals` / current plan | Promotion resumes the plan, it does not invent a new one |

## Allowed approximation (background only)

Background may be *coarse*, but must be **reconcilable**:

- Action timing may be scheduled in blocks rather than tick-exact.
- Paths may be resolved as "travel between areas with an ETA" rather than
  step-by-step, **provided the character is placed at a real area at the right
  tick** (no teleporting).
- Probabilistic outcomes are allowed **only** if seeded, so a span is
  reproducible.
- Numbers may move in whole units via the `vital_rates.change()` accumulator.

Background may never invent outcomes the foreground could not have produced
(e.g. an item appearing in an inventory that was never taken).

## Promotion handoff

On promotion the character must receive:

1. Their **current state** (already real — no update needed).
2. A **catch-up summary** built from the trace since they were last foreground
   (`engine/trace.summarize_window`), so the LLM knows what happened to them
   and can act as someone who lived it.
3. Their **standing goal/plan**, if any.

The LLM's first foreground output may revise the plan; it may not rewrite the
past.

## Demotion handoff

On demotion the foreground span is rolled into the trace: the character keeps
their state, and the *reasons* and *facts* of what they just did are recorded
(see trace format). No memory is deleted; live memories stay in the memory
store and the trace covers the mechanical span.

## Invariants that must hold across any promote/demote

1. **Position continuity** — the character is in a real area before and after.
2. **Object conservation** — items are neither duplicated nor lost.
3. **Vital continuity** — no jumps in vitals, only real accumulated change.
4. **Relationship symmetry** — A's view of B and B's view of A stay consistent.
5. **Identity stability** — the opaque id (`task-316`) never changes on promotion.
6. **Determinism** — a background span replays identically from its seed.
7. **No orphans** — promotion never creates a second node for an existing
   character (guards against the duplicate-character-node class of bug).

## Non-goals

- Pixel/tick-perfect motion while backgrounded.
- Identical LLM and rule outcomes — they will differ; they must not *contradict*.
- Making background characters as smart as foreground ones.

## Open problem

**Cross-zone roaming.** A character travelling between zones belongs to no
single zone. Background must model the transition as a scheduled event with an
ETA and promote on approach, so arrivals are coherent rather than spawned.
