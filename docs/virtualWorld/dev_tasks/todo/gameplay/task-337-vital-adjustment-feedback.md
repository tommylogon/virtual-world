# Task 337 — Polarity-aware vital adjustment feedback + Hunger/Thirst drive flip

**Status:** In Progress — flip IMPLEMENTED 2026-08-23 (engine/vitals.py,
tick_manager, effects.py, character-state.js, vital-thresholds.js, player
spawn defaults, sick condition, data migration of 110 characters across all
scenarios/templates/library). Flip-affected suites pass (173). Full-suite
verification deferred until Tommy's in-flight item_actions refactor lands.
Remaining: `stats` command wording audit, UI bar color polarity if not
already metadata-driven, autosave.json note (reset/reload instead of
migrating runtime state).

## Why

`adjust_vital` results render as *"Thirst adjusted by 20."* — no direction,
no sense of whether that's good or bad. Worse, sign conventions differ per
vital: eating applies `Hunger -30` (relief), damage applies `HP -5`
(loss), `Social +10` is good but `Bladder +40` is bad. Players and LLMs
both have to guess. Needs fixing for ALL vitals.

## Design

1. **Per-vital polarity metadata** — `engine/vitals.py` (`VITAL_POLARITY`,
   `polarity()`, `is_drive()`, `clamp()`, `format_vital_change()`).

### Verified polarity table (2026-08-23, from code)

Pre-flip engine truth: vitals DECAYED downward (tick_manager.py:160),
Hunger/Thirst killed at 0 (:210-239), Bladder FILLED up (+base_fill :190,
accident at 100). Welcome message said "keep above 25%".

| Vital | Model | Direction | Edge |
|-------|-------|-----------|------|
| HP | resource | ↑ good | ≤0 dead |
| Energy | resource | ↑ good | collapse at low |
| **Hunger** | WAS satiation | **FLIPPED → drive** (↑=hungrier) | ≥100 starves |
| **Thirst** | WAS satiation | **FLIPPED → drive** | ≥100 dehydrates |
| Bladder | drive | ↑ bad | 100 = accident (keep) |
| Social/Hygiene/Sanity/Entertainment/Comfort | resource | ↑ good | flavor at lows |
| Temperature | BAND (~37°C target) | both directions bad | hypo/hyperthermia |
| Mana | dormant (decay 0) | — | decide when magic lands |
| **Arousal** | drive (zone-system doc §Arousal: 0-100, condition tiers 15/30/50/90, climax edge) | ↑ = more aroused; release resets | like Bladder mechanically |
| **Pleasure** | **BAND** (doc §Pleasure: dynamic target window from arousal/mood/traits; exceeding comfort threshold flips to overstimulation, -3/tick drain) | below window = numb/frustrating, in window = good, above = pain | second band vital alongside Temperature |
| **Satisfaction** | resource (fills on release, decays over time back into need) | ↑ good | decay creates the seeking loop |

**Recommendation (agreed with Tommy): FLIP Hunger/Thirst to drive-style**
like Bladder. Rationale: ALL existing food/drink content across scenarios
already authors negative amounts as "relief" (taco_bell burrito -30,
mansion legacy items) — under the old satiation semantics that content
pushed characters toward starvation (feeding = harming). Two independent
authoring generations got it wrong the same way; the names also read
naturally as drives ("hunger rises"). Flipping made the existing content
correct without touching a single trigger.

**Principle going forward:** every NEW vital must declare its type in this
table at creation time — `resource`, `drive`, or `band`. No implicit
defaults.

### Flip implementation (2026-08-23, DONE)

- `engine/vitals.py` NEW — registry + helpers
- `tick_manager.py`: drives FILL (+rate, min 100); death/hp_loss checks
  flip to ≥100; Hunger/Thirst need-tiers remapped to rise-above tiers
  (25/50/75/90); threshold-crossing detector handles both directions;
  bladder-fill thirst coupling inverted (parched = slower fill)
- `effects.py`: adjust_vital default message → `format_vital_change()`
  ("Your thirst eases (-20)." / "Your hunger builds (+15).") replacing
  "adjusted by N"; trigger authors keep raw signs
- `virtual_world_engine.py`: welcome line updated
- `player.py`: spawn defaults Hunger/Thirst 100→0 (satisfied); Sick
  condition periodic -2→+2 (both player.py fallback and
  data/library/conditions/sick.json)
- `character-state.js`: prose comparisons flipped; `vital-thresholds.js`:
  DRIVE_URGENT/WARN/MILD added, isCritical routes Hunger/Thirst high=urgent
- plan-tracker criticalNeeds inherits via isCritical ✓
- **Data migration**: 110 characters across all scenarios +
  world_template.json + library converted v→100-v (flip_hunger_thirst.py);
  autosave.json intentionally NOT migrated — reset/reload instead

2. **Message rendering**: done via format_vital_change (see above).
3. Cross-check both adjust_vital render sites in trigger_system — they
   delegate to effects handlers ✓ single helper now.

## Remaining

- [ ] `stats` command wording audit (routes/action.py)
- [ ] UI bar color polarity check (inspector/agent-view vitals displays)
- [ ] Full-suite green once item_actions refactor lands
- [ ] Optional LLM-facing note in prompt docs about new semantics

## Verification

- Flip-affected suites: test_delayed_events, test_conditions,
  test_engine_init, test_traits — 173 passed post-fix
- Fresh spawn ticks idle with zero HP loss (was bleeding 3/tick pre-fix)
