# Bug 25 — take/wear no-ops read as failures and duplicate-wear stacks

**Status:** In Review — fixed 2026-08-24, 4 new/updated tests, full suite
1125 passed. Browser E2E pending.

## Found

2026-08-24 taco_bell run (post-reload):

1. miki, ALREADY carrying the Mystery Cream Sauce, submitted
   `take` again → *"You search for 'the mystery cream sauce packet' but
   can't find it here. Items you can see: Booth Table, tyler, miki doki…"*
   — no inventory check, and the "items" hint listed CHARACTERS. She then
   spiraled for a full react phase about the item "vanishing".
2. miki spawned WEARING one Blue Butterfly Earring and carrying a second
   (the found one). `wear` happily equipped it → worn line rendered
   *"Blue Butterfly Earring over Blue Butterfly Earring"*, the panel kept
   offering `wear`, and the LLM ruminated about the "missing" earring.

## Fix

- `engine/items/take_drop_actions.py` — take_item now checks carried +
  equipped roots FIRST (before darkness/state lookups): carried →
  "You're already carrying the X." (soft success, no raise), worn →
  "You're already wearing the X." The not-found hint list now includes
  items only, never characters.
- `engine/equipment.py` — equip_item refuses a second instance of the
  same-named worn item: "You're already wearing the X." Covers both the
  two-copies case and the same-node re-equip quirk (the stale CARRYING
  edge made find_item_node resolve the equipped copy, which used to
  append to the slot stack again).
- **Deliberate behavior change:** the old
  `test_equip_idempotent_adds_to_stack` pinned the stack-duplication
  quirk as "current engine behaviour"; updated to pin the refusal
  (`test_equip_same_item_twice_refused`). Different-named items on the
  same slot still layer normally (layering tests unchanged and green).

## Tests

- `test_item_actions.py::TestTakeAlreadyHeld` — carried → "already
  carrying", worn → "already wearing", not-found hint lists items only.
- `test_equipment_system.py::TestEquipmentLayering::test_cannot_wear_second_copy_of_same_item`
  and `TestEquipmentBasic::test_equip_same_item_twice_refused`.

## Verification

- pytest full suite 1125 passed
- Browser: wear the same item twice → second attempt refuses; take a
  carried item → "already carrying", no search-failure spiral.
