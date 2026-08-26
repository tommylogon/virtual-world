---
group: Agent AI & Behavior
wiki: "[[AI & Narration/Narration System]]"
---

# Observe Step: Use Full Area Description (like `look` command)

**Filed**: 2026-07-17
**Priority**: Medium
**Status**: Implemented / Needs Review

---

## Summary

The observe step (inner monologue) used a compact room context with a basic item list. Now it fetches the full rich description from `get_area_description()` — same output as the `look` command — with woven item descriptions, environment conditions, sounds, smells, and temperature warnings.

## Changes

- Added `/api/room/description` endpoint in `app.py` — calls `world.get_area_description()` for the current active player
- Added `ApiClient.getAreaDescription()` in `api.js`
- Modified `agent-engine.js` observe step to fetch the rich description and use it as the prompt body, with inventory and witnessed events appended
- Falls back to the compact `roomContext` if the API call fails

## Files Changed

- `app.py` — new route `/api/room/description`
- `static/js/api.js` — `getAreaDescription()` method
- `static/js/agent-engine.js` — observe step fetches and uses rich description