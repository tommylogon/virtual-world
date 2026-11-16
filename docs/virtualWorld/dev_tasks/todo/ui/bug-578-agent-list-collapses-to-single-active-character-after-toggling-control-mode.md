---
type: bug
status: todo
area: ui
priority: high
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [task-340, task-933, bug-577]
---

# bug-578: Agent list in left panel collapses to single active character after toggling control mode

**Filed:** 2026-11-09
**Related:** task-340, task-933, bug-577

<!-- deps:start -->
**Related:** [[task-340-event-stream-v2]], [[task-933-character-controller-selector-and-director-turn-composer]], [[bug-577-character-inspector-crashes-reading-bg-on-directed-control-mode]]
<!-- deps:end -->

## What

When cycling a character's control mode in the left-panel Agent List (e.g. clicking the control mode icon to switch from NPC to Human), all other characters in the scenario disappear from the list. Only the single selected/active character remains visible.

## Why

1. In `static/js/stream/stream-control-mode.ts` (lines 89-100), switching a character to `human` sets `makeActive = true`, which calls:
   ```ts
   config.controllingPlayer = charName;
   worldState.setRuntimeFocusForCharacter(charName);
   ```
2. `worldState.setRuntimeFocusForCharacter(charName)` sets `_runtimeFocus = [charId]`.
3. In `static/js/stream/stream-control-mode.ts` (lines 113-114):
   ```ts
   const freshState = await worldState.fetch();
   if (freshState && worldState.data) VW?.ui?.renderAll?.(freshState);
   ```
4. In `static/js/world-state.ts` (line 108):
   ```ts
   if (this._runtimeFocus.length) return this.fetchRuntime();
   ```
   Because runtime focus is non-empty, `worldState.fetch()` delegates to `this.fetchRuntime()`.
5. `fetchRuntime()` requests `/api/runtime/state?character_id=...`, which returns a character-scoped runtime snapshot (`snapshot_type: 'character_runtime'`). In this payload, `snapshot.players` contains ONLY the single focused character.
6. `fetchRuntime()` returns that isolated snapshot object as `freshState`.
7. Line 114 passes `freshState` directly into `VW.ui.renderAll(freshState)`.
8. `UIController.renderAll()` calls `renderAgentList(state)`. In `renderAgentList`:
   ```ts
   const players = state.players || {};
   let names = Object.keys(players);
   ```
   Because `state.players` holds only the single focused character, all other scenario characters are excluded and the list collapses.
9. Furthermore, `worldState.fetch()` violates its contract by returning the character runtime snapshot rather than `this.data` (the merged authoritative world state) when runtime focus is active.

## How

1. In `static/js/world-state.ts`:
   - When `this._runtimeFocus.length` is active in `fetch()`, await `this.fetchRuntime()` and then return `this.data`:
     ```ts
     if (this._runtimeFocus.length) {
         await this.fetchRuntime();
         return this.data;
     }
     ```
2. In `static/js/stream/stream-control-mode.ts`:
   - Pass `worldState.data` (or the returned `freshState` once guaranteed to be `worldState.data`) into `VW.ui.renderAll()`:
     ```ts
     const freshState = await worldState.fetch();
     if (worldState.data) VW?.ui?.renderAll?.(worldState.data);
     ```
3. Verify that `renderAgentList` retains all scenario characters when toggling control mode on any character.

## Acceptance Criteria

- Toggling control mode on any character in the left panel does not wipe out or hide the other scenario characters.
- All characters continue to appear in `#agent-list` with their respective control mode badges, vitals, and areas.
- `worldState.fetch()` always resolves to `worldState.data`, preserving complete world state access for callers.
