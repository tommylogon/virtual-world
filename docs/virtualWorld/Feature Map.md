---
type: index
area: docs
---

# Feature Map

**What this is:** the canonical list of what a person can actually *do* in VirtualWorld — in a game
and in the editor — and whether a note documents it. It is the denominator for documentation
coverage, and it exists because there was no way to measure that before.

**Why it had to be written.** Three earlier attempts to measure coverage all failed, and the failures
are the reason this file is shaped the way it is:

- **module filenames are not features.** `attention.py` is a mechanism; nobody "uses attention". A
  per-module audit answers a question nobody asked.
- **`@powers` is prose, not a vocabulary.** 156 modules declare 266 *distinct* `@powers` strings. There
  is no controlled set to check a document against, so a heading noun-word pass over them returns
  `the`: 54, `and`: 24 — unusable.
- **note titles are not a map.** 76 prose notes, no feature → note mapping, so "is foraging
  documented?" could only be answered by grepping, and grepping says *mentioned*, not *documented*.

So: a feature is a thing a person sees or does. The unit is the feature, deliberately, because the
documentation is for people.

**How to read the columns.**

- **Status** uses the repo's vocabulary: `wired` (the runtime path reaches it), `authored` (content
  invokes it), `planned` (a design or task exists, no behaviour), `unwired` (a module exists and is
  tested, but nothing calls it — the most misleading state, and the reason this file exists).
- **Docs** is a link to the note that documents the feature, or **`none`** — which is a legitimate and
  load-bearing value. A coverage list that only lists documented features hides exactly the gaps it
  was built to expose.

Counts as of 2026-10-01, measured from this file (58 numbered rows, 10 of them `none`):
**58 features, 10 with no note.**

---

## In a game

| # | Feature | What you can do | Status | Docs |
|---|---|---|---|---|
| 1 | Look around | Read a room: light, temperature, sound, smell, who's here, what they are doing | wired | [[Rooms & Areas]] |
| 2 | Examine | Inspect a thing in detail; a container reveals *and* credits its contents | wired | [[Items Overview]] |
| 3 | Move | Traverse ways; size, load and ability gate what you can pass | wired | [[Doors & Connections]] |
| 4 | Open / close | Doors, gates, lids — and ways that refuse to be hand-closed | wired | [[Doors & Connections]] |
| 5 | Take / drop / give | Move items between the world, containers, and inventories | wired | [[Items Overview]] |
| 6 | Use / use on | `use X on Y` with typed targets; writing and inscriptions | wired | [[Items Overview]] |
| 7 | Talk / speak | Dialogue, and speech heard by others in the area | wired | [[NPC Behavior System]] |
| 8 | Whisper / shout | Audibility as a channel, not a radius | wired | [[NPC Behavior System]] |
| 9 | Attack / grapple | Combat resolution, hit dice, armour class, restraint | wired | [[Combat System]] |
| 10 | Eat / drink | Consumption, nutrition, water, and the effects of both | wired | [[Items Overview]] |
| 11 | Sleep / rest | Restore over a span; rest quality | wired | [[Vitals System]] |
| 12 | Search / forage | Area forage tables, skill-gated draws, regrowth | wired | **none** |
| 13 | Read / write | Readable items; write on a surface | wired | [[Items Overview]] |
| 14 | Wear / equip | Equipment slots, paperdoll, weight and bulk | wired | [[Equipment & Paperdoll]] |
| 15 | Timeskip | Skip a span: idle, leisure, search, explore, travel | wired | [[Turn Queue & Human Turns]] |
| 16 | Vitals & needs | Hunger, thirst, energy, warmth, social, entertainment, sanity | wired | [[Vitals System]] |
| 17 | Conditions | Data-driven conditions, evaluated and auto-sourced | wired | [[Conditions System]] |
| 18 | Traits | Trait model, treatments, conflicts | wired | [[Traits System]] |
| 19 | Skills | Skills, proficiency, growth by use | wired | [[Skills System]] |
| 20 | Emotion | Emotion model, reflection, residue | wired | [[Emotion & Affect System]] |
| 21 | Relationships | Per-character relationships and their deltas | wired | [[Relationships System]] |
| 22 | Memory | What a character remembers, and recall by need | wired | [[Memory System]] |
| 23 | Temperature | Body and environment temperature, clothing, equipment | wired | [[Temperature System]] |
| 24 | Light | Ambient light, sources, seeing in the dark | wired | [[Light System]] |
| 25 | Time & weather | Calendar, clock, forecast, and weather that reaches the world | wired | [[Time & Weather]] |
| 26 | Activities & states | Multi-tick activities; busy, unconscious, asleep | wired | [[Activities & States]] |
| 27 | NPC behaviour | Autonomous states: idle, forage, eat, flee, hide | wired | [[NPC Behavior System]] |
| 28 | **Background simulation** | What everyone off-screen does, and the coarse social layer over it | **unwired** | **none** |
| 29 | **Per-agent knowledge (fog of war)** | Per-character known set; a map that only shows what you have found | **unwired** | **none** |
| 30 | Turn queue | Initiative, who acts when, the human's slot | wired | [[Turn Queue & Human Turns]] |
| 31 | The human turn | One turn, one card: the scene, your vitals, what you can do | wired | [[Turn Queue & Human Turns]] |
| 32 | Character art | Profile avatar + full-body portrait, per emotion | wired | [[Character Images & Expression Packs]] |
| 33 | The map | Painted map, graph, and levels layouts of the world | wired | [[Graph System]] |
| 34 | Narration | The prose you are told on a turn | wired | [[Narration System]] |
| 35 | LLM calls | Every character and narration call, and which provider served it | wired | [[LLM Providers]] |

## In the editor

| # | Feature | What you can do | Status | Docs |
|---|---|---|---|---|
| 36 | Graph canvas | Lay out the world; drag, search, scope-filter, bulk-select | wired | [[Graph System]] |
| 37 | Map layout | Painted map pitch and scope offsets | wired | [[Graph System]] |
| 38 | Levels layout | Hierarchical layout by relation level | wired | [[Graph System]] |
| 39 | **WorldPainter** | Paint a world on a grid: 8 tools (Select, Paint, Erase, Move, Route, Feature, Area, Inspect), 3 modes (world/town/interior), 4 layers (biome, road, floor, climate) | wired | **none** |
| 40 | Grid to graph | Compile cells into areas, ways, gateways, buildings | wired | **none** |
| 41 | Scopes | Nested world scopes, projection, manifest | wired | [[World Scopes]] |
| 42 | Node inspectors | 12 panels: area, item, character, way, memory, behaviours, lore, paperdoll, tags, conditions, traits, automation | wired | [[Inspector Panels]] |
| 43 | Way authoring | Create and edit ways, doors, connections, cardinals | wired | [[Way Properties]] |
| 44 | Trigger / effect editor | Author triggers, conditions and effects on any node | wired | [[Triggers & Effects]] |
| 45 | **NL editor** | Describe a change in prose; see a plan before it is applied | wired | **none** |
| 46 | Expression pack editor | Per-emotion art slots, plus **Split sheet** for grid sheets | wired | [[Character Images & Expression Packs]] |
| 47 | Library | Browse and edit the content registry: items, characters, biomes, behaviours, traits | wired | [[Library System Overview]] |
| 48 | Tags | Tag queries across nodes, and tag-targeted triggers | wired | [[Tags System]] |
| 49 | Scenario creation | The create wizard and the text-to-scenario path | wired | [[ScenarioCreationGuide]] |
| 50 | Save / load | Scenario and app saves, autosave, rename | wired | [[Settings & Configuration]] |
| 51 | Settings | Engine config, every slider | wired | [[Settings & Configuration]] |
| 52 | Command palette | Jump to anything | wired | [[Rendering & UI Modules]] |
| 53 | Help centre | In-app help | wired | [[Rendering & UI Modules]] |
| 54 | Recent edits / undo | What changed, and undoing it | wired | **none** |
| 55 | Validator & issues | Scenario lint, mismatches, authoring blockers | wired | **none** |
| 56 | **Event stream** | The turn-by-turn log with filters and search | wired | **none** |
| 57 | Export | Graph export, play-session log export | wired | [[Event Log Export]] |
| 58 | **Soak lab** | Automated long runs, live tuning, telemetry | wired | **none** |

---

## The ten gaps

Features with no note. Each is real, reachable, and shipped — this is not a wishlist.

| Feature | Why it matters |
|---|---|
| Search / forage | 629 lines of engine, a biome-keyed data file, and four passing mentions — no note says what it does |
| Background simulation | 2827 lines across two modules; the string "backsim" appears **once** in the whole codebase, in a comment |
| Per-agent knowledge (fog) | the module is complete and tested; nothing calls it. A `done/` task hides this |
| WorldPainter | an entire editor with 8 tools, 3 modes and 4 layers, and no reference |
| Grid → graph | the largest file in the repo; a design note exists but no reference |
| NL editor | reachable from the left rail; the two tasks that shaped it are cancelled |
| Recent edits / undo | a user-facing safety feature with no note |
| Validator & issues | the thing that tells an author their scenario is broken |
| Event stream | on screen every turn; only its *export* is documented |
| Soak lab | a whole tool surface; only a telemetry design note exists |

## Keeping this honest

- A feature with no note is allowed and expected to read `none`. Do not delete the line.
- A feature that is `unwired` is the dangerous one: the code and the task tree both say it exists.
  The Status column is what makes that visible.
- `python tools/feature_index.py --check` fails when a new module's `@powers` names no feature here,
  and `--report` prints the join in both directions. **`@powers` and this map currently speak
  different languages**: 68 of 156 modules name a feature, 88 name none, and 32 features have no
  module naming them. The headers are written as gerund phrases ("keeping and restoring your world")
  and this map as noun phrases ("Save / load"), so the two only partly join. That gap is filed as
  task-664; the 88 are baselined so the gate is green today and ratchets from here.
- `python tools/js_module_index.py --check` also fails when an `@docs` target is a folder or a dead
  path. That guard was added with this map: **28 module headers pointed at a directory**
  (`docs/virtualWorld/Library System/` and friends) and now point at real notes, and two pointed at
  task files that had moved between status folders.
- The `@docs`/`@powers` contract is **front-end only**. The back end's 147 modules have no such guard
  — that is **task-576**, and **task-578** (a doc resolver route) has nothing to resolve against
  until it exists.
- Adding a feature? Add the row. The value of this file is that it is the denominator, and a
  denominator that only counts successes measures nothing.
