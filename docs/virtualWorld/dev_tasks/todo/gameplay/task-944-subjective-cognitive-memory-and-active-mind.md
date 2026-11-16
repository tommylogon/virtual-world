# task-944: Subjective Cognitive Memory and Active Mind Architecture

**Status:** todo  
**Lane:** gameplay  
**Created:** 2026-11-11  
**Updated:** 2026-11-11  
**Dependencies:** task-943, task-789, task-689  

---

## 1. Context & Motivation

In human cognition, memory is split into two distinct tiers:
1. **Passive Involuntary Recall:** When you smell smoke, feel an urgent bladder, hear a door click, or see a friend's strained face, relevant memories and associations involuntary flood into your working memory without conscious effort.
2. **The Active Working Mind:** Conscious cognitive constructs that persist across turns:
   - **Open Questions:** Things the character is trying to solve ("Where did Jake put the basement key?").
   - **Assumptions & Working Beliefs:** Theories held until disproven ("Jake is hiding something from us").
   - **Obligations & Commitments:** Promises made to oneself or others ("I told Jake I would wait here").
   - **The Active `recall` Action:** A deliberate mental effort to search memory when passive recall did not surface what is needed.
   - **Memory Consolidation:** Distilling raw episodic experiences into long-term personal beliefs.

### The Current Problems in VirtualWorld

1. **Memories are sterile camera logs:** The engine records objective facts (`"Observed foyer: chandelier, rug..."`, `"Player Jake moved north"`). Characters do not store subjective appraisals, emotions, or personal takeaways.
2. **Triple duplication in prompts:** A character in the foyer receives:
   - `=== I REMEMBER ===`: `"Observed foyer: chandelier, rug, coat_rack..."` (100% spatial match)
   - `=== YOUR SURROUNDINGS ===`: `"You see: chandelier, rug, coat_rack..."` (exact duplicate)
   - `=== WITNESSED ===`: `"[Tick 2] Jake: 'Let's check upstairs.'"`
   - `=== CONVERSATION ===`: `"Jake: 'Let's check upstairs.'"` (dialogue echo)
   - `=== I REMEMBER ===`: `"Jake said: 'Let's check upstairs.'"` (recalled dialogue echo)
3. **Leaked debug meta and raw ticks:** Prompts and inspector bubbles display `[Match: 100%]` and `[Tick 2]`, breaking immersion and training LLMs on internal telemetry rather than human relative time.
4. **Muted somatic and auditory triggers:** Bodily drives (`vitals.Bladder`, `vitals.Hygiene`, pain) produce zero retrieval cues. Environmental audio (`type: sound_source` like door locks or gunshots) is completely dropped. Dialogue cues only check 2 lines and erase self-speech.

---

## 2. Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SENSORY REALITY                      │
│   • Visuals (Surroundings)    • Audio (Hearing, Speech, Sounds)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 1. WITNESSED (Working Memory Ledger - room-context.ts)                 │
│    • Objective sensory perception in current room (last 1-5 ticks)     │
│    • Relative timestamps: "[just now]", "[2m ago]" (NEVER raw "[Tick N]")│
│    • Feeds immediate situation to the character                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           │                                                 │
           ▼ Involuntary Trigger                             ▼ Appraisal & Filing
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│ 2. PASSIVE ASSOCIATIVE RECALL        │  │ 3. EPISODIC & SUBJECTIVE MEMORY      │
│    • Somatic Cues: Bladder, Pain,    │  │    • Player.memories[]               │
│      Hunger, Thirst, Fatigue         │  │    • Subjective appraisal & emotion  │
│    • Auditory Cues: Sound patterns,  │  │    • Associated tags & entity IDs    │
│      5 lines of dialogue history     │  │    • Invalidation window (invalid_at)│
│    • Suppresses current room echo    │  └──────────────────┬───────────────────┘
│    • Deduplicates against WITNESSED  │                     │
└──────────────────┬───────────────────┘                     │
                   │                                         │
                   ▼                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. ACTIVE WORKING MIND (Deliberation & Working State)                  │
│    • Open Questions: Unresolved queries ("Where is the key?")          │
│    • Assumptions & Beliefs: Active working models of people and danger │
│    • Obligations: Commitments made to self or companions               │
│    • Active "recall" Action: Deliberate mental query action            │
│    • Consolidation: Sleep/rest synthesis of episodic memories          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 5. PROMPT INJECTION (Clean Subjective Presentation)                    │
│    === I REMEMBER ===                                                  │
│    • [2m ago] 👁️ Jake locked himself in the bathroom. He looked panicked.│
│                                                                        │
│    === ACTIVE MIND ===                                                 │
│    • Question: What is Jake hiding in the bathroom?                    │
│    • Assumption: The front doors are bolted from outside.              │
│    • Obligation: Promised Jake I would not wander off alone.           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Models & Schemas

### 3.1 Subjective Memory Schema

```typescript
export interface SubjectiveMemory {
    /** Unique memory ID (8-char hex) */
    id: string;

    /** World tick when the memory was formed */
    tick: number;

    /** Unix timestamp (seconds) */
    timestamp: number;

    /**
     * Subjective appraisal text: What the character internalized,
     * felt, or concluded (NEVER sterile camera telemetry).
     * Example: "Jake locked himself in the bathroom. He looked terrified."
     */
    text: string;

    /** Memory category for cognitive routing */
    category: 'episodic' | 'belief' | 'social' | 'procedural' | 'obligation' | 'question';

    /** Memory type */
    type: 'observation' | 'dialogue' | 'action' | 'reflection' | 'thought' | 'trauma';

    /** Emotional state and intensity when formed */
    emotion?: {
        label: string;       // e.g. "fear", "suspicion", "relief"
        intensity: number;   // 1 to 10
    };

    /** Epistemic confidence (0.0 = doubtful guess, 1.0 = certain fact) */
    confidence: number;

    /** Subjective significance / retention weight (1 to 10) */
    importance: number;

    /** Associative lookup tags (e.g. ["need:bathroom", "rel:jake", "threat:danger"]) */
    tags: string[];

    /** Entity IDs involved (e.g. ["player_jake", "area_bathroom", "item_key"]) */
    entity_ids: string[];

    /** Area where this occurred (for spatial recall) */
    location: string;

    /**
     * Temporal invalidation: tick at which this memory/belief was proven obsolete.
     * E.g. "Jake is in the bathroom" invalidates when Jake is seen in the hallway.
     */
    invalid_at?: number;

    /** ID of the memory that superseded this one */
    superseded_by?: string;

    /** Dynamic access tracking */
    dynamics?: {
        access_count: number;
        last_recalled_tick: number;
        emotional_spike: number;
    };
}
```

### 3.2 Active Working Mind Schema

```typescript
export interface ActiveMindState {
    /** Open questions the character is actively wondering about */
    questions: Array<{
        id: string;
        question: string;
        hypothesis?: string;
        urgency: number; // 1-10
        created_tick: number;
    }>;

    /** Working assumptions / subjective beliefs */
    assumptions: Array<{
        id: string;
        belief: string;
        target_entity?: string;
        confidence: number; // 0.0-1.0
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

## 4. Concrete Examples

### Example 1: Subjective Memory Formation (React Phase)
Jake runs into the bathroom and slams the lock. Kayla forms an episodic memory:
```json
{
  "id": "m_8f2a1b",
  "tick": 42,
  "timestamp": 1731336000,
  "text": "Jake darted into the bathroom and jammed the lock shut. He wouldn't look me in the eye.",
  "category": "episodic",
  "type": "observation",
  "emotion": {
    "label": "suspicion",
    "intensity": 7
  },
  "confidence": 0.95,
  "importance": 7,
  "tags": ["need:bathroom", "action:lock", "rel:jake", "suspicious", "area:bathroom"],
  "entity_ids": ["player_jake", "area_bathroom", "item_bathroom_door"],
  "location": "foyer"
}
```

### Example 2: Involuntary Passive Recall (Somatic Drive)
At tick 65, Kayla is in the foyer. Her `vitals.Bladder` reaches 75 (drive urgency):
1. Cue generator notes `vitals.Bladder > 50` -> emits `need:bathroom`.
2. Cue matches `tags: ["need:bathroom"]` and `area:bathroom` on `m_8f2a1b`.
3. Associative score: 8.8 (Need + Spatial + Social overlap).
4. Prompt presentation:
```text
=== I REMEMBER ===
• [23m ago] 👁️ Jake darted into the bathroom and jammed the lock shut. He wouldn't look me in the eye.
```
Notice:
- No `[Match: 100%]` debug noise.
- Relative time `[23m ago]` instead of raw `[Tick 42]`.
- Does NOT duplicate the current foyer chandelier or rug.

### Example 3: Active Working Mind State
Kayla's conscious deliberation state in her turn prompt:
```text
=== ACTIVE MIND ===
• Questions:
  - Where did Jake hide the key he found in the parlour? (Hypothesis: Inside his jacket)
• Assumptions:
  - The bathroom is occupied; knocking might set Jake off.
• Obligations:
  - Promised myself I wouldn't leave the foyer until Jake comes out.
```

### Example 4: Active `recall` Action
When passive cues are not enough, a character can spend a minor mental action to deliberately search their memories:
```json
{
  "action": "recall",
  "target": "basement",
  "inner_monologue": "Wait... did someone mention a fuse box down in the basement?",
  "speech": null
}
```
Engine resolution: runs a deep semantic + keyword query on `Player.memories[]`, returning the top matches into the immediate next reaction prompt.

### Example 5: Deterministic Quest Obligation with Graph Evaluation
Jake promises to meet Lyrie in the library. This creates an engine obligation:
```json
{
  "id": "ob_7a1c9e",
  "commitment": "Wait for Lyrie in the library",
  "owed_to": "Lyrie",
  "status": "active",
  "condition": {
    "type": "co_present",
    "target": "player_lyrie",
    "extra": {
      "area": "area_library"
    }
  },
  "failure_condition": {
    "type": "not_in_area",
    "target": "area_library",
    "tick_limit": 50
  },
  "due_tick": 120
}
```
Engine evaluation on tick:
1. `engine/tick_manager.py` loops over active character obligations.
2. Evaluates `condition_tree.evaluate("co_present", actor="player_jake", target="player_lyrie", area="area_library")`.
3. If `player_lyrie` enters `area_library`: obligation status transitions to `"fulfilled"`.
4. Turn prompt updates immediately:
```text
=== ACTIVE MIND ===
• Obligations:
  - [COMPLETED] Wait for Lyrie in the library (Lyrie has arrived).
```
Zero LLM bookkeeping. The engine condition graph decides when an obligation is resolved.

### Example 6: Causal Invalidation Spawning an Active Inquiry
Kayla remembers putting the brass key in her trenchcoat pocket:
```json
{
  "id": "m_key_pocket",
  "tick": 30,
  "text": "I slipped the brass key into my left trenchcoat pocket.",
  "category": "episodic",
  "type": "action",
  "tags": ["item:brass_key", "action:pocket", "security"],
  "entity_ids": ["item_brass_key", "player_kayla"],
  "location": "foyer",
  "confidence": 1.0,
  "invalid_at": null
}
```
At tick 72, Kayla takes an action to check her pocket (`action: examine, target: pocket`), but the brass key is missing:
1. Engine action fails or returns empty pocket.
2. Physical reality takes precedence: `m_key_pocket.invalid_at` is set to 72, with `superseded_by: "m_key_missing_72"`.
3. Contradiction engine automatically spawns an open question in `active_mind.questions`:
```json
{
  "id": "q_brass_key_missing",
  "question": "Where did the brass key go?",
  "hypothesis": "Did it fall out when I ran, or did someone pick my pocket?",
  "urgency": 8,
  "created_tick": 72
}
```
4. Subsequent passive retrievals suppress `m_key_pocket` from popping up as a current truth; prompt now focuses the character on solving the mystery.

---

## 5. Implementation Plan

### Phase 1: Clean Up Prompt Presentation & Deduplication
- **Task 1.1:** In `static/js/agent/prompt-builder/room-context.ts`, replace `[Tick N]` with relative time (`[just now]`, `[1m ago]`, `[5m ago]`) using `events.tickToRelative`.
- **Task 1.2:** In `static/js/stream/stream-raw-llm.ts` and `memory-context.ts`, remove `[Match: N%]` and `[Score: N]` from prompts.
- **Task 1.3:** In `memory-context.ts`, suppress observation memories of the character's *current* room (`area_id === currentAreaId` with `type === 'observation'`).
- **Task 1.4:** Deduplicate recent speech lines so an utterance in `=== WITNESSED ===` does not echo into `=== I REMEMBER ===`.

### Phase 2: Somatic Drives & Sensory Audio Associations
- **Task 2.1:** In `engine/memory_retrieval.py`, expand `NEED_TAG_MAP` to include:
  - `need:bathroom` (`bathroom`, `toilet`, `restroom`, `pee`, `urinate`, `piss`, `lavatory`, `stall`, `wc`, `bladder`, `locked`)
  - `need:hygiene` (`wash`, `bath`, `shower`, `soap`, `clean`, `hygiene`, `dirty`, `filthy`, `groom`)
  - `need:safety` (`hide`, `cover`, `run`, `flee`, `threat`, `danger`, `safe`, `escape`, `locked`, `hiding`, `trauma`)
  - `need:pain` (`hurt`, `pain`, `wound`, `heal`, `bandage`, `medicine`, `bleed`, `injury`)
- **Task 2.2:** In `memory-context.ts`, wire vitals to cues:
  - `vitals.Bladder > 50` -> `need:bathroom`
  - `vitals.Hygiene < 30` -> `need:hygiene`
  - `vitals.HP < 40` -> `need:safety`, `need:pain`
- **Task 2.3:** In `memory-context.ts`, include `type === 'sound_source'` by extracting `h.sound_pattern` into auditory cue tokens.
- **Task 2.4:** Expand dialogue cues to the last 5 lines and retain recent self-speech.

### Phase 3: Active Mind Constructs & `recall` Action
- **Task 3.1:** Add `active_mind` property to `Player` model (`questions`, `assumptions`, `obligations`).
- **Task 3.2:** Register `recall` verb in `action-definitions.ts` and `contextual-actions.ts` as a mental minor action.
- **Task 3.3:** Inject `=== ACTIVE MIND ===` into turn prompts (`turn-prompts.ts`).
- **Task 3.4:** Add causal invalidation (`invalid_at`) when world observations contradict working assumptions.

### Phase 4: Soak Dreaming & The Commons Social Memory Formation
- **Task 4.1:** Implement sleep/downtime consolidation pass: samples 1-3 high-arousal memories to produce a dream record (`source: "dream"`, `confidence: 0.3`) and condenses fragmented observations into durable beliefs (`superseded_by`).
- **Task 4.2:** Integrate The Commons communication: reading posts/threads generates subjective impressions (`tags: ["commons", "rel:..."]`) rather than dumping raw transcripts into memory.

---

## 6. Acceptance Criteria

1. **Relative Time in Perception:** `=== WITNESSED ===` lines display relative temporal markers (`[just now]`, `[2m ago]`), never raw `[Tick N]`.
2. **Clean Memory Presentation:** `=== I REMEMBER ===` contains no engine debug tags (`[Match: 100%]`).
3. **Zero Static Room Echo:** Standing in room X never recalls the static observation memory of room X.
4. **Somatic Involuntary Recall:** When `vitals.Bladder > 50`, memories tagged with `need:bathroom` (such as someone entering the bathroom) rank in the top recalled memories.
5. **Sensory Sound Triggers:** Hearing a sound pattern (e.g. gunshot or door lock) retrieves associated episodic memories.
6. **Active Mind Injected:** Turn prompts render `=== ACTIVE MIND ===` with active questions, assumptions, and obligations.
7. **Dreaming & Soak Consolidation:** Sleep cycle recombines episodic fragments and produces summary beliefs without blowing up memory count.
8. **Passing Unit Tests:** Comprehensive tests in `tests/test_memory_retrieval_associations.py` and `tools/unit/test_memory_association.js` pass with zero failures.
9. **Clean Build:** `npm run build:ts` passes cleanly.
10. **Zero Em-Dashes:** No em-dash characters (code u2014) in any modified file. Plain hyphens only.

### 6.1 Deterministic Verification Fixtures

Testing cognitive memory does not evaluate stochastic LLM prose. It tests the deterministic scaffolding:

1. **Fixture 1 (Somatic Bladder Association):**
   - **Given:** `vitals.Bladder = 75` and past memory `M_bath: "Jake locked the bathroom."` tagged `["need:bathroom"]`.
   - **When:** Passive retrieval runs in `area_foyer`.
   - **Assert:** Cue generator emits `need:bathroom`, `M_bath` ranks #1, current foyer room items are suppressed from recall, relative time shows `[23m ago]`, and output contains 0 occurrences of `[Match:`.

2. **Fixture 2 (Auditory Trauma):**
   - **Given:** `recent_hearing` receives `sound_source` with `sound_pattern: "metallic latch click"`.
   - **When:** Passive retrieval runs.
   - **Assert:** Audio parser extracts tokens `"latch"` and `"click"`, locked closet trauma memory surfaces in passive recall.

3. **Fixture 3 (Causal Invalidation & Inquiry):**
   - **Given:** Memory `M_key: "Brass key in trenchcoat pocket"` with `invalid_at: null`.
   - **When:** Character checks pocket and finds no key.
   - **Assert:** `M_key.invalid_at` is set to current tick, future passive queries suppress `M_key`, and an active question `"Where did the brass key go?"` is inserted into `active_mind.questions`.

4. **Fixture 4 (Deterministic Quest Obligation):**
   - **Given:** Obligation `Wait for Lyrie in library` with condition `co_present: "player_lyrie"`, `target: "area_library"`.
   - **When:** Engine tick runs while `player_lyrie` is in `area_library`.
   - **Assert:** Engine evaluates graph condition -> marks obligation `status: "fulfilled"`. Prompt shows completion.

5. **Fixture 5 (Room Echo Suppression):**
   - **Given:** Character is in `area_kitchen`. Memory bank contains `M_kitchen: "Observed kitchen: stove, counter, sink"`.
   - **When:** Turn prompt generates `=== I REMEMBER ===` and `=== YOUR SURROUNDINGS ===`.
   - **Assert:** `M_kitchen` is completely suppressed from `=== I REMEMBER ===`. Stove and sink appear only once, in `=== YOUR SURROUNDINGS ===`.
