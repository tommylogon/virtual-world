---
type: task
status: todo
area: gameplay
priority: high
---

# task-425: Novelty recovery — Entertainment from places, things and people

**Filed:** 2026-09-21  
**Relates:** task-136 (novelty traits), task-423 (social interactions), task-410
(fixtures).  
**Spec:** `engine/movement.py:694-708`, `engine/items/take_drop_actions.py:41`,
`vital_rates.py` (Entertainment decay).

## Problem

Entertainment has **no recurring source**, so it sits at 0 forever.

Today (`engine/movement.py:697-708`):

```python
was_new = area_name not in player.visited_areas
player.visited_areas.add(area_name)
if was_new:            # +15, once per area, ever
elif wanderlust:       # +3, ONLY for wanderlust characters
```

Item discovery (`take_drop_actions.py:41`) is the same shape — once per item, ever.
`ACTIVITY_REGEN` has sleeping, resting, waiting, meditating, bathing, sitting and
lying: **nothing recreational**. So a settled camp goblin's Entertainment decays
(0.07/min ≈ 100/day) to zero within a day and nothing can restore it.

## Design: novelty is a per-subject recovery curve

Replace the binary new/familiar test with a **recovering** bonus, per character:

```
freshness = clamp((now - last_enjoyed_tick[subject]) / NOVELTY_RECOVERY_MINUTES, 0, 1)
bonus     = round(NOVELTY_MAX * freshness)      # NOVELTY_MAX = 15
last_enjoyed_tick[subject] = now
```

Behaviour the user specified: bounce between two areas and you get +15 on the new
one, **0** on the one you just left, and **0** immediately on return; wait a while
and it pays again, rising toward +15 as the subject goes stale. It saturates back
at the original novelty value, never above it.

**Subjects** — one mechanic, three uses:

| subject | triggered by | note |
|---|---|---|
| area | entering it | replaces `visited_areas` membership test |
| item | taking or using it | replaces `discovered_items` membership test |
| person | meeting/socialising | gives task-423 a recurring Entertainment source, and reuses the existing `_grant_meeting_entertainment` |

### Farming guard (important)

With a short recovery window this is a travel treadmill: bounce between two rooms
and Entertainment is free. Two acceptable fixes, pick one and hold it —

- **A window comparable to the decay time** (Entertainment empties in ~24h; a full
  refresh somewhere in the 1–4h range), so a route earns variety but loitering and
  bouncing do not; or
- **diminishing returns within a day** (the same subject pays progressively less
  until it has genuinely gone stale).

Make it a config key (`entertainment.novelty_recovery_minutes`, default to be
decided) so the tuning lives with the other rates.

### Derive the timestamps from observation memories (preferred)

`visited_areas` and `discovered_items` are **sets** today. Rather than grow them
into name→tick maps, take `last_enjoyed[subject]` from the **observation memory**
about that subject — `{subjects, verb, object_id, area_id, tick, supersedes}` —
which already carries who/what/where/when. Then:

```
last_enjoyed(subject) = newest non-superseded observation memory about subject
```

and the recovery curve reads that timestamp. `visited_areas` and
`discovered_items` are **deleted** rather than migrated: two more parallel
structures gone, which is the same move as `areas`/`rooms` and `entity_ids`.

**Mandatory condition — one observation per subject, superseded, not one per
visit.** Absence of a memory must mean "never been", never "went but didn't
record it". So entering an area (or seeing an item) **supersedes** the previous
observation for that subject instead of appending a new one:

- volume stays bounded by *subjects*, not by visits (a week of wandering does not
  become thousands of memories);
- "when did I last see this" is a single lookup, not a scan;
- the trace remains the history (bounded, salient-first) while the memory holds the
  current belief — the existing trace/memory split.

**Depends on:** the observation-memory work (`entity_ids` populated — currently
0/17 — plus a per-subject latest index or the memory graph). Without an index,
every area entry is an O(memories) scan, and memories are uncapped now.

**Emergent bonus, and one caveat.** Forgetting re-enchants the world: an area a
character can no longer remember becomes novel again, which is a lovely
consequence of the coupling and worth keeping. The caveat is the coupling itself —
suppression, eviction and deliberate forgetting now move a vitals system, so that
has to be stated rather than discovered.

## Changes

1. **Delete** `visited_areas` and `discovered_items`; derive last-seen from
   observation memories (requires `entity_ids` + a per-subject index — see
   "Derive the timestamps" above).
2. Novelty helper (one place): `novelty_bonus(subject, tick)` returning the scaled
   bonus, and superseding the subject's observation memory rather than appending.
3. `movement.py` area entry and the item discovery path use it, replacing the
   `was_new` / `wanderlust` branches. Keep the trait scaling (`curious` ×1.5,
   `homebody` 0).
4. **Recreational fixtures** — entertainment should also come from *things in the
   world*, the same fixture pattern as the wash spot: `on_use → adjust_vital
   Entertainment +N`. A drum, a dice game, a book, a fire to sit at. This is what
   makes a camp lively, and it means Entertainment is authored, not trickled.
5. Config: `entertainment.novelty_recovery_minutes` (+ Engine Config schema).

## Acceptance

- Bouncing between two areas repeatedly yields ≈0; leaving one alone for the
  recovery window and returning yields a bonus that saturates at 15.
- A background week soak at 1 and 15 min/tick ends with **Entertainment above 0**
  and settling, not pinned at 0.
- Item interaction pays on the same curve; a first-ever discovery still pays full.
- A subject with **no** observation memory pays full novelty; a visit supersedes
  the previous observation rather than appending a second one (volume stays
  bounded by subjects).
- An old save carrying `visited_areas`/`discovered_items` loads without error and
  pays novelty from memory instead (the stale sets are ignored, so the first visit
  after upgrading pays full — the generous reading).
- The farm guard holds: repeatedly entering the same area produces far less than a
  fresh route over the same time.

## Non-goals

- Perceptual novelty ("I *saw* a known item in a new area") — that is a perception
  trigger, not an action; defer until the perception path can carry it.
- Social interaction itself (task-423) — this only supplies the bonus it grants.
- Sanity, which wants its own sources (comfort, company, fear relief).

## Verification

- Unit: the curve — immediate re-entry 0, mid-window partial, saturated 15.
- Unit: set→map migration on load.
- Unit: a recreational fixture's authored `adjust_vital Entertainment` applies
  (background and player).
- Soak: Entertainment non-zero and stable over a week.
