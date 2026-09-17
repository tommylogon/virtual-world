---
type: task
status: todo
area: characters
priority: high
---

# task-404: Character life experience generator

**Filed:** 2026-09-17  
**Depends on:** task-403 (unified memory/knowledge system), task-324
(domain tags)

## Goal

Generate substantial life experience for characters — events, outcomes, fears,
hopes, dreams, wants, likes, dislikes, trauma, and everything that makes people
feel real — beyond what a personality summary can convey.

Aura/Diary (`F:\AI\Aura\Diary`) is the closest reference implementation and
should inform the design, but the goal is a VirtualWorld-native system, not a
Neo4j integration.

## What Aura/Diary teaches us

From `readme.md` and `diary_core.py`:

- Day-by-day simulation with LLM-driven choices and tiered outcomes
- 169+ events across life stages, milestones, and random events
- Emotional dimensions: happiness, anxiety, loneliness, energy,
  social_battery, confidence
- Relationships with quality/decay over time
- Location history (`LIVED_AT`)
- First-person diary entries via `memory_utils.generate_memory`
- RAG-based semantic memory retrieval from past events
- Event outcomes range from critical success to critical failure
- Memories incorporate emotional impact, not just factual recall

The valuable patterns to import:
1. **Events as structured choices**, not prose generation — each event has
   options with defined outcome ranges
2. **Emotional impact as first-class data**, not flavor text
3. **Memory as first-person reflection**, not third-person summary
4. **Traits that evolve** from experiences, not static character card data
5. **Relationship history** as a series of recorded interactions, not a number

## What NOT to import

- Neo4j dependency — VirtualWorld uses JSON files and in-memory graph
- The Diary simulation loop running inside VirtualWorld runtime
- Two-way sync between Diary and VirtualWorld state
- Real-time backstory generation during gameplay

## VirtualWorld-native life experience system

### Data model

Add to `engine/agent_memory.py` (task-403):

```python
class LifeExperience:
    """One recorded life event for a character."""
    def __init__(self, event_id, age_days, event_type, description,
                 choices, outcome, emotional_impact, location, tags,
                 participants, memory_text, source="generated"):
        self.event_id = event_id
        self.age_days = age_days
        self.event_type = event_type  # milestone, random, relationship, trauma, achievement
        self.description = description
        self.choices = choices        # [{text, weight, risk}]
        self.outcome = outcome        # {result, success, emotional_impact}
        self.location = location
        self.tags = tags              # ["childhood", "injury", "school"]
        self.participants = participants  # ["mother", "best_friend"]
        self.memory_text = memory_text  # first-person inner monologue
        self.source = source          # "generated", "preconceived", "background"
```

### Event tables

Create `data/life_events/` with JSON tables, modeled on Aura/Diary's
`events.json` but lighter:

```
data/life_events/
  milestones.json      # guaranteed events by age (first steps, puberty, etc.)
  childhood.json       # ages 0-12
  adolescence.json     # ages 13-17
  adulthood.json       # ages 18+
  trauma_events.json   # cross-age, high-impact negative events
  achievement_events.json  # cross-age, high-impact positive events
  relationship_events.json # meeting, bonding, conflict, loss
```

Each event entry:
```json
{
  "id": "childhood_fell_from_tree",
  "event_type": "accident",
  "age_min": 5,
  "age_max": 12,
  "prerequisites": [],
  "choices": [
    {"text": "Cry and run to parent", "risk": "low", "outcome_tables": ["comforted", "scolded"]},
    {"text": "Brush it off and keep playing", "risk": "medium", "outcome_tables": ["infection", "proud"]}
  ],
  "emotional_impact": {"anxiety": [0, 5], "confidence": [-3, 0]},
  "tags": ["childhood", "injury", "outdoors"],
  "location_contexts": ["home", "park", "schoolyard"]
}
```

### Generator script

Create `tools/generate_backstory.py` — a standalone script that:

1. Reads a character template or creates one from scratch
2. Rolls through ages 0 to current_age using milestone tables + random events
3. For each event, selects options based on character traits (risk tolerance,
   personality modifiers)
4. Resolves outcomes using seeded RNG + trait modifiers
5. Generates first-person memory text via LLM (or template fallback if no LLM)
6. Writes the result as a VirtualWorld preconceived-knowledge payload to
   `data/backstories/<name>.json`

Output format (consumed by task-403's `AgentMind.load_preconceived`):
```json
{
  "name": "miki",
  "backstory_source": "life_experience_generator",
  "emotional_state": {
    "base_happiness": 45, "base_anxiety": 60, "base_loneliness": 30,
    "base_energy": 50, "base_social_battery": 40, "base_confidence": 35
  },
  "memories": [
    {
      "text": "I remember falling off the oak tree in our backyard when I was 8. I scraped my knee badly and cried until Mom came running. She cleaned it up and told me I was brave, but I wasn't brave — I was scared and hurting. That's when I learned that brave doesn't mean not being afraid.",
      "tags": ["childhood", "injury", "mother", "outdoors"],
      "importance": 7,
      "salience": 8,
      "location": "childhood_home_backyard",
      "tick": 0,
      "source": "preconceived",
      "emotional_impact": {"anxiety": 5, "confidence": -2},
      "age_days": 2920,
      "participants": ["mother"]
    }
  ],
  "known_areas": ["childhood_home", "elementary_school", "high_school", "first_apartment"],
  "known_items": ["item_moms_locket", "item_childhood_diary"],
  "relationships": [
    {
      "name": "mother",
      "type": "family",
      "quality": 75,
      "history": ["nurturing", "strict", "supportive", "protective"],
      "key_events": ["childhood_fell_from_tree", "high_school_graduation"]
    }
  ],
  "fears": ["heights", "abandonment", "failure"],
  "hopes": ["become_asmr_artist", "find_stable_relationship", "overcome_anxiety"],
  "trauma": [
    {
      "event_id": "childhood_fell_from_tree",
      "severity": 3,
      "trigger": "heights",
      "description": "Fell 3 meters from an oak tree, scraped knee badly"
    }
  ],
  "diary_entries": [
    {
      "age_days": 2920,
      "entry": "Today I fell out of the oak tree again. Third time this month. Mom says I need to be more careful but the branches look so climbable. I don't want to tell her I was showing off for Jake from next door. My knee hurts but I think he was impressed. Worth it? Maybe.",
      "emotional_state": {"anxiety": 40, "happiness": 55, "confidence": 30},
      "location": "childhood_home_backyard",
      "tags": ["childhood", "injury", "crush"]
    }
  ],
  "personality_deltas": {
    "clingy": +2,
    "anxious": +1,
    "creative": +1
  },
  "traits": ["clingy", "anxious", "creative", "awkward"]
}
```

### LLM integration

The generator calls the same LLM provider VirtualWorld already uses. The prompt
asks for a first-person memory of the event, grounded in the character's
personality and the event's emotional impact. No new LLM plumbing is needed.

If no LLM is available, the generator falls back to template-based memories:
"I was [age] when [event]. I felt [emotion]. [One-sentence reflection.]"

### Determinism

All RNG is seeded from character name + event id + age. The same character
generated twice produces identical memories, relationships, and emotional
state. This is required for save/load consistency and for the editor to show
stable backstories.

### Scenario authoring workflow

1. Option A: Author a character template with `backstory_generation` block:
   ```json
   {
     "name": "goblin_scout",
     "backstory_generation": {
       "current_age": 22,
       "events": ["childhood_fell_from_tree", "adolescence_bullied"],
       "custom_memories": ["The camp food cache is in the pantry behind the kitchen."]
     }
   }
   ```
2. Option B: Run `python tools/generate_backstory.py --template goblin_scout.json`
   → outputs `data/backstories/goblin_scout.json`
3. In scenario player/character entry: `"backstory": "data/backstories/goblin_scout.json"`
4. At scenario load, `AgentMind.load_preconceived()` reads and injects

## Files

- `data/life_events/*.json` (new event tables)
- `tools/generate_backstory.py` (new generator script)
- `engine/agent_memory.py` — add `LifeExperience`, `diary_entries`, `fears`,
  `hopes`, `trauma`, `personality_deltas` fields
- `engine/tick_manager.py` — apply `personality_deltas` at load
- `docs/virtualWorld/Systems/Memory System.md` — document the authoring workflow

## Verification

- Generate backstory for Miki using `tools/generate_backstory.py`
- Load Pines scenario with her backstory attached
- Verify her first active prompt references a childhood memory with emotional
  weight, not just personality summary
- Verify fears/hopes/trauma affect behavior: a goblin with `fears: ["fire"]`
  avoids fire sources; one with `trauma: [{trigger: "heights"}]` refuses to
  cross high bridges
- Generate twice with same seed → identical output
- Save/load round-trip: life experience data survives serialization
- Run without LLM → template fallback produces valid memories

## Non-goals

- Running Aura/Diary inside VirtualWorld runtime
- Real-time backstory generation during gameplay
- Two-way sync between an external graph and VirtualWorld state
- Full Neo4j event graph import
