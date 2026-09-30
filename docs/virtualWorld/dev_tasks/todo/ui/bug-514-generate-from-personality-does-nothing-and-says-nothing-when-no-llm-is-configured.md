---
type: bug
status: todo
area: ui
priority: medium
---

# bug-514: Generate from Personality does nothing and says nothing when no LLM is configured

**Filed:** 2026-09-30
**Related:** 

## Goal

Both generators open with 'if (!player || !AIGenerator.isConfigured()) return;'. With no provider configured the button silently does nothing - no toast, no disabled state, no explanation - so it reads as a broken button rather than a missing setting. Verified in the browser: AIGenerator.isConfigured() false produces no prompt, no write and no message. Disable the button with a tooltip pointing at Settings, or toast a reason.

## Acceptance

- TODO
