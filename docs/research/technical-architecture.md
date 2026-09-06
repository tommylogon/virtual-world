# Technical Architecture & Scaling — Research

## The Problem
Virtual World's architecture has grown organically. The JS agent engine is powerful but lives entirely in the browser. The Python backend handles world state and triggers. This split creates constraints as the system scales.

## Current Architecture

```
┌─────────────────────────────────────────┐
│              Browser Client              │
│  ┌───────────────────────────────────┐  │
│  │  Agent Engine (JS, 1000+ lines)   │  │
│  │  - Prompt builder (10+ modules)   │  │
│  │  - LLM client (direct API calls)  │  │
│  │  - Memory manager                 │  │
│  │  - Turn queue                     │  │
│  │  - Response parser                │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  UI (HTML/JS)                     │  │
│  │  - Event stream                   │  │
│  │  - Graph editor                   │  │
│  │  - Inspector panels               │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
           │ Direct API calls │
           ▼                  ▼
┌─────────────────────────────────────────┐
│           Flask Backend (Python)         │
│  ┌───────────────────────────────────┐  │
│  │  World State (Graph)              │  │
│  │  - Nodes/edges                    │  │
│  │  - Serialization                  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Engine Systems                   │  │
│  │  - Triggers, effects, conditions  │  │
│  │  - Movement, lighting, equipment  │  │
│  │  - Tick manager                   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Key Constraints

### 1. Browser-Based LLM Calls
**Current:** LLM calls happen directly from the browser using the user's API key.

**Problems:**
- No server-side caching or logging
- API keys exposed in browser (obfuscated but not secure)
- No centralized rate limiting or cost tracking
- Can't run local models for NPCs without user setup
- CORS issues with some providers

### 2. Agent Engine in JS
**Current:** All agent logic (prompt building, turn orchestration, memory management) lives in JS.

**Problems:**
- Hard to test (no Node.js test suite for agent logic)
- Hard to debug (browser console only)
- Hard to scale (each client runs its own agent loop)
- No shared state between clients

### 3. No Vector Database
**Current:** Embeddings stored in JSON files (`data/embeddings.json`) or browser IndexedDB.

**Problems:**
- Slow retrieval at scale (>1000 memories per character)
- No efficient similarity search
- No hybrid search (metadata + vector)
- Memory serialization is expensive

### 4. No Background Jobs
**Current:** Everything is request-driven. LLM calls happen in the browser on player action.

**Problems:**
- NPC reflection only happens during player turns
- No background world simulation
- No scheduled events (daily NPC routines)
- No pre-generation of likely responses

## Scaling Considerations

### Client Count vs. Complexity
| Metric | Current | Target (1 year) | Target (5 years) |
|--------|---------|-----------------|------------------|
| Concurrent players | 1 | 10 | 100 |
| NPCs per world | 10 | 50 | 200 |
| LLM calls per minute | 5 | 50 | 500 |
| Memories per NPC | 100 | 1000 | 10000 |
| World objects | 100 | 1000 | 10000 |

### Bottleneck Analysis

**At 10 concurrent players:**
- 50 NPCs × 2 LLM calls/turn × 1 turn/min = 100 LLM calls/min
- Browser-based: each client makes its own calls → works but wastes API keys
- Server-based: can batch, cache, tier models → 40% cost reduction

**At 100 concurrent players:**
- 200 NPCs × 2 LLM calls/turn × 1 turn/min = 400 LLM calls/min
- Browser-based: 200 clients × 2 calls = 400 calls, but no coordination
- Server-based: central queue, batch processing, model routing → 60% cost reduction

**At 1000 memories per NPC:**
- Browser IndexedDB: ~500ms retrieval time
- Vector DB: ~50ms retrieval time
- 10x improvement matters for turn pacing

## Recommended Architecture Evolution

### Phase 1: Backend Agent Services (2-4 weeks)
**Move LLM orchestration to backend.**

**Benefits:**
- Centralized LLM calls (caching, logging, cost tracking)
- Shared NPC state across all players
- Background NPC processing (reflection, planning)
- No API key management in browser

**Implementation:**
```python
# New: engine/agent_services.py
class AgentService:
    def __init__(self, graph, player_manager, llm_client):
        self.graph = graph
        self.player_manager = player_manager
        self.llm = llm_client
    
    def step_npc(self, npc_name, world_state):
        """Run one NPC turn."""
        prompt = self.build_prompt(npc_name, world_state)
        response = self.llm.chat(prompt)
        action = self.parse_response(response)
        return self.execute_action(npc_name, action)
```

### Phase 2: Vector Database (1-2 weeks)
**Replace JSON embeddings with Qdrant or ChromaDB.**

**Benefits:**
- 10x faster memory retrieval
- Hybrid search (vector + metadata filter)
- Scales to millions of memories
- Built-in deduplication

**Implementation:**
```python
# New: engine/vector_memory.py
class VectorMemory:
    def __init__(self, qdrant_client):
        self.client = qdrant_client
        self.collection = "memories"
    
    def store(self, memory):
        self.client.upsert(
            collection_name=self.collection,
            points=[{
                "id": memory.id,
                "vector": memory.embedding,
                "payload": {
                    "text": memory.text,
                    "npc_id": memory.npc_id,
                    "tick": memory.tick,
                    "importance": memory.importance,
                    "tags": memory.tags
                }
            }]
        )
    
    def retrieve(self, npc_id, query, limit=10):
        results = self.client.search(
            collection_name=self.collection,
            query_vector=embed(query),
            query_filter=Filter(must=[FieldCondition(key="npc_id", match=MatchValue(value=npc_id))]),
            limit=limit
        )
        return [r.payload for r in results]
```

### Phase 3: Background Job Queue (2-3 weeks)
**Add Celery or RQ for background tasks.**

**Jobs:**
- NPC reflection (every 5 turns)
- Memory consolidation (every 20 turns)
- Pre-generation of likely responses
- World tick processing (decay, environment)
- Save/load operations

### Phase 4: Real-Time Sync (3-4 weeks)
**Add SocketIO for real-time state updates.**

**Events:**
- `state:delta` — world state changed
- `npc:action` — NPC took an action
- `player:joined` / `player:left`
- `turn:advanced` — turn queue advanced

## What NOT to Do

### Don't Rewrite the Agent Engine
The JS agent engine works. Don't rewrite it in Python just because "Python is better for AI." The browser-based approach has advantages:
- No server infrastructure for single-player
- Direct API calls (no proxy latency)
- User controls their own API keys

**Keep browser agent engine for single-player.** Add backend services for multiplayer/hosted.

### Don't Add a Vector DB Yet
At current scale (<1000 memories per NPC, <10 NPCs), the JSON approach works fine. A vector DB adds operational complexity (another service to run, backup, monitor). Add it when:
- Memory retrieval is visibly slow (>500ms)
- You have >10,000 memories total
- You need hybrid search (metadata + vector)

### Don't Move Everything to Backend
The browser-based architecture is a feature, not a bug. It lets users:
- Play offline (no server needed)
- Use their own API keys (no subscription)
- Debug locally (no network dependency)

Keep the split: browser for single-player, backend for multiplayer/hosted.

## Key Insight
**VW's architecture is appropriate for its current scale.** The browser-based agent engine is fast to iterate on and works well for single-player. The backend Python engine handles world state well. The gaps only appear at scale (>10 players, >50 NPCs, >1000 memories).

Design the scaling path now, but don't implement until you hit the constraints. The worst thing you can do is build infrastructure for a future that never arrives.
