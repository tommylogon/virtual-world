---
type: task
status: review
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

## Resolution (2026-10-02)

Model chosen: a new `concealed: true` property, deliberately distinct from
`current_state: "hidden"` (authoring-hidden world nodes) and from the character
`hidden` stealth flag. `concealed` means owner-visible / other-hidden.

- **Owner:** the inventory listing and `find_item_node` are ungated by design, so
  a concealed item lists for its owner and can be drawn/used (unchanged).
- **Others:** `get_visible_equipment` skips `concealed` nodes, so `examine
  <character>` does not show a concealed worn item. Carried (non-equipped) items
  were never listed for other characters, so a hidden pouch is already unseen.
- **Steal:** `steal_item` refuses a concealed item ("they keep it hidden —
  search them first"). `search <character>` (new verb, Perception dc 12) clears
  `concealed` on everything the target carries/wears; a failure reveals nothing.
- **Drawing reveals:** `equip_item` pops `concealed`, the documented choice that
  bringing an item into use ends its concealment.
- **Authoring round-trip:** `library_nodes.library_item_properties` and
  `effects._hydrate_item` carry `concealed` so it survives placement/spawn.
- Content: `krikka_hidden_pouch` (concealed, holds shiny finds) on Krikka;
  `zikka_backup_knife` (concealed weapon) on Zikka.

**Acceptance:**
- [x] Concealed carried item invisible to others' examine, available to owner.
- [x] Revealing (equipping) ends concealment — documented choice.
- [x] Steal/search path has an explicit rule (`search <name>` then steal) and a
      test (`tests/test_concealed_items.py`, 11 passed).
- [x] Zikka's backup knife and Krikka's hidden pouch authored on the model.

**Ownership note (task-514):** concealment is owned here; task-514
(provenance/acquisition) should reference `concealed` rather than introduce a
competing visibility flag.

Not done: the inspector hide/reveal toggle (task-236) and a per-thief discovery
memory (the reveal is global, matching the existing area `search` verb).
