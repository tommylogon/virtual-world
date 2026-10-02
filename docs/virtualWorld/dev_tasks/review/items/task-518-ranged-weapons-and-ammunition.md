---
type: task
status: review
area: items
priority: medium
---

# task-518: Ranged weapons and ammunition

**Filed:** 2026-09-24
**Related:** task-54, task-362, task-427

## Goal

Add a real ranged-weapon and ammunition model for Vekka's compact hunting bow.
Today the only "ranged" item is a scripted one-shot, not a weapon.

## Context

- `data/library/items/crossbow.json` has no `damage`; it fires via an `on_use`
  message plus a second `on_use` `destroy_self`, with `uses: 1`. It is a
  scripted set piece.
- Melee weapons use `damage`/`damage_type` (e.g. `data/library/items/cleaver.json`)
  and the universal weapon/attack path (task-54); combat finds a wielded/held
  weapon by name in inventory (`engine/combat.py:469-487`).
- No engine code references arrow/ammo/projectile/ranged (grep, 2026-09-24).
- Gear: Vekka's hunting bow, with arrows implied by the shared feathers/arrows
  vocabulary.
- Related: task-427 (spawners/death), task-504 (quantity for stacked ammo), and
  task-99/task-313 (area grids/facing) if ranges matter later.

## Proposal

- A `bow` (and `arrow`/`arrows`) template with `damage`,
  `damage_type: "piercing"`, and `equip_slots` (the hand pair as two-handed, or
  back), plus an attack path that requires and consumes one arrow.
- Ammo as a stackable item with quantity (task-504) or `uses`; firing
  decrements; zero ammo fails cleanly.
- Decide range/targeting: same-area only first, or tie into area grids/facing
  later.
- Re-author `crossbow.json` on the model, or document it as an intentional
  scripted exception.

## Acceptance

- A bow attack deals the item's damage through the existing combat resolution.
- Firing consumes one arrow from the wielder's inventory; no arrow gives a clear
  failure and no damage.
- Ammo stacks/quantities behave (task-504) or uses decrement correctly.
- Vekka's hunting bow is authored and tested.
- The crossbow's disposition is documented.

## Non-goals

- Ballistics/range simulation, ammunition crafting, projectile physics.

## Resolution (2026-10-02)

A ranged weapon is an item tagged ``ranged`` (or ``bow``); ammunition is an
item tagged ``ammo``. The attack is the ordinary `player_attack` path — the
ranged weapon supplies the damage and the ammo is the gate/charge.

- `engine/combat.py`:
  - `_is_ranged_weapon()` / `_carried_ammo_node()` / `_spend_ammo()`.
  - A ranged attack with no ammo returns a clean failure **before any roll**,
    so no damage is dealt.
  - Ammo is spent when the shot is *attempted*, before the hit/miss contest: a
    miss still costs the arrow.
  - `_spend_ammo` decrements the generic `uses` counter; a discrete arrow
    (`uses: 1`) is removed when spent; `uses <= 0` means an inexhaustible
    supply.
  - `_best_weapon_node` now skips `ammo` items. A broadhead arrow
    (`damage: 0` + `weapon`) used to be auto-selected and rolled `1d0`.
- Content: `vekka_hunting_bow` (1d6 piercing, `ranged`), `quiver_of_arrows`
  (20-use `ammo` stack), `arrow`/`broadhead_arrow` re-tagged `ammo`;
  `Vekka` now carries her bow and quiver. `tools/item_content_pass1.py` updated
  in lockstep so the pass and the shipped JSON agree.
- Range/targeting: same-area only (no area-grid/facing tie-in).
- **Crossbow**: left as an intentional scripted exception. It remains a
  one-shot `on_use` message + `destroy_self` with no `damage`, because it is an
  authored set piece whose effect is narrative, not a combat weapon. Documented
  here rather than re-authored.

Acceptance: a bow attack uses the item's damage through the normal combat
resolution; firing consumes one arrow and an empty quiver fails with no damage;
ammo stacks decrement via `uses`; Vekka's bow is authored and tested. Tests:
`tests/test_ranged_combat.py` (10 passed).
