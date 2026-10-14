---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Gameplay/Stage Chat]]"
---

# task-824: Stage chat: character perspective chat page

**Filed:** 2026-10-14
**Status:** review (2026-10-14)
**Related:** task-825 (async cooldown/talkativeness — provides pacing)

## What

Create a new "Stage Chat" page in the app (separate from the main game view,
like Soak/Timeline pages). Characters perceive the chat like a phone app — they
know it exists and can choose to open it, scroll back, and post. Characters do
not auto-see messages; they must choose to read. The page shows the public chat
log, each character's inner monologue and decision-making, and
join/leave/block controls.

## Current Progress (Updated 2026-10-14)

- [x] Backend model implemented in `engine/stage_chat.py` (ordered messages, participant tracking, perspective read).
- [x] Backend API routes created in `routes/stage_chat.py` (`/api/stage-chat/*`).
- [x] Wired backend into `virtual_world_engine.py` and `app.py`.
- [x] Page template and route added (`templates/stage_chat.html`, `routes/pages.py`).
- [x] CSS stylesheet added (`static/css/stage-chat.css`).
- [x] Navigation item added to Game menu in `templates/index.html`.
- [x] TypeScript API client created (`static/js/stage-chat/stage-chat-api.ts`).
- [x] Frontend state, UI, agent loop and app bootstrap implemented (`stage-chat-state.ts`, `stage-chat-ui.ts`, `stage-chat-agent.ts`, `stage-chat-app.ts`).
- [x] TypeScript build compiled cleanly (`npm run build:ts`).

## Acceptance

- [x] Separate Stage Chat page accessible from UI/nav (`/stage-chat`).
- [x] Public stage log with message ids, timestamps, author.
- [x] Per-character `last_read_message_id` tracking.
- [x] `read_chat` supports latest/all/range with correct semantics.
- [x] `write_chat` posts to public log.
- [x] Characters cannot auto-read; must explicitly choose. Silence allowed.
- [x] Character tools restricted to read_chat/write_chat only.
- [x] No DM mechanism; all writes go to stage.
- [x] Standard agent loop per action: recall → decide → act → write memory.
- [x] Subjective memory (1–4 sentences, first person) written to normal Player memory after each round.
- [x] Inner monologue visible in UI (first-class, not debug).
- [x] All scenario characters in chat by default.
- [x] Join/leave/block controls per character.
- [x] Per-character talkativeness slider (5s–120s with jitter).
- [x] No world/items connection (standalone social space).

## Files

- [x] `engine/stage_chat.py` (Chat state & perspective logic)
- [x] `routes/stage_chat.py` (API endpoints)
- [x] `routes/pages.py` (Page view)
- [x] `templates/stage_chat.html` (HTML shell)
- [x] `static/css/stage-chat.css` (UI styling)
- [x] `static/js/stage-chat/stage-chat-api.ts` (API Client)
- [x] `static/js/stage-chat/stage-chat-state.ts`
- [x] `static/js/stage-chat/stage-chat-ui.ts`
- [x] `static/js/stage-chat/stage-chat-agent.ts`
- [x] `static/js/stage-chat/stage-chat-app.ts`
