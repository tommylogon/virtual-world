---
group: Pleasure System
status: done
---

# Body State & New Vitals (Arousal/Stimulation/Pleasure)

**Filed**: 2026-08-11
**Priority**: High
**Status**: Review — implemented and verified against the code; shipped in v1.4.0

---

## Problem

There's no per-body-part numeric state and no arousal system. The design calls for a lightweight `body_state` dict on the Player plus three new vitals, all feeding existing condition/decay infrastructure.

## Design

- Add `player.body_state` dict: `nipples` (left/right: hardness, puffiness, flush, sensitivity, injury, pierced), `cheeks` (flush), `genitals` (erection, wetness, sensitivity, injury). Quick numeric lookups only — body parts are NOT graph nodes.
  - **Shipped:** the dict exists, keyed by body region id, with `sensitivity` seeded from the catalog (nipples 0.9/0.7) — `engine/body_parts.py::default_body_state`, `player.py:141`.
  - **Descoped:** the erogenous numerics (hardness, puffiness, flush, pierced, erection, wetness) are modeled as conditions instead (`nipple_hard`, `blushing`, `wetness`, `sensitized`, `satisfied`) in `engine/player_conditions.py`. Nothing reads those fields today; `engine/pleasure_actions.py` reads only `sensitivity`.
- Add vitals to `player.vitals`: `Arousal` (0-100, decays slowly), `Stimulation` (0-100), `Pleasure` (0-100).
- Add decay rates to `player.decay_rates` for the new vitals.
- **`sync_vitals_with_tags()`** (`player.py:274`) already does dynamic vital add/remove — mirror it if mature content ever needs to strip these vitals. Realized as `Player.sync_pleasure_vitals()` (`player.py:37`), driven by the mature-content toggle (task-206).

## Files

- `player.py` — `body_state` init (`:141`) and `sync_pleasure_vitals()` (`:37`)
- `engine/body_parts.py` — `default_body_state()` (`:265`) and nipple sensitivities (`:127`, `:132`)
- `engine/vitals.py` — Arousal/Stimulation/Pleasure classified as decaying resources (`:36-38`)

## Testing

- [x] `body_state` initializes with correct defaults (nipples 0.9/0.7 sensitivity) — `tests/test_body_parts.py`
- [x] New vitals appear in player vitals with correct range 0-100 — `tests/test_pleasure_system.py`
- [x] Decay applies each tick — `virtual_world_engine.py:90-96`, `tests/test_pleasure_system.py`

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §1, §4, Phase 1
