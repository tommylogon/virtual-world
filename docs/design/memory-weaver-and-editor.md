# Memory Weaver & Unified Editor - Design Document

**Status:** design / pre-implementation
**Related:** task-730 (interactive memory creation), task-785 (inspect memory record & evidence), task-756 (emotion editing in Mind view), task-729 (Mind panel editing surface), task-685/686/687/689/690/691 (memory dynamics & Mind dashboard), task-849 (narrative authoring feeds memories & goals), bug-519 (editorial notes in memory text)
**Modules:** `static/js/inspector/mind-view.ts`, `static/js/inspector/memory-view.ts`, `routes/memories.py`, `engine/memory_dynamics.py`, `engine/derive.py`

---

## 1. Problem Statement (Measured in Current Code)

1. **`InspectorMemory.generateMemory` (`static/js/inspector/memory-view.ts:458-656`) blocks grounded memories:**
   - `_buildSeedPrompt` (`memory-view.ts:552-559`) instructs the LLM: *"do NOT reference any current location, scene, other characters, or in-world events"* and *"never names, items, or places"*.
   - `_saveGeneratedMemory` (`memory-view.ts:643`) hardcodes `tick: 0`, `location: ''`, and omits `category`, `confidence`, `entity_ids`, and relationship deltas (`rel:<Name>`, `emotions: {who, data}`).
   - As a result, the generator cannot author a memory back in time (`tick < 0` or a past positive tick), cannot link world entities (`entity_ids`), and cannot shift per-person relationship dimensions in `engine/derive.py` (`derive_person_profile`).

2. **Two separate modals duplicate 70% of the same surface:**
   - `showMemoryEditor` (`memory-view.ts:57-294`) exposes `tick` / `Turns before start`, `category`, `confidence`, `location`, `entity_ids`, and `contradicts`, but has no LLM generation and no emotion picker (removed in task-756).
   - `generateMemory` (`memory-view.ts:458-656`) exposes a one-shot LLM prompt and the emotion picker (`_attachEmotionSelector`), but omits `tick`, `category`, `confidence`, `location`, `entity_ids`, `contradicts`, and relationship deltas.
   - Both render a stacked `.modal-overlay` (`#mem-editor-modal`) on top of the Mind modal (`z-index: 9991`), even though `InspectorMindView` (`static/js/inspector/mind-view.ts:2114-2129`) already has a dedicated right-hand detail column (`#mind-detail`) in the `Memories` tab.

3. **`_identityBlock` (`memory-view.ts:536-542`) ignores the character's actual mind:**
   - Only `player.personality` and `player.description` are sent to the LLM.
   - Structured Persona fields (`GET /api/players/<name>/record` - `narrative.biography`, `personality.values`, `fears`, `likes`, `dislikes`), existing relevant memories (`POST /api/players/<name>/memories/retrieve`), derived per-person profiles (`GET /api/players/<name>/memories/people`), and current mood (`player.emotion`) are not included.

4. **No structural boundary between editorial conversation and `memory.text` (bug-519):**
   - When an author iterates with an LLM in a single raw text box, editorial commentary (`"shorter, punchier, still sounds like miki rambling..."` in `data/scenarios/mansion.json`) gets saved inside `Player.memories[].text` and injected into `=== I REMEMBER ===` on every recall.

---

## 2. Design Principles & Invariants

1. **Zero new stores:** Every authored or generated memory is saved to `Player.memories` via `POST /api/players/<name>/memories/entry` (`add_player_memory`) or `POST /api/players/<name>/memories/entry/<entry_id>` (`update_player_memory`).
2. **One relationship reducer:** Memories about other people write `rel:<Name>` + `<dim>:<delta>` tags and/or `emotions: {who, why, data: {dim: delta}}` on the memory entry, which `engine/derive.py` (`derive_person_profile`) already reduces into `trust`, `fear`, `attraction`, `disgust`, `respect`, `familiarity`, `closeness`, `consent`, `role`, and `summary`.
3. **One dynamics model:** `engine/memory_dynamics.py` (`ensure_dynamics`, `effective_importance`, `decay_resistance`, `detect_contradiction`, `link`) owns `category`, `confidence`, `activation`, `reinforcements`, `reflection_depth`, `source_memory_ids`, and `contradicts`.
4. **Strict separation of voice thread and persisted record:** The conversational back-and-forth with the character (`character_reply`) is UI draft state only and is never written to `memory.text`.
5. **Retire the split modals:** Replace the separate one-shot generator modal and legacy edit modal with one unified **Memory Weaver & Editor** hosted directly in the Mind panel's `Memories` tab (with a modal fallback only when invoked outside the Mind panel).

---

## 3. Three Natural-Language Authoring Modes

The Memory Weaver supports three authoring intents through a single prompt bar and a shared structured output contract:

### Mode A: Ask Opinion / Reaction ("What did they think of a movie, book, rumour, or event?")
- **User prompt example:** *"What did you think of the horror movie 'The Glass Cellar' you watched with Rosa last night?"* or *"How do you feel about the elder's new ration law?"*
- **Grounding:** Queries `POST /api/players/<name>/memories/retrieve` (`reinforce: false`) for existing memories matching the topic/entities, reads Persona `likes` / `dislikes` / `fears` / `values`, and reads any referenced person's derived profile.
- **Draft output:**
  - `character_reply`: conversational reaction in the character's voice.
  - `memory`: first-person recollection (`category: "belief"` or `"episodic"`, `type: "reflection"` or `"event"`), backdated `tick`, `memory_emotions` (`[{label, intensity}]`), resolved `entity_ids`, and optional `relationship_deltas`.

### Mode B: Backdated Event ("Make a memory about an event back in time")
- **User prompt example:** *"Five years ago during the dock fire, he pulled a chest of ledgers out of the flames instead of helping the watchman."*
- **Grounding:** Resolves any named world areas, items, or characters against the scenario graph (`_resolve_entity_ids`), converts the relative time expression (`"five years ago"`, `"yesterday"`, `"30 turns before start"`) into a negative or past `tick`, and computes realistic age-adjusted `activation` via `decay_resistance`.
- **Optional linked expectation / goal:**
  - If the event teaches a behavioural rule (`behavior` in the structured draft), the author can tick **"Also record derived expectation"**, which writes a linked `category: "procedural"`, `type: "expectation"`, `reflection_depth: 1`, `source_memory_ids: [base_id]` entry (reusing the contract in `routes/memories.py:reflect_player_memories`).
  - If the event opens a long-term want, the author can tick **"Also propose GIMP goal"**, which appends a `status: "proposed"` goal (`what`, `motivation`, `intention`) to `player.goals` via `apply_mind_patch` (task-849).

### Mode C: Interpersonal / Social Memory ("Memories about other people")
- **User prompt example:** *"Two weeks ago, Gribba caught Kaelen sneaking near the larder and let him go with a warning."*
- **Grounding:** Resolves the other character via `_resolve_other` (`routes/player_ops.py:234`), reads the current derived relationship profile (`derive_person_profile`), and recalls prior shared memories (`rel:<Name>`).
- **Draft output & live relationship preview:**
  - Populates `category: "social"`, `entity_ids: [player_node_id]`, `tags: ["rel:<Name>", "<dim>:<delta>", ...]`, and `emotions: {who: "<Name>", data: {<dim>: <delta>}}`.
  - Displays a **live before -> after preview** of how committing this memory will shift `trust`, `fear`, `attraction`, `disgust`, `respect`, `closeness`, and `role` in `derive_person_profile`.
  - **Optional Bilateral / Shared Memory toggle:** When the target is another character in `worldState.players`, ticking **"Also draft counterpart memory for <Other>"** generates the other character's first-person memory of the same event at the same `tick`, allowing both perspectives to be reviewed and saved together.

---

## 4. Backdating & Age-Decay Mechanics

1. **Relative Time Parser & Timeline Click:**
   - Clicking a point on the SVG timeline ribbon (`_timelineHtml` in `mind-view.ts:147`) sets the draft's `tick` to that position.
   - Typing natural time expressions (`"45 minutes ago"`, `"3 days ago"`, `"2 years before start"`, `"tick -500"`) converts to ticks using `world.time_per_tick_minutes`:
     $$\text{tick} = \text{current\_tick} - \left\lfloor \frac{\text{minutes}}{\text{time\_per\_tick\_minutes}} \right\rfloor$$
   - Pre-scenario memories use negative ticks (`tick < 0`), matching `showMemoryEditor`'s existing `prestart` convention (`memory-view.ts:396`).

2. **Optional Natural Age-Decay (`activation`):**
   - By default, `ensure_dynamics` sets `activation = 1.0`.
   - When backdating a memory into the past, the editor offers a **"Simulate natural fading over elapsed time"** toggle:
     $$\text{activation}_0 = \max\!\left(0.15,\; 1.0 - \text{elapsed\_ticks} \times \text{rate} \times \text{decay\_resistance}(\text{entry})\right)$$
   - High-importance, emotionally intense, or belief/semantic memories naturally keep high activation due to `decay_resistance` (`engine/memory_dynamics.py:177`), while trivial old episodes start partially faded.

---

## 5. LLM Prompt & JSON Envelope Contract

### 5.1 Grounding Context Bundle (`POST /api/players/<name>/memories/context`)

A lightweight read-only endpoint in `routes/memories.py` (marked `g.no_broadcast = True`) assembles the character's grounding context for a given `query` / `theme`:

```json
{
  "character": "Kaelen Voss",
  "current_tick": 120,
  "time_per_tick_minutes": 1,
  "persona_summary": {
    "base_description": "...",
    "personality": "...",
    "values": ["self-reliance"],
    "fears": ["deep water"],
    "likes": ["old maps"],
    "dislikes": ["debt"],
    "early_life": "..."
  },
  "current_emotion": { "current": "calm", "intensity": 0.3 },
  "recalled_memories": [
    { "id": "mem_1", "tick": -200, "category": "episodic", "text": "..." }
  ],
  "people_profiles": {
    "Gribba": { "role": "rival", "trust": -20.0, "fear": 15.0, "respect": 25.0, "summary": "..." }
  },
  "world_entities": {
    "characters": ["Gribba", "Rosa"],
    "areas": ["Tavern", "Dock"],
    "items": ["Rusty Key"]
  }
}
```

### 5.2 Structured LLM Response Schema

The LLM is prompted with the grounding bundle and conversation history, and returns a single JSON object:

```json
{
  "character_reply": "First-person conversational response to the designer (why I felt that way, how it fits my past). Never stored in memory.text.",
  "memory": {
    "text": "Clean first-person recollection to store in Player.memories.",
    "type": "event",
    "category": "episodic",
    "importance": 7,
    "confidence": 0.9,
    "tick_offset_minutes": -20160,
    "location": "Tavern",
    "entities": ["Gribba"],
    "tags": ["larder", "warning", "rel:Gribba"],
    "memory_emotions": [
      { "label": "nervous", "intensity": 6 },
      { "label": "grateful", "intensity": 5 }
    ],
    "relationship_deltas": [
      {
        "who": "Gribba",
        "why": "Let me go with a warning instead of turning me in",
        "data": { "trust": 2.5, "respect": 3.0, "fear": -1.0 }
      }
    ],
    "derived_expectation": "Check whether Gribba is on watch before approaching the larder."
  },
  "counterpart_memory": {
    "character": "Gribba",
    "text": "I caught Kaelen snooping near the larder two weeks back and let him off with a warning.",
    "importance": 5,
    "memory_emotions": [{ "label": "amused", "intensity": 4 }],
    "relationship_deltas": [
      { "who": "Kaelen Voss", "data": { "familiarity": 2.0, "trust": -1.0 } }
    ]
  }
}
```

---

## 6. Unified Inspector & Editor UI (`mind-view.ts` & `memory-view.ts`)

In **🧠 Mind -> Memories**, the right-hand column (`#mind-detail`, widened from `380px` to `440px`) operates in two modes:

1. **Inspect & Edit Mode (when an existing memory card is selected - task-785 + task-756):**
   - Shows the full prose, dynamics bars (`activation`, `confidence`, `reinforcements`, `reflection_depth`), and emotional encoding bars.
   - **Underlying Record & Evidence fold (task-785):** Displays raw inspectable record fields (`id`, `tick` + wall-clock time, `source`, `kind`, `category`, `location`, `visits`, `entity_ids` with clickable node chips, `tags`, `contradicts`, `source_memory_ids`, and matching `lived_log` entries from `player.lived_log` at that tick/subject, or an explicit empty-evidence state when none exist).
   - **Inline Edit toggle:** Edits `text`, `type`, `category`, `importance`, `confidence`, `tick` (with relative time helper), `location`, `entity_ids`, `tags`, `contradicts`, and `memory_emotions` in place and saves via `ApiClient.updatePlayerMemory`.

2. **Weave / Create Mode (`+ Add / ✨ Weave Memory` button - task-730):**
   - **Top:** Mode selector chips (`💬 Ask Opinion`, `🕰️ Backdate Event`, `🤝 About a Person`, `✍️ Manual`) + natural-language prompt input + multi-turn conversation thread where the character replies in voice and the designer can send follow-up refinements (*"Make it more resentful"*, *"Set it 3 days ago in the Kitchen"*).
   - **Middle (Live Contradiction & Relationship Impact Banner):**
     - Runs contradiction detection against `player.memories` and flags any conflicting memory IDs before save.
     - Shows derived relationship dimension shifts (`trust`, `fear`, `respect`, `attraction`, `disgust`, `role`) when a person is referenced.
   - **Bottom (Editable Structured Card):**
     - The exact same form fields as Edit Mode, pre-filled by the LLM draft (or blank in `✍️ Manual` mode), plus optional checkboxes for **Simulate natural age decay**, **Record derived expectation**, and **Draft counterpart memory for <Other>**.
     - **Accept & Save** commits via `ApiClient.addPlayerMemory` with `source: "manual"` and refreshes the Mind view. **Cancel** discards the draft without mutating state.
