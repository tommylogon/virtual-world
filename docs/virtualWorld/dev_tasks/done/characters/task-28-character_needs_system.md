---
group: Agent AI & Behavior
wiki: "[[Characters/Vitals System]]"
---

# Character Needs System Expansion — Review

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `player.py` | Added Bladder, Sanity, Entertainment, Temperature (37.0) to vitals; added `decay_rates` dict; serialized in `to_dict()` | +11 |
| `virtual_world_engine.py` | Expanded `baseline_decay` (4→8), per-character decay rates, temperature drift, environment-based Sanity/Entertainment, death causes (madness/hypothermia/heat stroke), HP regen gates for Sanity + Temperature | +51 |
| `static/js/inspector.js` | Grouped Physical/Mental columns with `renderVital()`, Temperature bar (25-45°C range), °C suffix, trigger editor options for new vitals | replaced ~15 lines |
| `static/js/ui-controller.js` | Extended mini-bar loop (6→9 vitals + Temperature separate), alerts for Bladder/Sanity/Entertainment/Temperature | +15 |
| `static/js/agent-engine.js` | Replaced `_describeVitals()` with Bladder (3 thresholds), Sanity (3), Entertainment (3), Temperature (6 hot+cold thresholds) | replaced ~25 lines |

## Bugs Found & Fixed During Verification

1. **engine `load_from_dict` vitals replace vs merge** — template has both `player` + `players` keys, so `_load_from_template_format` is skipped. The main load path used `p.vitals = pdata.get("vitals", {})` which **replaced** the Player init defaults (Bladder/Sanity/Entertainment/Temperature lost). Fixed to `{**p.vitals, **pdata.get("vitals", {})}`.
2. **engine `to_dict()` missing `decay_rates`** — engine serialized players inline (not via `Player.to_dict()`) so `decay_rates` was never in API responses. Added `getattr(p, 'decay_rates', {})`.
3. **inspector Temperature display raw float** — `vitals[v]` used raw float (37.30000001°C) instead of rounded `val`. Fixed to `${val}`.

## Verification Results

- Backend `/api/state` returns all 11 vitals + `decay_rates` ✅
- Inspector shows grouped Physical/Mental columns with Bladder, Sanity, Entertainment, Temperature + °C ✅
- Mini-bars include Bladder, Sanity, Entertainment, Temperature (separate) ✅
- Alerts fire for Bladder≤15, Sanity≤15, Entertainment≤15, Temperature<34/ >40 ✅
- `/api/turn/apply` correctly decays all new vitals:
  - Bladder: 100→99 ✅
  - Sanity: 100→98 (baseline + alone penalty) ✅
  - Entertainment: 100→98 ✅
  - Temperature: 37.0→36.46 (drift toward room temp -12°C) ✅
- Death causes include madness, hypothermia, heat stroke ✅
- HP regen correctly gated on Sanity>25 + Temperature 35-39°C ✅

## Audit

**Status**: Ready to test
**How to test**:
- Load any scenario, open the inspector panel, click a player. Verify vitals show Bladder, Sanity, Entertainment bars under "Mental" and Temperature with °C suffix.
- Check the left sidebar mini-bars — Bladder, Sanity, Entertainment, Temperature should appear.
- Click Step. Observe alert messages (e.g. "Tommy: Bladder full (15)") when Bladder ≤ 15.
- Check `/api/state` returns `Bladder`, `Sanity`, `Entertainment`, `Temperature`, and `decay_rates` for all players.

## Commits

```
561fe36 feat(player): add Bladder, Sanity, Entertainment, Temperature vitals + decay_rates
5749e6d feat(engine): expand _update_vitals with Bladder, Sanity, Entertainment, Temperature drift
2dbc088 feat(ui): grouped vitals display with Physical/Mental columns + Temperature highlight
0c4aaec fix: use rounded val for Temperature display in inspector
926ab76 feat(ui): add new vitals to mini-bars, alerts, and NL descriptions
8e1afd1 fix: merge vitals on load instead of replace to preserve new defaults
6380da4 fix: serialize decay_rates in engine to_dict
f80b677 docs: add CRITICAL note to not restart server
```
