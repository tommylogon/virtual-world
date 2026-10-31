---
type: doc
tags: [surface/docs]
---

# Perception, Memory & The Director's Chair - 31 October 2026

Five days of work across the simulation engine, memory architecture, and scenario tooling. Three major systems change how you author and experience stories in VirtualWorld: characters now remember the past through realistic associative perception rather than keyword guessing, a new Directed Mode lets a human director step into an NPC's thought stream before they act, and long-form narrative text is protected against silent truncation.

---

## Associative Memory 3.0: Recalling what actually connects

Until now, memory retrieval was largely a flat keyword search over room names and whatever two dialogue lines happened to be last in the buffer. If someone stood in a kitchen holding a photograph of an old friend, their memories rarely connected the friend to the photo unless the exact string matched.

Memory Retrieval 3.0 replaces flat scoring with multi-facet perceptual cues:

- **Multi-facet perceptual cues:** When a character's turn begins, the retrieval engine builds a structured perceptual snapshot:
  - People present in the room (names and entity IDs).
  - Items held in inventory or sitting visibly in the room.
  - Spoken dialogue heard recently and own latest internal thought.
  - Active bodily needs (hunger, thirst, exhaustion).
  - Current emotional state.
- **Associative intersection surge:** Memories that link multiple active cues simultaneously (e.g. seeing Jake in the room while someone mentions tea) receive a multiplicative boost. True associative connections easily beat out random single-token noise.
- **Zero fake padding:** If nothing in memory relates to the current scene, the character recalls zero memories. We eliminated the legacy behavior of forcing the top three irrelevant memories into the prompt.
- **Open questions and suspicions:** Active unresolved questions (`category: "question"`) now live in their own dedicated prompt lane. When room entities or dialogue touch on a character's suspicion, their working theories surface automatically.
- **Dedicated Memory Model client:** You can now configure a separate, lightweight model in Settings specifically for memory reflections and extractions. Fast local models (such as small 2B models in LM Studio) run structured memory operations at 200+ tokens per second without tying up your primary story model.
- **AgentLens recall workbench:** Open the Agent Lens inspector to test memory recall interactively. You can type hypothetical dialogue lines or toggle simulated need states to preview exactly which memories win and read the scoring explanation.
- **Recall transparency & multi-signal breakdown:** Every recalled memory now carries its exact provenance across seven distinct channels (spatial proximity, social presence, conversational echo, emotional congruency with salience multipliers for intensity >= 6, bodily need drive, temporal recency, and semantic embedding).
- **Mind panel & Event Stream inspection:** Recalled memory chips in the Mind panel display signal badges and a full point breakdown (e.g. `[Match: 88%] 📍 Spatial (+35) · 👥 Social (+25) · 🥩 Need (+20) · 🧠 Semantic (+8)`). The Event Stream's `recalled: N memories` pill expands to show which memories were pulled into `=== I REMEMBER ===` and the primary trigger for each.
- **Negative knowledge (absence memories):** Characters now record and recall absence observations (`kind: "absence"`) for verified empty containers or cleared areas. These memories surface in `=== ALREADY KNOWN ===` to prevent repetitive re-searching, and automatically supersede when a new presence observation occurs.
- **Sleep consolidation:** During sleep and rest, routine episodic memories fade minor noise, while emotionally salient events (intensity >= 6 or importance >= 7) are reinforced and preserved.

---

## Directed Control & Scene Grounding

VirtualWorld has supported purely autonomous AI characters and direct human-controlled player characters. A third mode is now available for collaborative storytelling: **Directed Mode**.

- **The Director's Chair:** Set a character's controller to Directed. When their turn comes up, the AI character still generates its private thinking, emotional reaction, and proposed action. But instead of committing immediately, the turn opens in a director review composer.
- **Review and edit:** The human director can inspect the NPC's inner thoughts, tweak their proposed action text, adjust their speech, or hit **Reroll** to ask the model for an alternative take before committing the turn to the simulation.
- **Scene Context:** Scenarios can now author a live `scene_context` block holding a scene title, dramatic premise, and active narrative threads (e.g. "The anonymous note was slipped into Jake's locker before first period"). This grounds all acting characters in the current dramatic stakes without modifying their permanent character sheets.
- **Full, unclipped narrative recap:** The Human Turn panel and event recap feeds no longer truncate dialogue or actions at an arbitrary character limit. Multi-character scenes preserve complete sentences and background actions across turns.

---

## Provider Profiles & LLM Telemetry

Configuring local and cloud AI providers is now managed through persistent profiles:

- **Saved Provider Profiles:** Switch effortlessly between LM Studio, OpenRouter, Groq, Mistral, NVIDIA NIM, Google Gemini, and DeepSeek. Settings and base URLs persist safely in backend storage.
- **Native LM Studio Model Picker:** The model dropdown polls LM Studio directly for loaded models and reports real-time generation speeds.
- **OpenRouter Telemetry:** The LLM Inspector surfaces live token usage, inference latency, cost in USD, and provider endpoint routing for every generation.

---

## Millwood Scenario & Character Depth

The Millwood campaign has been expanded into a dense, itemized narrative environment:

- **Anchor room itemization:** Rooms across Millwood now feature physical props, containers, everyday objects, and interactive scenery authored for exploration.
- **Long-horizon character goals:** Core characters (Jake, Kayla, Kyrie, Sammy, Zoe, and newcomer Lulu) feature structured narrative goals, relational treaties, and multi-phase pursuit arcs stored in `data/library/character_goals/millwood_arcs.json`.
- **Tag library taxonomy:** Over 660 tag definitions in `data/library/tags/` have been audited, normalized, and expanded with clear examples and mechanical bindings.
- **Simulation philosophy docs:** Four foundational design essays have been added to `docs/virtualWorld/`, detailing character interiority, long-horizon pursuits, social entanglements, and simulation invariants.

---

## Engine Polish & UI Refinements

- **In-place graph edge diffing:** Updating edges in the graph view no longer causes the entire vis.js network to rebuild, freeze, or reset the camera view.
- **Custom UI dialogs:** Replaced native browser popups with styled in-app modal dialogs.
- **Decoupled trigger definitions:** Trigger condition trees (AND, OR, NOT) and action converters are now isolated in a dedicated shared module with full unit test coverage.
- **Single source of truth for characters:** Character definitions on graph nodes and player entity runtime models are unified under `character_store.py`, eliminating desynchronization between saves and runtime models.
- **Clean Code settings modal & default local memory worker:** Consolidated embedding configuration into the Connection tab, set the Dedicated Memory Worker to default enabled on localhost LM Studio (http://localhost:1234/v1, format lmstudio, model lmstudio-community/lfm3-1.7b), added a live latency diagnostic test button, and refactored the settings panel to a decoupled MVC architecture with a centralized CONFIG_SCHEMA and declarative data-config form bindings.
