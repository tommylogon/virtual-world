# Infrastructure — Web Dev, Vector DBs, LLM Serving

## Real-Time Multiplayer

### WebSocket Architecture
**Pattern:** Single WebSocket per game session, JSON message protocol
```
Client → Server: {"type": "player_action", "action": "go", "direction": "north"}
Server → All: {"type": "state_update", "player": "Alice", "new_area": "Forest"}
Server → All: {"type": "npc_action", "npc": "Guard", "action": "patrol"}
```

**State synchronization:**
- Server is authoritative — clients only send intents
- Server broadcasts state diffs, not full state (bandwidth)
- Optimistic updates for player's own actions, confirmed by server

**VW implementation:** Already uses Flask + SocketIO. Consider:
- Room-based rooms (SocketIO rooms per area) for targeted broadcasts
- Delta compression for large state updates
- Connection pooling for high player counts

## Vector Databases

### Options Comparison
| DB | Best For | Scale | Self-Hosted | Latency |
|----|----------|-------|-------------|---------|
| ChromaDB | Development, single-NPC memory | <1M vectors | Yes | <50ms |
| Qdrant | Production, multi-NPC | <100M vectors | Yes | <20ms |
| Pinecone | Managed, zero-ops | >100M vectors | No | <50ms |
| Weaviate | Hybrid search (vector + filter) | <10M vectors | Yes | <30ms |
| FAISS | Offline, batch retrieval | Any | Yes | <1ms (batch) |

### Recommended for VW
**Start with ChromaDB or Qdrant** (self-hosted, no external dependency):
- NPC episodic memory (conversations, observations)
- World knowledge (item descriptions, area lore, quest info)
- Semantic search over `world_lore` and `game_log`

**Schema design:**
```
NPC Memory Collection:
  - embedding: vector (384d or 1536d)
  - text: "Player asked about the healer, NPC recommended forest clearing"
  - metadata: {npc_id, player_id, timestamp, importance, memory_type}
  - id: auto-generated

World Knowledge Collection:
  - embedding: vector
  - text: "The ancient dragon Last Drake was last seen in the northern peaks"
  - metadata: {source: "lore_book_3", category: "creatures"}
  - id: "lore_001"
```

### Embedding Strategy
- **Model:** `all-MiniLM-L6-v2` (fast, 384d, good quality) or `text-embedding-3-small` (OpenAI, 1536d)
- **Chunking:** Recursive chunking for long texts (lore, quest descriptions)
- **Metadata filtering:** Always include `npc_id`, `player_id`, `timestamp` for targeted retrieval

## LLM Serving

### Options
| Method | Best For | Latency | Cost | Control |
|--------|----------|---------|------|---------|
| OpenAI API | Quick start, high quality | 500ms-2s | $$ | Low |
| Anthropic API | Long context, safety | 1-3s | $$ | Low |
| vLLM / TGI | Self-hosted, high throughput | 100-500ms | $ (GPU) | High |
| Ollama | Local dev, testing | 50-500ms | Free | High |
| LiteLLM proxy | Multi-model routing | Varies | Varies | Medium |

### Recommended Stack for VW
1. **Development:** Ollama (local Llama 3 8B or Mistral) — zero cost, fast iteration
2. **Production:** LiteLLM proxy → OpenAI/Anthropic for critical NPCs, self-hosted for background
3. **Fallback:** Cached responses for common queries, template responses for simple NPCs

### Cost Optimization
- **Prompt caching:** OpenAI and Anthropic support prompt caching — 50-90% cost reduction for repeated system prompts
- **Streaming:** Reduces perceived latency, enables progressive rendering
- **Model routing:** Tiered system (Tier 1: expensive, Tier 2: medium, Tier 3: cheap/cached)
- **Token budgets:** Cap at 500-1000 tokens per NPC interaction

## Frontend Architecture

### Current State
Flask + SocketIO server, HTML/JS client with custom log rendering and graph editor.

### Recommended Enhancements
- **React/Vue for client-side rendering** — better state management for complex UIs
- **Graph editor library** — Cytoscape.js or React Flow for the trigger graph
- **Scenario builder** — drag-and-drop area/item placement with live preview
- **NPC editor** — personality sliders, knowledge base management, prompt preview

### Observability
- **LLM tracing:** Log every prompt/response pair with metadata (NPC, player, timestamp, cost)
- **Prompt versioning:** Track prompt templates in Git, A/B test variations
- **Quality metrics:** LLM-as-judge scores, player feedback, conversation length

## Storage

### Current
- JSON files for world state, scenarios, saves
- In-memory graph for active world

### Recommended Addition
- **PostgreSQL** for persistent NPC memories, player relationships, world state history
- **Redis** for session caching, real-time state, SocketIO pub/sub
- **S3/Blob storage** for scenario templates, world backups

## Deployment

### Current
- Local Flask dev server
- No containerization

### Recommended
- **Docker** for reproducible deployment
- **Docker Compose** for local dev (Flask + Redis + Qdrant + Ollama)
- **Kubernetes** or **Azure Container Apps** for production scaling

### Cost Estimate (per 100 concurrent players)
- LLM API: $200-500/month (assuming 1000 interactions/hour)
- Vector DB: $50-100/month
- Compute: $100-300/month (4 vCPU, 8GB RAM)
- **Total: $350-900/month**
