---
type: index
area: docs
tags: [system/docs, topic/validation]
---

# Feature Ledger

**What this is:** the machine-readable half of the feature documentation — the
canonical list of **features** with their status and the note that documents
each one. It is the denominator for documentation coverage, and the file the
guards read.

**What it is not:** the guide. If you want "what can I do in VirtualWorld, and
where do I start", read [[Feature Map]]. This file is the ledger behind it: the
same features, with the honest columns.

A **feature** is something you do, interact with or use. A **mechanic** is how
it works: the operations and rules inside a feature. A **system** is the
implemented whole. The verbs (`go`, `take`, `attack`) are a feature's
*mechanics*, not features of their own.

**Rows are stable ids, not a sequence.** New rows are appended with the next
free number, so a citation of "row 51" never moves. (The original numbering ran
in-game 1–43 and editor 44–76; `Crafting` was appended as 77 rather than
inserted, for exactly this reason.)

Counts measured from this file: **78 features — 45 in a game, 33 in the editor.**

---

## In a game

| # | Feature | What you can do | Status | Docs |
|---|---|---|---|---|
| 1 | Look around | Read a room: light, temperature, sound, smell, who's here, what they are doing | wired | [[Rooms & Areas]] |
| 2 | Examine | Inspect a thing in detail; a container reveals *and* credits its contents | wired | [[Items Overview]] |
| 3 | Move | Traverse ways; size, load and ability gate what you can pass | wired | [[World Building/Movement\|Movement]] |
| 4 | Open / close | Doors, gates, lids — and ways that refuse to be hand-closed | wired | [[World Building/Movement\|Movement]] |
| 5 | Take / drop / give | Move items between the world, containers, and inventories | wired | [[Items Overview]] |
| 6 | Use / use on | `use X on Y` with typed targets; writing and inscriptions | wired | [[Items Overview]] |
| 7 | Talk / speak | Dialogue, and speech heard by others in the area | wired | [[NPC Behavior System]] |
| 8 | Whisper / shout | Audibility as a channel, not a radius | wired | [[NPC Behavior System]] |
| 9 | Attack / grapple | Combat resolution, hit dice, armour class, restraint | wired | [[Rules Engine/Combat System\|Combat System]] |
| 10 | Eat / drink | Consumption, nutrition, water, and the effects of both | wired | [[Items Overview]] |
| 11 | Sleep / rest | Restore over a span; rest quality | wired | [[Vitals System]] |
| 12 | Search / forage | Area forage tables, skill-gated draws, regrowth | wired | [[Search & Forage]] |
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
| 23 | Temperature | Body and environment temperature, clothing, equipment | wired | [[Environment/Temperature System\|Temperature System]] |
| 24 | Light | Ambient light, sources, seeing in the dark | wired | [[Environment/Light System\|Light System]] |
| 25 | Time & weather | Calendar, clock, forecast, and weather that reaches the world | wired | [[Environment/Time & Weather\|Time & Weather]] |
| 26 | Activities & states | Multi-tick activities; busy, unconscious, asleep | wired | [[Activities & States]] |
| 27 | NPC behaviour | Autonomous states: idle, forage, eat, flee, hide | wired | [[NPC Behavior System]] |
| 28 | **Background simulation** | What everyone off-screen does, and the coarse social layer over it | wired | [[Background Simulation]], [[design/Character Pursuits\|Character Pursuits]] |
| 29 | **Per-agent knowledge (fog of war)** | Per-character known set; a map that only shows what you have found | **unwired** — the *reveal* producer (`engine/fog.py`) still has no runtime caller; the player-facing surface it was blocking is row 43 | [[Per-Agent Knowledge (Fog of War)]] |
| 30 | Turn queue | Initiative, who acts when, the human's slot | wired | [[Turn Queue & Human Turns]] |
| 31 | The human turn | One turn, one card: the scene, your vitals, what you can do | wired | [[Turn Queue & Human Turns]] |
| 32 | Character art | Profile avatar + full-body portrait, per emotion | wired | [[Character Images & Expression Packs]] |
| 33 | The map | Painted map, graph, and levels layouts of the world | wired | [[Graph System]] |
| 34 | Narration | The prose you are told on a turn | wired | [[Narration System]] |
| 35 | LLM calls | Every character and narration call, and which provider served it | wired | [[LLM Providers]] |
| 36 | **The sky** | The world above you: time of day, date, moon phase, weather, and season | wired | [[Time & Weather]] |
| 37 | **Spectator mode** | Watch the simulation run without acting; the world updates itself | wired | [[Time & Weather]] |
| 38 | **Traversal abilities** | Walk, crawl, climb and jump as separate movement systems, each gated by ability and by the floor layer | wired | [[World Building/Movement\|Movement]] |
| 39 | **Auto-description** | Descriptions written for you when equipment or appearance changes | wired | [[Character Images & Expression Packs]] |
| 40 | **Taking an agent over** | Hand a character between simple behaviour, an LLM agent, and the human | wired | [[NPC Behavior System]] |
| 41 | **Memory pipeline** | What an agent's recall is built from, including embeddings over stored memory | wired | [[Memory System]] |
| 42 | **Prompt lens** | See exactly the context an agent would be given, with no LLM call | wired | [[LLM Providers]] |
| 43 | **Where you've been** | A map of the cells your character has actually walked, per scope | wired | [[Turn Queue & Human Turns]] |
| 77 | **Crafting** | Make, combine, split and teach: recipes, tools and results | wired | none |
| 78 | The Commons | Character messaging across distance: public posts, private groups and direct messages | wired | [[Gameplay/The Commons]] |

## In the editor

| # | Feature | What you can do | Status | Docs |
|---|---|---|---|---|
| 44 | Graph canvas | Lay out the world; drag, search, scope-filter, bulk-select | wired | [[Graph System]] |
| 45 | Map layout | Painted map pitch and scope offsets | wired | [[Graph System]] |
| 46 | Levels layout | Hierarchical layout by relation level | wired | [[Graph System]] |
| 47 | **WorldPainter** | Paint a world on a grid: 8 tools (Select, Paint, Erase, Move, Route, Feature, Area, Inspect), 3 modes (world/town/interior), 4 layers (biome, road, floor, climate) | wired | [[WorldPainter]] |
| 48 | Grid to graph | Compile cells into areas, ways, gateways, buildings | wired | [[Grid to Graph]] |
| 49 | Scopes | Nested world scopes, projection, manifest | wired | [[World Scopes]] |
| 50 | Node inspectors | 12 panels: area, item, character, way, memory, behaviours, lore, paperdoll, tags, conditions, traits, automation | wired | [[Inspector Panels]] |
| 51 | Way authoring | Create and edit ways, doors, connections, cardinals | wired | [[World Building/Ways\|Ways]] |
| 52 | Trigger / effect editor | Author triggers, conditions and effects on any node | wired | [[Triggers & Effects]] |
| 53 | **NL editor** | Describe a change in prose; see a plan before it is applied | wired | [[NL Editor]] |
| 54 | Expression pack editor | Per-emotion art slots, plus **Split sheet** for grid sheets | wired | [[Character Images & Expression Packs]] |
| 55 | Library | Browse and edit the content registry: items, characters, biomes, behaviours, traits | wired | [[Library System Overview]] |
| 56 | Tags | Tag queries across nodes, and tag-targeted triggers | wired | [[Tags System]] |
| 57 | Scenario creation | The create wizard and the text-to-scenario path | wired | [[ScenarioCreationGuide]] |
| 58 | Save / load | Scenario and app saves, autosave, rename | wired | [[Settings & Configuration]] |
| 59 | Settings | Engine config, every slider | wired | [[Settings & Configuration]] |
| 60 | Command palette | Jump to anything | wired | [[Rendering & UI Modules]] |
| 61 | Help centre | In-app help | wired | [[Rendering & UI Modules]] |
| 62 | Recent edits / undo | What changed, and undoing it | wired | [[Recent Edits & Undo]] |
| 63 | Validator & issues | Scenario lint, mismatches, authoring blockers | wired | [[Validator & Issues]] |
| 64 | **Event stream** | The turn-by-turn log with filters and search | wired | [[Event Stream]] |
| 65 | Export | Graph export, play-session log export (Markdown/plain/JSON/JSONL) | wired | [[Event Log Export]] |
| 66 | **Soak lab** | Automated long runs, live tuning, telemetry | wired | [[Soak Lab]] |
| 67 | **The human turn composer** | The structured card you answer a character's turn in: reply, JSON, and a free-text box | wired | [[Turn Queue & Human Turns]] |
| 68 | **Turn-based modes** | Sequential, random, or initiative (d20 + DEX), and simultaneous modes per room | wired | [[Turn Queue & Human Turns]] |
| 69 | **Agent overview** | Every agent at a glance, and the alert system that flags one that needs attention | wired | [[Rendering & UI Modules]] |
| 70 | **Action menu** | The verb menu for what you can do here; also `Ctrl+K` to jump to anything | wired | [[Rendering & UI Modules]] |
| 71 | **World lore** | Read the lore of a place, with tags gating who may access it | wired | [[Inspector Panels]] |
| 72 | **Entity generators** | Generate items, ways and areas from prose, then review before accepting | wired | [[NL Editor]] |
| 73 | **Library sync** | Push a node to the library and pull it back, in both directions | wired | [[Library System Overview]] |
| 74 | **Agent behaviour settings** | Per-agent behaviour and automation settings | planned | [[agent-behaviour-settings]] |
| 75 | **Graph settings** | Physics and layout settings for the graph view | planned | [[graph-settings]] |
| 76 | **Report a bug** | File what you are looking at as a bug task, with a screenshot and the DOM elements you picked | wired | [[Rendering & UI Modules]] |

---

## The one deliberate `unwired` row

**Per-agent knowledge (fog of war)** (row 29) is the single `unwired` row. The
code and the task tree both say it exists; nothing calls it. That is the state
this ledger exists to make visible — a feature nobody can reach looks exactly
like a quiet one.

## Rows 60–76 are code-evidence only

Each has a real code site behind it; none was exercised end to end. Read
`wired` on those rows as "a caller exists", not "a player reached it". Rows 1–59
are the trusted tier.

## Keeping this honest

- A feature with no note is allowed and reads `none`. Do not delete the line.
- `python tools/feature_index.py --check` fails when a new module's `@docs`
  names no feature here, and `--report` prints the join in both directions.
- Adding a feature? Append a row. The value of this file is that it is the
  denominator, and a denominator that only counts successes measures nothing.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Commands]], [[Emotion & Mood — Whole-System Analysis]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]], [[Patch Notes 2026-09-28]]

<!-- connected:end -->
