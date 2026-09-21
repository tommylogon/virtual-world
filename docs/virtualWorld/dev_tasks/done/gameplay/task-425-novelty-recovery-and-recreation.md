---
type: task
status: done
area: gameplay
priority: high
---

# task-425: Novelty recovery — Entertainment from places, things and people

**Filed:** 2026-09-21  
**Relates:** task-136 (novelty traits), task-423 (social interactions), task-410
(fixtures).  
**Spec:** `engine/movement.py:694-708`, `engine/items/take_drop_actions.py:41`,
`vital_rates.py` (Entertainment decay).

## Outcome (2026-09-21)

Done. Entertainment is no longer pinned at 0, and it settles rather than
pegging: a background week ends at **40.1 avg / 25 min / 50 max at 15 min/tick**
and **39.3 / 24 / 50 at 1 min/tick**, 23/23 alive. The two tick lengths agreeing
is the property that matters — the source is measured in game minutes.

- `engine/novelty.py` — one curve for three subjects, `NOVELTY_MAX = 15`,
  `curious` ×1.5, `homebody` 0, `wanderlust` recovers on half the window (which
  is how the old `+3 on re-entry` survives). Config
  `entertainment.novelty_recovery_minutes` (default 120).
- `observe_area` now reports each subject's **freshness measured before it
  refreshes the observation** — that is why the curve is computed there and not
  re-derived by the caller: an entry both refreshes the tick and earns novelty,
  and reading the tick afterwards reports every arrival as already stale.
- `movement.py` pays per subject the arrival made fresh (area, things, people)
  instead of a flat "+15 for a new area"; the `was_new`/`wanderlust` branches are
  gone. `visited_areas` is still written because spatial memory reads it.
- Item discovery is the same curve. The old "+8 once ever" set test is gone.
- Three authored fixtures (`camp_drum`, `knucklebones`, `story_fire`) placed by
  `tools/add_renewable_sources.py` in Chief's Pit, Camp Entrance and Cooking
  Area, plus a `_recreate` step in the background tier, which gates on need —
  that gate is also the anti-spam.

### Two decisions worth recording

**Item novelty is paid on perception, not only on take/use.** The subject table
below says "item — taking or using it", and the non-goal defers perceptual
novelty "until the perception path can carry it". The perception path now carries
it: entering an area observes what is visible there, so paying on take would pay
**zero** — the entry already stamped the item. Paying at perception is strictly
better and is what `observe_area` already computes. The take/examine path is kept
as a fallback for items perception could not see: hidden until examined, or taken
out of a container.

**The curve is squared, not linear.** A linear ramp pays a little for any gap: a
two-room bounce every 10 minutes earned +1 a hop, 6/hour against Entertainment's
1.8/hour decay — the treadmill the window was meant to prevent, and the "window
comparable to the decay time" reasoning further down was wrong about it. Squaring
makes a short gap worth nothing (10 minutes of 120 pays 0; 40 minutes pays 2)
while a real absence still pays in full. It also matches "rising toward +15"
better: slow at first, then real.

### Not done here

`visited_areas` and `discovered_items` are **not deleted**, because they have
consumers beyond novelty: spatial memory's known-route filter, the `adventurous`
micro-modifier in `tick_manager`, `take_drop_actions`' bookkeeping, and three
frontend readers (`room-context.js`, `memory-context.js`,
`contextual-actions.js`). Both are still written, so those readers keep working.
Retiring them is filed as **task-430**.

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
about that subject, which already carries who/what/where/when. Then:

```
last_enjoyed(subject) = the tick of the live observation memory about subject
```

and the recovery curve reads that timestamp. `visited_areas` and
`discovered_items` are **deleted** rather than migrated: two more parallel
structures gone, which is the same move as `areas`/`rooms` and `entity_ids`.

**The observation memory already exists** (task-403 slice 1, 2026-09-21) — this
dependency is met, so the shape below is what is actually on `Player`, not a
proposal:

| need | read this |
|---|---|
| last seen | `player.observation_tick(subject_id)` → tick or `None` |
| has seen | `player.has_seen(subject_id)` |
| the memory | `player.observation_memory(subject_id)` → `{entity_ids: [subject_id], location, kind, tick, visits, tags, text, superseded_by?}` |
| subject index | `player.memory_index` (`subject_id → memory_id`) |

`kind` is `"area"` / `"item"` / `"character"`, which is the subject kind.
Recording is `player.record_observation(subject_id, text, tick, kind=..., location=...)`,
and it **refreshes in place** — sightings do not chain, so volume stays bounded
by subjects. `supersede_observation(subject_id, reason)` retires a belief that
was replaced and is the only path that sets `superseded_by`.

Measured boundedness (task-403): 908 memories after a week at 1 min/tick vs 912
after a week at 15 min/tick — 15x the game time, the same count.

Novelty therefore no longer needs its own write path: entering an area is
already an observation (`engine/movement.py`), and item discovery can record one
too. `novelty_bonus(subject, tick)` only has to *read* `observation_tick` and
scale it — plus scale the trait multipliers.

**Note on what "supersede instead of append" turned into.** The original sketch
had each visit supersede the previous observation; implementation refreshes the
one memory in place, which achieves the same bound with a smaller structure. The
trace remains the history (bounded, salient-first) while the memory holds the
current belief — the existing trace/memory split.

**Emergent bonus, and one caveat.** Forgetting re-enchants the world: an area a
character can no longer remember becomes novel again, which is a lovely
consequence of the coupling and worth keeping — `Player._trim_memories` drops the
evicted subject from `memory_index` so this falls out for free. The caveat is the
coupling itself — suppression, eviction and deliberate forgetting now move a
vitals system, so that has to be stated rather than discovered.

## Changes

1. **Delete** `visited_areas` and `discovered_items`; derive last-seen from
   observation memories (the index they needed now exists — see above).
2. Novelty helper (one place): `novelty_bonus(subject, tick)` returning the scaled
   bonus. Recording is already handled by `Player.record_observation`; this only
   reads `observation_tick`.
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
- A subject with **no** observation memory pays full novelty; a visit refreshes
  the previous observation in place rather than appending a second one (volume
  stays bounded by subjects — already true, see task-403 slice 1).
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
