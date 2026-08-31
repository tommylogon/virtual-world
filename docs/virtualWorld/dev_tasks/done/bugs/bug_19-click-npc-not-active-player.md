# Bug-19: Clicking an NPC Does Not Set Them as Active Player

**Status:** Done — confirmed by Tommy 2026-08-30.
**Area:** Graph editor â€” character interaction
**Observed:** `clicking on a nc does not set them as active player`

## Root cause

Two click paths opened the inspector but never switched the active/controlling
player:

1. **Agent list** (`ui-controller.js` `renderAgentList`): rows for `simple_npc`
   characters used `ui.showAgentAndFocus(name)` (inspector + camera only) while
   normal agents used `selectAgent(name)` (sets active player via
   `/api/players/active`, sets `config.controllingPlayer`, focuses node).
2. **Graph click** (`graph/event-handlers.js` `onClick`): character node clicks
   only called `VW.inspector.showNode(...)`, which renders the agent inspector
   but never sets the active/controlling player.

## Fix

- `renderAgentList`: NPC rows now call `selectAgent(name)` like every other
  agent â€” click = set active + controlling player + open inspector + focus.
  Removed the now-unused `ui.showAgentAndFocus` helper.
- `GraphEventHandlers.onClick`: when the clicked node is a `character` backed by
  a `worldState.players` entry, it calls `ui.selectAgent(name)`; everything else
  keeps the plain inspector path.

## Verification

- `node --check` passes on both edited files.
- The shared `selectAgent` flow now also drives `config.controllingPlayer`, so
  the sim's Step Once acts on the clicked NPC in non-turn-based mode (test-as-you-
  build). Live browser re-check pending.
