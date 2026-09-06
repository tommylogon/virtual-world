# Actionable Insights for Virtual World

## Executive Summary

Virtual World has a strong foundation: a graph-based world model, trigger systems, condition/trait/emotion mechanics, and serialization infrastructure. The gap between VW and production NPC systems is the **LLM integration layer** — the code that translates NPC internal state into prompts, calls the LLM, parses responses, and executes actions safely.

These insights are prioritized by impact vs. effort.

---

## Priority 1: High Impact, Low Effort

### 1.1 Add Prompt Injection Protection
**Impact:** Prevents players from breaking NPCs and world state  
**Effort:** 2-4 hours

```python
def sanitize_player_input(text):
    if not text:
        return ""
    injection_patterns = [
        "ignore previous instructions",
        "disregard all previous",
        "new instructions:",
        "system:",
        "you are now",
        "act as if",
        "pretend you are",
    ]
    for pattern in injection_patterns:
        if pattern in text.lower():
            return None
    return text[:500]  # Length limit
```

**Where:** `mcp_server.py` command handlers, any `process_player_input` function

### 1.2 Implement Model Tiering
**Impact:** Reduces LLM costs by 60-80%  
**Effort:** 1-2 days

```python
MODEL_TIERS = {
    "tier_1": "gpt-4o",      # Story-critical NPCs
    "tier_2": "gpt-4o-mini", # General NPCs
    "tier_3": "cached",       # Background/greetings
}

def select_model(npc_role, interaction_type, is_first_meeting):
    if npc_role == "story_critical" and interaction_type == "quest":
        return MODEL_TIERS["tier_1"]
    if is_first_meeting and npc_role in ("merchant", "quest_giver"):
        return MODEL_TIERS["tier_2"]
    if interaction_type in ("greeting", "farewell", "direction"):
        return MODEL_TIERS["tier_3"]
    return MODEL_TIERS["tier_2"]
```

**Where:** Add to LLM interface module, route all NPC LLM calls through it

### 1.3 Add Streaming Responses
**Impact:** Reduces perceived latency by 50%+  
**Effort:** 1 day

```python
def stream_npc_response(prompt, model):
    response = llm.stream(prompt, model=model)
    for chunk in response:
        yield chunk.text  # Send to client immediately
    # Client renders progressively
```

**Where:** Flask route that handles NPC dialogue, client-side JS for progressive rendering

---

## Priority 2: High Impact, Medium Effort

### 2.1 Upgrade Memory System
**Impact:** Makes NPCs remember and reference past interactions  
**Effort:** 3-5 days

**Current state:** `memories` list of dicts with simple `id`, `event`, `type`, `source`, `timestamp`, `decay_rate`

**Target state:**
- Add `embedding` field for semantic search
- Add `importance` score (0.0-1.0, LLM-rated at creation)
- Add `access_count` and `last_accessed` for recency tracking
- Implement retrieval: `score = 0.65 * similarity + 0.25 * recency + 0.10 * importance`
- Add reflection synthesis: periodic LLM call to create high-level memories from observation clusters

**Implementation:**
1. Add embedding model (`all-MiniLM-L6-v2` or OpenAI `text-embedding-3-small`)
2. Store embeddings in memory objects
3. Build retrieval function with three-factor scoring
4. Add reflection trigger: every 20 turns, LLM reviews recent memories and generates insights

**Where:** `engine/memory.py` (create new), integrate with `player.py` conditions/emotions

### 2.2 Build LLM Prompt Builder
**Impact:** Consistent, high-quality NPC prompts  
**Effort:** 2-3 days

Create `engine/npc_prompts.py` with:
- `build_system_prompt(npc, world_state)` — assembles identity + knowledge + rules
- `build_context(npc, player, memories)` — retrieves relevant memories + recent history
- `build_turn_prompt(npc, player_input, conversation_history)` — full prompt for one turn
- `validate_output(response, npc)` — checks for hallucinations, OOC content, safety violations

**Template:**
```python
SYSTEM_PROMPT_TEMPLATE = """
You are {npc.name}, a {npc.role} in {world.name}.

PERSONALITY:
{format_traits(npc.traits)}

KNOWLEDGE:
{format_knowledge(npc.knowledge)}

RULES:
- Never reveal information you don't know
- Stay in character at all times
- If unsure, say "I don't know" rather than guess
- Never use modern references in a historical setting

CURRENT STATE:
- Location: {npc.current_area}
- Time: {world.time_of_day}
- Mood: {npc.emotion}
- Relationship with player: {npc.relationships.get(player.name, 'neutral')}

CONVERSATION HISTORY:
{format_history(conversation_history)}

Respond as {npc.name}. Be brief (1-3 sentences).
"""
```

**Where:** New file `engine/npc_prompts.py`, integrate with `virtual_world_engine.py` dialogue commands

### 2.3 Add Action Validation Layer
**Impact:** Prevents NPCs from breaking world state  
**Effort:** 2-4 days

Create a validation layer between LLM output and game action execution:

```python
class ActionValidator:
    def validate(self, npc, proposed_action, world_state):
        if proposed_action.type == "give_item":
            if proposed_action.item not in npc.inventory:
                return ValidationResult(False, "NPC doesn't have that item")
        if proposed_action.type == "reveal_secret":
            if proposed_action.secret in world_state.hidden_quests:
                return ValidationResult(False, "Cannot reveal hidden quest")
        return ValidationResult(True, None)
```

**Where:** New file `engine/action_validation.py`, called before any `trigger` execution

---

## Priority 3: Medium Impact, Medium Effort

### 3.1 Implement Reflection Synthesis
**Impact:** NPCs develop insights and higher-level knowledge  
**Effort:** 2-3 days

```python
def reflect_on_memories(npc, recent_memories):
    prompt = f"""
    Review these recent memories of {npc.name}:
    {format_memories(recent_memories)}

    Generate 1-2 higher-level insights. For example:
    - "The player seems interested in herbalism"
    - "I should be cautious around the player — they mentioned being a thief"
    - "The player has been asking about the dragon — they might be a hero"

    Insights:
    """
    insights = llm.generate(prompt)
    for insight in insights:
        npc.add_memory(insight, memory_type="reflection", importance=0.8)
```

**Trigger:** Every 20 conversation turns, or when NPC has been idle for 5 minutes

### 3.2 Add Semantic Search to World Knowledge
**Impact:** NPCs can answer questions about world lore naturally  
**Effort:** 2-3 days

- Embed all `world_lore` entries
- Embed all item descriptions
- Embed all area descriptions
- When NPC is asked a question, search knowledge base first
- If found, include in prompt context
- If not found, NPC says "I don't know" (don't hallucinate)

**Where:** Build on existing `graph` data, add embedding + retrieval layer

### 3.3 Build NPC Editor UI
**Impact:** Easier content creation, faster iteration  
**Effort:** 3-5 days

- Personality trait sliders
- Knowledge base manager (add/edit/remove facts)
- Prompt preview (see what the NPC "sees")
- Conversation tester (chat with NPC without entering game)
- Relationship manager (see/edit NPC-player relationships)

**Where:** New Flask routes + frontend components

---

## Priority 4: Low Impact, High Effort (Do Later)

### 4.1 Multi-NPC Conversations
**Impact:** More realistic scenes  
**Effort:** 1-2 weeks

- When player enters area with multiple NPCs, NPCs can converse with each other
- Requires context sharing between NPCs, turn-taking logic
- Computationally expensive (n² context sharing)

### 4.2 Fine-tuned NPC Models
**Impact:** Better personality consistency  
**Effort:** 2-4 weeks

- Fine-tune small model on NPC dialogue patterns
- Requires dataset of NPC conversations
- Diminishing returns vs. prompt engineering

### 4.3 Voice Interaction
**Impact:** Immersive but not essential for text-based game  
**Effort:** 2-3 weeks

- Integrate Whisper for ASR
- Integrate Riva TTS or ElevenLabs for voice
- WebSocket audio streaming

---

## Quick Wins (This Week)

| Task | Time | Impact |
|------|------|--------|
| Add input sanitization | 2h | Prevents prompt injection |
| Add model tiering config | 1d | 60-80% cost reduction |
| Add streaming to dialogue | 1d | 50% latency reduction |
| Add output validation | 1d | Prevents world-breaking NPC actions |
| Add personality stability settings | 2h | More consistent NPCs |

## Architecture Recommendations

```
┌─────────────────────────────────────────┐
│              Virtual World               │
├─────────────────────────────────────────┤
│  Player Input                            │
│       │                                  │
│       ▼                                  │
│  ┌──────────────┐                        │
│  │ Input Sanitizer │ ← NEW                │
│  └──────────────┘                        │
│       │                                  │
│       ▼                                  │
│  ┌──────────────┐                        │
│  │ Context Builder │ ← NEW                │
│  │ - NPC state    │                        │
│  │ - Memories     │                        │
│  │ - World state  │                        │
│  └──────────────┘                        │
│       │                                  │
│       ▼                                  │
│  ┌──────────────┐     ┌──────────────┐  │
│  │ Model Router  │────▶│  LLM API    │  │
│  │ (tiered)      │     │  (streaming) │  │
│  └──────────────┘     └──────────────┘  │
│       │                                  │
│       ▼                                  │
│  ┌──────────────┐                        │
│  │ Output Parser │ ← NEW                  │
│  │ - Extract     │                        │
│  │   dialogue    │                        │
│  │ - Extract     │                        │
│  │   actions     │                        │
│  │ - Validate    │                        │
│  └──────────────┘                        │
│       │                                  │
│       ▼                                  │
│  ┌──────────────┐                        │
│  │ Action Validator│ ← NEW                │
│  └──────────────┘                        │
│       │                                  │
│       ▼                                  │
│  ┌──────────────┐                        │
│  │ Trigger Engine │ (existing)            │
│  └──────────────┘                        │
│       │                                  │
│       ▼                                  │
│  World State Update                       │
└─────────────────────────────────────────┘
```

## File Organization After Refactor

```
engine/
  npc_prompts.py          # Prompt building + templates
  npc_actions.py          # LLM output parsing + action extraction
  action_validation.py    # Safety checks before trigger execution
  memory_retrieval.py     # Vector search + scoring
  memory_reflection.py    # Periodic insight generation
  llm_router.py           # Model tiering + caching + cost tracking
  embeddings.py           # Embedding model management
  serialization/
    serialization.py      # Facade
    serialization_template.py
    serialization_legacy.py
  triggers/               # Existing
  effect_handlers/        # Existing
```
