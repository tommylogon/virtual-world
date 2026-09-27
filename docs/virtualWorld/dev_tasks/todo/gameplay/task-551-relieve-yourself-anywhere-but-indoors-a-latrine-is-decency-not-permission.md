---
type: task
status: todo
area: gameplay
priority: high
---

# task-551: Relieve yourself anywhere but indoors; a latrine is decency, not permission

**Filed:** 2026-09-27
**Related:** task-549

## Goal

Bladder relief is currently only possible in an area tagged latrine/toilet/bathroom. Everywhere else the meter just maxes and Hygiene decays, which punishes a world for lacking a fixture. Let a character relieve themselves in any outdoor area; the tag marks a proper place, not the only legal one.

## Measured (2026-09-27) — already possible anywhere; nobody has any *privacy*

Relief is **not** gated, and the design intent is right: you can relieve yourself
wherever you are. Two paths exist and they disagree.

- **Foreground / agent** — `static/js/agent/prompt-builder/contextual-actions.js`
  offers the verb `relieve — relieve yourself (your bladder is full)` to any LLM
  or human character at `Bladder >= 65`, with no area check at all. Two authored
  actions in `world_template.json` carry `"success_message": "You relieve
  yourself"`. Anywhere goes.
- **Background (soak NPC)** — `engine/background_simulation.py` requires
  `_service_here(p, RELIEF_TAGS)`, so a background character can only relieve in
  an area tagged `latrine`/`toilet`/`privy`/`restroom`/`bathroom` or holding such
  an item. If neither is reachable the `_act` branch returns `None` and the
  character simply does not do it.

So the background tier is **more** restricted than the foreground, not less. And
that is the measured cause of the hub: in the Kraktooth camp, `Waste Disposal` is
the **only** `RELIEF_TAGS` area out of 84, and it is the busiest room in the world
by shared occupancy — 45,844 shared ticks across five pairs. Every background
goblin in the map funnels into the one latrine because for them it is the only
option, not because they prefer each other's company.

## What is actually missing: privacy

Nobody has a notion of a secluded place. A character should reasonably go
somewhere private — **not indoors, not a nest, not a living room, and away from
other people's line of sight** — but there is no such concept to express it:

- no occupancy check, so "away from others" cannot be scored;
- no line-of-sight or visibility test to rank a candidate area;
- no preference among candidates, so the background path takes whatever the
  nearest tag match is (`_target_step` is a plain nearest-by-BFS-hops search).

The fix is a *preference*, not a permission: any character may relieve anywhere,
and a character who cares about privacy picks the best nearby option rather than
the only option.

## Open decisions

1. **How is "private" scored?** Proximity of other characters, whether anyone can
   see out of the area, or a `private`/`secluded` tag. A tag is consistent with
   the rest of the design, but it puts the work back on the author for every area.
2. **What does the area's own character contribute?** The author names *nests* and
   *living rooms* as the places that are off-limits, so a small "private" or
   "public" tag vocabulary probably carries it.
3. **What if nothing is private?** A character should still relieve, less
   comfortably — a `Dignity`-style cost, or an embarrassed log line, rather than
   the current `return None`, which does nothing at all.
4. **Should privacy vary by character?** A goblin in a nest is fine; a human guest
   in someone else's sleeping hall is not. That is task-549's species/faction
   input.

## Acceptance

- A background character can relieve themselves with no latrine anywhere in the
  world, matching the foreground path.
- Given a choice between a shared latrine and a secluded spot, a character who
  values privacy takes the secluded spot.
- A test asserts the hub does not form: with privacy-aware selection, occupancy in
  the single latrine falls relative to the cast size.

## Related

- task-549 — whether a character's species changes what counts as private
- task-550 — an unowned camp water is what pulls the humans in the first place



- TODO
