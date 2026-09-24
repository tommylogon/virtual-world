---
type: bug
status: todo
area: bugs
priority: medium
---

# bug-44: EDGE_IN is inverted for authored container contents

**Filed:** 2026-09-23
**Related:** task-485

## Goal

Container contents authored in the item library land as container -> contained (item_Backpack -> item_Ink), but EDGE_IN is canonically contained -> container (place_actions.py:79, take_drop_actions.py:685, activities.py:505) and every reader looks up get_edges_for_target(container, EDGE_IN) (equipment.py:113, item_actions.py:141, matching.py:304, activities.py:466/541, item_reach.py:148). Autosave has 21 such inverted item->item edges (Backpack -> Ink/Book/Oil/..., grandfather_clock -> brass_key, medicine_cabinet -> antiseptic/bandages), so those contents are invisible to take/examine/search/lighting/reach. Fix the authoring path (or migrate the saves) so the item is the source; the graph layout works either way because it resolves by depth.

## Acceptance

- TODO
