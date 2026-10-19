---
type: task
status: todo
area: characters
priority: medium
wiki: "[[World Building/Character Creation & Archetypes]]"
---

# task-737: Intrinsic abilities are droppable: exclude them from take/drop/place and acquire them by grant/revoke

**Filed:** 2026-10-08
**Related:** task-352, task-733, task-537

## What

Treat intrinsic abilities (INTRINSIC_ABILITY_TAGS: spell/ability/innate/intrinsic/power) as non-physical everywhere, not just in appearance: exclude them from the physical-possession verbs (take, drop, place, put, stow, give, steal) and model acquisition as grant/revoke through a physical carrier (hacking chip, spellbook, implant). Today an ability can be dropped on the ground and picked up by anyone.

## Grounding (measured 2026-10-07)

Ability-ness is a **tag** (`engine/equipment.py:16`):

```python
INTRINSIC_ABILITY_TAGS = frozenset({"spell", "ability", "innate", "intrinsic", "power"})
```

It is consulted in exactly two places today:

- `_is_intrinsic_ability` / `_drop_intrinsic_abilities` (`engine/equipment.py:603`) —
  hides abilities from a character's **visible appearance** so others do not see them
  in examine/equipment narrative.
- `engine/items/take_drop_actions.py:737` — the **take** path checks the tags only to
  make an ability **skip hand slots** ("skip straight to carrying"). It does **not**
  forbid possession.

**The hole:** `drop_item` (`take_drop_actions.py:837`) and `place_item`
(`place_actions.py:124`) never check the tag. So an intrinsic ability in a
character's possession can be **`drop`-ped into the area and `take`-n by anyone** —
Violet dropping her invisibility on the ground. Latent, because no content authors
abilities yet.

## How

An ability is **non-physical**, so the physical-possession verbs do not apply:

- Exclude intrinsic abilities from `take`, `drop`, `place`, `put`, `stow`, `give`,
  `steal`. Refuse with a clear message ("your invisibility is not a thing you set
  down"), not a generic failure.
- Acquisition is **grant / revoke**, not take/drop. A physical **carrier** (hacking
  chip, spellbook, scroll, implant) is a normal item — you take/drop/equip the
  *carrier*; equipping/installing **grants** the intrinsic ability node, removing it
  **revokes** it. Two layers: carrier (physical) vs ability (intrinsic).
- Activation is `use` / `toggle` (task-352), not held/dropped.

## Relationship to 352

Abilities are the case that *requires* the per-item cost override: an ability's
`use` may be free or minor while a physical tool's is major, so its tier comes from
`action_costs.<verb>.tier`, with the ability tag supplying the default
(`task-352`). Because the verb set differs (no take/drop; use/toggle/grant/revoke),
the ability's cost table is over that different verb set.

## Acceptance

- [ ] `drop` / `place` of an intrinsic ability is refused with a clear message.
- [ ] `take` / `give` / `steal` of an intrinsic ability is refused.
- [ ] A carrier item grants the ability on equip/install and revokes it on removal
      (a test proves the grant/revoke round-trip).
- [ ] Intrinsic abilities stay out of other characters' examine/appearance (already
      true via `_drop_intrinsic_abilities`).
- [ ] The verb set and the tier source are documented; `npm run build:ts` and the
      unit runner pass.

## Open questions

- Is `grant`/`revoke` its own verb, or is it the effect of `equip`/`unequip` on a
  carrier? (Recommend the latter — no new verb.)
- Do abilities occupy a containment slot on the character at all, or are they purely
  tag-marked nodes owned by the character? Confirm the containment model before
  excluding the verbs.

## Why

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: in a scratch scenario, interact with an intrinsic ability
through the normal character action/command surface, and manage its physical
carrier through Inventory/Equipment. The ability itself is not a ground item;
the spellbook, chip, or implant is.

Current availability: the card reports that an intrinsic ability can currently
be dropped and taken. The proposed carrier grant/revoke interaction is not
claimed as implemented.

Live steps when available:
1. Give a character one intrinsic ability and one physical carrier item that
   grants it. Open Inventory and inspect both records.
   - expected: the carrier is listed as a physical item; the intrinsic ability
     is not presented as a carried object.
2. Attempt `take`, `drop`, `place`, `put`, `stow`, `give`, and `steal` against
   the intrinsic ability through the normal command/action surface.
   - expected: each physical-possession verb returns a clear non-physical
     refusal and does not create an item on the ground or in another
     character's inventory.
3. Equip/install the carrier, then remove it. Inspect the character's abilities
   and the carrier's equipment state after each operation.
   - expected: installing grants the intrinsic ability; removal revokes it;
     the carrier remains the physical object whose ownership changes.
4. Examine the character from another character before and after carrier
   removal.
   - expected: the intrinsic ability does not leak into another character's
     appearance or carried-item list.

These steps define the intended action and Inventory/Equipment behavior; they
do not claim carrier-based grant/revoke exists today.

This section is not a claim that planned UI exists or works today.
