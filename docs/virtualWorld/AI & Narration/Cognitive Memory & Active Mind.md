# Cognitive Memory, Active Mind, and Architectural Principles

**Status:** Master Architectural Specification  
**Last Updated:** 2026-11-11  
**Related Docs:** `[[Memory System]]`, `[[Memory Dynamics]]`, `[[Agent Engine]]`, `[[Gameplay/The Commons]]`  
**Related Tasks:** `task-944`, `task-943`, `task-789`, `task-689`  

---

## 1. Executive Summary: The Core Philosophy

VirtualWorld characters are conscious simulation agents living inside an authoritative physical graph. They are not database transaction clients and they are not text loggers. 

Their mental reality is strictly partitioned into two operational layers:

1. **`=== WITNESSED ===` (Objective Sensory Ledger):**
   - Built in `room-context.ts:748-870`.
   - Represents physical light and sound waves hitting sensory organs in the current room over the last 1 to 5 ticks.
   - Formatted using human relative time (`[just now]`, `[2m ago]`), never raw ticks (`[Tick 2]`).
   - Ground truth of what physically occurred in the character's presence.

2. **`=== I REMEMBER ===` (Subjective Cognitive Memory):**
   - Sourced from `Player.memories[]` and retrieved via multi-facet associative scoring (`memory-context.ts` and `engine/memory_retrieval.py`).
   - Represents internal personal appraisals, emotional reactions, working beliefs, prejudices, and stored knowledge.
   - Stripped of all engine debugging artifacts (`[Match: 100%]`, `[Score: N]`).
   - Strictly de-duplicated against the character's current surroundings and immediate witnessed events.

---

## 2. The 6 Pillars of Cognitive Memory Lifecycle

```
                     ┌────────────────────────┐
                     │ 3. MEMORY CREATION     │
                     │  Appraisals, trauma,   │
                     │  questions, bias       │
                     └───────────┬────────────┘
                                 │
                                 ▼
┌────────────────────────┐   ┌────────────┐   ┌────────────────────────┐
│ 1. PASSIVE RETRIEVAL   │◄──┤  5. MEMORY ├──►│ 2. ACTIVE RETRIEVAL    │
│  Involuntary cues:     │   │   NETWORK  │   │  Deliberate 'recall'   │
│  vitals, audio, senses │   │   (Graph)  │   │  mental action / focus │
└───────────┬────────────┘   └──────┬─────┘   └───────────┬────────────┘
            │                       │                     │
            └───────────┐           │           ┌─────────┘
                        ▼           ▼           ▼
                     ┌────────────────────────┐
                     │  WORKING MIND PROMPT   │
                     │  Clean subjective view │
                     └───────────┬────────────┘
                                 │
           ┌─────────────────────┴─────────────────────┐
           ▼                                           ▼
┌────────────────────────┐                  ┌────────────────────────┐
│ 4. MEMORY EDITOR       │                  │ 6. CONSOLIDATION       │
│  Player/Author deepens │                  │  Sleep/rest synthesis, │
│  or backdates memories │                  │  resolves & supersedes │
└────────────────────────┘                  └────────────────────────┘
```

1. **Passive Retrieval (Involuntary):** Senses, screams, smells, somatic drives (full bladder, pain), and heard speech spark associative memories into working consciousness without turn cost or conscious intent.
2. **Active Retrieval (Conscious):** The character takes a deliberate mental action (`action: "recall"`) to search their episodic archives for specific clues or facts.
3. **Memory Creation (Subjective Appraisal):** Storing personal takeaways, emotional resonance, prejudice, trauma, and questions, rather than flat objective telemetry.
4. **Memory Editor (Authoring & Deepening):** The human authoring surface (`Memory Weaver` / Mind UI) allowing the user to view, edit, backdate, seed, and deepen a character's interiority.
5. **Memory Network (Associative & Causal Graph):** How memories connect via causal links (`caused_by`), contradictions (`conflicts_with`), social edges (`about:jake`), and emotional tags (`trauma:fire`).
6. **Memory Consolidation (Synthesis over Time):** Periodic offline passes (downtime, sleep, soak dreaming) that merge fragmented turns into durable beliefs and supersede obsolete records.

---

## 3. Retrospective: Inferences vs. True System Understanding

Below is the unabridged comparison between previous agent inferences and the true system architecture established on 2026-11-11:

| Area | Before (Flawed Inferences) | After (True Architecture) |
|---|---|---|
| **What Memory Actually Is** | Treated memory like a RAG search database: auto-logging sterile facts (`"Observed foyer: chandelier, rug..."`) and pulling them back into the prompt. | **Subjective appraisal only.** Memory is what the character *felt, thought, or believed*. Objective reality belongs exclusively to `=== WITNESSED ===`. Recalling a list of furniture in the room you are currently staring at is an absurd echo. |
| **Soak & Memory Lifespan** | Panicked about memory bloat in soak runs; suggested pruning, truncating, or deleting older records when consolidating. | **Lifetime store, zero deletion (`player.py:1235`).** A human brain doesn't `rm -rf` files. An 80-year-old keeps all 15,000 memories. Memory is governed by **activation decay, recency half-life, and multi-facet retrieval**. Dormant memories sleep on disk; only the salient top 3-5 enter working consciousness. |
| **Obligations & Working State** | Worried obligations in `active_mind` would become permanent zombies because LLMs forget to output cleanup JSON. | **Obligations are Quests (40 years of game design).** VirtualWorld never delegates system resolution to an LLM. An obligation is an engine contract with a deterministic graph condition (`co_present`, `in_area`). The engine checks and resolves it on tick; the LLM just experiences it. |
| **Dreams & Nightmares** | Feared soak dreaming would poison the sim, making characters wake up and attack their friends over nightmares. | **Emotional residue with epistemic clarity.** Humans have terrifying dreams (e.g. violence against someone they love) and wake up shaken, yet fully knowing *it was only a dream*. `source: dream` + `confidence: 0.2` + high emotional intensity gives character trauma and depth without breaking waking reality. |
| **Invalidation & Desync** | Saw memory invalidation as a negative error-suppression patch to stop action rejection loops. | **Invalidation drives the detective loop.** When Kayla finds the key missing from her pocket, the invalidated memory records absence and actively spawns inquiry: *"Wait, what? Where did it go?!"* Contradiction is the engine of reasoning. |
| **Prompt Presentation** | Let `[Tick 2]` and `[Match: 100%]` sit in prompt logs as normal engine plumbing. | **Immersion-first framing.** A character is a living person, not a database client inspecting a search index. Prompts must use human relative time (`[just now]`, `[2m ago]`) and epistemic tags (`[Observation]`, `[Hunch]`, `[Nightmare]`), never raw ticks or match percentages. |

### Principle 1: Lifetime Archive vs. The Truncation Fallacy
- **What Was Inferred:** Worried about soak memory bloat and proposed deleting, pruning, or truncating older memories to save RAM.
- **The True Reality:** In VirtualWorld, `Player.memories[]` is a **lifetime store** (`player.py:1235: No cap, no eviction, no truncation`). An 80-year-old human has a lifetime of memories; they do not delete files with `rm -rf`. Memory bloat is controlled by **activation decay, recency half-life, reinforcement on recall, and contradiction linking** (`engine/memory_dynamics.py`). Dormant memories sleep on disk; only the top salient few enter working memory. Never delete history.

### Principle 2: Obligations are Quests (Deterministic Engine Contracts)
- **What Was Inferred:** Worried that obligations in `active_mind` would become permanent zombies because the LLM would forget to emit JSON to resolve them.
- **The True Reality:** Obligations are **Missions / Quests**, an established game mechanic for 40 years. VirtualWorld's cardinal rule is: *never delegate system resolution to the LLM*. An obligation is a contract with a deterministic graph condition (e.g. `co_present: "player_jake"`, `in_area: "area_school"`). The engine evaluates conditions on tick. When met, the engine marks it fulfilled. The LLM only roleplays the subjective awareness; it never does bookkeeping.

### Principle 3: Dreams: Emotional Residue vs. Epistemic Clarity
- **What Was Inferred:** Worried that soak dreaming would poison character memory, causing agents to wake up and attack companions over nightmares.
- **The True Reality:** Humans regularly wake from terrifying dreams (e.g. dreaming of violence against a loved one) feeling intense emotional shock and trauma, yet knowing *it was only a dream*. The schema models this split: `source: "dream"`, `confidence: 0.2`, `emotion: {label: "horror", intensity: 8}`. The prompt explicitly labels it as a dream. The emotional residue deepens character psychology without confusing factual reality.

### Principle 4: Invalidation Sparks Inquiry (The Detective Loop)
- **What Was Inferred:** Worried that memory/world desyncs (e.g. remembering a key in your pocket when it was stolen) would cause infinite action failure loops.
- **The True Reality:** Invalidation does not just silence a memory. When an action fails against physical reality, the engine marks the old memory `invalid_at: current_tick` and records an absence observation (`Confirmed absent: key in pocket`). This contradiction naturally triggers character reasoning: *"Wait, what? Where did it go?!"*, spawning an active question in `active_mind.questions`. Contradiction drives deductive reasoning.

### Principle 5: Somatic Drives & Sensory Audio Triggers
- **What Was Inferred:** Assumed `NEED_TAG_MAP` and memory retrieval were wired correctly to character vitals.
- **The True Reality:** `Bladder` was declared as a drive in `vitals.py`, but `memory-context.ts` checked only Hunger, Thirst, and Energy. Environmental audio (`sound_source` like door locks and gunshots) was filtered out 100%. Dialogue history was sliced to 2 lines and threw away self-speech. Associative recall was effectively deaf and somatically blind.

### Principle 6: Eliminating the Triple-Echo Duplication
- **What Was Inferred:** Accepted the prompt logs showing `Observed foyer: chandelier, rug...` in recalled memories.
- **The True Reality:** A character standing in a foyer does not "remember" the chandelier and rug while actively looking at them. Spatial retrieval matching the current room produced a redundant echo of `=== YOUR SURROUNDINGS ===` that crowded out real memories. Standing in room X must suppress static observation memories of room X.

### Principle 7: Stripping Debug Leaks from Character Consciousness
- **What Was Inferred:** Allowed `[Match: 100%]` and `[Tick 2]` to sit in prompts.
- **The True Reality:** These are internal engine debug tokens leaking into character monologue. Prompts must strictly use human relative time (`[just now]`, `[2m ago]`) and subjective framing, never database match percentages.

---

## 4. Complete Data Schemas

### 4.1 Subjective Memory Schema (`Player.memories[]`)

```typescript
export interface SubjectiveMemory {
    /** Unique memory ID (8-char hex) */
    id: string;

    /** World tick when the memory was formed */
    tick: number;

    /** Wall-clock Unix timestamp (seconds) */
    timestamp: number;

    /**
     * Subjective appraisal text: What the character internalized,
     * felt, or concluded (NEVER sterile camera telemetry).
     * Example: "Jake darted into the bathroom and jammed the lock shut. He refused to look me in the eye."
     */
    text: string;

    /** Cognitive category for retrieval routing */
    category: 'episodic' | 'belief' | 'social' | 'procedural' | 'obligation' | 'question';

    /** Concrete memory type */
    type: 'observation' | 'dialogue' | 'action' | 'reflection' | 'thought' | 'trauma';

    /** Epistemic source: observation (0.9), told (0.6), inferred (0.7), dream (0.2), authored (1.0) */
    source: 'observation' | 'told' | 'inferred' | 'dream' | 'authored' | 'auto';

    /** Emotional state and intensity when formed */
    emotion?: {
        label: string;       // e.g. "suspicion", "terror", "relief"
        intensity: number;   // 1 to 10
    };

    /** Epistemic confidence (0.0 = doubtful hunch, 1.0 = certain fact) */
    confidence: number;

    /** Base salience weight (1 to 10) */
    importance: number;

    /** Associative lookup tags (e.g. ["need:bathroom", "rel:jake", "threat:danger"]) */
    tags: string[];

    /** Entity IDs involved (e.g. ["player_jake", "area_bathroom", "item_key"]) */
    entity_ids: string[];

    /** Area where this occurred (for spatial recall) */
    location: string;

    /**
     * Temporal invalidation: tick at which this belief was disproven.
     * Checks `if memory.invalid_at <= current_tick: return False` on retrieval.
     */
    invalid_at?: number;

    /** ID of the memory that superseded this one */
    superseded_by?: string;

    /** Dynamic activation metrics (managed by engine/memory_dynamics.py) */
    dynamics?: {
        activation: number;          // Decays toward 0.0 unless reinforced
        last_recalled_tick: number;
        reinforcements: number;
        emotional_spike: number;
    };
}
```

### 4.2 Active Working Mind Schema (`Player.active_mind`)

```typescript
export interface ActiveMindState {
    /** Open questions the character is actively wondering about */
    questions: Array<{
        id: string;
        question: string;
        hypothesis?: string;
        urgency: number; // 1 to 10
        created_tick: number;
        resolved_tick?: number;
    }>;

    /** Working assumptions / subjective beliefs */
    assumptions: Array<{
        id: string;
        belief: string;
        target_entity?: string;
        confidence: number; // 0.0 to 1.0
        based_on_memory_ids: string[];
    }>;

    /**
     * Quests / Obligations: Deterministic engine contracts.
     * Evaluated on tick by engine condition trees (never LLM bookkeeping).
     */
    obligations: Array<{
        id: string;
        commitment: string;
        owed_to?: string; // character name or "self"
        status: 'active' | 'fulfilled' | 'violated';
        condition: {
            type: 'co_present' | 'in_area' | 'has_item' | 'action_taken';
            target: string;
            extra?: Record<string, unknown>;
        };
        failure_condition?: {
            type: 'not_in_area' | 'timeout' | 'hostile_action';
            target?: string;
            tick_limit?: number;
        };
        due_tick?: number;
    }>;
}
```

---

## 5. Somatic Drive & Auditory Mapping Reference

### 5.1 Somatic Drive Table (`NEED_TAG_MAP`)
In `engine/memory_retrieval.py`:

| Drive / Vital | Threshold | Emitted Cue Tag | Vocabulary Matches |
|---|---|---|---|
| `vitals.Bladder` | `> 50` | `need:bathroom` | `bathroom, toilet, restroom, pee, urinate, piss, lavatory, stall, wc, bladder, locked` |
| `vitals.Hygiene` | `< 30` | `need:hygiene` | `wash, bath, shower, soap, clean, hygiene, dirty, filthy, groom` |
| `vitals.Hunger` | `> 50` | `need:food` | `food, snack, eat, meal, cook, hunger, hungry, rations, bread, fruit, meat` |
| `vitals.Thirst` | `> 50` | `need:drink` | `drink, water, beverage, thirst, thirsty, fountain, stream, bottle, cup` |
| `vitals.Energy` | `< 30` | `need:rest` | `rest, sleep, bed, fatigue, tired, exhausted, bench, cot, bunk` |
| `vitals.HP` | `< 40` | `need:pain`, `need:safety` | `hurt, pain, wound, heal, bandage, medicine, bleed, injury, hide, safe, flee` |

### 5.2 Auditory Triggers
- Objects with `type === 'sound_source'` in `recent_hearing` are parsed for `sound_pattern`.
- Tokens (e.g. `latch`, `click`, `bang`, `scream`, `shout`, `glass`) feed directly into sensory associative cues.
- Dialogue echo covers the last 5 lines and retains self-speech commitments.

---

## 6. The Deterministic Test Fixtures

Testing cognitive memory does not evaluate stochastic LLM prose. It tests the **deterministic scaffolding**:

1. **Fixture 1 (Somatic Bladder Association):**
   - Given: `vitals.Bladder = 75` and past memory `M_bath: "Jake locked the bathroom."`
   - Assert: `need:bathroom` is emitted, `M_bath` is ranked top, current room items are suppressed, output contains `[15m ago]`, output contains 0 occurrences of `[Match:`.
2. **Fixture 2 (Auditory Trauma):**
   - Given: `recent_hearing` receives `sound_pattern: "metallic latch click"`.
   - Assert: Cues contain `"latch"` and `"click"`, locked closet trauma memory surfaces in passive recall.
3. **Fixture 3 (Causal Invalidation & Inquiry):**
   - Given: Memory `M1: "Jake in bathroom"` has `invalid_at = null`.
   - When: Event `Jake entered hallway` resolves.
   - Assert: `M1.invalid_at` equals event tick, future queries suppress `M1`, and absence observation spawns question `"Where did Jake go?"`.
4. **Fixture 4 (Deterministic Quest Obligation):**
   - Given: Obligation `Wait for Jake in foyer` with condition `co_present: "player_jake"`.
   - When: `player_jake` moves into `area_foyer`.
   - Assert: Engine evaluates condition -> marks obligation `fulfilled`. Prompt shows completion.

---

## 7. Note Inventory & Codebase Coverage

Coverage audit of every concept from your note against the current codebase (`engine/`, `routes/`, `static/js/`), documentation (`docs/`), and tasks (`dev_tasks/`).

| Your Term | Mentioned Before? | Current Code? | Documentation? | How It Is Used for an Agent (1 Paragraph) |
|---|---|---|---|---|
| `observations` | Yes (`Memory System.md`, `memory-redesign-3.md`, 30 tasks) | Yes (`engine/observation.py`, `static/js/agent/prompt-builder/context-sections.ts`, `room-context.ts`) | Yes (`Memory System.md`, `Cognitive Memory & Active Mind.md`) | Built every turn from what the character can currently see and hear in their area (`=== WITNESSED ===`) plus stored `observation`-type entries in `Player.memories[]`; grounds immediate perception and prevents the agent from acting on unseen or stale state. |
| `seedmemory` | Yes (`Memory Weaver.md`, `Memory Dynamics.md`, `history/` diagrams) | Partial (authored via `Player.memories[]` / `Memory Weaver` and `character-import.ts`, no separate `seed_memories` store) | Yes (`Memory Weaver.md`, `Memory Dynamics.md`) | Pre-scenario backstory beats (like Chub backstory entries) explaining what happened before turn 1; can be authored as an `observation` (who/what/where/when), story `event` (narrative beat), or `thought`/`memory` (inner monologue or reconsolidated takeaway). |
| `who did what, what items, where, when` | Yes (`lived_log`, `lived-log-format.md`, 36 tasks) | Yes (`engine/character_record.py`, `engine/background_simulation.py`, `engine/background_social.py`, `room-context.ts`) | Yes (`docs/design/lived-log-format.md`, `Cognitive Memory & Active Mind.md`) | Recorded objectively in `lived_log` / witnessed turn events with actor, verb, item/target, area, and tick timestamp; feeds the `=== WITNESSED ===` sensory ledger and gives memory retrieval exact episodic source anchors without relying on fuzzy prose. |
| `system results` | Yes (`system_messages`, `bug-517`, `agent-engine.ts`) | Yes (`routes/action_handlers.py`, `static/js/agent-engine.ts`, `static/js/main.ts` via `system_messages` / `actionResult`) | Partial (`bug-517`, `Agent Engine.md`) | Authoritative engine outcomes (success, failure, blocked movement, vital changes) returned from action resolution and injected back into the agent's turn context and event stream so the narrator and next turn know what physically happened rather than hallucinating success. |
| `facts` | Yes (`Cognitive Memory & Active Mind.md`, `Memory Dynamics.md`, `memory-redesign-3.md`) | Partial (`engine/memory_dynamics.py`, `engine/character_appearance.py`, `alreadyKnown` / `known` flags; Factual Lane not yet unified) | Yes (`Cognitive Memory & Active Mind.md`, `Memory Dynamics.md`) | Objective world-state truths (carried items, spatial layout, door locks, verified `known:` entries) kept separate from subjective memories so the agent and `PlanGrounding` validate physical actions against truth rather than flawed recollection. |
| `questions` | Yes (`sammy_mind_map.html`, `Memory Dynamics.md`, `Cognitive Memory & Active Mind.md`) | Partial (`static/js/agent-lens.ts`, inquiry/curiosity fields planned in `task-944` / Active Mind) | Yes (`Cognitive Memory & Active Mind.md`, `Memory Dynamics.md`) | Open unresolved uncertainties in the agent's Active Mind (`Open Questions`) spawned by contradictions, missing people, or unexplained events; steer the agent toward investigation, asking others, or searching rather than ignoring gaps. |
| `arguments` | Yes (`MOSIAC Character Profiles.md`, `Background Simulation.md`, 33 tasks) | Partial (social conflict/speech in `static/js/commons/commons-agent.ts`, `engine/background_social.py`) | Yes (`MOSIAC Character Profiles.md`, `Background Simulation.md`) | High-arousal interpersonal disagreements carried through recent speech, relationship deltas, and emotional state; shift trust/fear/affection and bias subsequent memory recall and conversational tone toward defensiveness or confrontation. |
| `missunderstandings` | Yes (Millwood gun-disarming example, 2026-11-15) | Partial (`contradicts[]` and `category: "belief"` exist; instant appraisal vs later correction flow not yet wired) | Partial (Section 8 below) | Emerge when an incomplete `observation` (e.g., seeing Jake holding a gun) produces a wrong `belief` ("Jake is about to shoot Tyler"); when later evidence reveals he disarmed Tyler, the new memory links via `contradicts[]` and updates the active belief while preserving the original mistaken memory as past perception. |
| `trauma` | Yes (`Persona.md`, `Memory Weaver.md`, `Cognitive Memory & Active Mind.md`, 22 tasks) | Yes (`engine/character_appearance.py`, `static/js/inspector/persona-view.ts`) | Yes (`Cognitive Memory & Active Mind.md`, `Memory Weaver.md`) | Deep formative wound stored in the character's persona and high-salience memories; acts as an involuntary associative trigger when sensory cues (sounds, places, people) match, spiking fear/distress and overriding casual plans. |
| `personaty` (personality) | Yes (`Emotion & Mood - Whole-System Analysis.md`, `character-inner-life-threads.md`, 162 tasks) | Yes (`engine/character_appearance.py`, `static/js/inspector/persona-view.ts`, `static/js/agent-lens.ts`, `Player`) | Yes (`Persona.md`, `Agent Engine.md`) | Core authored traits and temperament read from the character node into the Actor prompt and MOSIAC weights; shapes how the agent interprets neutral events, speaks in character, and prioritizes competing impulses. |
| `body` (vitals / anatomy / appearance) | Yes (`character-entity-refactor-plan.md`, `Cognitive Memory & Active Mind.md`, 290 tasks) | Yes (`routes/action_handlers.py`, `static/js/agent-engine.ts`, `engine/memory_retrieval.py` `NEED_TAG_MAP`, `engine/character_appearance.py`) | Yes (`Cognitive Memory & Active Mind.md`, `Persona.md`) | Live physical state (Hunger, Thirst, Energy, Bladder, Hygiene, HP, appearance/outfit); emits somatic drive cues (`need:food`, `need:bathroom`, `need:safety`) into passive memory retrieval and constrains what actions the agent can physically perform or endure. |
| `bias` | Yes (`Cognitive Memory & Active Mind.md`, `sammy_mind_map.html`, 18 tasks) | Partial (`engine/memory_retrieval.py`, `engine/background_social.py`, `engine/checks.py`) | Yes (`Cognitive Memory & Active Mind.md`) | Mood-congruent and relationship-skewed filtering during recall and appraisal; causes anxious, angry, or infatuated agents to surface matching memories and interpret ambiguous behavior through their current emotional lens. |
| `possessins` (possessions) | Yes (`Commands.md`, `character-entity-refactor-plan.md`, 14 tasks) | Yes (`static/js/agent-engine.ts`, `engine/inventory` / containment edges) | Yes (`Commands.md`, `Items Overview.md`) | Items currently carried or owned by the agent via graph containment/ownership; exposed in the Factual Lane and tool context so the agent knows what tools, keys, or consumables it actually holds before planning `use`, `give`, or `drop`. |
| `recall` | Yes (`agent-navigation-knowledge-authoring.md`, `decision_flow.html`, 90 tasks) | Yes (`engine/memory_retrieval.py`, `routes/action_handlers.py`, `static/js/agent-lens.ts`) | Yes (`Memory System.md`, `Cognitive Memory & Active Mind.md`) | Both passive involuntary surfacing from sensory/somatic cues and active deliberate retrieval (`recall` action) over `Player.memories[]`; supplies `=== I REMEMBER ===` context for the current turn and reinforces recalled traces. |
| `reminders` | Yes (`Character Pursuits.md`, 14 tasks) | Partial (no dedicated reminder queue; obligations/pursuits cover part of it) | Yes (`Character Pursuits.md`) | Prospective-memory nudges tied to a time, place, or entity trigger (e.g. remembering to check on something later); surfaces into the agent's active mind when the matching cue or tick arrives. |
| `goals` | Yes (`MOSIAC.md`, `Character Pursuits.md`, 229 tasks) | Yes (`engine/background_simulation.py`, `routes/action_handlers.py`, `routes/memories.py`, `engine/mosiac_selector.py`) | Yes (`MOSIAC.md`, `Character Pursuits.md`) | Explicit desired outcomes in GIMP; guide multi-turn planning, feed MOSIAC `M+I` scoring so goal-advancing actions rank higher, and anchor why an agent stays in or leaves a scene. |
| `obligations` | Yes (`MOSIAC Character Profiles.md`, `Cognitive Memory & Active Mind.md`, 28 tasks) | Yes (`routes/action_handlers.py`, `routes/player_ops.py`, `static/js/llm-bench.ts`) | Yes (`MOSIAC Character Profiles.md`, `Cognitive Memory & Active Mind.md`) | Commitments, promises, or deterministic quest duties with verifiable completion/failure conditions; compete with personal wants in decision-making and trigger social consequences or guilt when neglected. |
| `intentins` (intentions) | Yes (`MOSIAC Character Profiles.md`, `Character Pursuits.md`, 10 tasks) | Yes (`engine/mosiac_selector.py`, `static/js/llm-bench.ts`) | Yes (`MOSIAC Character Profiles.md`, `Character Pursuits.md`) | Near-term committed course of action chosen from competing motivations and obligations; keeps the agent coherent across turns instead of flip-flopping randomly on every prompt. |
| `notivatoins` (motivations) | Yes (`MOSIAC.md`, `Life Experience.md`, 12 tasks) | Yes (`static/js/inspector/agent-view.ts`, `static/js/inspector.ts`, `engine/mosiac_selector.py`) | Yes (`MOSIAC.md`, `Life Experience.md`) | Underlying reasons and drives behind an agent's goals; included in character prompts and MOSIAC ranking so two characters with the same goal act differently based on why they want it. |
| `ebtitye xtraction, connectins` (entity extraction & connections) | Yes (`Cognitive Memory & Active Mind.md`, `Agent Engine.md`, 38 tasks) | Yes (`static/js/agent-engine.ts`, `routes/graph_ops.py`, `engine/memory_retrieval.py` `entity_ids`) | Yes (`Memory System.md`, `Cognitive Memory & Active Mind.md`) | Linking people, items, and places (`entity_ids`) on every memory and event; lets retrieval traverse multi-hop associations (person -> item -> place) when any linked entity appears in the current room. |
| `choises` (choices) | Yes (`MOSIAC Character Profiles.md`, `Character Pursuits.md`, 69 tasks) | Yes (`static/js/agent-engine.ts`, `routes/action_handlers.py`, `engine/mosiac_selector.py`) | Yes (`MOSIAC Character Profiles.md`, `Character Pursuits.md`) | The bounded set of valid grounded actions/verbs available to the agent in the current situation; prevents hallucinated verbs and lets MOSIAC/Actor select among real affordances. |
| `wonder` | Yes (`Cognitive Memory & Active Mind.md`, `Interiority & Subtext.md`, 2 tasks) | No (only `worldpainter` / `world_compile` hits; no agent `wonder` state) | Yes (`Cognitive Memory & Active Mind.md`, `Interiority & Subtext.md`) | Unstructured curiosity or speculative musing in the agent's inner life when something feels off or intriguing without yet becoming a formal goal; fuels natural dialogue, hesitation, and exploration. |
| `schedules` | Yes (`Activities & States.md`, `Character Pursuits.md`, 147 tasks) | Yes (`engine/action_tiers.py`, `routes/action_handlers.py`, `engine/activities.py`) | Yes (`Activities & States.md`, `Character Pursuits.md`) | Time-of-day routines and expected locations/activities for NPCs; gives background and attended agents baseline daily structure unless interrupted by higher-priority events or needs. |
| `plans` | Yes (`Agent Engine.md`, `Character Pursuits.md`, 91 tasks) | Yes (`engine/background_plans.py`, `engine/background_simulation.py`, `static/js/agent-engine.ts`) | Yes (`Agent Engine.md`, `Character Pursuits.md`) | Short-term typed multi-step sequences (`act`, `target`, `area`, `until`) validated against world facts (`PlanGrounding`); lets an agent execute coherent multi-step behavior and replan when a precondition breaks. |
| `threatdetection` | Yes (`Animals.md`, `Background Simulation.md`, 63 tasks) | Yes (`static/js/agent-engine.ts`, `routes/action_handlers.py`, `engine/fear.py`) | Yes (`Background Simulation.md`, `Animals.md`) | Appraisal of nearby hazards, hostile actors, weapons, or fear sources; elevates urgency, overrides routine pursuits, and biases recall and action selection toward flight, defense, or caution. |
| `interests` | Yes (`Character Pursuits.md`, `MOSIAC Character Profiles.md`, 40 tasks) | Yes (`routes/action_handlers.py`, `static/js/character-import.ts`, `engine/character_appearance.py`) | Yes (`Persona.md`, `Character Pursuits.md`) | Topics, hobbies, and domains a character cares about; increase engagement and curiosity during conversation or idle exploration when matching items, people, or subjects appear. |
| `fears` | Yes (`MOSIAC Character Profiles.md`, `sammy_mind_map.html`, 44 tasks) | Yes (`static/js/character-import.ts`, `engine/background_social.py`, `engine/fear.py`) | Yes (`MOSIAC Character Profiles.md`) | Specific phobias, anxieties, and dread triggers; amplify threat detection, suppress risky choices, and surface protective or avoidance memories when triggered. |
| `kinks` | Yes (`Persona.md`, `10-sammy-cognitive-flow-v2.html`, 21 tasks) | Yes (`engine/character_appearance.py`, `static/js/character-import.ts`, `static/js/inspector/persona-view.ts`) | Yes (`Persona.md`) | Character-specific attraction and intimacy preferences stored in the persona sheet; inform private reactions, arousal/attraction dynamics, and consensual boundary behavior in adult-tagged contexts. |
| `tunoffs` (turn-offs) | Yes (`Persona.md`, `persona-import-and-round-trip.md`, `roadmap.md`) | Yes (`engine/character_appearance.py`, `static/js/inspector/persona-view.ts`) | Yes (`Persona.md`, `persona-import-and-round-trip.md`) | Explicit aversions and dealbreakers in the persona schema; dampen attraction, trigger disgust or withdrawal reactions, and block incompatible romantic/social choices. |
| `dissintrests` (disinterests / dislikes) | Yes (2026-11-15) | No | Partial (Section 8 below) | Neutral apathy or low-arousal dislike (e.g. hating/ignoring politics without fearing it); suppresses curiosity/follow-up questions and accelerates memory fading so unimportant topics decay faster than `interests` or `fears`. |
| `knowledge` | Yes (`agent-navigation-knowledge-authoring.md`, `Agent Engine.md`, 169 tasks) | Yes (`engine/agent_memory.py`, `engine/area_description.py`, `static/js/character-import.ts`, `crafting_known` / `known`) | Yes (`agent-navigation-knowledge-authoring.md`, `Agent Engine.md`) | Domain expertise, learned facts, recipes, and spatial familiarity (`known:` / `AlreadyKnown`); gates what an agent actually understands, can craft, or can deduce without leaking omniscient world state. |
| `lingo` | Yes (2026-11-15; 1 vendor JS hit only) | No (not implemented yet) | Partial (Section 8 below) | Domain-specific vocabulary/slang earned from what a character actually does (Sammy's skater lingo, Jake's computer/AI lingo, Zoe's DIY/Etsy lingo, Lulu's rich-people lingo); gates whether an agent naturally uses or misunderstands specialized terms in speech. |
| `events` | Yes (`Cognitive Memory & Active Mind.md`, `audio-and-video-audit.md`, 321 tasks) | Yes (`routes/action_handlers.py`, `static/js/agent-engine.ts`, `static/js/agent-lens.ts`) | Yes (`Cognitive Memory & Active Mind.md`, `Agent Engine.md`) | Discrete witnessed occurrences emitted into the turn stream and `lived_log`; form the raw objective history that characters perceive immediately and later consolidate into subjective episodic memories. |
| `languages` | Yes (`Persona.md`, `person-data-model.md`, 13 tasks) | Yes (`engine/character_appearance.py`, `static/js/inspector/persona-view.ts`) | Yes (`Persona.md`, `person-data-model.md`) | Spoken/understood languages on a character's persona; intended to gate comprehension and produce realistic language barriers (and partial word knowledge) when characters speak different tongues. |
| `music` | Yes (`Persona.md`, `Agent Engine.md`, 22 tasks) | Yes (`engine/character_appearance.py`, `static/js/llm-bench.ts`) | Yes (`Persona.md`, `Agent Engine.md`) | Musical tastes and preferences in the persona profile; serve as cultural hooks for bonding, small talk, nostalgia, and environmental reactions when music plays nearby. |
| `books` | Yes (`Persona.md`, `scenario-tag-baseline.txt`, 31 tasks) | Yes (`engine/character_appearance.py`, `static/js/llm-bench.ts`) | Yes (`Persona.md`) | Reading tastes and favored titles in the persona schema; shape intellectual references, item-inspection reactions around books, and shared-interest dialogue. |
| `fiction` | Yes (`Items Overview.md`, `event-stream-demo.html`, 17 tasks) | Partial (`engine/awareness.py`, `engine/companions.py`, `static/js/agent/turn-feed.ts`) | Yes (`Items Overview.md`) | Preferred fictional genres/media tastes and fictional-context framing; influence cultural banter, imagination, and how characters talk about stories or media items. |
| `movies` | Yes (`Persona.md`, `Inspector-Architecture.md`, 4 tasks) | Yes (`engine/character_appearance.py`, `static/js/llm-bench.ts`) | Yes (`Persona.md`) | Film preferences in the persona sheet; give characters concrete pop-culture references, conversation topics, and taste alignment/clashes with peers. |
| `thoughts` | Yes (`Memory System.md`, `Agent Engine.md`, 24 tasks) | Yes (`static/js/agent-engine.ts`, `static/js/agent/action-interpreter.ts`) | Yes (`Memory System.md`, `Agent Engine.md`) | Private internal monologue produced before/alongside action selection; kept hidden from other characters in the room so the agent can scheme, hesitate, or mask true feelings in public speech. |
| `relations` | Yes (`Emotion & Mood - Whole-System Analysis.md`, `Memory System.md`, 1,270 tasks) | Yes (`static/js/agent-engine.ts`, `routes/action_handlers.py`, `relationship_deltas`) | Yes (`Memory System.md`, `Memory Dynamics.md`) | Dynamic interpersonal attitudes (trust, fear, affection, rivalry) derived from memory deltas and social history; govern greeting tone, compliance, secrecy, and social target selection. |
| `feelings` | Yes (`Memory Dynamics.md`, `sammy_mind_map.html`, 15 tasks) | Yes (`static/js/agent-engine.ts`, `static/js/agent/action-interpreter.ts`) | Yes (`Memory Dynamics.md`, `Emotion & Mood - Whole-System Analysis.md`) | Subjective affective impressions attached to memories, people, or moments (`memory_emotions`); bridge raw emotion intensity with long-term sentiment toward specific entities. |
| `emotions` | Yes (`Emotion & Mood - Whole-System Analysis.md`, `Feature Ledger.md`, 190 tasks) | Yes (`static/js/agent-engine.ts`, `static/js/agent/action-interpreter.js`, `Player.emotion`) | Yes (`Emotion & Mood - Whole-System Analysis.md`) | Live emotional state (label + intensity + mood valence/arousal); drives facial expression/avatar selection, colors memory synthesis and recall bias, and leaks into prose tone. |
| `involuntary` (ticks / behaviours) | Yes (`Memory System.md`, `audio-and-video-audit.md`, 29 tasks) | Yes (`static/js/agent-engine.ts`, `engine/background_simulation.py`, `involuntary.ts`) | Yes (`Memory System.md`, `Cognitive Memory & Active Mind.md`) | Automatic somatic or emotional reflexes (flinching, pacing, fidgeting, blurting, vital-driven urges) fired outside deliberate choice; make characters feel embodied and leak subtext even when trying to act calm. |
| `assosiations` (associations) | Yes (`13-sammy-cognitive-data-flow-v3.html`, 6 tasks) | Partial (implemented implicitly via `entity_ids`, tags, and `NEED_TAG_MAP` in `engine/memory_retrieval.py`, no standalone `associations` module) | Partial (`13-sammy-cognitive-data-flow-v3.html`) | Graph and semantic links connecting sensory cues, concepts, places, and people to past memories; allow a smell, sound, or object to involuntarily pull up related memories from another time or place. |
| `mindpane` (Mind pane) | Yes (`2026-11-01-memory-export-audit.md`, `Agent Inspector` docs) | Yes (`static/js/inspector/agent-view.ts`, `static/js/inspector/memory-view.ts`) | Yes (`Memory Weaver.md`, `2026-11-01-memory-export-audit.md`) | Authoring and inspection dashboard (`Mind`) in the character inspector; lets developers inspect an agent's memories, persona, pursuits, relationships, and cognitive state without digging through raw JSON. |
| `memoryeditor` (Memory Editor / Weaver) | Yes (`Memory Weaver.md`, `Memory System.md`, 34 tasks) | Yes (`static/js/inspector/memory-view.ts`, `routes/memories.py`) | Yes (`Memory Weaver.md`, `memory-weaver-and-editor.md`) | Unified UI for viewing, searching, backdating, tagging, and weaving first-person memories into `Player.memories[]`; ensures authored backstory and runtime memories share one format. |
| `the commons` | Yes (`Cognitive Memory & Active Mind.md`, `client_architecture_and_component_master_plan.md`, 38 tasks) | Yes (`routes/commons.py`, `routes/action_handlers.py`, `engine/awareness.py`, `static/js/commons/`) | Yes (`Cognitive Memory & Active Mind.md`) | Shared multi-agent social arena/runtime where agents observe each other's public actions and speech in real time while keeping their private thoughts, memories, and subtext isolated. |
| `importance` | Yes (`Memory Dynamics.md`, `Memory System.md`, 57 tasks) | Yes (`static/js/agent-engine.ts`, `routes/action_handlers.py`, `engine/memory_retrieval.py`) | Yes (`Memory System.md`, `Memory Dynamics.md`) | Numeric salience weight (`1-10`) on each memory; determines retrieval ranking, resistance to decay, and whether a moment survives sleep pruning into long-term storage. |
| `connctions` (connections) | Yes (`Developer Tooling.md`, `client_architecture_and_component_master_plan.md`, 112 tasks) | Yes (`engine/area_description.py`, `routes/library_ops.py`, `routes/saveload.py`, graph edges + entity links) | Yes (`Graph System.md`, `Memory Dynamics.md`) | Structural links between areas/ways in the spatial graph and entity/causal links between memories; let agents navigate physical paths and traverse related memories. |
| `age` | Yes (`Memory Dynamics.md`, `character-inner-life-threads.md`) | Yes (tick/timestamp age on memories in `engine/memory_retrieval.py`, `engine/memory_dynamics.py`) | Yes (`Memory Dynamics.md`, `Memory System.md`) | Elapsed time since a memory was formed (`tick` / `timestamp`); drives recency weighting in recall, human-readable relative time formatting (`[2m ago]`), and activation decay over time. |
| `conflicts` (contradictions) | Yes (`Memory Dynamics.md`, `Character Pursuits.md`, 117 tasks) | Yes (`static/js/agent-engine.ts`, `engine/memory_dynamics.py` contradiction tracking) | Yes (`Memory Dynamics.md`, `Cognitive Memory & Active Mind.md`) | Explicit contradiction links (`contradicts[]`) between incompatible memories or beliefs; preserve both versions instead of silently overwriting so the agent notices discrepancies and asks questions. |
| `reinforces` | Yes (`Cognitive Memory & Active Mind.md`, `Memory System.md`, 42 tasks) | Yes (`engine/agent_memory.py`, `static/js/api.ts`, `engine/memory_dynamics.py`) | Yes (`Memory Dynamics.md`, `Cognitive Memory & Active Mind.md`) | Rehearsal and re-encounter counters (`reinforcements`) bumped when a memory is recalled or re-observed; boost activation and protect frequently accessed memories from fading. |
| `expecectatns` (expectations) | Yes (`Memory Dynamics.md`, `Character Pursuits.md`, 24 tasks) | Yes (`routes/memories.py`, `static/js/agent/memory-manager.ts`) | Yes (`Memory Dynamics.md`, `Character Pursuits.md`) | Anticipated outcomes or social assumptions formed from past patterns; when world events violate an expectation, surprise spikes and triggers inquiry or belief revision. |
| `forgetfullness` (forgetfulness) | Yes (`Cognitive Memory & Active Mind.md`, `Character Pursuits.md`, 35 tasks) | Yes (`static/js/agent-engine.ts`, `routes/action_handlers.py`, `engine/memory_dynamics.py`) | Yes (`Cognitive Memory & Active Mind.md`, `Memory Dynamics.md`) | Controlled loss of low-importance, unreinforced details over time; prevents prompt bloat and makes agents believably fallible rather than walking databases. |
| `fading` | Yes (`Memory Dynamics.md`, `sammy_mind_map.html`, 5 tasks) | Partial (`routes/action_handlers.py`, activation decay in `engine/memory_dynamics.py`) | Yes (`Memory Dynamics.md`) | Gradual drop in memory `activation` as time passes without rehearsal; lowers recall probability without deleting the underlying trace unless pruned during sleep. |
| `belives` (beliefs) | Yes (`Memory Weaver.md`, `Memory Dynamics.md`, 50 tasks) | Yes (`routes/memories.py`, `routes/player_ops.py`, `static/js/agent/memory-manager.ts`, `category: "belief"`) | Yes (`Memory Dynamics.md`, `Memory Weaver.md`) | Subjective conclusions or persistent convictions (`category: "belief"`) formed from experience and reflection; can be true, biased, or false, and guide decisions until contradicted by stronger evidence. |
| `intermediator` | Yes (`decision_flow.html`, `sammy_mind_map.html`, `task-947`, `task-948`) | No (planned in `task-947` / `task-948`, not yet implemented in `engine/` or `static/js/`) | Yes (`diagrams/`, `task-947`, `task-948`) | Dedicated second LLM call (reconsolidator) between raw recalled traces and the Actor LLM; synthesizes recalled memories, `lived_log`, and mood into a single personal thought fed into the prompt instead of a raw `=== I REMEMBER ===` list. |

---

## 8. Resolved Design Decisions (2026-11-15)

1. **Intermediator = Reconsolidator (2nd LLM Call):** When the Cue-Change Gate fires, a dedicated fast/local LLM call synthesizes recalled traces + `lived_log` + current mood/interests into a single personal thought/recollection fed to the Actor instead of the raw `=== I REMEMBER ===` list.
2. **Three-Way Memory & Seed Taxonomy:**
   - **Observations:** Who, what, where, when, who said what - filtered/weighted by `interests`, `fears`, and `disinterests`.
   - **Events:** Story beats (both pre-scenario seed events like "Kayla's dad had a heart attack and Jake brought food" and live witnessed beats).
   - **Thoughts / Memories:** Either the agent's inner monologue during a turn or a reconsolidated memory produced by the Intermediator.
3. **`lingo` vs `languages` (Anti-Omniscience Gating):**
   - `lingo` models domain-locked slang/jargon from life experience (skater, AI/comp, DIY/Etsy, rich-people).
   - `languages` models spoken languages plus partial wordlists (e.g. Sammy's English + partial Spanish/Danish) and must explicitly instruct the LLM what the character does *not* understand so underlying model multilingualism does not leak.
4. **Misunderstandings via Observation -> Belief -> Contradiction:** Misunderstandings (e.g., seeing Jake hold a gun and assuming he is about to shoot Tyler, before learning he disarmed Tyler) are modeled by storing the initial incomplete observation + subjective `category: "belief"`, then linking the later corrective observation via `contradicts[]` and superseding the active belief without erasing the earlier mistaken perception.
5. **`disinterest` / `dislike` & Faster Fading:** Distinct from `fears` and `turn_offs`. Low/negative interest dampens engagement and accelerates memory `activation` decay so uninteresting topics fade faster.
| `interpretor` (interpreter) | Yes (`Memory System.md`, `sammy_mind_map.html`, 14 tasks) | Yes (`static/js/agent/action-interpreter.ts`, `static/js/agent-engine.ts`) | Yes (`Memory System.md`, `Agent Engine.md`) | Post-Actor parser and grounding validator (`action-interpreter.ts`); extracts structured speech, thoughts, feelings, and intents from the Actor's output and checks actions against world rules before execution. |
