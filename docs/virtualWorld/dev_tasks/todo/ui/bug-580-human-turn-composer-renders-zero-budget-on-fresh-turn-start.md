---
type: bug
status: todo
area: ui
priority: high
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [bug-544, task-352]
---

# bug-580: Human turn composer renders 0 major 0 minor 0 free on fresh turn start

**Filed:** 2026-11-09
**Related:** bug-544, task-352

<!-- deps:start -->
**Related:** [[bug-544-disabling-turn-based-mode-does-not-reset-the-controlled-character-s-action-slots]], [[task-352-action-economy]]
<!-- deps:end -->

## What

When the Human Turn Composer opens on a character's turn start (e.g. `jake halloway's turn`), the budget indicators row renders all action pips hollow/spent and displays:

```
◇ □ ○ ○ ○  0 major · 0 minor · 0 free
```

The player appears to have zero actions available before taking any action.

## Why

1. On turn start, before any action is executed, `Player.turn_slots` in server state is `{}` (uninitialized budget).
2. In `static/js/agent/human-turn-composer.ts` (lines 289-298), `turnSlots()` correctly detects that `{}` means unstarted/unspent:
   ```ts
   function turnSlots(): Record<string, number> | null {
       const player = _charName ? worldState.runtimePlayer(_charName) : null;
       const slots = player?.turn_slots;
       if (!slots || typeof slots !== 'object') return null;
       return Object.keys(slots).length ? { ...slots } : null;
   }
   ```
   So `turnSlots()` returns `null` for a fresh turn.
3. However, in `renderPips()` (line 301):
   ```ts
   const s = turnSlots() || { major: 0, minor: 0, free: 0 };
   ```
   When `turnSlots()` returns `null`, line 301 falls back to `{ major: 0, minor: 0, free: 0 }`.
4. As a result, `renderPips()` marks every pip as `spent` and sets the budget labels to `0 major · 0 minor · 0 free`.

## How

1. In `static/js/agent/human-turn-composer.ts`:
   - Replace the zeroed fallback on line 301 with the default full turn budget:
     ```ts
     const defaultBudget = (window as unknown as { ActionTiers?: { DEFAULT_BUDGET: Record<string, number> } }).ActionTiers?.DEFAULT_BUDGET || { major: 1, minor: 1, free: 3 };
     const s = turnSlots() || { ...defaultBudget };
     ```
2. Verify that on turn start, before any actions are taken, all 5 pips render as unspent (`◆ ■ ● ● ●`) and the text reads `1 major · 1 minor · 3 free`.

## Acceptance Criteria

- Opening the Human Turn Composer on turn start renders full action pips: `◆ ■ ● ● ● 1 major · 1 minor · 3 free`.
- As actions are executed, pips update dynamically to reflect remaining slots.
- Only when all actions are genuinely spent does the display show `0 major · 0 minor · 0 free`.
