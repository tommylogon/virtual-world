---
type: task
status: done
area: world
priority: medium
---

# task-522: Way blocking pass: outdoor ways can't be hand-closed; seed-picked blocked subset with blocker prose

**Filed:** 2026-09-25
**Related:** 

## Goal

Secondary generation pass (item population / world state). Rule: a plain close action must NOT close an outdoor/outside way -- you cannot close a road into a forest or a cliff by hand. Blocking is done by an item or trigger setting the way state (fallen tree, barricade, rockslide, wolves den). At generation, deterministically mark a subset of outside ways blocked, each with a per-biome 'what blocks it' description.

## Constraints (decided with the user, 2026-09-25)

- **Determinism is non-negotiable.** The compiler has no `random`/clock; the
  blocked set must be a stable hash of `seed:way_id` so a regenerate reproduces
  the same world.
- **Never strand a pocket.** Do not block a *cut-edge* (bridge) of the scope's
  adjacency graph, or verify connectivity after choosing; blocking must not undo
  the island auto-linking (`link_islands`).
- **State shape.** The engine currently knows `open`/`closed` only. Decide
  between a real `blocked` state or `current_state: "closed"` plus a
  `blocked_by` / `blocked_description` property.
- **Which ways.** Outdoor/outside ways only (compiler-generated passages that
  leave the zone / have no door); interior doorways and gateways keep the normal
  toggle behaviour.
- **Blocker vocabulary.** Per-biome content (fallen tree, rockslide, flood,
  thicket, wolves) chosen by the same stable hash.

## Acceptance

- Compiling a painted grid blocks a deterministic subset of its **outdoor** ways;
  recompiling with the same seed reproduces exactly the same set.
- Each blocked way names what blocks it and says it in a sentence, and the
  refusal a character meets quotes that sentence.
- No area is ever stranded: a way whose removal would disconnect the scope is
  left open.
- A plain close action refuses a blocked or `prevent_close` way, with the
  recorded reason rather than a generic message.
- Interior doors, stairways and gateways keep their normal toggle behaviour.

## Progress — 2026-09-28 (in `review`)

### The "state shape" decision was already made by the codebase

The task asked to decide between a real `blocked` state and `current_state:
"closed"` plus a property. The engine had already decided, in three modules
predating this task:

- `engine/matching.py:247` lists `blocked` among the way states a command can
  match, so "examine blocked path" resolves;
- `engine/movement.py:561` refuses it — "The {direction} is blocked. There's no
  way through" — and teaches it as a learned aspect;
- `engine/area_description.py:739` keeps `blocked`/`jammed` hidden until the way
  is examined, which is a deliberate blind spot worth preserving;
- `engine/sound.py` costed it before task-421, and `engine/barriers.py` now
  gives it a light transmission of 0.0.

So: **a real `blocked` state**, and what was missing was a *reason*. That is what
`blocked_by` (an obstacle id) and `blocked_description` (a full sentence) add.
`closed` would have been wrong for three reasons: it puts a shut door and a
fallen tree in one bucket, it makes the learned aspect "closed" when what the
character saw was a tree, and it loses the "examined to learn" blind spot that
`area_description` was built around.

### Both rules were partly there already

**"A plain close action must not close an outdoor way"** is
`engine/movement.py:_open_passage_block`'s existing `prevent_close` flag, which
already answers "You can't close the {label} — this opening is permanent." The
pass sets that flag on the ways it blocks. What was missing is that the refusal
quoted nothing, so I made it quote `blocked_description` (falling back to
`refusal_message`, then to the generic sentence). A blocked way also now refuses
**open**, which is the other half: you cannot swing a fallen tree either.

**"Which ways"** is the compiler's own `kind` (task-562): `open` is a path you
walk, `door` and `stairs` are thresholds. Only `kind == "open"` ways are
candidates, so a building's own front door is never blocked. A way already
refused by a climb (task-525) is also excluded — that one is closed for a reason
the player can fix, and two refusals for one obstacle reads as noise.

### Never stranding a pocket, by construction

Not by picking carefully: **each candidate is blocked only if every area is still
reachable once it is.** A way that is the last route into somewhere is therefore
never blocked, whatever the hash does. This is checked per candidate against the
(area, way, area) triples the compiler already holds, before the patch is applied
— there is no graph to walk yet. It also means the pass cannot undo the island
auto-linking (`link_islands`): the two are independent and this one can only
refuse, never strand.

Measured: a 9×9 painted grid loses a real subset of its ways and strands nothing
across five seeds; a 2×2 grid (K4, six ways) loses exactly one; a single painted
cell loses nothing; a pure chain with no redundancy loses nothing.

### The determinism requirement needed a real hash

"a stable hash of `seed:way_id`" — the compiler had `_stable_index`, a weighted
character sum, and it is the wrong tool here. Two reasons:

- **`hash()` is out.** CPython salts str hashing per process, so a blocked set
  derived from it would differ every run while looking entirely plausible. That
  is the failure mode the task's "determinism is non-negotiable" is about.
- **`_stable_index` clusters.** Over `way_0..way_499` the only varying characters
  are in the last three positions, and measured at **73%/27%** across the id
  space for a 12% threshold. Deterministic, but visibly lopsided, and a reader
  would file it as a bug.

So `stable_digest` (FNV-1a 32-bit, 20 lines, byte-exact across runs and
platforms) is used for both new decisions: the blocked/open pick and the blocker
pick. Measured after: 12.6% hit rate over 500 ids, 50.8% in the first half,
quartiles [18, 14, 17, 14]. `_stable_index` is untouched, because every painted
description fragment is already chosen by it and changing it would reshuffle all
of them.

### Blocker vocabulary

`BLOCKERS_BY_TERRAIN`, keyed by the terrain class `terrain_class()` already
computes (`woods`, `rock`, `water`, `cultivated`, `road`, `open`) — so a new
biome joins by declaring its terrain, not by a code change. Two or three
blockers each, picked per way by the same digest, each a full sentence because
it is what the refusal and the description both quote:

- woods — a fallen tree with its roots shearing the ground up; a thicket of
  bramble; years of deadfall layered deep enough nothing has walked since;
- rock — a rockslide still loose underfoot; a boulder the size of a cottage,
  bedded in and not going anywhere;
- water — floodwater cut a channel; a washout you can see the bottom of;
- cultivated — field fence down in a tangle; an irrigation ditch too deep to step;
- road — the surface broken away into a channel of mud; a tree down with a
  length of the verge;
- open — bramble interwoven and unwilling; a trench with standing water in it.

`BLOCKED_WAY_PERCENT = 12`, low on purpose: nothing in a compiled grid sets a
blocked way back to open, so every blocked way is permanent map until an author
or a trigger clears it. At 12% a scope reads as a landscape with weather history
in it rather than as a maze.

### New tests — `tests/test_way_blocking.py` (33)

`blocked` being a pre-existing state (pinned by source, not by my say-so); every
terrain class having prose; the same seed giving the same set and a different seed
a different set; the pick being a *spread* rather than a prefix (and the
percentage bounds being total); the blocker pick varying per way; the chain /
ring / K4 / 9×9-grid connectivity cases including five seeds; percent zero and a
single cell being no-ops; an unknown way id skipped rather than raising; the
recorded shape of a blocked way including that it does **not** put the blocker in
the always-visible `description` (which would leak the examine-to-learn blind
spot); doors never blocked; and the close rules — a blocked way refusing both
close and open with its own sentence, a way with no reason still refusing with
*something*, a plain outdoor way refusing close, an interior door unaffected, a
wedged panel, and the jump/climb/crawl message unchanged.

End to end through the real compiler: a 9×9 grid blocks outdoor ways and leaves
doors alone; the same seed recompiles identically; a **fresh manifest** compiles
to the same world (a regenerate, not a re-read); the generate report says what
it blocked; nothing is stranded; and the 2×2 and single-cell edges.
