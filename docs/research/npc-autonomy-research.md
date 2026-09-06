# Research Synthesis: Autonomous NPCs + Scalable World Authoring for ViWo

## Problem Statement

You want NPCs indistinguishable from players — fully autonomous, believing their world is real, with physics/consequences/limitations enforced by the system. The bottlenecks are:

1. **World authoring doesn't scale** — Can't hand-place 10,000 areas, items, connections
2. **NPCs don't learn the world** — No mental maps, routes, schedules, wants at scale
3. **Hybrid architecture needed** — Behaviors + state machines + LLMs working together

---

## What ViWo Already Has (Leverage These)

| System | Capability | Gap |
|--------|-----------|-----|
| Trigger/effect engine | 77 trigger types, 27 effects, condition trees | No schedule/routine format |
| BFS pathfinding | Obstacle-aware navigation | NPCs don't build/query mental maps |
| Behavior evaluation | Priority-ordered condition→action rules | Static priority, no urgency computation |
| Vitals decay | Hunger/thirst/social/sanity drain | NPCs don't USE vitals as behavioral drivers |
| Emotion system | Multi-dimensional affect with decay/spikes | Not connected to decision-making |
| Delayed event queue | FIFO timer for future events | Dumb timer, no dependency chains |
| Condition system | Rich status effects with stacking | No quantified NPC-NPC relationship scores |
| Spatial memory | `visited_areas` set on characters | Player-facing only, not queryable by NPC logic |
| Activity system | Sleep/rest/wait/bathe/meditate | Single activity, no scheduling around it |
| Sound propagation | Sound sources propagate through areas | Not used by NPC awareness behaviors |
| Environment propagation | Temperature flows between connected areas | Not used by NPC comfort-seeking |
| Trait system | Passive bonuses and scripted trait acquisition | Not used as "internal voices" |
| Relationship data | Stored on players | Not queried by behavior logic |

---

## Patterns From Games That Solve Your Problems

### 1. RimWorld: Needs → Thoughts → Mood → Behavior Pipeline

**The pattern:** NPCs don't have explicit goals. They react to internal states.

```
Need (hunger=0.2, energy=0.1) 
  → ThoughtWorker evaluation ("I'm starving" = -20 mood)
  → Composite mood score across all needs/thoughts
  → Behavior picks highest-mood-improvement action
```

**Key design patterns:**
- Each need has `CurLevel` (0.0–1.0), fall rate per interval, thresholds, mood effects
- Joy uses `JoyKindDef` categories with **tolerance building** — repeated activities give diminishing returns, forcing variety
- Thoughts compose into a single `Need_Mood` value via summation of all `baseMoodEffect` values
- Traits create personality differences that drive emergent diversity
- Mental breaks as emergent behavior trigger when mood stays low

**Transferable to ViWo:**
- ViWo vitals already decay (hunger/thirst/social/sanity)
- ViWo emotion system already tracks mood dimensions
- **Missing bridge:** A "ThoughtWorker" layer that converts vital levels + conditions into emotional pressure, then connects that pressure to behavior priorities

**Concrete design:** Instead of static `priority` on behaviors, compute urgency dynamically:
```python
urgency = (1 - current_vital / max_vital) * trait_weight + emotion_modifier
if urgency > threshold: execute_behavior
```

This makes NPCs autonomously seek food when hungry, rest when exhausted, socialize when lonely — without hardcoded schedules.

---

### 2. Dwarf Fortress: Three-Tier Memory + Personality Evolution

**The pattern:** Short-term → long-term → core memories. Core memories change personality traits over time.

**Memory tiers:**
| Tier | Capacity | Function | Promotion |
|------|----------|----------|-----------|
| Short-term | 8 slots | Immediate experiences | Randomly promoted |
| Long-term | Unlimited | Recalled memories with emotional weight | 1:3 chance on recall |
| Core | Limited | Personality-defining memories | Causes trait/value changes |

**How DF dwarfs learn the map:**
- Perception-driven memory creation — every witnessed event generates thought/memory with emotion strength
- Spatial awareness through exploration — unexplored tiles unknown; discovered but unvisited tracked separately
- Path knowledge accumulates through exploration (A* based on current map knowledge)

**Personality change mechanism:** When a long-term memory is recalled and promoted to core memory, it modifies one or more personality facets. Memories can cause permanent shifts in values.

**Transferable to ViWo:**
- ViWo already has memory storage with tags, surface/suppress effects, embeddings
- ViWo already has traits that modify behavior
- **Missing:** Memory promotion pipeline and personality drift

**Concrete design:** Add reflection triggers that fire periodically on agents:
```json
{
  "trigger": "on_delayed",
  "conditions": [{"type": "tick_since_state", "value": 500}],
  "effects": [
    {"type": "reflect_memories", "params": {"focus": "social"}},
    {"type": "update_trait", "params": {"trait": "cautious", "delta": +0.1}}
  ]
}
```

This lets NPCs evolve from experience rather than being pre-defined static personalities.

**Comparison to Generative Agents (Stanford 2023):**

| Aspect | Generative Agents | Dwarf Fortress |
|--------|-------------------|----------------|
| Storage | Natural language descriptions | Structured thought groups |
| Retrieval | Cosine similarity + importance scoring | Random recall from long-term pool |
| Synthesis | LLM-powered reflection | Time-based emotion drift |
| Personality change | Ongoing from reflections | Core memory promotion (1:3) |
| Scale | ~25 agents demonstrated | Hundreds simultaneously |

---

### 3. The Sims: Utility AI + Interaction Advertising

**The pattern:** Every interactive object "advertises" its benefit. NPC scores all options, picks highest utility, adds randomness among top choices.

**Architecture:**
- Needs range -100 to +100, constantly decaying
- Object "advertising" — every interactive object advertises its benefit (bed offers +10 energy, toilet offers +20 bladder)
- Sim surveys available objects + interactions
- Scores each option based on current motive levels + weighted importance
- Picks highest-utility interaction
- Introduces randomness among top-scoring options to prevent robotic predictability
- Aspiration system for long-term goals beyond basic needs

**Transferable to ViWo:**
- ViWo items already have triggers with effects (bed restores energy, toilet fixes bladder)
- ViWo behaviors already evaluate condition→action
- **Missing:** Object advertising + utility scoring + randomization

**Concrete design:** Give items an `advertised_benefits` field in scenario JSON:
```json
{
  "id": "bed_01",
  "type": "item",
  "advertised_benefits": [
    {"effect": "rest_activity", "vital_restore": {"energy": 30}},
    {"area": "bedroom", "privacy_bonus": true}
  ]
}
```

Then in behavior evaluation, NPCs survey available objects, score them against current needs, pick best match. Add `randomize_top_n(3)` to prevent robotic predictability.

---

### 4. F.E.A.R. / KCD2: GOAP + FSM Hybrid

**GOAP (Goal-Oriented Action Planning)** — Used in F.E.A.R., Shadow of Mordor, Kingdom Come: Deliverance II

**Core components:**

| Component | Description | Example |
|-----------|-------------|---------|
| **World State** | Symbolic key-value map of situation | `{ hasWeapon: true, enemyInSight: false, healthLow: true }` |
| **Goals** | Desired future states with priority weights | `{ defendBase: 8, findFood: 5, patrol: 2 }` |
| **Actions** | Steps with preconditions and effects | `Eat { precondition: hasFood, effect: notHungry }` |
| **Planner** | A* search through action space to reach goal | Forward/backward regression planning |

**Planning loop:**
1. Each NPC has assigned goals
2. Planner receives current world state + available goals + action library
3. Selects highest-priority goal
4. Searches action space using A* to find lowest-cost sequence reaching goal
5. Executes plan; replans immediately if any action fails or world state changes
6. F.E.A.R. had 120 actions ranging from animations to smart object usage

**Evolution:** F.E.A.R. → Shadow of Mordor/War → KCD2 combines GOAP with Modular Behavior Trees (MBTs). MBTs specify desired NPC state → GOAP finds actions to transition from current to desired state.

**Emerging pattern — Neuro-Symbolic Hybrid:**
```
LLM Layer:    "Player is injured and nearby" → generate goal: "Seek medical supplies"
GOAP Layer:   {hasMedkit: false} → plan: [goToMedBay → pickUpMedkit → return]
Execution:    Deterministic action sequence via FSM/pathfinding
```

Benefits:
- LLM handles high-level semantic reasoning (what should happen)
- GOAP guarantees valid, cost-optimal action sequences (how to do it)
- Eliminates LLM's weakness with long-horizon deterministic planning
- Complete human-readable audit trail of every decision step

**Transferable to ViWo (requires code addition):**
- ViWo has actions (`go`, `speak`, `damage`, `set_environment`, etc.)
- ViWo has conditions for checking world state
- **Missing:** Planner that chains actions toward goals

---

### 5. Disco Elysium: Internal Voice Competition

**The pattern:** Competing skill voices frame decisions from different perspectives. Failed checks produce interesting outcomes, not dead ends.

**Architecture:**
- 24 Skills across 4 Attributes (Intellect, Psyche, Physique, Motorics)
- **Passive thresholds** — When skill level meets threshold, voice automatically adds commentary/clues/warnings
- **Active checks** — Dice roll (2d6 + skill vs hidden DC); success/failure both produce interesting outcomes
- **Distinct personalities** — Each skill speaks as a separate character with unique perspective
- **Thought Cabinet** — Ideas internalized as permanent passive modifiers; limited slots force prioritization

**Decision-making pattern:** Skills don't just give numerical bonuses — they **frame perspectives**:
- Logic builds elegant but potentially incorrect theories
- Encyclopedia provides historical context that may overwhelm
- Inland Empire offers gut feelings/hunches
- Authority pushes back against anti-patterns

**Application to NPC internal monologue:**

Give NPCs competing internal voices that argue about decisions. An NPC considering whether to help a stranger might have:
- **Caution** voice: "This could be dangerous, remember what happened last time"
- **Empathy** voice: "They look desperate, you know what it's like to need help"
- **Ambition** voice: "Helping them could gain you valuable allies"
- **Pragmatism** voice: "You have your own problems right now"

**Transferable to ViWo today (prompt engineering only):**
- ViWo agents already use LLM prompts with personality
- ViWo has traits that could map to "voices"
- **Missing:** Structured internal monologue with competing perspectives

**Concrete design:** In agent prompts, inject trait-based internal voices:
```
[Caution] "Last time you trusted a stranger, they robbed you."
[Empathy] "They look desperate. You know what help feels like."
[Ambition] "Helping them could gain you an ally."
[Pragmatism] "You have your own problems right now."
```

---

### 6. Dwarf Fortress / UE5 PCG: Procedural World Generation

**DF approach:** Parameter sets + rejection-based generation. Authors specify constraints, generator creates candidates, rejects if quality fails. External tools like Armok's Blueprint provide visual previews.

**RimWorld biome scoring:** Score-based biome competition rather than threshold gates. Modular `workerClass` system lets authors add biomes by writing a single class + XML Def. Planetsmith mod replaces this with physically-motivated climate simulation (wind, ocean currents, rain shadows, monsoons).

**UE5 PCG Framework:** Node-graph rule chains — Surface Sampler → Filter → Transform → Static Mesh Spawner. Landscape layers define biomes; filters read layer weights to control spawn density per biome.

**Wave Function Collapse (WFC):** Input tile patterns → output coherent maps. Good for local detail within BSP-partitioned rooms. Used commercially first in Caves of Qud.

**Caves of Qud Village Generation Pipeline (multi-stage):**
1. Design — Define prefabs: object blueprints, population tables, factions, quest templates
2. World Gen — Generate history: name, base faction, region, government, religion
3. Fabricate — Generate culture: practices, storytelling tradition, signature dish
4. Resolve Neighbors — Determine location, relationships with local sites/NPCs
5. Generate Architecture — Choose style, produce map of buildings
6. Populate Objects — NPCs with dialog, furniture, quests

**Spelunky-style template systems:** Hand-design ~200 room templates with defined entrance/exit connectors. Generator picks template sequence based on compatibility rules. Gets 90% of benefit with 10% of complexity.

**Transferable to ViWo:**

**Pattern 1: Template-Based Generation (Highest ROI)**
- Hand-author ~20 room templates per area type (kitchen, bedroom, office, dungeon)
- Generator selects compatible templates based on constraints
- Fill with context-aware items (kitchen → stove, fridge, utensils)

**Pattern 2: Parameter-Driven Seeding**
```json
{
  "world_gen": {
    "theme": "haunted_mansion",
    "size": "large",
    "density": 0.7,
    "biomes": ["corridor", "grand_hall", "secret_room"],
    "npc_density": 0.4,
    "event_frequency": "high"
  }
}
```

Generator uses parameters to create areas, place items contextually, assign NPCs to roles, generate connections.

**Pattern 3: Graph Grammar Topology**
- Define room types as nodes, connections as edges
- Production rules rewrite subgraphs iteratively
- Constraint solver ensures connectivity and playability

**Context-Aware Item Placement Patterns:**
- Rule-based randomized algorithms with constrained probability domains (level-appropriate items)
- Pair2Scene framework: models object placement via learned local rules — support relations (physical hierarchy) and functional relations (semantic links)
- Room assignment algorithms: discretize space via flood fill from anchor points, store border voxels, enable O(1) location queries

---

### 7. Elder Scrolls Radiant AI: Schedule-Driven Autonomy

**The pattern:** NPCs follow 24-hour schedules with goal-oriented decisions. "Eat at location X at 2pm" → NPC determines how.

**Two parts:**
1. **Radiant AI:** NPC behavior system — 24-hour schedules, goal-oriented decisions, ~30 monitored NPC actions
2. **Radiant Story:** Procedural quest generation — fills quest roles from NPC pool based on player history

**Oblivion chaos problem:** Too much autonomy → NPCs killed each other over items/drugs → guards executed offenders on sight → developers nerfed the system. Skyrim refinement reduced aggression stats, added respawning, balanced autonomy vs. stability.

**Transferable to ViWo (requires schedule engine):**
- ViWo has `time_of_day` condition (HH:MM exact match)
- ViWo has delayed event queue
- ViWo has activities (sleep, rest, wait)
- **Missing:** Schedule definition format + time-aware scheduling

**Concrete design:** Scenario JSON extension:
```json
{
  "schedule": [
    {"time": "06:00", "action": "wake_up"},
    {"time": "07:00", "action": "goto", "target": "kitchen"},
    {"time": "08:00", "action": "eat_breakfast"},
    {"time": "09:00", "action": "patrol", "route": ["hallway", "library"]},
    {"time": "22:00", "action": "return_to_bedroom"},
    {"time": "23:00", "action": "sleep"}
  ],
  "interruptions": [
    {"condition": "player_in_danger", "action": "rush_to_player"},
    {"condition": "fire_detected", "action": "alert_and_flee"}
  ]
}
```

Schedule runs as timed events via existing delayed event queue. Interruption behaviors override schedule when triggered.

---

### 8. Shadow of Mordum/Nemesis: Interaction Memory as Narrative Engine

**The pattern:** Every encounter stored → world remembers → world reacts → new stories emerge. Kill an orc → survivor promoted. Fail to kill → orc taunts next time.

**Architecture:**
- Procedural orc generation — each orc has name, appearance, personality traits, rank
- Hierarchy: Overlord → Warchiefs → Captains → Soldiers
- Memory: Every interaction stored — who killed you, who you killed, who escaped
- Promotion/Demotion: Kill an orc → survivor promoted; fail to kill → orc remembers and taunts
- Social dynamics: Orcs form alliances, rivalries, betrayals independent of player
- Narrative feedback loop: Player actions → world remembers → world reacts → new stories

**Design theory basis:** Self-Determination Theory (SDT) — Competence, Autonomy, Relatedness.

**Transferable to ViWo:**
- ViWo stores memories on characters
- ViWo tracks relationships
- **Missing:** Encounter memory with emotional weight + behavioral consequences

**Concrete design:** Effect to store encounters:
```json
{
  "type": "record_encounter",
  "params": {
    "target": "player",
    "event_type": "combat",
    "outcome": "won",
    "emotional_impact": "fear"
  }
}
```

Later, behavior checks stored encounters:
```json
{
  "trigger": "encounter_player",
  "conditions": [
    {"type": "has_encounter_history", "with": "player", "last_outcome": "lost"}
  ],
  "effects": [{"type": "speak", "message": "You think you won last time?!"}]
}
```

---

### 9. STALKER A-Life System: Continuous World Simulation

**The pattern:** The world continues evolving when the player isn't watching.

**Architecture:**
- Continuous simulation regardless of player presence
- Faction-based motivation graphs (combat, movement, goals)
- Events cascade across the game world even in unloaded areas
- Traders adjust prices based on market events
- No two playthroughs identical

**Transferable to ViWo:** Between turns, world state continues evolving — vitals decay, environment changes, NPC behaviors fire independently. This is already partially implemented but could be extended with persistent world-state tracking.

---

## Recommended Hybrid Architecture for ViWo NPCs

```
Perceptual Layer (sync with turn)
├── World state snapshot (existing graph queries)
├── Entity proximity detection (existing proximity condition)
└── Environmental check (existing temperature/weather conditions)

Utility AI Layer (needs-based scoring) ← Leverage existing vitals + emotions
├── Needs[] with decay rates (existing vitals)
├── Traits[] modifying weights (existing traits)
└── DecisionEngine: score_options(needs, traits) → pick highest utility + randomize top N

Hybrid Decision Engine
├── Routine: Behavior Tree (patrol, eat, sleep) ← Extend existing behaviors
├── Complex: GOAP planner (multi-step goals) ← New system
│   └── LLM generates semantic goals from world state ← Existing agent prompts
└── Dialogue: LLM with personality constraints ← Existing system
    └── Fallback: authored dialogue tree ← Possible via trigger messages

Internal Monologue Layer (Disco Elysium pattern) ← Prompt engineering only
├── Competing perspective voices (traits as voices)
├── Decision framing (prompt template)
└── Thought cabinet (internalized experiences as modifiers)

Event Director (RimWorld pattern) ← New system
├── Incidents[] with probability curves
├── Pacing tracking (suppress after clusters)
└── Narrative arc grouping

Memory System (Generative Agents pattern) ← Extend existing memory
├── Observation stream (episodic memories) ← Existing
├── Reflection synthesis (periodic summarization) ← New effect type
└── Retrieval by relevance (recency + importance + similarity) ← Existing embeddings
```

---

## ViWo Systems Audit: What Exists vs. What's Missing

### Trigger/Effect System Capabilities

**77 trigger types:** take, drop, examine, use, eat, drink, read, light, equip, unequip, throw, break, open, close, enter, speech, delayed, state_enter/exit, tick, look, search, fail_jump/climb, toggle, activate, and many more.

**27 effect types:** message, damage, heal, save, spawn_item, spawn_character, give_item, remove_item, consume_item, set_state, set_environment, teleport, rename, unlock_way, drain, set_description, append_description, adjust_vital, adjust_environment, set_hidden, adjust_uses, end_scenario, restart_scenario, apply_condition, remove_condition, apply_trait, remove_tag, add_tag, set_parameter, adjust_parameter, surface_memory, suppress_memory, unblock_memory, schedule_trigger.

**Condition capabilities:** area checks, proximity, vitals comparison, temperature checks, time_of_day, weather, traits, tags, items, equipment, skill saves, speech matching, sound detection, state checks, random chance, equality, boolean composition (AND/OR/NOT).

### Scenario JSON NPC Definition Support

Scenarios CAN define NPCs with: name, personality, description, stats, vitals, skills, traits, tags, behaviors (condition→action rules), patrol routes, starting position, emotion, relationships, memories, autonomy flag, npc_behavior type, npc_action_interval.

Scenarios CANNOT define: schedules, routines, goals, plans, hierarchical tasks, time-based patterns, need-driven behavior loops, NPC-NPC interaction rules, territory assignments.

---

## Implementation Roadmap

### Phase 1: Immediate Actions (No Code Changes Needed)

1. **Add `advertised_benefits` to item definitions** — Context-aware item placement in scenarios
2. **Inject trait-based internal voices into agent prompts** — Disco Elysium pattern
3. **Connect vital levels to behavior urgency** — RimWorld needs→thoughts→mood pipeline
4. **Add `record_encounter` effect** — Nemesis-style interaction memory
5. **Hand-author room templates per scenario type** — Spelunky-style template-based generation

### Phase 2: Medium Effort (Code Additions)

1. **Schedule engine** — Timed event definitions with interruption overrides
2. **Utility AI scoring** — Score available interactions against current needs
3. **Memory query API** — "where did I last see X?", "what do I know about area Y?"
4. **Reflection effect** — Periodic memory synthesis feeding back into traits/emotions
5. **Goal decomposition** — GOAP planner for multi-step NPC plans

### Phase 3: Long Term (Architecture)

1. **Procedural world generator** — Template-based + WFC + graph grammar topology
2. **NPC mental map builder** — Runtime navmesh learning from agent/player trajectories
3. **NPC-NPC interaction system** — Conversation initiation, social dynamics, relationship propagation
4. **Emergent event director** — RimWorld-style incident budgeting with pacing control

---

## Key Insight

**ViWo already has 80% of what's needed.** The missing pieces are primarily the *bridge layers* — connecting existing systems (vitals→behavior, memories→personality, items→utility scoring) rather than building entirely new subsystems.
