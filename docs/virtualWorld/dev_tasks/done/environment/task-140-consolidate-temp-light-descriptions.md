---
group: Environment & Climate
---
# Consolidate Temperature & Light Description Systems

**Filed**: 2026-07-30 (updated 2026-07-30)  
**Priority**: Medium  
**Status**: Review  

---

## Summary

Temperature and light descriptions are duplicated across 6+ locations with inconsistent thresholds, inconsistent labels, and some paths using raw ambient temperature while others use equipment-adjusted `feels_like`. Consolidate into one authoritative backend source, remove frontend duplicates, widen thresholds to cover realistic ranges.

---

## Current Duplication Map

### Temperature (5 independent systems — #6 removed via dead code cleanup)

| # | File | Thresholds | Uses | Problem |
|---|------|------------|------|---------|
| 1 | `engine/area_description.py:146-157` env_summary | ≥35/≥30/≥25/≤10/≤0/≤-10 | `feels_like` | Gaps at 11-24°C and -9 to -1°C |
| 2 | `engine/area_description.py:203-212` warnings | >35/>32/<-5/<5 | `feels_like` | Different labels than env_summary |
| 3 | `engine/area_description.py:287-299` exit clues | <5/<15/>35/>28 | **raw ambient** ❌ | Should use `feels_like` |
| 4 | `prompt-builder.js:477-478` lead-in | <5/<15/>35/>28 | **raw ambient** ❌ | Different labels ("bitterly cold" vs "freezing") |
| 5 | `prompt-builder.js:431-435` exit clues | <5/<15/>35/>28 | **raw ambient** ❌ | Identical to #3 but in JS |
| ~~6~~ | ~~`agent-engine.js:_buildRoomContext`~~ | ~~<5/<15/>35/>28~~ | ~~**raw ambient** ❌~~ | **Removed** — dead code cleanup |

Still present but separate use-case: `agent-engine.js:182` sensory memory snapshot — logs "I'm at [area]. It's [temp] and [light] here." as a character memory (not a prompt). Thresholds: `<5 freezing` / `<15 cold` / `>35 sweltering` / `>28 warm`. Light: `<10 pitch dark` / `<30 dimly lit` / `<70 well lit` / `else bright`. Uses raw ambient temp.

### Light (5 independent systems)

| # | File | Thresholds | Problem |
|---|------|------------|---------|
| 1 | `engine/lighting.py:13-30` | ≤20/40/70/90 | Reference |
| 2 | `prompt-builder.js:25-32` | <20/≤40/≤70/≤90 | Same thresholds, duplicate |
| 3 | `agent-engine.js:184` | <10/<30/<70 | **Different thresholds** ❌ |
| 4 | `network-manager.js:351-356` | 10/30/55/80/95 | Different int mapping |
| 5 | `network-manager.js:396-438` | Full spill reimplementation | Pure frontend duplicate |

---

## Requirements

### 1. Widen temperature thresholds

Replace the current coarse bands with a fuller spectrum:

| Feels Like | env_summary text | Warning text |
|------------|-----------------|--------------|
| ≥60°C | "The heat is infernal — you can't breathe." | "You are burning! Seek shelter or die!" |
| ≥50°C | "Blazing heat — the air shimmers." | "The heat is cooking you alive!" |
| ≥40°C | "Scorching hot." | "The intense heat is draining your energy!" |
| ≥35°C | "Very hot." | "You're overheating — find shade or water." |
| ≥30°C | "Hot." | "It's quite hot; you're feeling thirsty." |
| ≥25°C | "Warm." | (none) |
| ≥18°C | "Pleasant." | (none) |
| ≥12°C | "Cool." | (none) |
| ≥5°C | "Chilly." | (none) |
| ≥0°C | "Cold." | "The cold is biting." |
| ≥-10°C | "Freezing." | "It's freezing! You need to warm up." |
| ≥-25°C | "Bitterly cold." | "The cold is sapping your strength." |
| ≥-50°C | "Arctic — the cold is lethal." | "Hypothermia is imminent — find warmth now!" |
| < -50°C | "Deadly cold — nothing survives." | "You are freezing to death!" |

### 2. All paths use `feels_like` (equipment-adjusted)

- Exit clues must use `feels_like` (or at minimum the area's ambient temp, not the target room's raw temp)
- Frontend prompt builder must receive `feels_like` from backend state instead of calculating from raw temp
- Remove the 3+ frontend temperature description code paths

### 3. Remove frontend light description duplicates

- `lightToLevel` already exists in `prompt-builder.js` — but `agent-engine.js:184` uses different thresholds. Fix to match.
- `network-manager.js:396-438` light spill reimplementation is a full frontend duplicate of `engine/lighting.py:get_ambient_light`. Remove or mark as visual-only.

### 4. Consolidation approach

**Option A: Backend as single source of truth**
- Backend generates all temperature/light text and includes it in `/api/state`
- Frontend removes all its own temperature/light description code
- Frontend directly renders what the backend sends

**Option B: Shared constants**
- Extract threshold tables to `shared/` or a constants module
- Both backend and frontend import from the same source
- Lighter lift but doesn't fix the architecture

---

## What was changed

### Backend — single source of truth for temperature/light descriptions

- `engine/area_description.py` — Added `temperature_description()`, `temperature_warning()` functions with widened thresholds (14 bands from -50°C to 60°C). Replaced inline env_summary and warnings with calls to these functions. Exit clues now use `feels_like` (equipment-adjusted) instead of raw ambient temp.
- `engine/lighting.py` — No change (it remains the reference).
- `engine/serialization.py` — Added `_compute_feels_like()` method. Each player's serialized state now includes `feels_like` (equipment-adjusted temperature). Areas include `light_description`.

### Frontend — removed duplicates, fixed thresholds

- `static/js/agent/prompt-builder.js` — `lightToLevel` thresholds fixed to match reference (`<20` → `<=20`). Exit clue temperature thresholds widened to match backend bands. Lead-in tempFeel now reads `player.feels_like` from backend state instead of computing from raw ambient temp.
- `static/js/agent/agent-engine.js` — Light thresholds at line 184 changed from `<10/<30/<70` to `<=20/<=40/<=70/<=90` (matching `lighting.py`). Temperature thresholds widened to match the 14-band spectrum.
- `static/js/graph/network-manager.js` — Added doc comment marking `_computeAmbientLight` as visual-only duplicate of backend.

## Related

- [[review/ui/task-113-vital-detail-modal|task-113: Vital detail modal]] — vital detail modal shows feels_like correctly
- [[review/environment/task-5-heat_propagation|task-5: Heat propagation]]
