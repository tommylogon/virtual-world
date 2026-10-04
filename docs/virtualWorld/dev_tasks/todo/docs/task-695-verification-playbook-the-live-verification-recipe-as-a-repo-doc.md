---
type: task
status: todo
area: docs
priority: medium
---

# task-695: Verification playbook: the live-verification recipe as a repo doc

**Filed:** 2026-10-04
**Related:** bug-520,bug-521,task-444

## Goal

TODO

## Acceptance
A short doc (docs/design/verification-playbook.md) capturing how to verify a UI
claim end-to-end, distilled from the 2026-10-04 session so the next agent does not
rediscover it. AGENTS.md points at it.

- [ ] Documents where state lives: turn queue is client-side (`VW.agent`), world
      state is server-side; a second browser tab is a safe sandbox.
- [ ] The safe-interaction list: hover, chip clicks (draft only — "nothing fires
      until Act"), menus, `#player-room` as the character-teleport control,
      `HumanTurnComposer.request(name)` to open the turn card directly.
- [ ] The unsafe list: Act / close turn / skip-react / Escape (dismiss resolves
      with endTurn) / scenario switching on a live session / server restarts.
- [ ] Evidence sources: DOM counts via getBoundingClientRect (offsetParent lies for
      position:fixed), `data/autosave.json` as server truth, event stream rows,
      screenshots for layout claims.
- [ ] Where server logs go (stdout of the launching terminal) and why that means
      agents need task-696.
- [ ] Linked from the STOP gate section of AGENTS.md as the "how" companion.

