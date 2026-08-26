# Pause/Restart Resets Turn to Zero

**Filed**: 2026-07-19
**Priority**: High
**Status**: Done — fixed via the TurnQueue refactor (start() only initializes the queue when empty; turnNumber preserved across pause). Audited 2026-08-03

## Summary

Pausing the simulation and clicking "Start" calls `initializeTurnQueue()`, which resets `this.turnNumber = 0`. The turn count should be preserved across pauses so the simulation continues from where it left off.

## Current State

`agent-engine.js:45-76` — `initializeTurnQueue()`:

```javascript
initializeTurnQueue() {
    // ... build turn queue from players ...
    if (allPlayers.length === 0) {
        this.turnQueue = [];
        this.currentTurnIndex = 0;
        this.turnNumber = 0;  // ← resets
        return;
    }
    // ... sort by initiative ...
    this.currentTurnIndex = 0;
    this.turnNumber = 0;  // ← resets at end too
}
```

Called from `start()` at line 471:

```javascript
async start() {
    if (config.turnBased) {
        this.characterHistories = {};
        this.initializeTurnQueue();  // ← resets turnNumber
        ...
    }
    ...
}
```

Also called from `setCharacter()` in `main.js:1352` and `main.js:1396/1410`.

## Flow

1. Simulation runs for 10+ turns → `this.turnNumber = 10`
2. User clicks "Pause" → `stop()` → `config.running = false` (state preserved)
3. User clicks "Start" → `start()` → `initializeTurnQueue()` → `this.turnNumber = 0` (lost!)
4. Turn counter UI shows "Turn: 0" instead of "Turn: 10"

## Fix

### Option A: Preserve existing turnNumber in initializeTurnQueue

```javascript
initializeTurnQueue() {
    const existingTurn = this.turnNumber;
    // ... existing logic ...
    this.currentTurnIndex = 0;
    this.turnNumber = existingTurn;  // restore
}
```

But this could cause issues if players were added/removed between pause and restart.

### Option B: Don't call initializeTurnQueue in start() if queue exists

```javascript
async start() {
    if (config.turnBased) {
        this.characterHistories = {};
        if (this.turnQueue.length === 0) {
            this.initializeTurnQueue();
        }
        ...
    }
}
```

This preserves the existing queue and turnNumber. But if players changed, the queue would be stale.

### Option C: Reset only if explicitly requested

Add a `preserveTurn` parameter:

```javascript
initializeTurnQueue(preserveTurn = false) {
    // ... existing logic ...
    if (!preserveTurn) {
        this.currentTurnIndex = 0;
        this.turnNumber = 0;
    }
}
```

**Recommendation**: Option B is simplest and safest. `start()` should only rebuild the queue if it's empty (hasn't been initialized yet or was explicitly reset). If the user wants a full reset, they can click "Reset."

## Files

- `static/js/agent-engine.js:45-76` — `initializeTurnQueue()`
- `static/js/agent-engine.js:470-474` — `start()`
