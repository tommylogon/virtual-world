# NPC-to-NPC Interaction — Research

## The Problem
Virtual World NPCs take turns in the queue, but they don't meaningfully interact with each other. Each NPC's turn is isolated — they observe the world and act, but don't respond to other NPCs' actions unless the player mediates.

**Current behavior:**
```
Turn 1: NPC_A examines the room
Turn 2: NPC_B examines the room
Turn 3: NPC_A says "This room is interesting" (doesn't reference NPC_B's observation)
```

**Desired behavior:**
```
Turn 1: NPC_A examines the room
Turn 2: NPC_B examines the room
Turn 3: NPC_A says "Did you see that painting? Lyrie mentioned it yesterday." (references NPC_B's shared context)
```

## Why It Matters
- Makes the world feel alive, not a collection of isolated characters
- Creates emergent social dynamics (alliances, rivalries, gossip)
- Reduces player burden (NPCs create their own drama)
- Increases replayability (different social dynamics each playthrough)

## State of the Art

### 1. Generative Agents (Park et al., 2023)
**Approach:** NPCs observe each other and react. When an NPC sees another NPC do something interesting, they form a "social memory" and may reference it later.

**Key mechanism:**
- Observation buffer: every NPC action is visible to nearby NPCs
- Social relevance scoring: is this observation worth remembering?
- Lazy reaction: NPCs don't respond immediately, but incorporate observations into future responses

**Relevance to VW:** VW already has observation (room context shows other characters). The gap is the "social memory" layer and the "reference past observations" behavior.

### 2. Convai NPC-to-NPC
**Approach:** NPCs can converse without player presence. Uses a "conversation manager" that decides when NPCs should talk and who should speak next.

**Key mechanism:**
- Proximity-based conversation initiation
- Topic tracking (what are they talking about?)
- Turn-taking within NPC conversations
- Player can join or overhear

**Trade-offs:**
- Pro: Feels natural, emergent social dynamics
- Con: Expensive (N² potential conversations)
- Con: Can spiral into infinite NPC chatter

### 3. The "Social Context" Pattern
**Approach:** Instead of full NPC-to-NPC conversations, inject social context into each NPC's prompt.

**Example:**
```
=== SOCIAL CONTEXT ===
You observed:
- Lyrie examined the chest and looked worried (2 turns ago)
- Miki mentioned wanting to leave town (last turn)
- Valerius has been avoiding eye contact with you

You can reference these observations in your responses.
```

**Trade-offs:**
- Pro: Cheap, no extra LLM calls
- Pro: Feels like NPCs are aware of each other
- Con: One-way observation, not true interaction
- Con: NPCs can't respond to each other's speech

## Recommended Approaches for VW

### Phase 1: Observation Injection (1-2 days)
**Add to room context:** When building the prompt for an NPC, include what other NPCs did/said recently.

```javascript
function buildSocialContext(charName, currentTurn, recentTurns) {
    const observations = recentTurns
        .filter(t => t.character !== charName)
        .filter(t => t.character in getCurrentArea(charName))
        .slice(0, 5)
        .map(t => `- ${t.character} ${t.action_summary}`)
        .join('\n');
    
    if (!observations) return "";
    
    return `\n=== WHAT YOU NOTICED ===\n${observations}\nYou can reference these if relevant.`;
}
```

**Expected impact:** NPCs feel more aware. Low cost, high value.

### Phase 2: Social Memory (1 week)
**Add memory type:** `observation` memories for NPC actions (separate from player-triggered memories).

**Recall rule:** Include 1-2 recent social observations in the memory block.

**Expected impact:** NPCs reference past interactions naturally.

### Phase 3: NPC-to-NPC Turn Responses (2-3 weeks)
**Mechanism:** When an NPC acts (speaks, moves, uses item), nearby NPCs can add a "reaction" to the event stream without consuming their turn.

**Implementation:**
```javascript
// After NPC_A speaks:
const nearbyNpcs = getNpcsInSameArea(npcA.current_area).filter(n => n !== npcA);
for (const npc of nearbyNpcs) {
    if (shouldReact(npc, npcA.action)) {
        queueReaction(npc, npcA.action); // Adds to event stream
    }
}
```

**Cost control:**
- Cap reactions to 1 per NPC per 3 turns
- Only for story-relevant NPCs (not background)
- Use cheap model for reactions

## Key Insight
**Start with observation, not conversation.** Full NPC-to-NPC dialogue is expensive and prone to spiraling. Observation injection (Phase 1) gives 80% of the perceived benefit for 10% of the cost.
