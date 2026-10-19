# Bug 1: trigger-editor.js â€” `effOpts is not defined` on add trigger

**Filed**: 2026-07-23
**Priority**: High
**Status**: Fixed

## Summary

Clicking "Add Trigger" in the library item editor throws `Uncaught ReferenceError: effOpts is not defined` at trigger-editor.js:69.

## Root Cause

Typo in `trigger-editor.js`. The variable is declared as `const effectOpts` on line 41 but referenced as `effOpts` (missing the `c`) on lines 66 and 69:

```
Line 41:  const effectOpts = this._effectTypes.map(...).join('');
Line 66:  effectRowsHtml += this._buildEffectRowHtml(effOpts, eff, idx);
Line 69:  effectRowsHtml = this._buildEffectRowHtml(effOpts, null, 0);
```

## Fix

Change `effOpts` to `effectOpts` on lines 66 and 69.

## File

`static/js/shared/trigger-editor.js:66,69`

---
_Audited 2026-08-03 — duplicate file consolidated into this record._
