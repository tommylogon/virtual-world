---
type: task
status: todo
area: items
priority: medium
---

# task-516: Concealed carried items for hidden pouches and backup knives

**Filed:** 2026-09-24
**Related:** task-3, task-236, task-177

## Goal

Define concealed-on-person items — hidden from onlookers and loot but drawable
by the owner — distinct from authoring-hidden world nodes. Motivating gear:
Zikka's hidden backup knife and Krikka's hidden pouch of favourite shiny finds.

## Context

- `current_state == "hidden"` already removes a node from area listings
  (`engine/area_description.py:290`), from beyond-visibility
  (`engine/beyond_visibility.py:30`) and from the equipment another character
  sees (`engine/equipment.py:425-433`). `hidden` was consolidated into
  `current_state` (task-177).
- Layering already makes worn items under outer layers less visible (task-3,
  done).
- However the owner's inventory listing
  (`engine/items/examine_actions.py:470`, `get_inventory`) and the steal matcher
  (`engine/matching.py:327`, `match_item_name_in_inventory`) do not appear to be
  gated by concealment: a carried "hidden" item may list for its owner as
  intended, but may also be lootable/stealable with no search step.

## Questions to settle

- Is `current_state: "hidden"` on a *carried* item (a) "owner knows, others do
  not" or (b) "removed from play"? Today it behaves as (b) for area nodes and is
  used as (b) for wearables visible to others.
- Should concealment be its own flag (`concealed`) so an item can be
  owner-visible yet unseen by others, separate from authoring-hidden nodes?
- Does `equip`/`unequip` preserve concealment? Does drawing a concealed weapon
  reveal it?
- Does stealing a concealed item require a Perception/search step first?

## Proposal

- Define the semantics explicitly, then either reuse `current_state: "hidden"`
  with an owner-visible special case or add `concealed: true`.
- Owner: concealed items list normally in their inventory and can be drawn/used.
- Others: concealed items are skipped in examine/loot/equipment narratives
  unless a search or Perception check succeeds; stealing one is harder or
  requires noticing it first.
- A concealed container's contents are not auto-revealed.

## Acceptance

- A concealed carried item is invisible to other characters' examine/loot but
  available to its owner.
- Revealing/equipping it ends concealment (or that is a documented choice).
- The steal/search path has an explicit rule and a test.
- Zikka's backup knife and Krikka's hidden pouch are authored on the chosen
  model.

## Non-goals

- Redoing wear-layer visibility (task-3).
- The inspector hide/reveal toggle (task-236), a separate UI concern.
