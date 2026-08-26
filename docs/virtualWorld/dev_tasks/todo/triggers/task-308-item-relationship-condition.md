---
group: Triggers
---
# Item Relationship Condition (Bulging Pocket Check)

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Idea

---

## Idea

Condition to check if self has an item in a relationship, or if an item has another item of a certain relationship type. Example: if a coat has an item inside (`in` edge), an effect makes the `pocket` param message say "the pocket is bulging" — else "the pockets are empty".

## Notes

- Mostly covered by existing conditions: `has_item` / `has_items` / `in_area` plus spatial edges (`EDGE_IN`, `EDGE_ON`, etc.).
- The missing bit is condition syntax for *relationship type on a specific node* (e.g. "does item X have anything with edge `in`?"), plus wiring the result into message templating.
- Small completion of the existing trigger system, not a new system.

## Related

- `developer ideas.md` line 15
- `engine/trigger_system.py` (`has_item`, `has_items`, `in_area`), `graph.py` spatial edges
