---
type: task
status: done
area: characters
priority: medium
---

# task-366: Character Knowledge manager modal

**Filed**: 2026-08-30
**Status**: Done — implemented + live-verified 2026-08-30.

## What was built

- Per-entity "Known by" panels removed from item/area/way inspectors.
- Character inspector Advanced tab → 🧠 Knowledge section (chips + 🎛 Manage)
  → modal (`static/js/inspector/known-by.js` rewrite): category tabs
  (Items/Characters/Areas/Ways with live counts), search, ✓ All / ✕ None,
  hidden markers, stale-ref cleanup, immediate save via
  `updateCharacter(known)`. Alias refs written so engine + prompt builder
  match (name / player_<slug> / character_<slug>; area name + node id + guess).
