---
type: task
status: todo
area: graph
priority: high
---

# task-617: Node positions stored twice, one store dead; 42 nodes have neither

**Filed:** 2026-09-30
**Related:** 

## Goal

Two position stores exist (hand-authored 2-key and runtime 5-key); one is dead and 42 nodes have no position in either. The store in use does not persist.

## Acceptance

- TODO

## Corrected by measurement 2026-09-30

The filed claim was "two position stores, one dead; 42 nodes have neither". In
the loaded world the shape is different:

| measurement | value |
|---|---|
| nodes | 239 (98 item, 99 logic_trigger, 20 way, 19 area, 3 character) |
| position keys present in the whole graph | **`x` and `y` only**, on 138 nodes |
| nodes using a `position` / `pos` object | **0** |
| nodes with neither store | **101** |

Two corrections:

1. **There is only one position store in use here**, not two with one dead. The
   hand-authored 2-key store and the runtime 5-key store described in the finding
   are not both present in this world's data -- so either the second store is
   world-specific, or the finding conflated a schema with a populated instance.
2. **The orphan count is 101, not 42** -- but **99 of those are `logic_trigger`**
   nodes, which are logic rather than place and arguably should carry no
   coordinate at all. The genuinely unexpected orphans are the remaining 2
   `item` nodes.

So the useful part of this finding is narrower than filed: *do items need a
position, and if so why are 2 missing?* The "two stores" and "42 orphans" framing
does not survive contact with the data.
## My correction above was itself a wrong-world artefact — retracting it

I measured this in `world_template` (239 nodes: 98 item, 99 logic_trigger) and
concluded there was only one position store, 101 orphans, and 99 of them
triggers. **That measurement described the other world, not this task's.** The
original finding was recorded against `kraktooth_goblin_camp`, and loading it
reproduces the filed numbers exactly:

| | `world_template` (what I measured) | `kraktooth_goblin_camp` (what was filed) |
|---|---|---|
| nodes | 239 | **636** (205 area, 351 way, 29 logic_trigger, 28 item, 23 character) |
| with `x`/`y` | 138 | **594** |
| orphans | 101 | **42** |
| orphans are | 99 `logic_trigger` + 2 item | **all 42 `item`** |

So the filed claim stands: **42 nodes have neither position store, and every one
of them is an `item`.** My "correction" was me making the exact error this audit
has spent the session retracting -- judging a claim against whichever world was
loaded. I had written the method warning into `AGENTS.md` and then committed the
mistake inside the same hour.

The remaining open question is the same one I raised, and it is sharper in this
world: 28 items exist and **42** lack a position, so the count does not even
match the item total -- some items do have one. What the layout does with an
item that has no coordinate is the thing worth checking next.