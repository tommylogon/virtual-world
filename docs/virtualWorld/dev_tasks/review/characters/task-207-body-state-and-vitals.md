

# Body State & New Vitals (Arousal/Stimulation/Pleasure)

**Filed**: 2026-08-11
**Priority**: High
**Status**: Todo

---

## Problem

There's no per-body-part numeric state and no arousal system. The design calls for a lightweight `body_state` dict on the Player plus three new vitals, all feeding existing condition/decay infrastructure.

## Design

- Add `player.body_state` dict: `nipples` (left/right: hardness, puffiness, flush, sensitivity, injury, pierced), `cheeks` (flush), `genitals` (erection, wetness, sensitivity, injury). Quick numeric lookups only — body parts are NOT graph nodes.
- Add vitals to `player.vitals`: `Arousal` (0-100, decays slowly), `Stimulation` (0-100), `Pleasure` (0-100).
- Add decay rates to `player.decay_rates` for the new vitals.
- **`sync_vitals_with_tags()`** (`player.py:274`) already does dynamic vital add/remove — mirror it if mature content ever needs to strip these vitals.

## Files

- `player.py` — `body_state` init, vitals init, decay rates (verified at `player.py:273-317`)

## Testing

- [ ] `body_state` initializes with correct defaults (nipples 0.9/0.7 sensitivity)
- [ ] New vitals appear in player vitals with correct range 0-100
- [ ] Decay applies each tick

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §1, §4, Phase 1
