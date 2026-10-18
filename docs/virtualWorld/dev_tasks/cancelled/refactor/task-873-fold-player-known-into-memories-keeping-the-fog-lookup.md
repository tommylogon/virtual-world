---
type: task
status: cancelled
area: refactor
priority: medium
horizon: later
goal: Knowledge has one store of record, not two (fog registry versus memory records).
wiki: "[[Persona]]"
---

# task-873: Fold player.known into memories, keeping the fog lookup

**Filed:** 2026-10-18
**Related:** 

## What

`player.known` is the fog / perception registry (`engine/fog.py`): a plain list of node ids and names the character has seen, read by room perception, `agent_memory.is_known`, and condition triggers. `player.memories` are records (`engine/agent_memory.py`, `remember` / `recall`): episodic, semantic, procedural, social, belief. They overlap in meaning ("I know this area" versus "I remember being here") but not in reader.

This card makes memories the store of record for knowledge, while keeping the fast id lookup the fog gate needs.

## Why

Two independent stores for "what this character knows" will drift, and the one nobody reads becomes the lie. This is a consolidation, not a rename: the perception gate must keep working.

## How

1. Decide the direction (record it in the card): memories as the store and `known` a derived index over them, OR `known` entries gain a memory record and stay the fast index. Do not keep two independent stores.
2. Keep `engine/fog.py` gating and `agent_memory.is_known` working; the id lookup is on the perception path and must stay fast.
3. Migration: a save that carries `known` must load.
4. Round-trip.

## Browser UI and intended live verification

N/A for the store change. Observable path: a walk writes the knowledge, the Room perception gate still hides what is not known, and `recall` can surface the same knowledge.

## Steps to verify

1. Walk through an area.
   - expected: the knowledge is recorded and the fog / perception gate reflects it.
   - observed: TODO
2. Memory recall for the same knowledge.
   - expected: `recall` can surface it from the single store.
   - observed: TODO
3. Load a save that carries `known`.
   - expected: it migrates without loss.
   - observed: TODO

## Acceptance

- [ ] One store of record for knowledge.
- [ ] The fog / perception gate still works and stays fast.
- [ ] A save carrying `known` migrates on load.
- [ ] Open decision recorded: the direction (memories-as-store or known-as-index).

## Files

- `engine/fog.py`
- `engine/agent_memory.py`
- `player.py`
- `engine/serialization.py`
- `tests/test_known.py`
- `tests/test_fog.py`

## Retracted 2026-10-18

Duplicate. `task-734` (Knowledge is memory: fold known/recipes/known-places into one prose+data record with episodic vs semantic kinds) already covers folding `player.known` into the memory model, with more detail (a lifecycle per kind, the derived-index rule for `discovered_*`, and migration). This card is cancelled; the `known` consolidation lives on task-734. Related: task-736 (cognitive map), task-789 (per-area observation memories).
