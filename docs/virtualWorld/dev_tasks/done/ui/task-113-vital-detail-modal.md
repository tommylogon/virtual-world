---
area: ui
type: task
status: done
priority: medium
---

# Task 113: Vital Detail Modal — click vitals, see what affects them, edit values, decay rates, time to empty, mana for magic chars

**Status**: Review  
**Priority**: High  
**Filed**: 2026-07-29  
**Updated**: 2026-07-31  

---

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. Select a character, click its Hunger vital bar, and read the Vital Detail
   modal's current value, max, percentage, decay rate, time to empty, and
   conditions list.
   - expected: the modal identifies Hunger and shows values for that character;
     a zero rate reads “No decay”.
   - observed: the task records these frontend controls as implemented; a live
     click-through is not recorded here.
2. Edit Hunger and its decay rate, save, reopen the modal, and press Escape.
   - expected: both values persist after reopen and Escape closes the modal.
3. Add the `magic` tag to a disposable character, open the inspector, and
   click Mana in the Arcane group.
   - expected: Mana appears only while the character has the magic tag and its
     detail modal shows the current value and decay information.

## Browser UI and intended live verification

Intended UI home: Character Inspector → Bio → Vitals; click a vital bar to
open Vital Detail.

Current availability: The card records the modal, editing controls, conditions
list, time-to-empty calculation, and magic-tag Mana group as implemented. It
does not record a browser run of these interactions.

Live steps when available:
1. Click Hunger on a character with non-zero decay and a condition that affects
   Hunger; inspect the full Vital Detail modal.
   - expected: current/max/percentage, decay rate, time to empty, and the
     affecting condition are visible together.
2. Change the value and decay rate, save, reopen the modal, then close with
   Escape.
   - expected: saved values survive reopening and Escape closes the modal.
3. Add or remove the `magic` tag on a disposable character and compare the
   inspector before and after a state refresh.
   - expected: Mana appears in Arcane only while the magic tag is present;
     clicking it opens the same detail modal.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Acceptance

- [ ] TODO

## Files

- TODO
