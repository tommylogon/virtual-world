---
group: Items & Inventory
---
# Jumpsuit Can't Be Equipped + Appearance Saved on Failed Equip

**Filed**: 2026-08-07
**Priority**: Medium
**Status**: In Review — implemented 2026-08-07, verified live against the running server (wear/unequip + success flag), pending browser E2E.

---

## Summary

Two coupled problems when equipping the library-placed jumpsuit:

1. `wear jumpsuit` failed with **"The jumpsuit can't be equipped."**
2. The failed equip still triggered **"Appearance saved."** — the equipment-description auto-generate ran and rewrote the character appearance even though nothing was equipped.

Observed in the event stream (three consecutive turns):

```
⚙️ [Tick 2 | 08:10]
⚙️ The jumpsuit can't be equipped.
⚙️ Appearance saved.
```

## Root cause

- **Data**: `data/library/items/jumpsuit.json` had `equip_slots: []` and empty `tags`, while the canonical `item_Jumpsuit` node (from the world template) is `equip_slots: ["torso","arms","legs"]` + `tags: ["clothing","insulation","equips_all_slots"]`. Duplicate placements (`build_item_from_library`) snapshot the library entry at build time, so both `item_jumpsuit_…` nodes inherited the empty slots.
- **Code**: `/api/action` had no success/failure signal — a `ValueError` (e.g. "can't be equipped") was folded into `output` text with HTTP 200. `runAction()` (`static/js/api.js`) therefore auto-generated the equipment description after every `wear`/`remove`/`unequip`, success or not.

## Changes

- `data/library/items/jumpsuit.json` — `equip_slots: ["torso","arms","legs"]`, `tags: ["clothing","insulation","equips_all_slots"]` (matches the canonical world node).
- `routes/action.py` — `/api/action` response now includes `"success": true|false`; `false` when the handler catches a `ValueError` (expected game error).
- `static/js/api.js` — `runAction` auto-generates the equipment description only when `data.success === true`.
- Live placed nodes refreshed via `POST /api/items/<node_id>/refresh-from-library`.

## Verification

- Live server: `wear jumpsuit` → `You equip the jumpsuit on your torso. It also covers your arms, legs.` (`success: true`); `wear nonexistent-thing` → `success: false`; `remove jumpsuit` clean.
- Full suite: **585 passed, 1 skipped** (71 deselected).
