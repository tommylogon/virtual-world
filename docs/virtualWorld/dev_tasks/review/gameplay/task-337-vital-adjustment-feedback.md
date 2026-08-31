> NOTE 2026-08-30: duplicate todo copy removed — this file is canonical.

# Task 337 — Polarity-aware vital adjustment feedback + Hunger/Thirst drive flip

**Status:** In Progress — flip IMPLEMENTED 2026-08-23 (engine/vitals.py,
tick_manager, effects.py, character-state.js, vital-thresholds.js, player
spawn defaults, sick condition, data migration of 110 characters across all
scenarios/templates/library). Flip-affected suites pass (173). Full-suite
green: **1113 passed, 1 skipped** (2026-08-24). Remaining items closed
2026-08-24: stats command now uses polarity-aware `format_vitals_readout`,
UI bar colors driven by `vital_polarity` metadata from `/api/state`,
autosave note confirmed.

## Why

`adjust_vital` results render as *"Thirst adjusted by 20."* — no direction,
no sense of whether that's good or bad. Worse, sign conventions differ per
vital: eating applies `Hunger -30` (value DOWN = good), damage applies
`HP -5` (down = bad), `Social +10` is good but `Bladder +40` is bad.
Players and LLMs both have to guess. Needs fixing for ALL vitals.

## Design

1. **Per-vital polarity metadata** — one table (engine/vitals.py or
   runtime_config DEFAULTS): for each vital, which direction is
   "improving" plus display name.

### Verified polarity table (2026-08-23, from code)

Current engine truth: vitals DECAY downward (tick_manager.py:160,
baseline_decay all positive), Hunger/Thirst kill at 0 (:210-239),
Bladder FILLS up (+base_fill :190, accident at 100). Welcome message
(virtual_world_engine.py:80) confirms "keep above 25%".

| Vital | Model | Direction | Edge |
|-------|-------|-----------|------|
| HP | resource | ↑ good | ≤0 dead |
| Energy | resource | ↑ good | collapse at 0 |
| **Hunger** | satiation TODAY | **FLIP → drive** (↑=hungrier) | ≤0 starves today → ≥100 after flip |
| **Thirst** | satiation TODAY | **FLIP → drive** | same |
| Bladder | drive | ↑ bad | 100 = accident (keep) |
| Social/Hygiene/Sanity/Entertainment/Comfort | resource | ↑ good | flavor at lows |
| Temperature | BAND (~37°C target) | both directions bad | hypo/hyperthermia — metadata needs `band` mode, not a direction |
| Mana | dormant (decay 0) | — | decide when magic lands |
| **Arousal** | drive (zone-system doc §Arousal: 0-100, condition tiers 15/30/50/90, climax edge) | ↑ = more aroused; release resets | like Bladder mechanically |
| **Pleasure** | **BAND** (doc §Pleasure: dynamic target window from arousal/mood/traits; exceeding comfort threshold flips to overstimulation, -3/tick drain) | below window = numb/frustrating, in window = good, above = pain | second band vital alongside Temperature |
| **Satisfaction** | resource (fills on release, decays over time back into need) | ↑ good | decay creates the seeking loop |

**Principle going forward:** every NEW vital must declare its type in this
table at creation time — `resource` (↑good, decays ↓), `drive` (↑bad,
fills ↑), or `band` (comfort window, both extremes bad). No implicit
defaults.

**Recommendation (agreed with Tommy): FLIP Hunger/Thirst to drive-style**
like Bladder. Rationale: ALL existing food/drink content across scenarios
already authors negative amounts as "relief" (taco_bell burrito -30,
mansion legacy items) — under today's satiation semantics that content
pushes characters toward starvation (feeding = harming). Two independent
authoring generations got it wrong the same way; the names also read
naturally as drives ("hunger rises"). Flipping makes the existing content
correct without touching a single trigger.

2. **Flip checklist (Hunger/Thirst)**:
   - baseline_decay entries become FILL (+rate) or move to a fill table
   - death checks flip (≥100 instead of ≤0)
   - threshold drop-below tiers remap to rise-above (tick_manager.py:90-91)
   - welcome message + `stats` command wording
   - character-state.js prompt lines + UI bar polarity (driven by the new
     metadata, so this is free afterwards)
3. **Message rendering** replaces "adjusted by N":
   - improvement: *"Your thirst eases."* / *"Hunger recedes."*
   - worsening: *"Your thirst worsens."*
   - numbers signed from the PLAYER'S perspective (relief shown as
     reduction of the drive, damage shown as loss) so raw `-20` never
     appears.
4. **Trigger authors keep raw signs** — after the flip their existing
   negatives mean relief, matching intent. Only FEEDBACK translates.
5. Cross-check both adjust_vital render sites (trigger_system ~:376/:809)
   so both paths share one helper.

**Content bug flagged meanwhile**: taco_bell_date eat/drink triggers are
harmful under CURRENT semantics (pre-flip). Harmless to leave until this
task lands — flip fixes them retroactively.

## Related

- task-327 vitals-threshold-context-awareness (threshold FLAVOR text —
  this task covers adjustment RESULT messages; keep them consistent)
- task-207 body-state-and-vitals

## Verification

- Drink → thirst-easing message; take poison → worsening wording
- Every vital type renders direction-correct feedback via unit test

## Remaining (closed 2026-08-24)

- [x] `stats` command wording audit — `routes/action.py` now uses
  `format_vitals_readout()` (engine/vitals.py): one line per vital, drives
  annotated "fills toward 100", bands "comfort band", resources plain.
- [x] UI bar color polarity — `vital_polarity` dict added to `/api/state`
  payload (routes/action.py). `agent-view.js` (`vitalBarColor`) and
  `ui-controller.js` (agent overview mini-bars) now drive bar color from
  polarity metadata: drives invert (high = red). Also removed a duplicate
  `'HP'` in the ui-controller vitals loop.
- [x] Full-suite green: 1113 passed, 1 skipped.
- [x] autosave.json note — already documented (line 77): intentionally NOT
  migrated, reset/reload handles it.

## Follow-up (2026-08-24): trigger-effect data migration gap closed

The 2026-08-23 migration covered character spawn vitals but MISSED
trigger djust_vital effects — every eat/drink/relieve trigger still
used pre-flip positive amounts (+hunger on food, +thirst on drinks,
+bladder on toilets), so consuming food made characters HUNGRIER.
Fixed 51 effects across taco_bell_date, mansion, pines, both
world_template copies and 14 library items: consume effects now NEGATIVE
(drives fall toward 0 = satisfied). Kept positive: water_pitcher's
bladder +10 on_drink — drinking filling the bladder is correct new
semantics. Verified by re-scan + full suite (1120 passed).
