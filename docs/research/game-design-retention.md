# Game Design & Player Retention — Research

## The Problem
Virtual World is a powerful simulation engine, but simulations aren't inherently *games*. Players need goals, stakes, progression, and reasons to return. The current architecture supports all of these technically but doesn't provide them by default.

## What VW Is vs. What VW Could Be

### Current: Sandbox Simulator
- Player can go anywhere, do anything
- NPCs react to player actions
- World evolves over time
- No goals, no win conditions, no failure states

### Target: Emergent Narrative Game
- Player has reasons to explore (quests, secrets, relationships)
- Choices have meaningful consequences
- Progression is visible (skills, relationships, reputation)
- World remembers player actions across sessions
- NPCs have their own goals that intersect with player goals

## Key Design Questions

### 1. What Makes Players Return?
**Research finding:** Players return for **social bonds** (relationships with NPCs) and **unfinished business** (active quests, unresolved mysteries).

**VW advantage:** Already has relationship system, memory system, persistent world state.

**Gap:** No quest system, no mystery generation, no "unfinished business" tracking.

### 2. How Do You Create Goals in an Open World?
**Approaches:**
- **NPC-driven quests:** NPCs have needs → player can fulfill them → relationship improves → new opportunities
- **Environmental storytelling:** World state contains clues → player pieces together narrative
- **Dynamic events:** World generates situations (bandit attack, festival, disaster) → player responds → consequences ripple

**VW implementation:** The trigger system can generate quest-like events. The gap is **quest tracking** — does the player remember what they're trying to do?

### 3. What's the Right Pacing for LLM Turns?
**Problem:** LLM turns are slow (500ms-2s per call). In reactive mode, 2 calls per turn = 1-4s per NPC action.

**Current:** Turn-based mode gives players time to think. Continuous mode is faster but overwhelming.

**Finding:** Most successful LLM NPC games use **hybrid pacing:**
- Player actions: real-time or fast turn-based
- NPC responses: 500ms-2s (player expects "thinking time")
- World ticks: periodic (every 10-30 seconds)
- NPC autonomous actions: every 30-60 seconds

### 4. How Do You Teach the Interaction Model?
**Problem:** VW has a rich command set (go, take, use, examine, give, steal, etc.) but no tutorial.

**Finding:** Players learn through **failure + feedback**, not manuals.
- First action: "look" → shows room description
- Second action: "take key" → succeeds, teaches take
- Failed action: "climb wall" → "You can't do that" → teaches verb boundaries

**VW advantage:** The event stream shows all actions and results. A "first turn" guide could highlight the most important actions.

### 5. What's the Right Difficulty Curve?
**Problem:** LLM NPCs are unpredictable. Sometimes brilliant, sometimes broken. How do you create consistent challenge?

**Finding:** Good game difficulty comes from **meaningful choices**, not statistical challenge.
- Easy: "Pick the lock" (single action, deterministic outcome)
- Hard: "Convince the guard to let you pass" (requires social skill, multiple possible outcomes)
- Brilliant: "The guard is corrupt but loyal. You could bribe him, threaten him, or appeal to his sense of duty. Each has different consequences."

**VW advantage:** The trigger system + LLM can create exactly this kind of branching social challenge.

## Retention Mechanics

### Short-term (Session)
- **Immediate feedback:** Every action has visible consequences (event stream)
- **Curiosity gaps:** "What's behind that locked door?" → player returns to find out
- **Social obligations:** "Lyrie asked me to find her brother" → player feels compelled

### Medium-term (Days)
- **Relationship depth:** "Miki trusts me now — I should visit her"
- **World changes:** "The festival I helped organize is tomorrow"
- **Unfinished quests:** "I still need to find the blacksmith's lost sword"

### Long-term (Weeks)
- **Reputation:** "Everyone in town knows me as the hero who saved the festival"
- **World legacy:** "The decisions I made changed the town forever"
- **Character growth:** "My character has changed from the person I started as"

## Recommended VW Game Design Additions

### 1. Quest Tracker (1-2 weeks)
- Track active/completed/failed quests
- Show quest log in UI
- NPCs reference active quests in dialogue
- Quest completion triggers world state changes

### 2. Consequence System (2-3 weeks)
- Player actions set world flags
- NPCs react to flags (welcome/reject based on reputation)
- World state changes persist across sessions
- "Butterfly effect" — small actions have delayed consequences

### 3. Mystery Generation (1-2 weeks)
- Procedurally generate secrets in the world
- Clues scattered across areas
- NPCs have hidden knowledge (only revealed through relationship building)
- Player pieces together narrative from fragments

### 4. Progression System (2-3 weeks)
- Skills improve with use (Athletics from climbing, Persuasion from talking)
- Reputation with factions (townsfolk, guards, merchants)
- Unlock new areas/actions as relationships deepen
- Visible progression in UI (skill bars, reputation meters)

## Key Insight
**VW doesn't need to *add* game mechanics — it needs to *surface* the game mechanics it already has.** The trigger system, relationship system, and memory system are all there. The missing piece is a quest/consequence layer that connects player actions to meaningful outcomes over time.
