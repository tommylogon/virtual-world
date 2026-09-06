# Memory Architecture at Scale — Research

## The Problem
Virtual World has a working memory system, but it was designed for single-player, single-NPC use. As the world scales to many NPCs, long play sessions, and complex relationships, the current architecture shows strain.

## Current State
- `Player.memories[]` — flat list of memory objects
- Each memory: `{id, text, type, tick, timestamp, importance, location, entity_ids, embedding, tags, emotion, memory_emotions, salience_override, source}`
- Recall: `POST /api/players/<name>/memories/retrieve` — scores by importance + recency
- Reflection: Every 5 turns, LLM generates 1-2 insights from high-importance memories
- Embeddings: Stored per-memory, generated via API or local model
- Tag system: Auto-registers new tags, dedupes by ID

## Scaling Problems

### 1. Recall Quality Degrades with Volume
**Problem:** When a character has 1000+ memories, the current recall (importance + recency) returns irrelevant memories because:
- Importance is static (set at creation, never updated)
- Recency favors recent over relevant
- No semantic similarity search

**Example:** After 500 turns, a character's "meeting the blacksmith" memory (importance 3, 400 ticks ago) might be recalled instead of "the blacksmith is my uncle" (importance 7, 200 ticks ago) — even though the latter is more relevant to current context.

### 2. Context Window Budget
**Problem:** Each turn injects recalled memories into the LLM prompt. With 30 messages max and 9500 token limit, memories compete with conversation history.

**Current allocation:**
- System prompt: ~300 tokens
- Room context: ~400 tokens
- People/items: ~300 tokens
- Available actions: ~100 tokens
- Memory block: ~500 tokens (5-8 memories)
- Conversation history: ~2000 tokens (6 turns)
- Total: ~3600 tokens → fits in budget

**At 1000+ memories:** If recall returns low-quality memories, the 500-token memory block becomes noise instead of signal.

### 3. No Forgetting Mechanism
**Problem:** Memories never decay or get archived. A character played for 100 hours has the same memory weight for day-1 events as day-100 events.

**Impact:** LLM prompts become cluttered with irrelevant old memories. Character "personality" drifts as early memories dominate context.

### 4. Cross-Character Memory Isolation
**Problem:** Memories are per-character. If two NPCs witness the same event, they each store separate memories. No shared knowledge base.

**Impact:** NPCs contradict each other about shared events. Player notices "didn't you just tell me that?"

## State of the Art

### 1. Three-Factor Retrieval (Park et al., 2023)
**Formula:**
```
score = 0.65 * cosine_similarity(query, memory)
      + 0.25 * recency_decay(timestamp)
      + 0.10 * importance_score
```

**Evidence:** Generative Agents paper showed this outperformed any single-factor retrieval. Removing any factor caused measurable behavior degradation.

**VW Gap:** VW has recency + importance, but no semantic similarity. Adding cosine similarity would require actual vector search, not just embedding storage.

### 2. Memory Consolidation (Cognitive Science + LLM)
**Approach:** Periodically "consolidate" memories — merge similar memories, extract key facts, discard noise.

**Process:**
1. Every 20 turns, cluster recent memories by similarity
2. For each cluster, generate a "consolidated memory" via LLM
3. Demote original memories to archive (lower importance, excluded from recall)
4. Keep consolidated memory as the active representation

**Evidence:** Human memory research shows consolidation is essential for long-term retention. LLM-based consolidation (Park et al.) showed improved coherence over 48+ simulated hours.

**VW Implementation:** Already has reflection (every 5 turns). Extend to full consolidation every 20 turns.

### 3. Episodic vs. Semantic Memory
**Taxonomy:**
- **Episodic:** "The player asked me about the healer on turn 42" (specific event)
- **Semantic:** "The healer lives in the forest clearing" (generalized fact)
- **Procedural:** "When someone asks about healing, recommend the healer" (skill)

**Current VW:** All memories are episodic (specific events with timestamps). No semantic layer.

**Benefit of semantic layer:** NPCs can answer questions from generalized knowledge without recalling the specific conversation where they learned it.

### 4. Memory Importance Re-scoring
**Problem:** Importance is set once at creation and never updated.

**Solution:** Periodically re-score memories based on:
- How often they've been recalled
- Whether they led to important decisions
- Whether they're still relevant to current goals

**VW Implementation:**
```javascript
function recalculateImportance(memory, recallHistory) {
    let score = memory.importance;
    if (recallHistory.timesRecalled > 5) score += 1;
    if (recallHistory.ledToAction) score += 2;
    if (memory.tick < currentTick - 200) score -= 1; // age decay
    return clamp(score, 1, 10);
}
```

### 5. Memory Forgetting Curve
**Approach:** Apply Ebbinghaus forgetting curve to memory importance.

```
forgetting_rate = 0.005 per tick  // tune this
new_importance = old_importance * exp(-forgetting_rate * ticks_since_access)
```

**Variant:** Only forget memories that haven't been accessed recently. Frequently accessed memories stay strong.

## Recommended VW Memory Architecture

### Phase 1: Semantic Recall (1-2 weeks)
1. Add vector search to memory retrieval
2. Implement three-factor scoring (similarity + recency + importance)
3. Tune weights: `0.65 * similarity + 0.25 * recency + 0.10 * importance`

**Expected improvement:** 30-50% better recall relevance

### Phase 2: Memory Consolidation (2-3 weeks)
1. Extend reflection from "generate insights" to "consolidate clusters"
2. Build semantic memory layer from consolidated episodes
3. Add forgetting curve with access-based reinforcement

**Expected improvement:** NPCs feel smarter over time, not just more cluttered

### Phase 3: Cross-Character Memory (3-4 weeks)
1. Shared world knowledge base
2. NPCs can "ask" other NPCs about events they missed
3. Gossip mechanism: NPCs share memories during idle time

**Expected improvement:** NPCs feel like they live in the same world

## Key Insight
**The goal is not "more memories" — it's "better recall."** A character with 50 well-organized, semantically-searchable memories feels smarter than a character with 5000 memories that mostly return noise.
