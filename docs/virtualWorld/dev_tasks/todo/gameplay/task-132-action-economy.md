---
group: Agent AI & Behavior
---
# Action Economy

**Filed**: 2026-07-30  
**Priority**: Low  
**Status**: Design  

---

## Summary

Add a flexible action economy system where characters have configurable numbers of actions per turn (action, bonus action, free action, reaction). Different characters can have different budgets — some might get 3 actions with no reactions, others 1 action with 2 bonus actions. Map all valid verbs to default action tiers.

---

## Problem

Currently every command costs flat time+energy (`move: {time:1, energy:1}`). There's no distinction between major actions (attacking, using an item) and trivial ones (opening an unlocked door, speaking). A character can attack, move, open a door, pick up an item, and talk all in one turn with no budget constraints. The economy is purely time-based, not action-slot-based.

---

## Complete Action Inventory

Below is every valid action in the game, organized by category, with proposed default action tier and time/energy costs.

### Movement
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `go` | `go [exit]` | **Action** | 1 | 1 | Moving to another area |
| `open` (unforced) | `open [exit]` | **Free action** | 0 | 1 | Unlocked/unforced door — trivial |
| `open` (forced/locked) | `open [exit]` | **Action** | 1 | 2 | Requires force — significant |
| `close` | `close [exit]` | **Free action** | 0 | 1 | Same as unforced open |

### Item Interaction
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `take` | `take [item]` | **Action** | 1 | 1 | Picking something up |
| `drop` | `drop [item]` | **Free action** | 1 | 0 | Dropping is quick |
| `use` | `use [item]` | **Action** | 1 | 1 | Activating/consuming an item |
| `use [item] on [target]` | | **Action** | 1 | 1 | Combined interaction |
| `eat` | `eat [item]` | **Action** | 1 | 0 | Consuming food |
| `drink` | `drink [item]` | **Action** | 1 | 0 | Consuming drink |
| `examine` | `examine [target]` | **Bonus action** | 1 | 0 | Quick inspection |
| `put [item] in [container]` | | **Bonus action** | 1 | 1 | Stowing item |
| `toggle` | `toggle [item]` | **Free action** | 0 | 0 | Flicking a switch, lighting a candle |

### Equipment
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `wear` / `equip` | `wear [item]` | **Bonus action** | 1 | 1 | Equipping one item |
| `remove` / `unequip` | `remove [item]` | **Bonus action** | 1 | 0 | Unequipping one item |
| `undress` | `undress` | **See task-131** | — | — | Stateful multi-turn action |
| `strip` | `strip` | **See task-131** | — | — | Stateful multi-turn action |

### Information
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `look` | `look` | **Free action** | 1 | 0 | Glancing around |
| `inventory` | `inventory` / `i` / `inv` | **Free action** | 0 | 0 | Checking your gear |
| `stats` | `stats` / `status` | **Free action** | 0 | 0 | Checking your condition |
| `examine` | `examine [target]` | **Free action** | 1 | 0 | Inspecting something |

### Social
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `speak` / `say` | `say [text]` | **Free action** | 0 | 0 | Speaking a few sentences |
| `yell` / `shout` | `yell [text]` | **Free action** | 0 | 1 | Loud speech costs energy |
| `whisper` | `whisper [text]` | **Free action** | 0 | 0 | Quiet speech |
| `do` | `do [description]` | **Free action** | 0 | 0 | Emote/narrative |

### Combat
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `attack` | `attack [target]` | **Action** | 1 | 2 | Standard attack |
| `attack with [weapon]` | | **Action** | 1 | 2 | Weapon attack |
| (off-hand attack) | | **Bonus action** | 1 | 1 | Off-hand weapon |
| (opportunity attack) | | **Reaction** | 0 | 1 | Triggers on enemy movement |
| (parry / dodge) | | **Reaction** | 0 | 1 | Triggered defensive action |

### Vitals / Self
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `rest` / `sleep` | `rest [min]` | **Action → stateful** | — | — | See task-131 |
| `fumble` | `fumble around` | **Action** | 2 | 3 | Blind search in darkness |
| `relieve` | `relieve` | **Action** | 1 | 0 | Bathroom break |

### Ghost
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `manifest` | `manifest` | **Bonus action** | 0 | 1 | Become visible |
| `vanish` | `vanish` | **Bonus action** | 0 | 1 | Become invisible |

### Default (unlisted actions)
Any verb not listed defaults to **Action** with `{time: 0, energy: 0}`.

---

## Action Economy Model

### Per-character configuration

Action budget is a per-character trait/config, not hardcoded:

```python
player.action_budget = {
    "action": 1,       # major actions per turn
    "bonus": 1,        # minor quick actions per turn
    "free": 3,         # trivial actions per turn (capped, but rarely hit)
    "reaction": 1,     # reactive actions per turn (resets on turn start)
}
```

These can vary by character:
- **Standard**: 1 action, 1 bonus, 3 free, 1 reaction
- **Veteran fighter**: 2 actions, 1 bonus, 3 free, 1 reaction
- **Quick / DEX-based**: 1 action, 2 bonus, 3 free, 1 reaction
- **Sluggish / exhausted**: 1 action, 0 bonus, 2 free, 0 reaction
- **Panicked**: 1 action, 1 bonus, 3 free, 0 reaction (can't react)

Traits can modify budgets:
- `slow`: -1 action per turn
- `quick_reflexes`: +1 reaction per turn
- `indecisive`: -1 bonus action per turn

### Tier definitions

| Tier | Used for | Capped per turn | Resets |
|------|----------|-----------------|--------|
| **Action** | Major activities (attack, cast, use item, move, take) | Configurable (default 1) | Start of character's turn |
| **Bonus action** | Quick secondary activities (toggle, equip, off-hand attack) | Configurable (default 1) | Start of character's turn |
| **Free action** | Trivial activities (speak, examine, drop, look) | Configurable (default unlimited / soft cap 3) | Start of character's turn |
| **Reaction** | Response to others' actions (parry, opportunity attack, dodge) | Configurable (default 1) | Start of character's turn |

### Interaction with existing time/energy costs

The action economy is an **additional layer** on top of time/energy:

- An action still costs its `time` and `energy` values
- BUT if the character has no **Action** slots remaining, they can't take an action-tier verb even if they have energy
- A **Free action** that costs 1 time still takes game time but doesn't consume a budget slot
- Reactions can happen off-turn — they consume a reaction slot and reset at the start of the character's next turn

### Prompt injection

The agent prompt should include remaining action budget:

```
=== ACTION BUDGET ===
Actions remaining: 1/1
Bonus actions remaining: 1/1
Reactions available: 1/1 (used off-turn)

Choose ONE action from the list above.
```

Low-action-budget agents should be prompted to prioritize ("You only have 1 action left this turn — make it count.")

### Time cost ties to stateful actions (task-131)

Time costs feed into the stateful actions system — if an action costs 1 time and the character has no time remaining, they're out of actions for the turn. Time is the bridge between the action budget and the turn cycle.

---

## Agent Multi-Action: Design Decision

If a character has budget for e.g. 1 action + 1 bonus + 1 free, how does the agent execute them?

### Option A: Single prompt, sequence of actions

Agent generates all actions in one LLM response with a multi-part JSON schema:

```json
{
  "action": "attack Butcher",
  "bonus": "examine bookshelf",
  "free": "say 'take that!'"
}
```

- **One LLM call** per turn — fast, cheap
- **Coherent plan** — actions can reference each other
- **Simpler turn queue** — one cycle per character
- **Con:** Complex validation — if the action fails, what happens to the bonus and free? Do they still execute?
- **Con:** Larger prompt, more tokens per call
- **Con:** Can't adapt mid-turn based on action results

### Option B: Multiple prompts, loop per character

Agent generates one action at a time. After each action resolves, if budget remains, prompt again for the next action:

```
→ Prompt 1: "You have 1 action + 1 bonus + 3 free remaining. What do you do?"
  → Agent: {"action": "attack Butcher"}
  → Action resolves, budget = 0 action / 1 bonus / 3 free
→ Prompt 2: "Action resolved. You have 1 bonus + 3 free remaining. Bonus action?"
  → Agent: {"bonus": "examine bookshelf"}
  → Bonus resolves, budget = 0 bonus / 3 free
→ Prompt 3: "Bonus resolved. You have 3 free actions. Free action?"
  → Agent: {"free": "'take that!'"}
  → Free resolves, turn ends
```

- **Adaptive** — each action sees the result of the previous one
- **Simpler schema** — one action type per response
- **Smaller prompts** — per-action context
- **Con:** Multiple LLM calls (3× slower, 3× cost per character turn)
- **Con:** Actions may lose coherence — agent might change its mind mid-turn based on results
- **Con:** Turn queue becomes more complex (sub-cycles per character)

### Option C: Hybrid — single prompt, sequential execution

Agent generates all planned actions at once, but they're executed sequentially with result chaining:

```json
{
  "action": "attack Butcher",
  "expected_result": "Butcher takes damage and retaliates",
  "bonus_if_possible": "examine bookshelf",
  "free": "say 'take that!'"
}
```

- One LLM call for planning
- Each action still resolves independently
- If action fails (Butcher dodged), bonus is skipped or replaced
- **Con:** More complex schema, harder for LLM to predict outcomes

### Recommendation

Start with **Option A** for simplicity — single prompt, multi-part response. If the action sequence is interrupted, remaining actions are lost (the character only gets to act out what they planned). Can evolve to Option B later if adaptive behavior is worth the extra cost.

- Add `player.action_budget` dict (configurable, with defaults)
- Reset budgets at the start of each character's turn in `turn-queue.js`
- Check budget in `routes/action.py` before executing the command
- Return an error if budget is exhausted: "You're out of actions this turn."
- Free actions have a soft cap (log a warning but don't block unless over ~5+)
- Reactions are checked in the agent loop when processing other characters' actions
- `engine/tick_manager.py` resets budgets via `apply_turn()`

## Related

- [[todo/gameplay/task-131-stateful-actions-over-time|task-131: Stateful actions]] — rest/sleep become stateful
- `engine/tick_manager.py` — existing time/energy costs
- `static/js/agent/turn-queue.js` — turn cycle management
- `routes/action.py` — verb dispatch
