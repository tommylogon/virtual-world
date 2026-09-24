---
group: Prompt & Narrative Quality
status: done
---
# Emotion Should Reflect Actual Vitals/State

**Filed**: 2026-07-30
**Priority**: Medium
**Status**: Done (live game) — kept open for the optional extensions below

## Status — implemented (2026-09-22)

**This is a live-game (attended agent) feature.** The derived mood lands in the
prompt and inspector for characters whose turn is being driven; it is not part
of the background/cheap policy ([[Simulation Model]] §One entity, four
processing levels — cognition may read state better, it never changes state).

**Shipped (v1.4.0, engine-side so it is one source of truth):**
- `engine/emotion.derive_from_vitals(vitals, state)` builds a point-spiked
  affect map from physical signals, or `None` when asleep/unconscious/healthy.
- `Player.emotions_description()` (`player.py`) returns the explicit affect
  map's description when it is non-neutral, and otherwise falls through to the
  vitals-derived one. "Explicit always wins; vitals fill the silence" is
  therefore the recency rule — an explicit emotion narrates until it decays
  back under the speak threshold (`emotion.SPEAK_THRESHOLD`).
- `prompt-builder/character-state.buildEmotionContext` renders
  `player.emotions_description`, so all three prompt call sites
  (`agent-engine.js`, `plan-manager.js`, `agent-lens.js`) get it for free.

**Signals covered** (drives are inverted — high = urgent; resources low = urgent):
| Signal | Derived |
| --- | --- |
| Energy ≤ 25 | irritated (also melancholic) |
| Hunger ≥ 75 | craving (also anxious) |
| Thirst ≥ 75 | anxious |
| Entertainment < 25 | melancholic |
| Social < 25 | lonely (added 2026-09-22; task-353 makes Social a real gate) |
| Sanity < 25 | anxious |
| Temperature < 35 / > 38 | uneasy / irritated |
| Bladder ≥ 75 | irritated (also anxious) |
| HP < 50 | afraid |
| state `dead` | calm (ghost POV) |
| state `sleeping`/`unconscious` | silent |

**Added 2026-09-22:**
- `Social < 25 → lonely`, so isolation is an affect state and not only a
  behavioural flag.
- Hand-written band phrases for the derived dimensions (`lonely`, `craving`,
  `anxious`, `uneasy`, `irritated`, `melancholic`) in `_BANDS`. Before this a
  derived mood could render the placeholder prose "You feel <dim> with unusual
  intensity." — a debug string in the live prompt.
- Tests: `TestDeriveFromVitals` and `TestEmotionDescriptionDerivation` in
  `tests/test_emotion.py` (16 cases).

**Optional / not done (keep the task open for these):**
- **Condition-derived affect**: `frightened` → afraid, `poisoned`/`sick` →
  uneasy, `itch`/`goosebumps` → irritated. Conditions already narrate through
  `buildPerceivedState`, so this is a de-duplication/quality question, not a
  gap.
- **Species temperature band**: `derive_from_vitals` still hardcodes 35/38
  rather than reading `VitalThresholds.temperatureBand` (cold-blooded
  characters get warm-blooded mood thresholds). Matching the prose bands would
  be the correct follow-up.
- Sleeping → "groggy/disoriented (if woken)" would need a post-wake signal;
  today sleep is simply silent.

---

## Original problem

The emotion system (`player.emotion`) is currently set via triggers, action outcomes, or API calls — but it doesn't automatically reflect the character's actual physical state. A character can be shivering, exhausted, thirsty, and desperate for a bathroom, yet the prompt says "Kaelen Voss is quite relieved but vigilant."

## Original requirements

- Emotion should be dynamically derived from vitals if no explicit emotion has been set recently
- `buildEmotionContext()` (or a new function) should aggregate physical state signals and produce a coherent emotional summary
- Signals to consider:
  - Energy < 25 → tired/irritable
  - Hunger/Thirst < 25 → desperate/focused (inverted since task-337: high = urgent)
  - Entertainment < 25 → bored/restless
  - Sanity < 25 → paranoid/fractured
  - Temperature < 35 → cold/distressed
  - Temperature > 38 → hot/agitated
  - Bladder > 75 → uncomfortable/distracted
  - HP < 50 → pained/weak
  - State is "sleeping" → groggy/disoriented (if woken)
  - State is "dead" → detached/calm (ghost)
- If an explicit emotion was set recently (within N ticks), prefer that

## Related
- `developer ideas.md` — emotion not matching vitals
- [[Simulation Model]] — why this lives on the attended/agent tier
