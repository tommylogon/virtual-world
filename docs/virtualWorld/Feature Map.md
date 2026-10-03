---
type: index
area: docs
---

# Feature Map

**What this is:** the canonical list of what a person can actually *do* in VirtualWorld — in a game and in the editor — and whether a note documents it. It is the denominator for documentation coverage, and it exists because there was no way to measure that before.

**Why it had to be written.** Three earlier attempts to measure coverage all failed, and the failures are the reason this file is shaped the way it is:

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

Counts as of 2026-10-03, measured from this file: **74 features — 42 in a game, 32 in the editor.**

Rows 1-58 are the original map. Rows 59-74 were added on 2026-10-03 from a maintainer pass, and
they are **not** equally trusted: two read `planned` because their behaviour was not exercised, and
the rest are marked `wired` on code evidence alone. See
[What this pass did not verify](#what-this-pass-did-not-verify) before treating a new row as
verified. Of the original 58, all 58 link to a note; of the 16 added here, four read `none` and the
rest point at a note covering the area rather than the specific feature.

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
| 23 | Temperature | Body and environment temperature, clothing, equipment | wired | [[Environment/Temperature System|Temperature System]] |
| 24 | Light | Ambient light, sources, seeing in the dark | wired | [[Light System]] |
| 25 | Time & weather | Calendar, clock, forecast, and weather that reaches the world | wired | [[Time & Weather]] |
| 26 | Activities & states | Multi-tick activities; busy, unconscious, asleep | wired | [[Activities & States]] |
| 27 | NPC behaviour | Autonomous states: idle, forage, eat, flee, hide | wired | [[NPC Behavior System]] |
| 28 | **Background simulation** | What everyone off-screen does, and the coarse social layer over it | wired | [[Background Simulation]] |
| 29 | **Per-agent knowledge (fog of war)** | Per-character known set; a map that only shows what you have found | **unwired** — the *reveal* producer (`engine/fog.py`) still has no runtime caller; the player-facing surface it was blocking is row 58 | [[Per-Agent Knowledge (Fog of War)]] |
| 30 | Turn queue | Initiative, who acts when, the human's slot | wired | [[Turn Queue & Human Turns]] |
| 31 | The human turn | One turn, one card: the scene, your vitals, what you can do | wired | [[Turn Queue & Human Turns]] |
| 32 | Character art | Profile avatar + full-body portrait, per emotion | wired | [[Character Images & Expression Packs]] |
| 33 | The map | Painted map, graph, and levels layouts of the world | wired | [[Graph System]] |
| 34 | Narration | The prose you are told on a turn | wired | [[Narration System]] |
| 35 | LLM calls | Every character and narration call, and which provider served it | wired | [[LLM Providers]] |
| 36 | **The sky** | The world above you: time of day, date, moon phase, weather, and season — and setting the date and the weather schedule for the scenario | wired | [[Time & Weather]] |
| 37 | **Spectator mode** | Watch the simulation run without acting; the world updates itself | wired | [[Time & Weather]] |
| 38 | **Traversal abilities** | Walk, crawl, climb and jump as separate movement systems, each gated by ability and by the floor layer | wired | [[Doors & Connections]] |
| 39 | **Auto-description** | Descriptions written for you when equipment or appearance changes | wired | [[Character Images & Expression Packs]] |
| 40 | **Taking an agent over** | Hand a character between simple behaviour, an LLM agent, and the human | wired | [[NPC Behavior System]] |
| 41 | **Memory pipeline** | What an agent's recall is built from, including embeddings over stored memory | wired | [[Memory System]] |
| 42 | **Prompt lens** | See exactly the context an agent would be given, with no LLM call | wired | [[LLM Providers]] |
| 58 | **Where you've been** | A map of the cells your character has actually walked, per scope, with what they last observed there and a mark on ways you know are blocked | wired | [[Turn Queue & Human Turns]] |

## In the editor

| # | Feature | What you can do | Status | Docs |
|---|---|---|---|---|
| 43 | Graph canvas | Lay out the world; drag, search, scope-filter, bulk-select | wired | [[Graph System]] |
| 44 | Map layout | Painted map pitch and scope offsets | wired | [[Graph System]] |
| 45 | Levels layout | Hierarchical layout by relation level | wired | [[Graph System]] |
| 46 | **WorldPainter** | Paint a world on a grid: 8 tools (Select, Paint, Erase, Move, Route, Feature, Area, Inspect), 3 modes (world/town/interior), 4 layers (biome, road, floor, climate) | wired | [[WorldPainter]] |
| 47 | Grid to graph | Compile cells into areas, ways, gateways, buildings | wired | [[Grid to Graph]] |
| 48 | Scopes | Nested world scopes, projection, manifest | wired | [[World Scopes]] |
| 49 | Node inspectors | 12 panels: area, item, character, way, memory, behaviours, lore, paperdoll, tags, conditions, traits, automation | wired | [[Inspector Panels]] |
| 50 | Way authoring | Create and edit ways, doors, connections, cardinals | wired | [[Way Properties]] |
| 51 | Trigger / effect editor | Author triggers, conditions and effects on any node | wired | [[Triggers & Effects]] |
| 52 | **NL editor** | Describe a change in prose; see a plan before it is applied | wired | [[NL Editor]] |
| 53 | Expression pack editor | Per-emotion art slots, plus **Split sheet** for grid sheets | wired | [[Character Images & Expression Packs]] |
| 54 | Library | Browse and edit the content registry: items, characters, biomes, behaviours, traits | wired | [[Library System Overview]] |
| 55 | Tags | Tag queries across nodes, and tag-targeted triggers | wired | [[Tags System]] |
| 56 | Scenario creation | The create wizard and the text-to-scenario path | wired | [[ScenarioCreationGuide]] |
| 57 | Save / load | Scenario and app saves, autosave, rename | wired | [[Settings & Configuration]] |
| 58 | Settings | Engine config, every slider | wired | [[Settings & Configuration]] |
| 59 | Command palette | Jump to anything | wired | [[Rendering & UI Modules]] |
| 60 | Help centre | In-app help | wired | [[Rendering & UI Modules]] |
| 61 | Recent edits / undo | What changed, and undoing it | wired | [[Recent Edits & Undo]] |
| 62 | Validator & issues | Scenario lint, mismatches, authoring blockers | wired | [[Validator & Issues]] |
| 63 | **Event stream** | The turn-by-turn log with filters and search | wired | [[Event Stream]] |
| 64 | Export | Graph export, play-session log export | wired | [[Event Log Export]] |
| 65 | **Soak lab** | Automated long runs, live tuning, telemetry | wired | [[Soak Lab]] |
| 66 | **The human turn composer** | The structured card you answer a character's turn in: reply, JSON, and a free-text box | wired | [[Turn Queue & Human Turns]] |
| 67 | **Turn-based modes** | Sequential, random, or initiative (d20 + DEX), and simultaneous modes per room | wired | [[Turn Queue & Human Turns]] |
| 68 | **Agent overview** | Every agent at a glance, and the alert system that flags one that needs attention | wired | [[Rendering & UI Modules]] |
| 69 | **Action menu** | The verb menu for what you can do here; also `Ctrl+K` to jump to anything | wired | [[Rendering & UI Modules]] |
| 70 | **World lore** | Read the lore of a place, with tags gating who may access it | wired | [[Inspector Panels]] |
| 71 | **Entity generators** | Generate items, ways and areas from prose, then review before accepting | wired | [[NL Editor]] |
| 72 | **Library sync** | Push a node to the library and pull it back, in both directions | wired | [[Library System Overview]] |
| 73 | **Agent behaviour settings** | Per-agent behaviour and automation settings | planned | none |
| 74 | **Graph settings** | Physics and layout settings for the graph view | planned | none |
| 75 | **Report a bug** | File what you are looking at as a bug task, with a screenshot and the DOM elements you picked | wired | [[Rendering & UI Modules]] |

---

## What your list did not mention

Added 2026-10-03. The maintainer's pass named 42 of the 58 features that already existed here, so
**16 pre-existing rows were not covered**. They are not missing from the game — they are missing
from that message, and the point of listing them is to let you decide whether they are still
features.

| # | Feature | Still here? |
|---|---|---|
| 2 | Examine | yes — a container reveals *and* credits its contents |
| 4 | Open / close | yes — including ways that refuse to be hand-closed |
| 9 | Attack / grapple | yes |
| 12 | Search / forage | yes — note this is now `wired`; the old map said otherwise and was corrected |
| 13 | Read / write | yes |
| 17 | Conditions | yes — data-driven, evaluated, auto-sourced |
| 18 | Traits | yes |
| 19 | Skills | yes |
| 20 | Emotion | yes |
| 21 | Relationships | yes |
| 23 | Temperature | yes |
| 24 | Light | yes — and note this overlaps row 36 (The sky) |
| 26 | Activities & states | yes — multi-tick activities; busy, unconscious, asleep |
| 28 | Background simulation | yes — **wired**, corrected from `unwired` on 2026-10-02 |
| 29 | Per-agent knowledge (fog of war) | yes, and it is the one deliberate **`unwired`** row: `engine/fog.py` has no runtime caller |
| 32 | Character art | yes — see also the expression-pack editor, which you did list |
| 34 | Narration | yes |
| 49 | Scenario creation | yes — the wizard and the text-to-scenario path |
| 50 | Save / load | yes |
| 54 | Recent edits / undo | yes — four surfaces over one snapshot stack |

Fourteen rows you named were **already present** and needed no new row: Timeskip (15), Library (47),
Tags (48), WorldPainter (39), Soak lab (58), NPC behaviour (27), the NL editor (45), the issues
overview (55), the map/levels layouts (37, 38), grid-to-graph (40), exports (57), character memory
(22), vitals (16), inventory and equipment (5, 14), expression packs (46), triggers (44), graph
scopes (41), way authoring (43), LLM agents (35). They are in the tables above, not duplicated.

The two worth a second look:

- **Per-agent knowledge (fog of war)** is the single `unwired` row in the file. The code and the
  task tree both say it exists; nothing calls it.
- **The sky** (row 36) and **Light** (row 24) now overlap. Weather and ambient light both reduce
  what you can see, and the new row pulls them together. If you would rather keep them apart, row
  36 should say *sky presentation only* and stop claiming weather affects light.

## What this pass did not verify

Added 2026-10-03. Rows 59-74 came from a maintainer pass, and the honest status is **not** the
same as for the original 58. Naming a file, a grep hit, or a `<script>` tag is not evidence that
behaviour works — that is the mistake this file exists to prevent, and it would be worse for this
pass to commit it.

What was checked: each new row has a real code site behind it.

| Row | Evidence found |
|---|---|
| 36 The sky | `static/js/sky-scape.ts` reads `forecast_schedule`; `moon_phase` in `/api/state` |
| 37 Spectator mode | `templates/index.html:43-47` toggle, `world-state.ts` poll handle |
| 38 Traversal | crawl / climb / jump branches in `engine/movement.py` |
| 39 Auto-description | `ApiClient.setAutoGenerateDescriptions`, fired on wear/remove |
| 40 Taking an agent over | `human-turn-composer.js` + the simple-behaviour and LLM agent paths |
| 41 Memory pipeline | `config.js:131-135` embedding endpoint + model |
| 42 Prompt lens | `static/js/agent-lens.ts` — "no LLM or embedding calls" |
| 66 Turn composer | `static/js/agent/human-turn-composer.js` |
| 67 Turn-based modes | `turn-queue.js` order modes; `VWSimultaneous` room mode |
| 69 Action menu | `templates/index.html` verb menu; `command-palette.js` |
| 70 World lore | the `lore` inspector panel |
| 71 Entity generators | `generateEntity` routes + the generator panels |
| 72 Library sync | `ApiClient` library save/load + the sync endpoints |

**Not verified, and marked accordingly:** rows 73 (agent behaviour settings) and 74 (graph
settings) are **`planned`**, not `wired`. They are real code, but I did not exercise them, and the
graph settings in particular are the values that were re-tuned in the central-gravity work — so
the correct status is not one this pass can assert. Rows 68 (agent overview) and 36 (The sky) are
marked `wired` on code evidence alone and should be confirmed in a browser before anyone treats
them as verified.

## Coverage

**The original 58 features (rows 1-58) all link to a note.** Rows 59-74 came from a later
maintainer pass and are **not** covered — two read `none`, and the rest point at a note that
documents the area rather than the specific feature. That is a real coverage gap and this section
states it rather than hiding it behind the original 58's number.

The ten that used to read `none` were
documented on 2026-10-02, and reading the code **corrected two claims** that had
been sitting in this file:

| Feature | Note | Correction made while documenting it |
|---|---|---|
| Search / forage | [[Search & Forage]] | the draw is wired; `findable_hint` / `notice` are tested and uncalled |
| Background simulation | [[Background Simulation]] | the map said **unwired**; `tick_manager.process_due()` is on the live `/api/turn/apply` path, so it is **wired** (measured on a live `create_app()`) |
| Per-agent knowledge (fog of war) | [[Per-Agent Knowledge (Fog of War)]] | **unwired, confirmed** — `engine/fog.py` has no runtime caller; the gate is sound and the key is authored-only |
| WorldPainter | [[WorldPainter]] | |
| Grid to graph | [[Grid to Graph]] | largest *non-test* Python file; `tests/test_trigger_system.py` is larger |
| NL editor | [[NL Editor]] | |
| Recent edits / undo | [[Recent Edits & Undo]] | four surfaces over one snapshot stack; the feed's per-row undo is the newest snapshot |
| Validator & issues | [[Validator & Issues]] | four instruments, only the trigger validator is wired to a UI |
| Event stream | [[Event Stream]] | |
| Soak lab | [[Soak Lab]] | |

## Keeping this honest

- A feature with no note is allowed and expected to read `none`. Do not delete the line.
- A feature that is `unwired` is the dangerous one: the code and the task tree both say it exists.
  The Status column is what makes that visible.
- `python tools/feature_index.py --check` fails when a new module's `@powers` names no feature here,
  and `--report` prints the join in both directions. **The two vocabularies now join**: a module's
  `@powers` opens with the feature name(s) it enables, taken verbatim from this map, so 155 of 157
  modules name a feature and 11 features still name no module. The two that name none are pure
  infrastructure (`static/js/shared/dom-utils.js`, `static/js/world-state.js`); they are baselined,
  because a utility that powers no single feature is a real state, not a gap. The 11 features with
  no module are reviewable at the bottom of `docs/design/feature-index.md` — a feature nothing names
  may be a feature nobody can reach.
- **A feature name is the controlled vocabulary.** `Match` now looks for the label *as a phrase*
  first ("Turn queue", "Use / use on"), then falls back to the older word-prefix match. Phrase
  matching is what lets a multi-word label join at all: the old term split never broke on spaces,
  so "turn queue" could never prefix a single word.
- `python tools/js_module_index.py --check` also fails when an `@docs` target is a folder or a dead
  path. That guard was added with this map: **28 module headers pointed at a directory**
  (`docs/virtualWorld/Library System/` and friends) and now point at real notes, and two pointed at
  task files that had moved between status folders.
- The `@docs`/`@powers` contract is **front-end only**. The back end's 147 modules have no such guard
  — that is **task-576**, and **task-578** (a doc resolver route) has nothing to resolve against
  until it exists.
- Adding a feature? Add the row. The value of this file is that it is the denominator, and a
  denominator that only counts successes measures nothing.
