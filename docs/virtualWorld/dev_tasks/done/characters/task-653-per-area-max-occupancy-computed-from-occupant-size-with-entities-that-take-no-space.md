---
type: task
status: done
area: characters
priority: high
---

# task-653: Per-area max occupancy computed from occupant size, with entities that take no space

**Filed:** 2026-09-30
**Related:** 

## Goal

DECIDED 2026-09-30 by Tommy. Each area gets a max occupancy, and occupancy is computed from the SIZE of what is standing in it, not a headcount. Some areas must hold a titanic dragon; some hold 4 normal-sized creatures; a fairy's house holds 7 small creatures. Some entities take up NO space at all -- a ghost is the example -- so size needs a zero-space flag distinct from 'tiny', because a 1cm spider is tiny but a ghost is intangible. This is the natural consumer of the size property from task-605: size already exists as a trait and is already used for way max_size gating, so occupancy is a second reader of the same axis rather than a new concept.

## Acceptance

- [x] **A per-area budget exists and is authorable** — the area's
      `max_occupancy` property, with a generous default
      (`DEFAULT_MAX_OCCUPANCY = 100`) for areas that declare nothing.
- [x] **Occupancy is a sum of footprints, not a headcount.** `space_of` maps a
      size tier to a named budget unit (`TIER_SPACE`), and the tiers are
      deliberately non-linear: a titanic thing is not six normals.
- [x] **Zero space is a distinct concept from tiny.** `takes_no_space` reads the
      `ghost` tag that `PlayerManager.is_incorporeal` already owns (task-309)
      plus its synonyms, and a ghost costs 0 however large it was authored. A
      1 cm spider is `tiny` and still costs 1.
- [x] **The size is read from the right object.** A `Player` carries `.size`; a
      graph character node does not (it is created bare), so a node's size is
      read from its `properties`, with a `size_*` trait as the fallback for a
      world predating the `size` property. A graph-only resident is scored at
      its own size, not defaulted to `normal`.
- [x] **The four that fit where four people do not** — four `normal` creatures
      and one `huge` one fill the same budget; a dragon alone over capacity is a
      reportable state; a room at zero occupancy always admits anything;
      `fits` refuses only an arrival into a *full* room.
- [x] **Ghosts always fit** — into any room, however full.
- [x] **It is readable** — `world.area_occupancy(area)` and `world.would_fit`
      expose the report; the area description narrates a crowded/full room, and
      says nothing at all for an empty or quiet one.
- [x] **The dead do not occupy a room** (a corpse on the floor is not crowding),
      but `include_dead=True` can count them.
- [x] Tests in `tests/test_occupancy.py` (40 tests), including the description
      wiring and the bare-node cases.

## Implementation — 2026-10-02 (WT-characters-engine)

### Files

- `engine/occupancy.py` — **new**. `space_of`, `takes_no_space`, `area_budget`,
  `occupants`, `occupancy_used`, `occupancy_report`, `fits`,
  `normalize_area_id`, `describe_occupancy`, and the `TIER_SPACE` /
  `ZERO_SPACE_TAGS` / `DEFAULT_MAX_OCCUPANCY` tables.
- `engine/area_description.py` — appends a crowd sentence to the description.
- `virtual_world_engine.py` — `area_occupancy(name)` and `would_fit(name)`.
- `tests/test_occupancy.py` — **new**, 40 tests.

### The decisions

1. **Footprints are a named table, not a formula.** `TIER_SPACE` (tiny 1 →
   titanic 200) is a tunable scale an author can reason about — "a person fills
   a quarter of a default room" — rather than an emergent result of, say, `tier²`.
   The tiers are non-linear because a leviathan is not six normals; it does not
   sit beside them.
2. **`0` as a budget means unbounded, not emptied.** `0` is the obvious way to
   write "no limit" in an editor, and refusing every arrival on that reading
   would be a nasty surprise. `area_budget` treats non-positive as "fall back to
   the default", and a junk value (`"roomy"`) does the same rather than raising.
3. **Capacity is a budget and a reportable state, not a gate on identity.** A
   titanic dragon in a small hall is a legitimate scene, so `fits` always admits
   anything into an *empty* room and only refuses an arrival into a *full* one.
   Nothing in the engine refuses movement on it — `would_fit` is a report.
4. **The consumer is the description, not a movement gate.** The area
   description already narrates who is present; adding "the room is crowded"
   there makes a packed room legible without changing where anyone can walk. The
   `relief.py` privacy score was deliberately **not** switched to footprints: a
   giant is one *witness*, and scoring it as 40 onlookers would be a new bug.
5. **The crowd sentence is quiet by default.** `describe_occupancy` returns `""`
   for an empty room and for one under 40% of budget. A phrase on every area
   trains the reader to skip the sentence; the one time it fires is the time it
   means something.

### A bug the wiring caught immediately

The first `_entity_in_area` had a copied-from-`relief.py` fallback that compared
`area_id` against *itself*, so every character in the world counted as an
occupant of whichever area was being measured — the counts were off by exactly
the whole roster. Caught by the very first test run, and it is why `occupants`
now funnels through a single `normalize_area_id` and compares one resolved id to
one resolved id.

### Verify

```
python -m pytest tests/test_occupancy.py -q                          # 40 passed
python -m pytest tests/test_area_description.py tests/test_area_id_case.py \
  tests/test_area_sounds.py tests/test_beyond_visibility.py \
  tests/test_background_relief_and_washing.py tests/test_npc_perception.py \
  tests/test_realism_perception.py tests/test_room_perception_contract.py \
  tests/test_ghost_visibility.py tests/test_size_property.py \
  tests/test_occupancy.py -q                                         # 156 passed
python tools/js_module_index.py --check                              # OK
python tools/feature_index.py --check                                # OK
```

**Full suite compared by failure NAME against the same clean-master baseline used
for task-538**: 15 failed on both, `Compare-Object` empty.

### Live verification — 2026-10-02, `python app.py` on `VW_PORT=4466`

The reporting surface here is the sentence the reader already sees when they
arrive, so that is what was checked — through `GET /api/area/description`, the
call the client itself makes.

1. `PATCH /api/graph/node/area_blizzard_forest_clearing {"properties":
   {"max_occupancy": 8}}` — a room sized for a couple of people.
2. Added a character node `character_vhaidra_the_titanic` with
   `size: titanic` (200 units) and moved `rat` into the same area (4 units).
3. `GET /api/area/description` now ends:

       an animal is here.
       The room is full.

4. **Counter-case**, so the sentence is not just always-on: the same request
   with `max_occupancy: 10000` returns a description in which none of
   `The room is full / crowded / busy`, `packed past its limits` or
   `cannot properly hold` appear — an empty-sounding room, which is the point.

Live world returned to its prior state afterwards (the titanic test node
deleted, the authored budget reset to the default, `rat` moved back to the
Kitchen).


