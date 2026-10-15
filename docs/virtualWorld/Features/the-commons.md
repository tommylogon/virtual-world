---
type: feature
feature_id: 78
status: wired
section: in-game
tags: [status/wired, surface/in-game, system/gameplay]
---

# The Commons

**What you can do:** Let characters talk across distance through public posts,
private group chats, and direct messages.

## How it works

- [[Gameplay/The Commons]] — conversation types, membership and privacy, read
  state, character memory, persistence, and current limits.

## Where it lives

- `templates/index.html` — menu entry.
- `templates/commons.html` — The Commons page.
- `engine/commons.py` and `routes/commons.py` — conversation data and
  authorized message operations.
- `static/js/commons/` — conversation interface and character actions.

## Connected

- Feature Map: [[Feature Map|row 78]] (In a game)
- Sibling features: [[talk-speak]], [[whisper-shout]], [[relationships]]
- Deep documentation: [[Gameplay/The Commons]]
- All features: [[Features Overview]]

> [!note] Status — `wired`
> The public, group, and direct-message flows are implemented and browser-checked.
> See [[Gameplay/The Commons]] for the unfinished standard agent path and
> scenario-authoring limits.
