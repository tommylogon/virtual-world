# Research Plan — Virtual World Specific (Updated from Log Analysis)

## What the Logs Revealed

Analyzed `data/log exports/` — real production sessions showing:
- Multiple LLM providers in active use (qwen3.6-35b-a3b, deepseek-v4-flash, dots-studio, LM Studio, OpenRouter)
- 1.4k-3.6k tokens per LLM call, 2 calls per reactive turn
- Production errors: "LLM retry 1/3 after 500...", "Step cancelled"
- Duplicate memories stored in prompts
- Very long prompts (~1500-2500 tokens of system/context before the actual conversation)

## Revised Research Priorities (Based on Real Data)

### P0: Immediate Production Issues

#### 1. Duplicate Memory Bug
**Evidence:** Log shows identical memory stored twice:
```
[5 minutes ago] 💭 Tried to check my reflection...
[5 minutes ago] 💭 Tried to check my reflection...
```
**Impact:** Wastes context window, LLM sees same memory twice
**Research needed:** Where does deduplication fail? Is it storage or retrieval?

#### 2. Prompt Length Optimization
**Evidence:** Prompts are 1500-2500 tokens before conversation even starts:
- Personality: 200-400 tokens
- Appearance: 200-500 tokens  
- World lore: 100-200 tokens
- Action rules: 300-500 tokens
- State: 100-200 tokens
- Memories: 200-400 tokens
- Room context: 300-500 tokens

**Impact:** At 2 calls/turn × 2000 tokens = 4000 tokens per turn. At $0.15/1M input = $0.0006 per turn. For 5 NPCs + 1 player at 10 turns/min = $0.036/min = $2.16/hour per session.

**Research needed:** Which prompt sections can be compressed, cached, or removed without quality loss?

#### 3. LLM Retry/Error Handling
**Evidence:** "LLM retry 1/3 after 500...", "Step cancelled"
**Impact:** NPC turns fail silently, player sees nothing happen
**Research needed:** What's failing? Network? Rate limits? Model errors? What's the recovery strategy?

### P1: Cost Management (Now Measurable)

#### 4. Token Budgeting & Tracking
**Evidence:** No cost tracking in logs. Multiple models with different prices.
**Impact:** Unknown spend, can't optimize
**Research needed:** How much is each scenario costing? Which NPCs are expensive? Where to cut?

#### 5. Model Tiering (Already Happening, Needs Coordination)
**Evidence:** mansion uses deepseek-v4-flash, taco_bell uses qwen3.6-35b-a3b, Jessica uses dots-studio
**Impact:** Uncoordinated — could be cheaper or better with intentional routing
**Research needed:** Which models work best for which NPC types? What's the quality/cost tradeoff?

### P2: Quality & Consistency

#### 6. NPC Quality Evaluation
**Evidence:** No quality metrics in logs. Can't tell if NPCs are "good" without manual play.
**Impact:** Prompt changes ship without knowing if they helped or hurt
**Research needed:** How to measure NPC believability automatically?

#### 7. Memory Architecture
**Evidence:** Memories work but are verbose. No semantic search. Duplicate entries.
**Impact:** Context window wasted on irrelevant or repeated memories
**Research needed:** Three-factor recall, consolidation, deduplication

### P3: Feature Gaps

#### 8. NPC-to-NPC Interaction
**Evidence:** NPCs take turns but don't reference each other
**Impact:** World feels like isolated characters, not a living society
**Research needed:** Observation injection, social memory

#### 9. Content Generation
**Evidence:** Scenarios are hand-authored JSON. No AI assistance in building worlds.
**Impact:** Slow scenario creation, inconsistent quality
**Research needed:** AI-assisted item/area/NPC generation

## What VW Already Does Well (From Logs)

1. **Structured output works** — JSON parsing is reliable across multiple models
2. **Memory system functions** — memories are stored, recalled, and used in prompts
3. **Relationship system visible** — "jake halloway - a close friend" shows inline
4. **Multi-model support** — works with OpenAI, DeepSeek, Qwen, OpenRouter, local models
5. **Turn structure sound** — think→act→react pipeline is implemented correctly
6. **Error handling exists** — retries, fallbacks, step cancellation all work

## Research Format

For each P0/P1 issue, produce:
1. **Root cause analysis** — where in the code does the problem originate?
2. **State of the art** — how do other systems handle this?
3. **Recommendation** — specific fix for VW
4. **Implementation notes** — how to build/test it
