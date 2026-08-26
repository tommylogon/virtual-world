# Task 335 — Fixture-aware relieve + turn-message polish

**Status:** In Review — all four items closed 2026-08-24. Toilet-aware
relieve and the emote pronoun fix were already landed by earlier sessions;
this pass added bare eat/drink auto-pick and fixed structured eat/drink
losing its item. Full suite green (1116 passed). Browser E2E pending.

## Implementation notes (2026-08-24)

1. **Structured eat/drink keeps its item** — `normalizeStructuredAction`
   (`static/js/agent/action-normalizer.js`) had NO case for eat/drink, so
   `{action:'eat', item:'burrito'}` fell through to `default: return verb`
   and became bare `eat`. Added `eat/consume` and `drink/quaff` cases:
   `{action,item}` → `eat burrito`; bare payload → `eat` (auto-resolves
   backend-side).
2. **Toilet-aware relieve** — verified already implemented
   (`routes/action.py` relieve branch checks `toilet`/`bathroom` tags in
   the area; no fixture → corner message + urine smell + puddle spawn).
3. **Bare-eat grammar + auto-pick** — bare `eat`/`drink` previously fell
   through the dispatcher (only `"eat "` with trailing space matched),
   producing *"You stop waiting. jake halloway eat."*. Now:
   - `routes/action.py` catches both bare and suffixed forms.
   - `_consume_item` (`engine/items/consume_actions.py`) with a blank name
     auto-picks the first consumable in reach via new
     `reachable_items()` (extracted from find_reachable's visibility walk,
     `engine/item_reach.py`) — carried before area, deterministic order,
     same validity rule as the normal path. Nothing suitable →
     "You have nothing to eat." / "...drink."
   - Side-fix: a blank name never reaches `find_item_node` anymore — its
     containment match (`'' in anything`) would have grabbed the first
     carried object regardless of edibility.
4. **Emote prefix doubling** — verified already fixed (G1 pronoun
   stitching, see presence-gap-analysis-2026-08.md).

## Why

Miki entered the women's restroom, ran `relieve`, and got *"You relieve
yourself in a corner. That's going to stink up the place."* — standing in
a restroom with no toilet item (none existed; Tommy hand-placed toilets at
ticks 95/96 to patch the gap). Then Jake's `use toilet` hit the
carried-only lookup bug (fixed same day via engine/item_reach.py — reload
to verify), but `relieve` itself still has no notion of toilet fixtures.

## Work items

1. **Structured eat/drink LOSES its item (primary bug)** — Tommy submitted
   a turn that parsed down to bare `eat` ("eat item burrito" →
   `act eat`, tick 20-22: *"You stop waiting. jake halloway eat."* — the
   burrito vanished). Root-cause the human path: structured payload
   `{action:'eat', item:'burrito'}` → command-string building (composer /
   `_normalizeStructuredAction` / routes dispatch) drops the item for
   eat/drink-class verbs somewhere before execution. Fix the flattening,
   then re-test `eat burrito` from BOTH the panel payload and raw text.
2. **Toilet-aware relieve** — when relieving, resolve a fixture in reach
   (engine/item_reach.find_reachable: name contains toilet/urinal, or a
   `toilet` mechanical tag if we add one) and branch:
   - fixture found → normal message, no stink penalty, hygiene benefit
   - none → current corner behavior (stink warning)
3. **Bare-eat grammar** — `eat` with no item produced *"You stop waiting.
   jake halloway eat."* (tick 22). Fix verb conjugation / phrasing of the
   no-item fallback.
4. **Emote prefix doubling** — witness lines render *"jake halloway he
   grins happily…"* when LLM emote text starts with a pronoun (ticks 23,
   42). Same family as the second-person converter gotcha (guide §20);
   strip/merge leading name+pronoun pairs in emote rendering.

## Verification

- Panel-submitted `{action:'eat', item:'burrito'}` → `eat burrito`
  (normalizer cases added); raw text `eat burrito` unchanged
- Bare `eat`/`drink`: 4 new unit tests in
  `tests/test_item_actions.py::TestConsumeItem` — auto-pick works,
  carried beats room, drink skips food-only items, nothing consumable →
  friendly error. Full suite: 1116 passed.
- Relieve fixture branching + emote pronoun fix verified by code read
  (landed in earlier sessions). Browser E2E still pending.
