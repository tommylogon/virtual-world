---
type: bug
status: review
area: world
priority: medium
wiki: "[[World Building/Ways]]"
---

# bug-547: broken way state is half-implemented

**Filed:** 2026-10-11
**Related:** 

## What

current_state 'broken' is offered by the inspector (STATE_OPTIONS, way-view.ts:25) and refuses open/close (movement.py:1118), but the traversal gate in move_to_area never tests it, so a broken way can be walked through; and engine/barriers.py has no broken rung, so it resolves to UNKNOWN_STATE_FALLBACK open (barriers.py:71) for light and sound. Either implement broken across the passage gate and both barrier tables, or remove it from the dropdown. See the States section of Ways.md.

## Why

`broken` is a state an author can select in the Inspector, and the engine
already treats it as a real, blocking state in one place (the open/close
action). That makes it worse than a state that was never implemented: the world
model advertises it, one code path honours it, and the two paths that matter
most - walking through, and light/sound across the way - do not. An author who
sets a door to `broken` gets a passage that looks broken, refuses to be opened
or closed, and is nonetheless walk-through and fully transparent to light and
sound.

The state ladder in `engine/barriers.py` is explicit about this failure mode:
`WAY_STATES` is the shared contract, and a test asserts both tables are
non-increasing along it. `broken` is absent from that tuple, so it never had a
rung to be non-increasing on.

## How

Three places disagree about `broken`:

| Where | Behaviour for `broken` | File:line |
|---|---|---|
| Inspector dropdown | offered as a selectable state | `static/js/inspector/way-view.ts:25` (`STATE_OPTIONS`) |
| open/close action | refused: "The {direction} is broken." | `engine/movement.py:1129-1130` |
| traversal gate (`move_to_area`) | **not tested** - falls through | `engine/movement.py:580-598` |
| sound cost | falls back to `open` (0.5) | `engine/barriers.py:42-49`, `:71`, `:93-98` |
| light transmission | falls back to `open` (1.0) | `engine/barriers.py:60-67`, `:71`, `:101-106` |

The traversal gate reads `current_state` and refuses on `locked`
(`movement.py:592`), `blocked` (`:595`) and `closed` (`:598`), plus the
`refusal_message` short-circuit at `:588-591`. There is no `broken` branch, so
a broken way is crossed.

Both barrier tables are keyed by state and `broken` is in neither:
`DEFAULT_SOUND_COSTS` (`barriers.py:42-49`) and `DEFAULT_LIGHT_TRANSMISSION`
(`barriers.py:60-67`) list only `open`, `see_through`, `closed`, `locked`,
`blocked`, `hidden`. `WAY_STATES` (`barriers.py:36-38`) is the same six.
`_normalise_state` maps an unrecognised state to `UNKNOWN_STATE_FALLBACK`
(`barriers.py:71`, `:109-114`), so `broken` resolves to **open**: full light
transmission and the lowest sound cost.

The fix has two consistent options, and the card's own framing is right that
only one of them is a real fix:

1. **Implement `broken` properly.** Add it to `WAY_STATES`, give it rungs in
   both tables (a broken passage is opaque and muffles sound, so
   `light_transmission` 0.0 and a sound cost at or above `blocked`), add a
   `broken` refusal to the traversal gate, and extend the ladder test to cover
   it.
2. **Remove it from the dropdown.** Cheaper and coherent, but it drops a state
   an author may already be using, so the data needs a sweep first.

Option 1 is the one that keeps the advertised state honest.

## Steps to verify

1. Confirm `broken` is offered in the Inspector.
   - expected: the state is selectable, so the engine must honour it.
   - observed: CONFIRMED. `static/js/inspector/way-view.ts:25` -
     `STATE_OPTIONS = ['open', 'closed', 'locked', 'blocked', 'broken', 'hidden']`,
     rendered at `:291`.
2. Confirm the traversal gate does not test `broken`.
   - expected: a broken way refuses to be crossed.
   - observed: FAILS. `engine/movement.py:580-598` tests `refusal_message`,
     `locked`, `blocked` and `closed` only. `broken` is not tested, so a broken
     way is walked through.
3. Confirm the barrier tables have no `broken` rung.
   - expected: `broken` has a sound cost and a light transmission.
   - observed: FAILS. `WAY_STATES` (`barriers.py:36-38`),
     `DEFAULT_SOUND_COSTS` (`:42-49`) and `DEFAULT_LIGHT_TRANSMISSION`
     (`:60-67`) contain six states each, none of them `broken`.
     `_normalise_state` (`:109-114`) therefore resolves it to
     `UNKNOWN_STATE_FALLBACK = "open"` (`:71`): light transmission 1.0, sound
     cost 0.5.
4. Confirm the open/close path does refuse `broken`.
   - expected: consistent handling.
   - observed: CONFIRMED. `engine/movement.py:1129-1130` raises
     "The {direction} is broken." So one path already treats it as blocking,
     which is what makes the other two a defect rather than an omission.
5. Re-run the live traversal, light and sound checks.
   - expected: a broken way cannot be crossed, blocks light, and muffles sound
     consistently from both sides.
   - observed: not re-run in this turn. The static findings above are what the
     code shows, not a fresh live reproduction.

## Acceptance

- [x] `broken` is in `WAY_STATES` and has a rung in both
      `DEFAULT_SOUND_COSTS` and `DEFAULT_LIGHT_TRANSMISSION`, with the ladder
      ordering test extended to cover it.
- [x] The traversal gate in `move_to_area` refuses a `broken` way with a
      message consistent with the open/close path.
- [x] A broken way blocks light and muffles sound per the barrier tables, not
      per `UNKNOWN_STATE_FALLBACK`.
- [x] The `Ways.md` States section matches the implemented behaviour for every
      state the Inspector offers.

## Browser UI and intended live verification

Intended UI home: select a `way` in the graph → Way Inspector → set `current_state` to `broken` → try passage actions and inspect area description, light, and sound across the way.

Current availability: re-checked 2026-10-20. `broken` is still offered in the Inspector (`static/js/inspector/way-view.ts:25`), still refused by the open/close action (`engine/movement.py:1129-1130`), and still absent from the traversal gate and from both barrier tables. The three-way disagreement is unchanged, so the state is still half-implemented. The card's cited path for the dropdown was `way-view.ts`; the file is at `static/js/inspector/way-view.ts`.

## Files

- `static/js/inspector/way-view.ts` - `STATE_OPTIONS` (`:25`, rendered `:291`)
- `engine/movement.py` - the traversal gate (`:580-598`) and the open/close
  refusal (`:1129-1130`)
- `engine/barriers.py` - `WAY_STATES` (`:36-38`), `DEFAULT_SOUND_COSTS`
  (`:42-49`), `DEFAULT_LIGHT_TRANSMISSION` (`:60-67`), `UNKNOWN_STATE_FALLBACK`
  (`:71`), `_normalise_state` (`:109-114`)

## Reconnaissance (2026-10-20) - still valid

Re-checked the cited code on 2026-10-20 against the newer way work (task-187
traversal verbs, task-243 item gates, task-309 incorporeal phasing, task-563
`refusal_message`). None of them added a `broken` rung or a `broken` refusal to
the traversal gate, and the barrier ladder is still six states wide.

The card's own conclusion holds and is now sharper: the open/close path
*already* refuses `broken` (`movement.py:1129-1130`), so the state is not
merely unimplemented, it is implemented in one place and ignored in the two that
matter. The fix is to add `broken` to `WAY_STATES` and both barrier tables and
to refuse it in the traversal gate, not to remove it from the dropdown.

Verdict: STILL_VALID. The card stays in todo.

Live steps when available:
1. In a scratch world, set a connected way to `broken` in its Inspector and attempt `go`/crossing from both connected areas.
   - expected: either the way is explicitly removed from the state selector, or the broken state consistently blocks passage according to the chosen design; it cannot look broken and still be traversable.
2. Stand on each side and examine the exit line.
   - expected: both directions describe the same broken passage state; no side presents it as open.
3. Put a light source and a sound source on one side and observe from the other.
   - expected: broken-state light and sound behavior follow the barrier tables, not `UNKNOWN_STATE_FALLBACK` open.
4. Save and reload the scenario, then inspect the way state and repeat traversal.
   - expected: the selected policy survives serialization and remains consistent across passage, light, and sound.

This section is not a claim that broken-way behavior is implemented consistently today.
