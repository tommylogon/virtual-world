---
group: Environment & Climate
wiki: "[[World Building/Rooms & Areas]]"
---

# Relieve Yourself Should ADD to Area Smell, Not Replace

**Filed**: 2026-07-17
**Priority**: Low
**Status**: In Review — implemented (code-verified 2026-08-11). Exact append logic at `routes/action.py:275`: `env["smell"] = (existing + "; urine" if existing else "urine")`; `engine/area_description.py:343` consumes the smell.

---

## Summary

The `relieve` command uses `env["smell"] = "urine"` which outright replaces any existing room smell. If the room already smells of smoke, dust, or rotting food, that's lost.

## Current Code

In `app.py:221`:
```python
env["smell"] = "urine"
```

## Edge Cases to Consider

- **First time**: no smell → set to `"urine"`
- **Already smells of something else** (e.g. `"smoke"`, `"dust"`) → append: `"smoke, urine"`
- **Already smells of urine** (you pissed here before) → do nothing, the point is made. Not `"urine, urine, urine"`.
- **Already has urine among other smells** (e.g. `"smoke, urine"`) → do nothing, don't add another "urine"
- **Cleaning up** — if a cleaning action or trigger sets smell back to something else, that should naturally override. That's separate from this fix.

## Desired Logic

```python
current = env.get("smell", "")
if "urine" not in current:
    if current:
        env["smell"] = current + ", urine"
    else:
        env["smell"] = "urine"
```

## Files Affected

- `app.py` — line 221, the `relieve` handler