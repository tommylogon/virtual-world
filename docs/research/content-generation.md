# Content Generation for Virtual World — Research

## The Problem
Virtual World's scenario creation is entirely manual. An author designs areas, items, exits, triggers, and NPCs by hand in JSON or via the UI. This is slow, and the quality depends entirely on the author's skill and time.

The trigger system has an "AI-generated triggers" task (`task-330`) but it's unimplemented. The `generateWithAI()` function in `main.js` exists but only handles basic item generation.

**The question:** What's the right level of AI assistance for world building? Full automation? Co-pilot? Refinement?

## What VW Needs Generated

### 1. Items
- Name, description, actions, state, weight, tags
- Triggers (on_examine, on_use, on_take, etc.)
- Contents (items inside items)
- Skill checks, action costs, effect params

### 2. Areas/Rooms
- Name, description, environment (light, temperature, smell, noise)
- Exits (directions, target areas, way states)
- Items present in the room
- NPCs present in the room

### 3. Triggers
- Trigger type (on_examine, on_use, on_tick, etc.)
- Conditions (when it fires)
- Effects (what happens)
- Effect parameters

### 4. NPCs
- Personality, description, backstory
- Knowledge (what they know about the world)
- Relationships with other NPCs
- Behaviors and schedules

### 5. Quests
- Objective, steps, rewards
- Prerequisites, failure conditions
- NPC involvement

## State of the Art

### 1. AI Dungeon (Latitude)
**Approach:** Full procedural generation. LLM generates entire adventures from a single prompt.

**What works:**
- Infinite content variety
- Player-driven narrative direction
- Low authorial burden

**What fails:**
- Incoherent world state (LLM forgets what it generated)
- No persistence (each adventure is ephemeral)
- No structured game mechanics

**Lesson for VW:** Pure LLM generation is too loose for a structured world. Need hybrid: LLM suggests, engine validates.

### 2. Inworld AI's "SmartNPC" Generation
**Approach:** LLM generates NPC personality, knowledge, and dialogue from a character brief.

**Process:**
1. Author writes: "A grumpy blacksmith who lost his apprentice"
2. LLM generates: personality traits, speech patterns, knowledge base, relationship dynamics
3. Author reviews and adjusts sliders

**What works:**
- Fast NPC creation
- Consistent personality
- Knowledge boundaries respected

**Lesson for VW:** Character generation is the lowest-risk entry point. NPCs are self-contained — bad generation doesn't break the world.

### 3. Bethesda's "Neural LOD" (Research Concept)
**Approach:** LLM generates environmental details on-demand based on player focus.

**Concept:**
- Author defines area skeleton (size, theme, key locations)
- LLM fills in details when player examines something
- Details are cached after first generation

**Lesson for VW:** Could apply to item descriptions, NPC backstory details, room flavor text.

### 4. RAG-Based World Building (Emerging Pattern)
**Approach:** Use vector search over existing world content to generate consistent new content.

**Process:**
1. Author generates new item description
2. System retrieves similar existing items
3. LLM generates new item consistent with existing ones
4. Validation: does new item contradict existing lore?

**Lesson for VW:** VW already has a graph and embeddings. This could prevent hallucinated content.

### 5. Constrained LLM Generation
**Approach:** LLM generates content within strict schemas and rules.

**Techniques:**
- JSON schema enforcement (Pydantic, Zod)
- Rule-based post-processing
- Validation against world state
- Template filling with LLM creativity within bounds

**Lesson for VW:** VW's trigger system is already schema-constrained. LLM generation should fill templates, not create from scratch.

## Recommended VW Content Generation Strategy

### Phase 1: Item Generation (1-2 weeks)
**Input:** Natural language prompt → structured item JSON
**Example:**
```
Prompt: "A rusted sword found in a goblin cave"
Output:
{
  "name": "Rusted Sword",
  "description": "A dented iron blade, pitted with corrosion. It has seen better days.",
  "actions": ["examine", "take", "equip"],
  "weight": 3.0,
  "current_state": "normal",
  "triggers": [
    {"type": "on_examine", "effects": [{"type": "message", "text": "The blade is..."}]}
  ]
}
```

**Validation:**
- Schema check (required fields present)
- Consistency check (name matches description, actions are valid)
- World check (no duplicate item IDs)

### Phase 2: NPC Generation (2-3 weeks)
**Input:** Character brief → structured NPC JSON
**Example:**
```
Prompt: "A nervous librarian who hides a secret"
Output:
{
  "name": "Elena",
  "personality": "Shy, meticulous, secretive",
  "description": "A woman in her thirties with ink-stained fingers...",
  "knowledge": ["The library has a hidden basement", "She saw someone sneaking in at night"],
  "relationships": {"player": "neutral", "town_square": "friendly"},
  "behaviors": ["wander_library", "avoid_cellar"]
}
```

**Validation:**
- Personality consistency check
- Knowledge boundary enforcement
- Relationship sanity check

### Phase 3: Area Generation (3-4 weeks)
**Input:** Theme + constraints → area with items, exits, NPCs
**Example:**
```
Prompt: "A cozy tavern in a small town, 3 exits, 2 NPCs"
Output:
{
  "areas": {
    "The Rusty Tankard": {
      "description": "A warm tavern with a crackling fire...",
      "exits": {"north": {"target": "Town Square"}, "east": {"target": "Kitchen"}},
      "items": [{"name": "Wooden Table", ...}],
      "npcs": [{"name": "Barkeep", ...}]
    }
  }
}
```

**Validation:**
- Connectivity check (exits reference valid areas)
- Capacity check (room not overstuffed)
- Theme consistency (items match room theme)

### Phase 4: Quest Generation (4-6 weeks)
**Input:** World state + NPC relationships → quest chain
**Example:**
```
Input: Elena trusts player, Elena knows about hidden basement
Output:
{
  "quest": "The Librarian's Secret",
  "steps": [
    {"action": "talk to Elena about basement", "requirement": "relationship > 30"},
    {"action": "search library for hidden door", "requirement": null},
    {"action": "enter basement", "requirement": "found hidden door"}
  ],
  "rewards": {"reputation": {"town": 10}, "item": "Ancient Tome"}
}
```

**Validation:**
- Feasibility check (can player actually complete this?)
- Consistency check (quest doesn't contradict world state)
- Balance check (rewards proportional to difficulty)

## Implementation Considerations

### 1. Prompt Engineering for Generation
**Key difference from NPC dialogue:** Generation prompts need to be:
- Constrained to schemas
- Grounded in existing world content
- Deterministic where possible (temperature 0.0-0.3)
- Validated before execution

### 2. The Author-in-the-Loop Pattern
**Never generate without human review.**
- Generate → Preview → Edit → Validate → Commit
- Author can adjust any generated field
- LLM is assistant, not replacement

### 3. Incremental Generation
**Don't generate everything at once.**
- Generate skeleton first (areas, connections)
- Fill in items second
- Add triggers third
- Add NPCs last

Each layer validates against previous layers.

## Key Insight
**Content generation is not about "more content faster" — it's about "authorial leverage."** The goal is to let authors focus on creative decisions (what happens, why it matters) while the LLM handles tedious details (item stats, trigger wiring, description polishing).

The risk is **content bloat without quality** — generating 100 items that feel generic. Better to generate 10 items that feel hand-crafted.
