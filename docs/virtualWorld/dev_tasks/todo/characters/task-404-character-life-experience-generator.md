---
type: task
status: todo
area: characters
priority: high
related: [task-403, task-457, bug-519]
wiki: "[[Memory System]]"
---

# task-404: Character life experience authoring and import

**Filed:** 2026-09-17  
**Reframed:** 2026-10-15

<!-- deps:start -->
**Related:** [[task-403-unified-agent-memory-and-knowledge]], [[task-457-character-nodes-are-the-canonical-character-record-human-agent-simple-npc]], [[bug-519-editorial-rewrite-notes-are-stored-inside-character-memories-so-a-character-recalls-its-own-drafting-notes]]
<!-- deps:end -->

## What

Give a character a substantial, emotionally grounded past that can influence
their existing memories and behavior. This is an offline authoring/import
workflow. It does not simulate a second life beside VirtualWorld or add another
place to store memories.

## Source of truth and boundaries

- Runtime memories remain on `Player.memories`. Scenario-authored starting
  memories enter through `preconceived_knowledge.memories` and the existing
  `AgentMind.load_preconceived()` path from task-403.
- Character wants belong to the existing GIMP goal records. MOSIAC reads those
  records as runtime context; it is not another motivation store. See
  [[Character Pursuits]] and [[GIMP]].
- Authored personality and character description remain on the character node;
  private memories, goals, and runtime state remain on Player, following
  task-457's ownership boundary.
- Event tables and a seeded generator may be authoring inputs. Do not persist a
  parallel `LifeExperience` collection, `diary_entries`, emotional-state
  snapshot, fear/hope/trauma store, or external graph in the running game.
- Generate first-person experience records using fields the existing memory
  loader supports. Any location or entity reference must resolve to an actual
  world node. Convert other desired effects only through an existing GIMP,
  memory, relationship, or character-definition field; omit unsupported data
  instead of inventing a second model.

## Aura/Diary reference checked 2026-10-15

The local reference checkout at `F:\AI\Aura\Diary` was at commit `a551328`
(2026-10-11, “offline simulation mode, event forge API, and decision-loop
fixes”). That update added offline event generation/review, stable event IDs
and chains, duplicate checks, age-aware choices, outcome tiers, seeded runs,
and JSON export. Its export
`Diary/exports/anna_anjou_20261011_191821.json` contains 77 events, 2
relationships, 1 location, 8 milestones, and 77 emotional-trajectory entries.
Event records include `event_id`, `date`, `age_days`, `raw_memory`,
`emotional_impact`, `choice_made`, `outcome_text`, `involved_persons`, and
`location_id`.

Reuse the useful authoring ideas: structured event choices, reproducible
outcomes, emotional grounding, and first-person memories. Treat this checkout
and export as reference data, not a runtime dependency or a second source of
truth. Before importing an event, review it as character-authored content and
resolve every referenced person and location against VirtualWorld's existing
scenario.

## How

1. Define a small event vocabulary and a deterministic seed contract for an
   offline generator or importer.
2. Emit a VirtualWorld scenario-player `preconceived_knowledge` block whose
   memories use the existing memory fields. Preserve the lived experience in
   first-person text; keep event-selection metadata in the authoring input
   unless an existing memory field can represent it.
3. For an Aura/Diary export, map only verified fields. Unresolved names and
   locations must be reported for author review, not converted into invented
   nodes or relationships.
4. Load the resulting scenario through the existing task-403 bootstrap. Do not
   add a new loader, memory index, persona, or biography panel.

## Acceptance

- Generating twice with the same inputs and seed yields the same authored
  memory payload.
- Generated/imported experiences are first-person memories stored in the
  existing Player memory collection after scenario load; loading twice does
  not duplicate them.
- Memory locations and entity references either resolve to real scenario node
  IDs or are omitted with a clear authoring error.
- A character's wants are represented only through existing GIMP goals when
  explicitly authored; the generator does not create a separate hopes/fears/
  motivation store or let MOSIAC decide actions.
- Existing character node properties and Player-owned private state continue
  to follow task-457's ownership boundary.
- The Diary importer reports unsupported or unresolved fields and does not
  silently drop, fabricate, or persist a second representation of an event.

## Steps to verify

1. Load generated/imported memories through the existing task-403 scenario path.
   - expected: records land in the character's existing Player memory store
     without duplicates.
   - observed: not run; implementation remains open.
2. Follow the intended browser path below when the generator/importer is
   available in a scenario.
   - expected: generated experience is visible and usable through the existing
     Mind/Memory surface.
   - observed: not run; this card records the acceptance path.

## Browser UI and intended live verification

Intended UI home: Character Inspector → 🧠 Mind → Memories; any authored GIMP
goal appears in the existing Goals section.

Current availability: the Mind and Memories surfaces exist; this generator and
import workflow are not implemented.

Live steps when available:

The author-facing home for generated experience is the existing character
Inspector's **🧠 Mind** panel, **Memories** tab. Show each memory through the
same memory list and detail view as other Player memories. If an authored goal
is also present, it belongs in the existing Mind tab's Goals section. Do not
add a separate backstory, persona, or memory screen. Missing visibility in this
panel is an acceptance failure even if the JSON or API payload is correct.

1. Open the generated test scenario from **Scenario Manager** and select the
   character in the graph.
2. Open **🧠 Mind → Memories**; locate a generated/imported experience, select
   it, and inspect its full text and memory details.
   - expected: first-person experience appears in the ordinary memory UI; any
     authored goal appears in the existing Goals section.
3. Reload the scenario and inspect the same character again.
   - expected: the memory remains visible once, with no duplicate on reload.
4. Inspect `/api/state` for the same character's Player memories and compare the
   selected record with the panel. Then trigger a normal character decision in
   the scenario.
   - expected: the existing memory/prompt path can use the experience; no new
     memory collection or world node was created.

These are required UI acceptance steps for the implementation. This section
defines intended access and live acceptance; it is not a claim that planned UI
exists or works today. No browser run is recorded for this card.

## Non-goals

- Running Aura/Diary or its graph database inside VirtualWorld.
- Real-time backstory simulation during play.
- Creating a second memory, emotion, goal, or persona store.
- Inferring world facts from prose or adding nodes for unresolved references.

## Files

- `tools/` authoring/import workflow (new, if needed)
- Event authoring data for the generator (new, if needed)
- Existing scenario player data using `preconceived_knowledge.memories`
- `tests/` only for the generator/importer mechanism and its task-403 payload
  contract
