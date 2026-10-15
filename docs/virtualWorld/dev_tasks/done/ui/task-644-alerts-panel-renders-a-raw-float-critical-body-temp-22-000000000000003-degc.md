---
type: task
status: done
area: ui
priority: low
---

# task-644: Alerts panel renders a raw float: Critical body temp (22.000000000000003 degC)

**Filed:** 2026-09-30
**Related:** 

## What

Floating point reaches user-facing prose unformatted, and the stream truncates the player name to 'player_hu...'.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. Load a scenario with a character at the critical temperature threshold and inspect the Alerts section.
   - expected: temperature is displayed to one decimal place, such as `22.0°C`, not `22.000000000000003`.
   - observed: current `ui-controller.ts` formats Temperature with `Number(...).toFixed(1)`; this card records no live browser result.
2. Click the temperature alert.
   - expected: the inspector opens for the full character name, not a truncated internal ID such as `player_hu...`.
   - observed: not recorded in this card.
3. Compare the alert with the same character's Temperature vital detail.
   - expected: both show the same rounded value and unit.
   - observed: not recorded in this card.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Left panel → Alerts section → click a temperature alert to inspect the named character.

Current availability: `ui-controller.ts` now formats Temperature with one decimal place and builds the alert text from the full character name. The card itself has no recorded live observation for these two display values.

Live steps when available:
1. Load a scenario with a character whose body temperature crosses the critical threshold and open the Alerts section.
   - expected: the alert reads `Critical body temp (22.0°C)` (or the measured threshold value at one decimal), never the raw `22.000000000000003` float.
2. Click that alert row.
   - expected: the inspector opens for the full character name; the event stream or alert row does not truncate it to an internal ID such as `player_hu...`.
3. Compare the alert with the character's Temperature vital detail.
   - expected: both surfaces identify the same character and show the same rounded measurement and unit.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
