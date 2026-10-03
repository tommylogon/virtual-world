---
type: task
status: todo
area: ui
priority: medium
---

# task-682: Scene chips leak snake_case node ids as display names

**Filed:** 2026-10-04
**Related:** 

## Goal

Things you can see renders raw node ids for items whose name is an id: coat_rack, calling_cards, protein_bar, vase (ok) while neighbouring chips read denim cut-offs. The You strip shows energy drinkbroken -- the item name and its broken state concatenated with no separator. scene_snapshot emits describe_item_quantity(node) and build_item_quantity_label joins name+state; both need a display-name resolution layer plus a separator. Check whether the id is already available as a display_name/label property before adding a second resolution path.

## Acceptance

- TODO
