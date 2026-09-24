---
type: task
status: todo
area: items
priority: high
---

# task-513: Kraktooth goblin gear spec-driven library batch

**Filed:** 2026-09-24
**Related:** task-9, task-3, task-408

## Goal

Turn the six-goblin gear matrix into real `data/library/items/*.json` templates
via a compact, reviewable spec, so the kit exists, validates, and can be
attached to the characters (task-519).

## Why a spec instead of hand-written JSON

The matrix names roughly sixty distinct items across clothing, armor, weapons,
tools, accessories and shared materials. Hand-authoring each JSON invites drift
(the same hunting bow in three spellings, three tags lists). A spec table is
small, reviewable and re-runnable, matching the folder-authoring precedent
(`tools/compile_scenario.py`, `tools/build_scenario.py`) and the tag-chain
population engine (`engine/population.py`, task-9).

Note the distinction from task-9: `engine/population.py` *places existing*
library items by tag and deliberately does not mint new ones. This task mints
the templates that population/loadouts then use.

## Source matrix (condensed)

| Goblin | Clothing | Armor / protection | Weapons | Tools / utility | Accessories / personal |
|---|---|---|---|---|---|
| Zikka | patchwork leather vest, leather leg wraps, reinforced waist cloth | scavenged metal shoulder plate, leather knee guards, heavy boots | short goblin cleaver, hooked knife, hidden backup knife (task-516) | whetstone, leather repair strips, rope loops, hooks | bone necklace, ear piercings, trophy tags, old human buckle, scar-marked leather strips |
| Mikka | pocket work vest, shortened sleeves, work trousers, fingerless gloves | reinforced palms/elbows/knees, scrap-metal plates | improvised pry-bar/dagger, small utility blade | hammer, pliers, wrench, awl, files, wire, nails, screws, springs, glue, pitch, lockpicks | copper earrings, gears, washers, broken keys, dwarven mechanism component |
| Gribba | butcher's apron, loose leather clothing, cloth head wrap | thick leather forearm guards, heat-resistant scraps around hands | heavy butcher's knife, meat hook | cooking spoon, cleaver, scraper, skewers, flint, salt, herbs, spices, containers | fish teeth, mushrooms, bones, food charms, the Good Knife (task-515) |
| Rikka | asymmetric leather and cloth, hanging strips, colorful scraps | light leather (unrestricted movement) | throwing knives, small club/performance stick | juggling stones, string puppet, cups, feathers, little drum | bells, beads, colored glass, cheap jewelry, feathers |
| Vekka | close-fitting layered leather, dull cloth, hooded cloak | thin forearm/knee protection | compact hunting bow (task-518), curved knife | rope, string markers, chalk, charcoal, flint, small mirror, water container, folded map | found stones, feathers, pottery fragments, glass bits |
| Krikka | lightweight fitted leather and cloth | reinforced palms, climbing knee/ankle protection | small hooked blade, backup knife | climbing rope, hooks, harness, resin, small pouches | coins, beads, glass, shiny stones, metal scrap, hidden pouch (task-516) |

Shared Kraktooth vocabulary: belts, pouches, rope, wire, bone, metal scrap,
cloth, leather, feathers, coins, glass, hooks, scrap.

## Item schema to emit

Per `data/library/items/cleaver.json` and `data/library/items/rope.json`:
`name, description, actions, uses, weight, current_state, light_level,
defense, damage, damage_type, insulation, tags, triggers, contents`.
Wearables add `equip_slots`; the valid set is
`head, neck, torso, arms, hands, legs, feet, back, waist, accessory,
hand_left, hand_right` (`engine/equipment.py:24-37`,
`tools/fix_item_equipment.py:76-79`).

## Proposed shape

- A spec file (e.g. `data/library/items/_specs/kraktooth_gear.json`) keyed by
  item id, holding `name`, one-line `description`, `category`
  (clothing/armor/weapon/tool/accessory/material), `equip_slots`,
  `damage`/`damage_type`, `defense`, `insulation`, `uses`, `weight`, `tags`,
  `actions`.
- `tools/gen_library_items.py --spec <file> [--check|--apply]`: deterministic
  emission to `data/library/items/<id>.json` (sorted keys, stable order,
  byte-identical on re-run); `--check` is the CI/lint mode.
- Dedupe shared materials across goblins to one template each (rope, hook,
  bone, coin, glass...). Give per-goblin flavor at instance level (task-514
  provenance) or in `description`, not by cloning near-identical templates.

## Open question: partial-armor mapping

The matrix names palms, elbows, knees, shoulders, forearms and ankle
protection; the slot set has no such granularity. Decide whether to map those
onto the coarse slots (`arms`, `hands`, `legs`, `feet`, `torso`) with
`description` flavor, or to add finer slots later. Record the decision here; do
not block the batch on new slots.

## Acceptance

- Every unique item in the matrix exists as a valid library template, or is
  explicitly deferred with a reason.
- Re-running the generator changes nothing (`--check` clean).
- `tools/lint_library.py` stays clean.
- Emitted items carry the fields required by their category (wearables have
  valid `equip_slots`; weapons have `damage`/`damage_type`).
- The partial-armor mapping decision is documented.
- No duplicate/near-duplicate templates for a shared material.

## Non-goals

- Attaching items to characters (task-519).
- New engine mechanics for concealment (task-516), ownership (task-515) or
  ammunition (task-518); those get their own fields once decided.

## Verification

- `python tools/gen_library_items.py --check` (compile-twice equality).
- `python tools/lint_library.py`.
- Targeted item/library tests via `python -m pytest tests/ -q`.
