---
group: Prompt & Narrative Quality
---
# Task 113: Vital Detail Modal — click vitals, see what affects them, edit values, decay rates, time to empty, mana for magic chars

**Status**: Review  
**Priority**: High  
**Filed**: 2026-07-29  
**Updated**: 2026-07-31  

---

## Summary

Clicking a vital bar opens a modal with: current value (editable), decay rate (editable), time to empty, and conditions/effects affecting that vital. Characters with the `magic` tag get a Mana vital.

---

## Backend

### Done
- `player.py`: Added `sync_vitals_with_tags()` — injects/removes "Mana" based on "magic" tag. Called at end of `__init__`.
- `virtual_world_engine.py`: Added `"Mana": 0` to `baseline_decay` so it appears in the iteration but doesn't decay by default.
- `routes/players.py`:
  - `sync_vitals_with_tags()` called when tags are updated via the update-player route
  - `sync_vitals_with_tags()` called in the create-player route (after tags set)
  - `sync_vitals_with_tags()` called in the import-player route
  - `GET /api/players/<name>/vitals/<vital>` — returns value, max, percentage, decay rate (base + override), time to empty, and conditions affecting (from `PERIODIC_CONDITIONS`)
  - `PATCH /api/players/<name>/vitals/<vital>` — updates value and/or decay rate

### What's left
- Nothing — backend is done

---

## Frontend

### Done
- `templates/index.html`: Added vital detail modal HTML (lines 593-605) with value input, decay rate input, time to empty display, conditions list
- `templates/index.html`: Implemented `openVitalModal()`, `closeVitalModal()`, `saveVitalEdit()` functions (lines 611-777)
- `templates/index.html`: Added Escape key handler to close modal (lines 779-783)
- `static/js/inspector/agent-view.js`: Made vitals clickable with onclick handlers (line 236, 253)
- `static/js/inspector/agent-view.js`: Added Mana display in separate "Arcane" group when `player.vitals.Mana !== undefined` (lines 262-267)

### Features implemented
- Click any vital bar to open modal showing current value, max, percentage
- Edit value and decay rate with number inputs
- Time to empty calculation (shows "No decay" if rate is 0)
- Lists conditions affecting the vital from PERIODIC_CONDITIONS
- Temperature-specific display: comfort status, room temp, feels like, drift, time to threshold, damage per turn, insulation from equipment
- Mana vital appears in separate "Arcane" section for magic-tagged characters
- Escape key closes modal

---

## Details

### Modal should show:
- Vital name as title
- Current value / max (large text)
- Percentage indicator
- **Edit Value** — number input, clamps to 0-max
- **Edit Decay Rate** — number input (float, step 0.1), stored in `player.decay_rates`
- **Time to Empty** — computed as `value / decay_rate` (turns), shows "No decay" if rate is 0
- **Conditions Affecting** — lists conditions from `PERIODIC_CONDITIONS` that affect this vital (e.g., "poisoned: -5 HP/turn", "sick: -2 Hunger/turn")

### Time to Empty calculation:
- `effective_rate = player.decay_rates.get(vital, baseline_decay.get(vital, 0))`
- If rate > 0: `time_to_empty = value / rate` (rounded to 1 decimal)
- If rate <= 0: null / "No decay"

### Mana:
- Added to vitals as "Mana": 100 when player has "magic" tag
- Removed from vitals when "magic" tag is removed
- No baseline decay by default (rate = 0), but can be edited via the modal
- Display in frontend when `vitals.Mana !== undefined`

---

## Files to touch

### Backend (done)
- `virtual_world/player.py`
- `virtual_world/virtual_world_engine.py`
- `virtual_world/routes/players.py`

### Frontend (done)
- `virtual_world/templates/index.html` — modal HTML + modal JS functions
- `virtual_world/static/js/inspector/agent-view.js` — clickable vitals, Mana display
