# Research Findings — Deep Dive (Updated 2026-09-06)

## What ViWo Already Has (from actual log analysis)

- Turn-based architecture with per-turn context window cap (no endless growth)
- Reactive think→act→react pipeline with structured JSON output
- Memory system with embeddings, reflection, spatial recall
- Graph-based world model with triggers/effects/conditions
- Multi-model support (qwen, deepseek, openrouter, LM Studio)
- Event stream with parse-error inspection
- Manual mode for debugging

## Key Findings from Industry & Research

### 1. Voyager (MineDojo, NVIDIA/Caltech, TMLR 2024)

**What it is:** LLM-powered Minecraft agent that learns by writing JavaScript functions and storing them in a skill library. Never forgets what it learned.

**Three components:**
1. **Automatic curriculum** — curiosity-driven task proposer, bottom-up exploration
2. **Skill library** — skills as executable code (JS), retrievable by embedding similarity
3. **Iterative prompting** — execute → observe errors → refine → commit to library

**Results:** 3.3× more unique items, 8.5× faster stone tools, 6.4× faster iron tools, 2.3× longer map traversal vs baselines.

**What ViWo can adapt:**
- **Skill libraries for NPC behaviors** — store successful NPC action sequences as reusable code, not just prompts
- **Error-driven refinement** — when an NPC's plan fails, feed execution feedback back to LLM for correction
- **Skill composition** — combine primitive skills (take_item, examine_area, speak_to) into complex behaviors
- **Embedding-based retrieval** — retrieve relevant skills by semantic similarity to current situation

**Implementation idea:**
```python
class NPCSkill:
    name: str
    description: str  # natural language, used for retrieval
    code: str  # executable Python/JS
    version: int
    tags: list[str]
    dependencies: list[str]  # other skills this depends on

class SkillLibrary:
    def register(self, skill: NPCSkill)
    def search(self, query: str, top_k=5) -> list[NPCSkill]  # embedding similarity
    def compose(self, skills: list[NPCSkill]) -> NPCSkill  # combine into new skill
    def refine(self, skill: NPCSkill, feedback: str) -> NPCSkill  # version bump
```

**Relevance to ViWo:** ViWo's trigger system already stores effect chains. A skill library would let NPCs *learn and reuse* successful strategies across sessions, rather than re-planning from scratch each turn.

---

### 2. HeRoN (Cimino et al., Springer Neural Computing 2026)

**What it is:** Mediated RL-LLM framework for adaptive NPC behavior. Three components:
- **NPC** — RL-driven agent (learned behavior)
- **Helper** — LLM in zero-shot mode (generates diverse strategies)
- **Reviewer** — fine-tuned LLM (critiques and refines Helper's suggestions)

**Key insight:** Functional separation + critique-based mediation. LLM doesn't directly control NPC — it *advises* the RL agent, which is then evaluated by a Reviewer.

**Results:** HeRoN outperforms both pure RL and pure LLM baselines in strategy refinement, learning efficiency, and adaptability.

**What ViWo can adapt:**
- **LLM-as-advisor, not controller** — LLM suggests strategies, ViWo's trigger system executes them
- **Reviewer/critic layer** — validate LLM output against game constraints before execution
- **Early LLM guidance improves exploration** — even brief LLM mediation during training helps RL agents generalize

**Relevance to ViWo:** ViWo's agent engine already has think→act→react. Adding a Reviewer layer (validate LLM output against world state, trigger conditions, and game rules) would catch hallucinations and out-of-character outputs before they affect the world.

---

### 3. Event-Driven Behavior Trees for NPC Coordination (Agis et al., Expert Systems with Applications 2020)

**What it is:** Extension to behavior trees with three new coordination nodes for multi-agent coordination in video games.

**Three new node types:**
1. **Request nodes** — NPCs request actions from other NPCs (soft or hard requests)
2. **Response nodes** — NPCs respond to incoming requests
3. **Event nodes** — trigger coordination based on world events

**Key findings:**
- Event-driven BTs enable coordination without hard-coding
- Emotional behavior trees (EBT) add emotion-based decision weights
- Coordination nodes maintain BT's intuitive, scalable nature

**What ViWo can adapt:**
- **Coordination nodes in ViWo's trigger system** — NPCs can request/respond to each other via events
- **Emotion-influenced decision weights** — current emotions affect which triggers fire
- **Event-driven coordination** — when NPC A does something, nearby NPCs can react without consuming their turn

**Relevance to ViWo:** ViWo's trigger system is already event-driven (on_take, on_use, on_tick). Adding coordination nodes would let NPCs interact with each other's triggers — e.g., when NPC A opens a door, NPCs nearby can react.

---

### 4. LLM-Coordination Benchmark (Agashe et al., NAACL 2025)

**What it is:** Benchmark evaluating LLMs' ability to coordinate in multi-agent settings.

**Key findings:**
- LLMs excel when decisions rely on environmental variables
- LLMs struggle with **Theory of Mind** (considering partners' beliefs/intentions)
- **Joint planning** is a significant weakness
- Zero-shot coordination is robust to unseen partners (unlike RL)

**What ViWo can adapt:**
- **Explicit ToM in NPC prompts** — "Consider what the other NPCs know about this situation"
- **Joint planning prompts** — "Coordinate with nearby NPCs to achieve shared goal"
- **Environment-first reasoning** — LLMs are better at reacting to world state than planning social dynamics

**Relevance to ViWo:** ViWo's NPCs already have awareness of nearby NPCs. Adding explicit ToM prompts ("What do you think [NPC name] knows about this?") could improve multi-NPC coordination.

---

### 5. V-JEPA 2 (Meta, 2025)

**What it is:** Self-supervised video world model trained on >1M hours of internet video. Achieves zero-shot robot control in new environments.

**Key concept:** World model = g(history, action) → future latent. Policy = h(world model, goal) → action.

**What ViWo can adapt:**
- **World model for NPC planning** — NPCs simulate future states before acting
- **Neural simulation** — NPCs "imagine" what would happen if they took action X
- **Prediction-based planning** — evaluate multiple plans by simulating their outcomes

**Relevance to ViWo:** ViWo's graph-based world model is essentially a symbolic world model. Adding a predictive layer (simulate future graph states given actions) would enable NPCs to plan ahead rather than react.

---

### 6. LLM-Driven NPCs Cross-Platform (Li Song, arXiv 2025)

**What it is:** Prototype connecting LLM NPCs to both Unity game and Discord bot. Shared database across platforms.

**Key features:**
- Cloud database stores all interactions (character, user, content, timestamp, favorability, platform)
- Favorability mechanism shapes NPC responses based on interaction history
- Cross-platform continuity — NPC remembers player from Discord when they enter the game

**What ViWo can adapt:**
- **Cross-platform memory** — share NPC memories across ViWo's web interface and any future Discord/Twitter bot
- **Favorability/reputation tracking** — explicit metric for NPC-player relationship quality
- **Platform-agnostic storage** — store all interactions in a unified format

**Relevance to ViWo:** ViWo already has a memory system. Adding platform-agnostic storage would enable future cross-platform NPC continuity.

---

### 7. CPDC 2025 Challenge (Winning Solution)

**What it is:** Competition evaluating LLM NPCs on tool calls and dialogue. Winning approach combined context engineering + GRPO training.

**Evaluation dimensions (LLM-as-judge):**
1. Scenario adherence & quest progression
2. NPC believability & engagement
3. Persona consistency
4. Dialogue flow & coherence

**Key techniques:**
- **Context engineering** — structured prompt with character settings, knowledge, worldview
- **GRPO training** — reinforcement learning from LLM-as-judge reward signals
- **Function calls for knowledge** — NPCs retrieve world knowledge via function calls, not hardcoded text

**What ViWo can adapt:**
- **LLM-as-judge evaluation** — automatically evaluate NPC responses on the four dimensions
- **Context engineering** — structured prompt with character settings, knowledge, worldview (ViWo already does this)
- **Function calls for knowledge retrieval** — NPCs query the graph/world via structured calls instead of having all knowledge in the prompt

**Relevance to ViWo:** ViWo's prompt builder already structures context. Adding automated evaluation on the four dimensions would enable continuous quality improvement.

---

### 8. Socio-Cognitive NPC Interaction Ladder (SCNIL, Thesis 2024-2025)

**What it is:** Framework for designing increasingly complex LLM-based NPC interactions. Ten levels from basic text to complex multi-modal.

**Theoretical foundations:**
- Theory of Mind (understanding others' mental states)
- Anthropomorphism (attributing human qualities to NPCs)
- Distributed Cognition (cognition spread across agent, environment, tools)
- Joint Attention (shared focus between player and NPC)

**What ViWo can adapt:**
- **Level 1-3 (basic text)** — ViWo is already here
- **Level 4-6 (context-aware)** — add explicit ToM prompts, shared attention tracking
- **Level 7-10 (multi-modal)** — future: voice, gestures, spatial awareness

**Relevance to ViWo:** ViWo's current system is roughly SCNIL levels 1-3. The ladder provides a roadmap for incremental improvement.

---

### 9. LLM-Guided RL for Multi-Agent Combat (arXiv 2026)

**What it is:** Runtime LLM strategy selection for RL-trained NPCs in combat.

**Key findings:**
- Runtime LLM (Mistral 7B) reading game state every 5 seconds
- 83.8% preference for "Surround" strategy (limited differentiation)
- Hybrid RL+LLH hierarchy: LLM as slow planner, RL as fast executor

**What ViWo can adapt:**
- **Runtime LLM guidance** — LLM reads world state and suggests strategy, RL/trigger system executes
- **Strategy differentiation** — LLM should consider opponent state, not just default to one strategy
- **Hierarchical planning** — LLM plans at high level (turns), triggers execute at low level (actions)

**Relevance to ViWo:** ViWo's turn-based system is already hierarchical. Adding runtime LLM strategy selection (e.g., "focus on healing" vs "focus on offense") would improve NPC adaptability.

---

## Actionable Recommendations for ViWo

### Immediate (1-2 weeks)

1. **Add LLM-as-judge evaluation** — automatically evaluate NPC responses on four dimensions (scenario adherence, believability, persona consistency, dialogue flow)
2. **Add Reviewer layer** — validate LLM output against game constraints before execution
3. **Fix duplicate memory bug** — same memory stored twice in prompts

### Short-term (2-4 weeks)

4. **Implement skill library for NPC behaviors** — store successful NPC strategies as reusable code
5. **Add coordination nodes to trigger system** — NPCs can request/respond to each other
6. **Add explicit ToM prompts** — "Consider what other NPCs know about this situation"

### Medium-term (1-2 months)

7. **Add world model prediction layer** — NPCs simulate future states before acting
8. **Implement cross-platform memory storage** — unified format for Discord/Twitter integration
9. **Add runtime LLM strategy selection** — LLM suggests high-level strategy, triggers execute

### Long-term (3-6 months)

10. **Implement GRPO training for NPCs** — train NPCs to improve based on LLM-as-judge feedback
11. **Add multi-modal NPC interaction** — voice, gestures, spatial awareness
12. **Implement full SCNIL levels 4-10** — progressively add socio-cognitive depth

---

## Sources

- Voyager: Wang et al., TMLR 2024, arXiv:2305.16291
- HeRoN: Cimino et al., Neural Computing & Applications 2026, DOI:10.1007/s00521-026-12275-w
- Event-Driven BTs: Agis et al., Expert Systems with Applications 2020, DOI:10.1016/j.eswa.2020.113457
- LLM-Coordination: Agashe et al., NAACL 2025 Findings, DOI:10.18653/v1/2025.findings-naacl.448
- V-JEPA 2: Meta FAIR, 2025, arXiv:2506.09985
- Cross-Platform NPCs: Li Song, arXiv 2025, arXiv:2504.13928
- CPDC 2025: arXiv 2025, arXiv:2511.20200
- SCNIL: Kroes B, Thesis 2024-2025, theses.liacs.nl
- LLM-Guided RL: Nair & Karim, arXiv 2026, arXiv:2609.02931
