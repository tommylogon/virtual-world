# Bug-17: Rounding of Area Temperature

**Status:** Done — fully fixed 2026-08-30: display rounding at every UI site (tree-view outline+copy, agent-lens, world-export, area-view improve prompt) plus storage rounding in `engine/environment_propagation.py` (round to 0.1 on writes). Live-verified in the GUI (outline shows -10.5, 0.8, -1 instead of noise); full suite green.
**Area:** Environment — area temperature / area inspector
**Observed:** The Temp °C field in the area inspector shows raw unrounded floats
and `parseInt` truncates on save.

## Repro (live area inspector HTML)

```html
<label style="min-width:50px;">Temp °C</label>
<input type="number" min="-50" max="100" value="23.22679159375" style="flex:1;"
       onchange="InspectorAreaView._updateEnv('area_conservatory','temperature',parseInt(this.value))">
```

Two bugs in one:
1. **Display**: `value` renders the raw stored float (`23.226791593125`), so the
   inspector shows long decimals that drift with environment propagation.
2. **Save**: `parseInt(this.value)` *truncates* — `23.8` saves as `23`, and
   negative values are fine but fractional temps get silently floored every
   edit, so you can never store a decimal temperature.

## Root cause

`static/js/inspector/area-view.js` line 194:

```js
<input type="number" min="-50" max="100" value="${env.temperature ?? 21}" style="flex:1;"
       onchange="InspectorAreaView._updateEnv('${escapedId}','temperature',parseInt(this.value))">
```

No rounding for display, `parseInt` for the value.

## Fix

- Display: round to 1 decimal (`Math.round(env.temperature * 10) / 10`).
- Save: use `parseFloat` rounded to 1 decimal instead of `parseInt`.
- Check whether the effective temp fed to vitals/drain math elsewhere also needs
  a consistent rounding (engine `environment_propagation.py` writes floats; the
  display should match the value actually stored).