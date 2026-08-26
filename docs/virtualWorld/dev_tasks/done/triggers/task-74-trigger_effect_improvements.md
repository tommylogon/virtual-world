# Trigger Effect Improvements — adjust_vital, set_state, Memory, TurnQueue

**Filed**: 2026-07-18
**Priority**: High
**Status**: Done

---

## Summary

Four fixes/improvements applied across multiple files:

1. **adjust_vital Stat dropdown** — free-text stat field replaced with `<datalist>` of common vitals
2. **set_state Node ID / State dropdowns** — Node ID defaults to "self", state uses datalist of common states
3. **Area observation memory** — spatial context stored as memory each step for agent recall
4. **Scenario load turnQueue bug** — stale characters from previous scenario persisted in initiative order after reload

---

## Changes

### 1. adjust_vital — Stat datalist

**Files**: `item-library.js`, `inspector.js`

**What changed**:
- ADD overlay (item-library.js line 591, inspector.js line 1107): `<input class="eff-vital-stat">` now has `list="eff-vital-stat-list"`
- EDIT overlay (inspector.js line 1243): same change
- Global datalist `eff-vital-stat-list` created in body with options: HP, Energy, Bladder, Sanity, Entertainment, Temperature
- Datalist created once per overlay (guarded by `document.getElementById`)

**Why**: Agents need to adjust vitals like HP, Energy, Bladder, Sanity, etc. Free-text was error-prone.

### 2. set_state — Node ID default "self" + State datalist

**Files**: `item-library.js`, `inspector.js`

**What changed**:
- ADD overlays: Node ID input defaults to `value="self"` with `list="eff-state-node-list"`
- ADD overlays: New State input defaults to `value="on"` with `list="eff-state-val-list"`
- EDIT overlays: same with `${ep.node_id || 'self'}` fallback
- State datalist `eff-state-val-list`: on, off, open, closed, locked, unlocked, lit, unlit, broken, pristine, activated, deactivated, hidden, visible
- Node ID datalist `eff-state-node-list`: populated from `worldState.graph.nodes` keys
- Save functions (`_saveTrigger`, `_saveTriggerToNode`): when node_id is empty or "self", substitutes `'self'` (engine interprets as current item)

**Why**: set_state without a node ID should target the current item ("self"). States are limited to known values.

### 3. Area observation memory

**File**: `agent-engine.js` line 207

**What changed**:
- After building room context each step, a concise spatial snapshot is stored as memory:
  ```
  At {room name}. Exits: north → Living Area (open); south: A wooden door (closed)
  ```
- Memory type: `'observation'`, importance: 4

**Why**: Previously, the agent saw room descriptions each step but couldn't recall where exits or locations were between steps (e.g., "where is the outhouse?").

### 4. Scenario load turnQueue bug

**Files**: `agent-engine.js`, `main.js`

**What changed**:
- `agent.reset()` now clears `this.turnQueue`, `this.currentTurnIndex`, `this.turnNumber`
- `worldState.on('update', ...)` auto-initializes turnQueue when empty and players exist

**Root cause**: `reset()` did not clear the turn queue. On scenario load, `uploadWorld()` called `agent.reset()` then `worldState.fetch()`, but the old queue survived. `stepOnce()` only re-initialized when `turnQueue.length === 0`, which was never true with stale names. So the old scenario's characters appeared in initiative order.

**Why it's fixed now**: `reset()` clears the queue → `_renderInitiative` shows nothing → on worldState update, queue auto-initializes from current `worldState.players` → correct characters appear.
