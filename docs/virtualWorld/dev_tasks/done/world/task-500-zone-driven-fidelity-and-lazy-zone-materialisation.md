---
type: task
status: done
area: world
priority: medium
---

# task-500: Zone-driven fidelity and lazy zone materialisation

**Filed:** 2026-09-24
**Related:** task-399, task-495, task-401, task-411, task-418
**Design:** `docs/design/worldpainter-knowledge-and-fog.md`

**Overlaps task-401 and task-411.** task-401 already owns chunk load/evict (the actual materialisation), and task-411 (selector) + task-418 (awareness channels) own fidelity-tier selection. This task's only unique delta is using *zones* as the selection key and keeping WorldPainter-side zone records — consider folding it into 401/411 rather than tracking it separately.

## Goal

Use zones (world_scopes) as the spatial key for the existing fidelity tiers (task-399 background fidelity; engine/soak.py promote/demote; engine/trace.py records promote/demote). Distant zones should exist as scope records only and materialise their areas/ways on approach (lazy instantiation), so a 500-zone world does not hold every area/way node at once - this is the actual offloading win. Tie to task-411/412/418 attention tiers and task-407 graph edge-indexing/perf.

## Acceptance

- Fidelity-tier selection can key off a character's zone/scope (in addition to attention).
- Distant zones hold only scope records; their areas/ways are materialised on approach and can be released — a test proves node count stays bounded as the world grows.
- Promotion/demotion records survive materialise/release (`engine/trace.py`).

## Progress — 2026-09-28 (in `review`)

### Only the unique delta is built, as the task's own header asks

> "task-401 already owns chunk load/evict … and task-411 (selector) + task-418
> (awareness channels) own fidelity-tier selection. This task's only unique delta
> is using *zones* as the selection key … consider folding it into 401/411
> rather than tracking it separately."

Agreed. So: **zones** (`engine/zones.py`, new) plus the zone key added to
`engine/attention.py` (`zones_in_play=…`, opt-in). Nothing reimplements 401's
chunking or 411/418's selection.

**This is the third task in a cluster of duplicates** — 401 (chunk load/evict),
411+418 (fidelity selection) and 500 all describe the same mechanism. Posted to
the board with 411's.

### Acceptance 3 cannot be built as written, and that is a finding

It names `engine/trace.py`. **That file does not exist**, and the task that owned
promote/demote records — task-412 — is **cancelled**. `engine/soak.py` exists but
is player soak orders (a bounded time-skip span), not per-zone materialisation, so
it is not the same thing with another name.

The property behind the acceptance line is real and *is* tested, in a form the
world can actually honour: **a released zone keeps its scope record.** The zone
stops being a graph citizen and stays a fact about the world, with its
`area_ids` inventory intact, which is what lets a rebuild be checked against what
used to be there.

### The zone as the selection key

`select(..., zones_in_play=["zone_0", ...])` reads each character's
`world_scope_id` and puts a character in a zone nobody is attending **below every
other tier, including "recent"** — their recency is a fact about a zone the world
is not paying attention to, and ranking them on it is how a whole distant zone
quietly holds the budget.

Two things the tests forced:

- **The key is a demotion, so it needed something to lift.** My first version
  left an in-zone character with no channel signal at `TIER_NONE` alongside a
  distant one, and the key was inert. In-zone-with-no-signal is now
  `TIER_RECENT` (recency is the only signal left) and out-of-zone is
  `TIER_NONE`; that is what separates them.
- **It is opt-in**, so a world with no zones pays nothing and a caller that
  forgets the argument gets the old behaviour rather than an error. Pinned by a
  test that runs the same two characters with and without the key.
- An **unplaced** character (no `world_scope_id`) is nobody's neighbour. Guessing
  "near" for them would let a loose character hold the budget over a placed one.

### The refusals are the actual content

A release is destructive and mostly irreversible, so the rules that stop one
matter more than the happy path. Four, in the order they are checked, each with a
test that fires it:

1. **A zone with a character in it** is not released — its areas vanish under
   their feet and `current_area` dangles. Occupancy is read off the graph (`in`
   edges), not passed in, so the rule cannot be satisfied by a caller that
   forgot.
2. **A `baked` zone** is never released and never re-materialised. A baked zone
   compiles once and is hand-edited afterwards, so a release/materialise cycle
   destroys the edits — **the clobber trap (task-496) wearing a different hat**.
   This is the rule most worth having and the one a naive implementation misses.
3. **A zone with hand-authored nodes in it** is not released unless every
   non-generated node is one the compiler can rebuild. Same reason, found by
   inspection rather than by policy.
4. **A zone whose parent this store released** is not released — the gateway way
   is emitted by whichever scope compiles second. Only a parent *this store*
   released blocks: a parent that was never materialised is the author's own
   doing, and refusing on that would fire on every scope whose parent has no grid
   of its own, which is a normal authoring shape and not a reason to keep a zone
   resident.

Two non-refusals that are also deliberate: releasing an already-released zone is
a **no-op, not an error** (a second release is the normal way to confirm the
first took, and raising there teaches callers to ignore the result), and a store
with no injected compiler uses the **real** one — the injection point is for
tests, not a licence to have no behaviour.

### A bug this task's own test caught, and it is the one that matters

**A rebuild silently used a different seed.** `compile_grid` mints its own default
(`<scope>:grid.v2`) when given none, and the release path was remembering the
*store's* configured seed rather than the one the zone was actually built with. A
re-materialise cycle would therefore have produced a **different zone wearing the
old one's name** — same node ids, different contents, no error. That is worse than
not rebuilding at all, and it is invisible until you diff the two.

The seed now comes from the **nodes' own provenance** before they are dropped,
and a zone not built from one seed is reported with `ambiguous_seed` rather than
guessed. Tested both ways: a zone built with no seed rebuilds byte-identically,
and a zone with two seeds in it says so.

Provenance was the natural selector throughout — every compiled node already
carries `properties.generated.scope_id` (`engine.generation.provenance`), so
"release this zone" is "delete exactly the nodes that recipe produced for it". The
same mechanism the design doc's 🧹 Ungenerate calls for, used as the runtime half
of a cycle. A hand-placed area carrying only `world_scope_id` is in the inventory
too, or a zone holding only that kind would look empty and be released while
still holding the thing that was there.

### New tests — `tests/test_zones.py` (24) and +4 in `test_attention.py`

The selection key (distant zone loses on recency as well as awareness; opt-in;
unplaced; same-zone not demoted; demotes rather than promotes); provenance as the
selector; the four refusals; the release keeping the record and dropping only its
own nodes; the rebuild reproducing ids *and* provenance, plus the ambiguous-seed
report; approach idempotence; the injected compiler; and the **bounded node
count**: 2, 8 and 32 zones, one resident, measuring that 16× the zones costs
under 4× the nodes and that 8 and 32 cost *the same*.
