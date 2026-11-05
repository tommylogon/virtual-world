---
type: task
status: todo
area: docs
priority: medium
wiki: "[[Feature Map]]"
---

# task-695: Verification playbook: the live-verification recipe as a repo doc

**Filed:** 2026-10-04
**Related:** bug-520,bug-521,task-444

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — this task creates a repository verification guide, not a new product surface. The guide's examples direct future agents to existing browser controls and state surfaces.

Current availability: the acceptance names `docs/design/verification-playbook.md` and lists the required safe-interaction and state-ownership guidance. The guide is not claimed as written by this card.

Why no browser UI: the deliverable is a document that teaches how to inspect the application; the document itself is checked as repository content, not opened from the game UI.

Alternative verification steps:
1. Read the completed playbook and check that it distinguishes `VW.agent` client turn-queue state from server world state and explains why a second browser tab is safe.
   - expected: those exact ownership boundaries and the no-commit/no-world-mutation condition are stated.
2. Follow its safe-interaction list in a scratch browser tab: hover a chip, click it to draft, open a menu, inspect `#player-room`, and call `HumanTurnComposer.request(name)`.
   - expected: the documented outcome matches each interaction; hovering is free-look, clicking a chip drafts only, and nothing acts before Act.
3. Run `npm run precommit` after updating the vault note and AGENTS pointer.
   - expected: vault guards pass and the playbook is linked from the project guidance.

This section is not a claim that planned UI exists or works today.
