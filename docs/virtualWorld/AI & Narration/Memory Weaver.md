---
type: doc
tags: [system/memory, topic/memory-dynamics, surface/editor]
---

# Memory Weaver & Unified Editor

## What you can do

The **Memory Weaver & Unified Editor** lets you author, backdate, and refine a character's memories in natural language or through direct structured controls. Starting from the **🧠 Mind** dashboard (`static/js/inspector/mind-view.ts`) or the character inspector's **Memories** tab (`static/js/inspector/memory-view.ts`), you can ask how a character felt about a movie or idea, plant an event at any point in their past (before or during the scenario), or weave an interpersonal memory about other characters that shifts derived `trust`, `fear`, `attraction`, `disgust`, and `respect` profiles. Before saving, the editor shows live `before -> after` relationship profile previews and flags potential contradictions against existing memories.

Full architecture and contract reference: `docs/design/memory-weaver-and-editor.md` (`task-730`).

---

## 1. How to open the Memory Weaver

All memory creation, natural-language generation, and editing share a single unified modal (`InspectorMemory.openWeaver`), reachable from four places:

1. **Mind Dashboard - Memories Toolbar** (`🧠 Mind` button in the character inspector header -> **Memories** tab):
   - **`💬 Ask Opinion`** - opens the Weaver in **Ask Opinion / Reaction** mode.
   - **`🕰️ Backdate Event`** - opens the Weaver in **Backdate Event** mode.
   - **`🤝 About Person`** - opens the Weaver in **About a Person** mode.
   - **`+ Add / Edit`** - opens the Weaver with the structured editor ready for direct authoring or natural-language prompting.
2. **Mind Dashboard - Timeline Ribbon Double-Click** (`🧠 Mind` -> **Memories** or **Timeline** tab):
   - **Double-click any horizontal position** on the SVG timeline (`#mind-timeline-svg`). The Weaver opens in **Backdate Event** mode pre-anchored to that exact past tick (`tick -250`, `tick 42`, etc.).
3. **Mind Dashboard - People Tab** (`🧠 Mind` -> **People** tab):
   - Every person card derived by `engine/derive.py` includes a **`🤝 Weave Memory`** button. Clicking it opens the Weaver in **About a Person** mode with that character pre-selected in the Interpersonal Feelings row and entity links.
4. **Memory Row Edit (`✏️`)**:
   - Clicking **`✏️`** on any existing memory in the Memories tab or Mind panel opens the same unified modal in **Edit Memory** mode, pre-populated with the memory's text, tick, category, dynamics, emotions, relationship deltas, and live previews. Even while editing an existing memory, you can expand the **✨ Natural-Language Weaver** panel to rewrite or refine it in the character's voice.

---

## 2. The three Natural-Language modes

| Mode | Default Type & Category | Best For | Example Prompt |
|---|---|---|---|
| **💬 Ask Opinion / Reaction** | `type: thought`, `category: belief` | Asking what the character thought of a movie, book, rumor, philosophy, or recent event | *"What did she think of the horror movie The Pale Lighthouse she watched last week?"* |
| **🕰️ Backdate Event** | `type: observation`, `category: episodic` | Planting a concrete lived experience at a specific point in the past (childhood, years before the scenario, or earlier today) | *"Three years before the scenario started, he got locked in the abbey cellar during a thunderstorm."* |
| **🤝 About a Person** | `type: observation`, `category: social` | Authoring a shared moment, betrayal, kindness, or impression involving one or more people that shifts how the character feels about them | *"Yesterday Anna Bandura bandaged his burned hand without asking for anything in return."* |

---

## 3. Step-by-step workflow

### Step 1: Set the time anchor ("When did this happen?")

In the **When did this happen?** field (`#weaver-when`), type a natural-language time expression or edit the raw **Tick** field directly:

| Input | Resolved Tick (at `current_tick = 100`, `1 min/tick`) | Notes |
|---|---|---|
| `"now"` or empty | `100` | Current simulation tick |
| `"30 minutes ago"` | `70` | Converted via scenario `minutes_per_tick` |
| `"2 hours ago"` | `-20` | Negative ticks represent pre-scenario time |
| `"yesterday"` | `-1340` | `1440` minutes before `current_tick` |
| `"3 days ago"` | `-4220` | Multi-day offset |
| `"2 weeks ago"` | `-20060` | Multi-week offset |
| `"5 years ago"` | `-2627900` | Pre-scenario backstory (`SEED` badge) |
| `"100 turns before start"` | `-100` | Explicit pre-scenario tick offset (`-N`) |
| `"tick -250"` or `"-250"` | `-250` | Direct tick number |

- **Simulate natural age decay (`#weaver-age-decay`)**: When checked on a backdated memory (`tick < current_tick`), saving automatically computes a decayed initial `activation` (`max(0.25, 1.0 - age_factor)`) weighted by the memory's importance and emotional intensity, so an older minor memory starts naturally faded while a defining trauma stays vivid.
- **Pre-birthday memory gate (`birth_tick`)**: If the character has an authored `identity.birthday` (`dd.mm.yyyy`) or `identity.age`, `engine/lifecycle.py:ensure_birth_tick` resolves their `birth_tick`. Both the frontend (`#mem-editor-birth-gate`, timeline double-click, and `InspectorMemory.parseRelativeTime`) and backend (`POST /api/players/<name>/memories/entry` and `/entry/<id>`) clamp or reject (`400`) any memory tick earlier than `birth_tick`.

### Step 2: Weave & refine in the character's voice

1. Enter your prompt in the **Natural-Language Weaver** box (`#weaver-prompt`) and click **`✨ Weave in Character Voice`**.
2. The Weaver fetches a read-only grounding packet (`POST /api/players/<name>/memories/context`, with `g.no_broadcast = True` so it never mutates recall counts or triggers emotional respikes) containing:
   - Character identity (`personality`, `description`, `traits`, `current_emotion`)
   - Top relevant existing memories (non-reinforcing read)
   - Current derived relationship profiles (`engine/derive.py`)
   - Known world entities (characters, areas, items)
3. The LLM drafts a structured response and automatically populates:
   - **First-person memory text** (sanitized by `InspectorMemory.stripEditorialLeakage` so omniscient notes like *"unbeknownst to her"* or *"though he doesn't realize it"* are stripped)
   - **Type**, **Category** (`episodic`, `belief`, `social`, `procedural`, `semantic`), **Importance** (`1-10`), and **Confidence** (`0-100%`)
   - **Emotions** (`[{label, intensity}]`) and single-word conceptual **Tags**
   - **Entity references** (matched to canonical world `entity_ids`)
   - **Interpersonal feelings** (`relationship_deltas`: `who`, `why`, and deltas across `trust`, `fear`, `attraction`, `disgust`, `respect`)
   - **Optional Behavioral Expectation** (`derived_expectation`, e.g. *"Check the cellar lock before entering"*)
   - **Optional Counterpart Memory** (the other character's first-person memory of the same moment)
4. **Multi-turn refinement**: Once a draft is generated, a follow-up bar (`#weaver-refine-input`) appears. Type instructions like *"Make it more bitter"* or *"Add that she still respects his skill"* and click **`↻ Refine`** to iterate without losing your time anchor or context.

### Step 3: Edit interpersonal feelings & inspect live previews

- **Interpersonal Feelings (`#weaver-rel-rows`)**: Add or edit rows for one or more characters (`+ Add Person`). Each row specifies a target character, an optional reason (`why`), and sliders/inputs (`-5..+5`) for `trust`, `fear`, `attraction`, `disgust`, and `respect`.
- **Live Relationship Impact Preview (`#weaver-rel-preview`)**: As you edit the memory text, importance, or relationship deltas, the modal queries `POST /api/players/<name>/memories/context` (`debounced 250ms`) to run `engine/derive.py:derive_person_profile` on a temporary copy of the character's memory list. It renders `before -> after` bars (`0-100`) and net deltas (`+12`, `-8`) so you can see the exact effect on the character's social model before saving.
- **Live Contradiction Check (`#weaver-contradictions-preview`)**: Runs `engine/memory_dynamics.py:detect_contradiction` against the character's existing memories as you type. If the draft shares an entity with an existing memory and has negation asymmetry (one affirms what the other denies), a warning banner shows which memory (`tick` and snippet) will be linked in `contradicts[]`.
- **Derived Expectation & Counterpart Memory checkboxes**:
  - Checking **Also store derived behavioral expectation** saves a second linked `category: "procedural"` memory (`reflection_depth: 1`, `source_memory_ids: [<new_id>]`) that surfaces in the `EXPECTATIONS` section of agent prompts.
  - Checking **Also plant counterpart memory on `<Target>`** writes the other person's perspective to their `Player.memories[]` on save.

---

## 4. Inspecting the underlying record & lived-log evidence

In the **🧠 Mind** dashboard (`static/js/inspector/mind-view.ts`), selecting any memory in the **Memories** tab opens a detail pane at the bottom of the list with four sections:

1. **Header & Action Bar**: Category badge, confidence percentage, activation percentage, reinforcement count (`×N`), and a **`✏️ Edit in Weaver`** button.
2. **Connections**:
   - **⚡ Contradicts**: Memories that conflict with this one (click to jump).
   - **🔗 Derived from**: Source memories (`source_memory_ids`) when `reflection_depth >= 1`.
   - **👥 Shared context**: Sibling memories referencing the same `entity_ids`.
3. **Underlying Record & Lived-Log Evidence** (collapsible `<details>` section, `task-785`):
   - **Record metadata chips**: `id`, `source` (`auto` vs `manual`), `tick`, `type`, `category`, `importance`, `confidence`, `activation`, `reinforcements`, `last_recalled_tick`, `salience_override`, `location`, `entity_ids`, and `tags`.
   - **Lived-log evidence**: Matches entries from `player.lived_log` within `±2` ticks of the memory's `tick` (or whose text overlaps the memory), showing the raw runtime event that produced or accompanied the memory. Backdated seed memories (`tick < 0`) clearly state that no runtime log precedes tick 0.
   - **Raw JSON record**: Nested `<details>` disclosure showing the exact serialized JSON dictionary stored in `Player.memories[]`.

---

## 5. Current boundaries & what is not ready yet

- **LLM provider required for `✨ Weave in Character Voice`**: Natural-language drafting and multi-turn refinement use the browser's `LLMClient.chatCompletion` and require an active LLM provider in Settings. When no LLM is configured, every other part of the unified modal (natural-language relative-time parsing, manual text authoring, multi-person relationship delta sliders, live `derive.py` relationship previews, live contradiction detection, and age-decay simulation) works offline.
- **Deterministic write-time contradiction detection**: The live contradiction preview and write-time linker (`engine/memory_dynamics.py:detect_contradiction`) use fast deterministic negation-asymmetry + content-word overlap on shared entities rather than an LLM call on every edit. Subtle semantic contradictions without shared entities or negation markers are surfaced later during `AgentMemory.reflect()` (`Reflection 2.0`), or can be linked manually via the **Contradicts** selector in the **Advanced** section.
- **Single counterpart memory per save**: The optional **Counterpart Memory** checkbox plants one perspective memory on the primary target character. For scenes with three or more witnesses who all need distinct memories, weave or edit each additional witness separately.

---

## Where it lives

- **`static/js/inspector/memory-view.ts`** - Unified Memory Weaver & Editor modal (`openWeaver`, `openWeaverAtTick`, `parseRelativeTime`, `stripEditorialLeakage`, `parseWeaverResponse`, `buildWeaverMessages`, live preview wiring)
- **`static/js/inspector/mind-view.ts`** - Memory Mind dashboard (`_memoryToolbarHtml` mode buttons, `#mind-timeline-svg` double-click-to-backdate, `_peopleHtml` `🤝 Weave Memory` button, `_recordAndEvidenceHtml` record & lived-log inspector)
- **`routes/memories.py`** - `POST /api/players/<name>/memories/context` (grounding + live relationship/contradiction preview), `POST /api/players/<name>/memories/entry`, and `POST /api/players/<name>/memories/entry/<id>` (`relationship_deltas`, `simulate_age_decay`, `derived_expectation`)
- **`engine/derive.py`** - `fold_emotions_into_profile` and `derive_person_profile` (multi-person `relationship_deltas` + `rel:<slug>` / `dim:delta` tag folding)
- **`engine/memory_dynamics.py`** - `ensure_dynamics`, `detect_contradiction`, `apply_decay`, `reinforce`
- **`tests/test_memory_weaver.py`** & **`tools/unit/test_memory_weaver.js`** - Backend and frontend unit test suites
- **`docs/design/memory-weaver-and-editor.md`** - Full architecture and schema specification
