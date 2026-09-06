# Cost Management for Hosted Play — Research

## The Problem
Virtual World currently relies on user-provided API keys. For hosted/multiplayer operation, LLM costs are the dominant expense. No model tiering, no prompt caching, no token budgets exist.

## Cost Model

### Per-NPC-Turn Cost (Current)
```
Reactive mode: 2 LLM calls per turn
  - Think-decide: ~800 tokens input, ~300 tokens output
  - React: ~1000 tokens input (includes context), ~200 tokens output
  Total per turn: ~1800 input + 500 output tokens

At $0.15/1M input + $0.60/1M output (GPT-4o-mini):
  Cost per turn = (1800 × 0.15 + 500 × 0.60) / 1,000,000 = $0.00057

For 5 NPCs + 1 player, 10 turns per minute:
  Cost per minute = 6 × 10 × $0.00057 = $0.0342
  Cost per hour = $2.05
  Cost per player per day (4 hours) = $8.20
```

### Scaling to 100 Concurrent Players
```
100 players × 4 hours/day × $8.20 = $3,280/day = $98,400/month
```

**This is unsustainable without optimization.**

## State of the Art

### 1. Model Tiering (Industry Standard)
**Approach:** Route different NPC types to different models.

| Tier | Model | Cost | Use Case |
|------|-------|------|----------|
| Background | Llama 3 8B (local) | $0 | Greetings, idle chatter |
| Standard | GPT-4o-mini | $0.15/1M in | Merchants, quest givers |
| Story | GPT-4o | $5/1M in | Plot-critical NPCs, companions |

**Evidence:** Inworld AI, Convai, Character.AI all use tiering. Background NPCs get cheap models; story NPCs get expensive models. 70% of interactions are trivial → 60-80% cost reduction.

**VW Implementation:**
```javascript
// In prompt-builder or agent-engine:
function selectModel(npc, interactionType) {
    if (npc.role === 'story_critical') return 'gpt-4o';
    if (interactionType === 'greeting' && npc.has_cached_greeting) return 'cached';
    if (interactionType === 'direction') return 'cached';
    return 'gpt-4o-mini';
}
```

### 2. Prompt Caching (50-90% Cost Reduction)
**Approach:** Cache the system prompt prefix (which is largely static) and reuse it.

**Evidence:** OpenAI and Anthropic both support prompt caching. Production reports show 50-90% cost reduction for repeated system prompts.

**VW Implementation:**
- System prompt is ~300 tokens, rarely changes
- Cache the system prompt on first call
- Only send dynamic context (memories, room state, conversation history) per turn

### 3. Response Caching (Near-Zero Cost for Common Interactions)
**Approach:** Pre-generate or cache responses for common interactions.

**Cacheable interactions:**
- Greetings ("Hello, traveler!")
- Directions ("The tavern is to the north.")
- Repeated questions ("What do you know about the dragon?")

**Evidence:** Character.AI caches common responses. Reduces cost by 30-40% for new conversations.

**VW Implementation:**
```javascript
const responseCache = new LRUCache({
    max: 1000,
    ttl: 5 * 60 * 1000, // 5 minutes
});

function getCachedResponse(npc, playerInput) {
    const key = `${npc.name}:${hash(playerInput)}`;
    return responseCache.get(key);
}
```

### 4. Speculative Pre-generation
**Approach:** Generate likely NPC responses during idle time.

**Evidence:** Used in production game NPC systems. When player approaches NPC, response is often already generated.

**VW Implementation:**
- During tick processing, generate "thoughts" for idle NPCs
- Store in cache with TTL
- When player interacts, serve from cache if match

### 5. Token Budgeting
**Approach:** Cap total tokens per NPC per session.

**Strategy:**
```javascript
const DAILY_TOKEN_BUDGET = 50000; // per NPC
const TURN_TOKEN_LIMIT = 1000;

function canAffordTurn(npc, estimatedTokens) {
    const spent = npc.token_usage_today || 0;
    return spent + estimatedTokens < DAILY_TOKEN_BUDGET;
}
```

## Recommended VW Cost Architecture

### Phase 1: Quick Wins (1-2 days)
1. **Model tiering** — add `npc.role` field, route to appropriate model
2. **Response caching** — cache common greetings/directions
3. **Token counting** — track tokens per NPC per session

**Expected savings: 40-60%**

### Phase 2: Prompt Caching (3-5 days)
1. **System prompt caching** — cache static prompt prefix
2. **Context optimization** — reduce context window by 20-30% through better memory selection

**Expected savings: Additional 20-30%**

### Phase 3: Advanced (1-2 weeks)
1. **Speculative generation** — pre-generate during idle time
2. **Dynamic model routing** — adjust model based on conversation complexity
3. **Batch processing** — generate NPC thoughts in batches during low-traffic periods

**Expected savings: Additional 10-20%**

## Cost Comparison

| Configuration | Cost per Player-Hour | Monthly (100 players) |
|---------------|---------------------|----------------------|
| Current (no optimization) | $2.05 | $98,400 |
| + Model tiering | $1.23 | $58,800 |
| + Response caching | $0.95 | $45,600 |
| + Prompt caching | $0.61 | $29,200 |
| + All optimizations | $0.41 | $19,700 |

## Key Insight
**The goal is not "make NPCs cheaper" — it's "spend the same money on better NPCs."** By cutting background NPC costs by 80%, you can afford to use better models for story-critical characters without increasing total spend.
