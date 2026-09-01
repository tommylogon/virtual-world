---
group: Characters
---
# Pack Logic for Simple NPCs

**Filed**: 2026-08-19
**Priority**: Low
**Status**: Idea

---

## Idea

Pack logic for simple NPCs so multiple of the same type can coordinate together via code. Examples: rats, wolves, and other such animals. the idea is that they can hear or smell others of their kind over larger areas to call or warn each other to go away or approach. pack creatures might move or follow each other to areas, attack in groups etc.

## Notes

- Exploratory — flagged "maybe not, we'll see". The idea is recorded for later evaluation. 
- MVP if it ever gets picked up: a shared `pack` tag/property on group members, packmate awareness (detect nearby packmates in the same area), and a coordinated-target behavior rule ("attack the same target as the nearest packmate").
- Full pack AI (formation, flanking, role assignment) is intentionally out of scope for the MVP.

## Related

- `developer ideas.md` line 1
- NPC behavior system (`engine/npc_behaviors.py`)
