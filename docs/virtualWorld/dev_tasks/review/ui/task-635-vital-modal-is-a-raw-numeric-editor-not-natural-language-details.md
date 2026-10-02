---
type: task
status: review
area: ui
priority: medium
---

# task-635: Vital modal is a raw numeric editor, not 'natural-language details'

**Filed:** 2026-09-30
**Related:** 

## Goal

The modal advertises natural-language details but offers raw numeric fields with a decimal decay rate and a 'TIME TO EMPTY' label that runs the wrong direction.

## Acceptance

- [x] The modal leads with a natural-language read of the vital, reusing
  `VitalThresholds.hoverText` (the same prose the hover shows): "Hunger: 47/100 ·
  a drive — it fills over time… · You are hungry. FIND SOMETHING TO EAT NOW."
- [x] The direction is stated correctly. The rate line reads *"Fills toward 100 …
  it reaches the top (most urgent) in about 15588.2 turns"* for drives
  (Hunger/Thirst/Bladder) and *"Drains toward 0 … it empties in about 442.3
  turns"* for resources. Polarity comes from the engine (`engine/vitals.py`,
  exposed as `polarity` on `GET /api/players/<name>/vitals/<vital>`), not a UI
  guess.
- [x] The misleading `TIME TO EMPTY` label is gone; a zero rate reads
  *"Stable — it does not change on its own over time."*
- [x] The raw value/rate inputs are moved behind a default-collapsed
  **Advanced** disclosure, so the natural-language detail is the surface.
- [x] The override line distinguishes an unset override (*"none — using base"*)
  from a real one, instead of printing base and override identically with no
  meaning.
- [x] Temperature keeps its band block and no longer offers a meaningless decay
  editor.

## Verification (live browser, 2026-10-02)

Server `VW_PORT=4463`; Playwright opened the app and called `openVitalModal` for
a character with Hunger:

```
API_HUNGER {"polarity":"drive","decay_rate":0.0034,"value":47,"max":100,"time_to_empty":13823.5}
HUNGER: "Hunger: 47/100 / a drive — it fills over time; eat before it maxes at 100.
         / You are hungry. FIND SOMETHING TO EAT NOW.
         / Fills toward 100 at about 1 point every 294 turns — it reaches the top
           (most urgent) in about 15588.2 turns."
POSITIVE: HAS_FILLS true, HAS_TIME_TO_EMPTY_LABEL false
ENERGY: "Drains toward 0 at about 1 point every 10 turns — it empties in about 442.3 turns."
Advanced disclosure: before {open:false, inputs:2}; after click {open:true, value:"47", rate:"0.0034"}
```

Screenshot: `review-verify/635-vital-modal.png`.

## Files

- `templates/index.html` — `openVitalModal` markup; `escVital`/`fmtVitalNum`.
- `routes/player_ops.py` — `GET .../vitals/<vital>` returns `polarity`.

