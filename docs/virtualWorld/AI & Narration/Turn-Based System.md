---
type: system
status: done
area: agent
priority: high
---

# Turn-Based System

The engine supports four modes of operation for how agents and the game world advance: **off** (continuous), **sequential**, **random**, and **initiative**. All are toggled from the Automation tab in the Settings modal.

## Modes

### Off (Continuous)

- `config.turnBased = false`
- No turn queue. The active character acts immediately when "Play" is clicked.
- The agent loop runs on whichever character is set as `controllingPlayer`.
- Steps are counted directly, not divided among queue positions.
- **No automatic vital decay** — decay only fires on `/api/turn/apply`, which only happens on queue wraps.

### Sequential

- `config.turnBased = true`, `config.turnOrder = 'sequential'`
- Characters sorted alphabetically by name.
- Each character acts once per round in order.
- When the queue wraps (last character acts), the backend applies a tick: vital decay, environmental effects, NPC behavior, clock advancement.

### Random

- `config.turnBased = true`, `config.turnOrder = 'random'`
- Queue is shuffled via `Math.random()` on each round.
- Otherwise identical to sequential.

### Initiative

- `config.turnBased = true`, `config.turnOrder = 'initiative'`
- Each character rolls `d20 + DEX bonus` on queue init.
- Sorted descending by roll; alphabetical tiebreaker.
- Rolls are stored and displayed in the initiative sidebar.
- Otherwise identical to sequential.

## Architecture

### Frontend: Turn Queue

**File:** `static/js/agent/turn-queue.js`

The `TurnQueue` singleton builds and manages the ordered list:

1. **`initialize()`** — Gathers alive players (all if ghost mode), sorts by current mode, rolls initiative if needed, resets index/round counter.
2. **`advance()`** — Moves to next character. On wrap (`currentTurnIndex === 0`):
   - Calls `ApiClient.applyTurn()` → `POST /api/turn/apply` → `TickManager.tick_turn()`
   - Calls `ApiClient.clearTurnEvents()` → `POST /api/turn/clear`
3. **`getCurrentCharacter()`** — Returns the active character for the current step.

Queue state lives on the `AgentEngine` instance (`VW.agent`):
- `turnQueue` — ordered array of character names
- `currentTurnIndex` — 0-based position
- `turnNumber` — completed rounds
- `initiativeRolls` — `{charName: roll}` map

### Backend: Tick Processing

**File:** `engine/tick_manager.py`

`TickManager.tick_turn()` fires on queue wrap and handles:
- Periodic condition processing (poison, sick, etc.)
- Baseline vital decay (hunger, thirst, sanity, bladder)
- Trait multiplier application
- Exhaustion → unconscious → death chain
- Environmental effects (temperature, air quality, noise, light, smell)
- Body temperature drift
- Active item usage (uses decrement, `on_tick` triggers)
- Sleep timers
- Clock advancement (+1 tick)
- Simple NPC behavior processing

### Step Flow

```
Play/Step clicked
  → TurnQueue.build() if empty
  → AgentEngine.step()
    → /api/action (LLM decides + acts)
    → TurnQueue.advance()
      → wraps? → /api/turn/apply (decay) + /api/turn/clear (inc turn_number)
    → Set next character
  → Re-render UI
  → Repeat if running (2s delay between steps)
```

## UI

### Turn Mode Selection

Settings modal → Automation tab:
- **Checkbox:** Turn-Based Mode — toggles `config.turnBased`
- **Select:** Turn Order — Sequential / Random / Initiative (shown only when turn-based is checked)

### Initiative Sidebar

Rendered by `ui-controller.js` `_renderInitiative()`:
- Round number
- Per-character row: position number, icon (▶️ active / ✅ done / ⏳ waiting), name, initiative roll (in initiative mode), status text
- Hidden entirely when turn-based is off or queue is empty

### Step Display

- Turn-based: `Turn N+1 — M/K` (current step / total steps per round)
- Continuous: `Step: runs/max (remaining)`

## Ghost Mode Interaction

Dead characters are excluded from the turn queue by default. When `config.ghostMode` is true, dead characters are included — they can observe and move but need skill checks to interact physically.

## Reactive Mode (Separate Concern)

`config.reactiveMode` controls the **LLM interaction pipeline**, not the turn queue:
- **On (default):** Three-phase cycle — think (observe) → decide → act → react
- **Off:** Single combined response (thought + speech + action in one LLM call)

Orthogonal to turn-based vs continuous.

## Key Files

| File | Role |
|------|------|
| `static/js/agent/turn-queue.js` | Queue init, sort, advance |
| `static/js/agent-engine.js` | Step loop, LLM orchestration |
| `static/js/config.js` | `turnBased`, `turnOrder` persistence |
| `static/js/ui-controller.js` | Initiative sidebar, step display |
| `static/js/ui/settings-view.js` | Settings form |
| `templates/index.html` | Settings checkbox + select |
| `engine/tick_manager.py` | `tick_turn()` — decay, environment, NPCs |
| `engine/logging_events.py` | Turn events logging |
| `routes/action.py` | `/api/turn/apply`, `/api/turn/clear` |
