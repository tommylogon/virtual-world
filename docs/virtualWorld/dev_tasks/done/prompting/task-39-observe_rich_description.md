---
area: prompting
wiki: "[[AI & Narration/Narration System]]"
type: task
status: done
priority: medium
---

# Observe Step: Use Full Area Description (like `look` command)

**Filed**: 2026-07-17
**Priority**: Medium
**Status**: Implemented / Needs Review

---

## What

The observe step (inner monologue) used a compact room context with a basic item list. Now it fetches the full rich description from `get_area_description()` — same output as the `look` command — with woven item descriptions, environment conditions, sounds, smells, and temperature warnings.

## How

- Added `/api/room/description` endpoint in `app.py` — calls `world.get_area_description()` for the current active player
- Added `ApiClient.getAreaDescription()` in `api.js`
- Modified `agent-engine.js` observe step to fetch the rich description and use it as the prompt body, with inventory and witnessed events appended
- Falls back to the compact `roomContext` if the API call fails

## Files

- `app.py` — new route `/api/room/description`
- `static/js/api.js` — `getAreaDescription()` method
- `static/js/agent-engine.js` — observe step fetches and uses rich description

## Why

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO
