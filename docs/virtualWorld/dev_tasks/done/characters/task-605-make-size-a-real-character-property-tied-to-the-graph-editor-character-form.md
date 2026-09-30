---
type: task
status: done
area: characters
priority: high
---

# task-605: Make size a real character property tied to the graph editor character form

**Filed:** 2026-09-30
**Related:** 

## Goal

**DECIDED 2026-09-30 by Tommy:** add a **separate `size` property to character
nodes**.

`engine/size.py` has 6 tiers (`tiny, small, normal, huge, giant, titanic`) and
ways carry a `max_size` gate, but size lives as a `size_*` **trait**: 0 of 69
library characters and 0 world characters carry one, and `size_tier()` is called
from exactly one place -- the passage gate. A prefixed trait key is invisible in
the graph editor and cannot be filtered or sorted on, so it is promoted to a
first-class character property surfaced in the graph editor character form.

Open question carried forward, not blocking: whether the 6 tiers still span the
range once the occupancy rule below is in play. A 1cm spider and a
world-consuming leviathan are both ends, and 6 buckets may not cover both
without something between `small` and `normal`.

engine/size.py has 6 tiers (tiny..titanic) as a size_* TRAIT, but 0 of 69 library characters and 0 world characters carry one, and size_tier() is called from exactly one place: the way max_size passage gate. Promote size to a character property surfaced in the graph editor character form.

## Acceptance

- [x] `size` is a first-class character property, not only a trait
- [x] The `size_*` trait keeps working, so task-187 worlds are unchanged
- [x] The property wins when both are present, and an unrecognised value falls
      back rather than being stored
- [x] Loaded from a library definition, validated against the six tiers
- [x] Serialized in the `/api/state` player payload
- [x] Settable from the graph editor character form
- [x] A bad value is refused with 400 and does not clobber a good one
- [x] Covered by regression tests pinning the precedence
- [x] Verified live in the browser

## Resolution (2026-09-30)

`engine/size.py` gained `size_name(player)`, which resolves in this order:
the `size` property, then a `size_*` trait, then `normal`. `size_tier()` is now
a lookup over that, so both existing readers (way `max_size` gating, and
task-653's occupancy) read one function.

`Player.size` is `None` until authored. **That is load-bearing and I got it
wrong first time**: defaulting it to `"normal"` made the property outrank every
hand-authored trait, and two `TestSizePassage` tests failed because the way gate
had silently stopped working. `None` means "not authored", which is what lets
the trait fallback fire.

Also changed: `effects.py` loads `size` from a library definition and validates
it against the six tiers; `serialization.py::_serialize_player` publishes it (the
inspector reads `player.size` from the state payload, and without this the
control reverted to "not set" on every render); `player_ops.py` accepts
`size` on `POST /api/players/<name>`, rejecting anything outside the six with a
400; and the character inspector's vitals block gained a **Size** dropdown
carrying a tippy that says what the two consumers do with it.

**Verified live**, full round trip through the real endpoint:

| step | result |
|---|---|
| initial | `null` (not authored) |
| set `giant` | 200 |
| read back from `/api/state` | `"giant"` |
| control re-renders | `<option value="giant" selected>`, "not set" deselected |
| set `colossal` | **400** |
| value after the bad write | still `giant` -- a refused write does not clobber |
| clear (`null`) | back to the trait fallback |

8 regression tests in `tests/test_size_property.py` pin the precedence
explicitly, including the case that broke it: trait-only, property-only, both,
unrecognised-with-trait, unrecognised-without, case/whitespace, no player, and
every tier resolving to its own index.

**Not done here, deliberately:** the 6 tiers still may not span the range once
occupancy is in play -- a 1cm spider and a world-consuming leviathan are both
ends. Left as the open question on this task rather than guessed at.

- TODO
