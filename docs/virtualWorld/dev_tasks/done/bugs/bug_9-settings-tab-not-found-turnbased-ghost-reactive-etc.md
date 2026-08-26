# Bug 9: Can't find settings tab with turn-based, ghost mode, reactive, LLM logs etc.

**Filed**: 2026-07-23
**Priority**: Medium
**Status**: Fixed (escaped `&` entity, renamed tab to "Behavior & Automation")

## Summary

User cannot see a tab or section in the Settings modal that contains turn-based mode, ghost mode, reactive mode, LLM logs toggle, and related settings.

## Current State

These settings exist in the Settings modal under the "Automation & Advanced" tab (`tab-automation`), which is the second of two tabs (alongside "Connection"). If the tab button is not rendering or the user can't find it, possible causes:

1. CSS issue hiding the `.tab-btn` for `data-tab="tab-automation"` (unlikely — both tabs use the same class)
2. The button is visible but the label "Automation & Advanced" is not descriptive enough — user may be looking for a "Provider" or "Behavior" tab label
3. Tab switching or tab rendering issue where the pane content doesn't show

## Investigation

- Check that the `tab-automation` button renders in the DOM
- Check `switchSettingsTab()` function (`main.js:92`) and `SettingsView.switchTab()` for bugs
- Consider adding clearer tab labels or a dedicated "Provider" tab

## Files

- `templates/index.html:179-182` — settings tab buttons
- `templates/index.html:207-228` — Automation & Advanced tab content (turn-based, ghost, reactive, LLM logs all here)
- `static/js/ui/settings-view.js` — `switchTab()` logic
- `static/css/style.css:673-721` — tab button and pane styles
