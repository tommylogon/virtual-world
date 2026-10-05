---
type: doc
tags: [system/docs]
---

# VirtualWorld Wiki

This is the Obsidian vault for **VirtualWorld** — a Flask + JS text-based game engine for AI beings. This wiki documents every system, how it works, how it's wired, and where the code lives.

> **Repo**: this vault lives inside the game repo, under `docs/virtualWorld/`.  
> **Code conventions**: [`AGENTS.md`](../../AGENTS.md) at the repo root - layout, commands, testing baseline, and known gotchas.  
> **Design specs**: `docs/superpowers/specs/`  
> **Code map**: `docs/design/js-module-index.md` — what each front-end module contributes (generated).

---

## [[Feature Map|🎮 Feature Map]]

| Doc | What it covers |
|---|---|
| [[Feature Map\|Feature Map]] | **Start here for "can I do X?"** Every user-facing feature in a game and in the editor — **76 of them**, each with its status and the note that documents it. It is the denominator for documentation coverage |
| [[Features/Features Overview\|Features Overview]] | One page per feature row: what it is, how it works, where it lives, what it connects to. The entry points; the deep docs stay the deep docs |

---

## [[History|📜 History]]

| Doc | What it covers |
|-----|---------------|
| [[History\|History]] | The whole lineage: the 2025 Aura/APSE origins, the 2026-02-21 monorepo reorg, the July 2026 build-out and modularization, the 2026-08-26 public split, and how to re-derive any of it from git |
| [[Patch Notes 2026-08-22 to 2026-09-22\|Patch Notes]] | The last 30 days written to be shared cold: time as a timeframe, the background tier, the identity refactor, one copy of every truth, structures, and the bugs killed |
| [[Patch Notes 2026-09-28\|Patch Notes 2026-09-28]] | Fog-of-war reveal, traits v2, production surfaces, and the doc tooling pass |
| [[Patch Notes 2026-09-30\|Patch Notes 2026-09-30]] | Scope-tree work, soak findings, UI restructure |
| [[Patch Notes 2026-10-03\|Patch Notes 2026-10-03]] | The human-turn composer and narration alignment |

## [[Roadmap|🗺️ Roadmap]]

| Doc | What it covers |
|-----|---------------|
| [[Roadmap\|Roadmap]] | Where the world is going, in what order, and why: the three rules that set priority, the WorldPainter epic in flight, the simulation-contract debt, and the scale work that follows |
| [[Roadmap-core-systems\|Roadmap-core-systems]] | The core-systems track beneath the main roadmap |

## [[Simulation Model|🧭 Core Model]]

| Doc | What it covers |
|-----|---------------|
| [[Simulation Model\|Simulation Model]] | **Start here.** One entity at four processing levels (soak NPC / simple NPC / agent / human), cognition refines but never creates capability, attention-bounded scale, a turn as a *timeframe* filled by an action flow, survival by slack and emptiness rather than a drain rate, routine over hunt |

## [[World Building/Rooms & Areas|🏠 World Building]]

| Doc | What it covers |
|-----|---------------|
| [[World Building/Rooms & Areas\|Rooms & Areas]] | Area nodes, environment properties, descriptions per light level, area concept |
| [[World Building/Doors & Connections\|Doors & Connections]] | Way nodes, 6 states, connections, hidden doors, unlocking, auto-close, pass_message |
| [[World Building/Graph System\|Graph System]] | WorldGraph, Node/Edge dataclasses, 5 node types, 7 edge types, serialization, derived layout (orbit, levels, per-node physics) |
| [[World Building/World Scopes\|World Scopes]] | Scope hierarchy and manifest, per-scope projection, unmade scopes, deterministic generation recipes |
| [[World Building/WorldPainter\|WorldPainter]] | Paint a world on a grid: 8 tools, 3 modes, 4 layers |
| [[World Building/Grid to Graph\|Grid to Graph]] | Compile painted cells into areas, ways, gateways, buildings |
| [[World Building/Way Properties\|Way Properties]] | The full way-property set, generated from the single source of truth |

## [[Characters/Characters Overview|🧑 Characters]]

| Doc | What it covers |
|-----|---------------|
| [[Characters/Characters Overview\|Characters Overview]] | Player class, 3 character types, import/export, registry, library format |
| [[Characters/Traits System\|Traits System]] | Trait definitions, library format, how traits modify gameplay |
| [[Characters/Skills System\|Skills System]] | Skill checks, progression, action resolution, combat integration |
| [[Characters/Vitals System\|Vitals System]] | HP, energy, hunger, thirst, sanity, decay per **game minute**, Sanity sources, Entertainment novelty, death, ghost mode |
| [[Items & Inventory/Equipment & Paperdoll\|Equipment & Paperdoll]] | Per-character generated equipment lists by slot, worn/carried effects, weight and bulk |
| [[Characters/NPC Behavior System\|NPC Behavior System]] | Simple NPCs, behavior types, action intervals (game minutes), the background tier, LLM agent vs scripted |
| [[Characters/Relationships System\|Relationships System]] | Closeness model, the one mutation path, bands, what moves it, background social interactions, labels, grapple modifier |
| [[Characters/Emotion & Affect System\|Emotion & Affect System]] | Multi-dimensional affect map, semantic emotion mapping, mental-vital coupling, relationship valence, self- & social-recall re-feel |
| [[Emotion & Mood — Whole-System Analysis\|Emotion & Mood — Whole-System Analysis]] | **Survey of the whole subsystem**: the two coexisting emotion models, the six vocabularies (7 / 11 / 12 / 36 / 70 / ~50), the four copies that can diverge, and what contradicts what |
| [[Characters/Character Images & Expression Packs\|Character Images & Expression Packs]] | Profile + full-body art per emotion or action (SillyTavern-style pack), upload/remove API, resolver, library round-trip, avatar-by-emotion |
| [[Characters/Activities & States\|Activities & States]] | Multi-tick activities; busy, unconscious, asleep |
| [[Characters/Background Simulation\|Background Simulation]] | What everyone off-screen does, and the coarse social layer over it |

## [[Gameplay/Turn Queue & Human Turns|🎲 Gameplay]]

| Doc | What it covers |
|-----|---------------|
| [[Gameplay/Turn Queue & Human Turns\|Turn Queue & Human Turns]] | Whose turn it is, the scene-first human turn panel, guest speech, and what the world does while it waits |
| [[Gameplay/Character Spatial Position\|Character Spatial Position]] | Where every character is, per scope, and how that resolves on the map |
| [[Gameplay/Search & Forage\|Search & Forage]] | Area forage tables, skill-gated draws, regrowth |
| [[Gameplay/Per-Agent Knowledge (Fog of War)\|Per-Agent Knowledge (Fog of War)]] | Per-character known set; a map that only shows what you have found — the one deliberately `unwired` row |

## [[Items & Inventory/Items Overview|📦 Items & Inventory]]

| Doc | What it covers |
|-----|---------------|
| [[Items & Inventory/Items Overview\|Items Overview]] | Item class, states, actions, placement, containers, matching, locked_with |
| [[Items & Inventory/Inventory\|Inventory]] | Edge model, take/drop, context menus, API client, weight system |
| [[Items & Inventory/Equipment & Paperdoll\|Equipment & Paperdoll]] | 13 equipment slots, paperdoll grid, equipping, LLM appearance gen |
| [[Items & Inventory/Item States & Toggleables\|Item States & Toggleables]] | Toggleable items, active effects, room modification, drain per tick |
| [[Items & Inventory/Item & Action Model\|Item & Action Model]] | The item/action data model in depth — verbs, typed targets, `use_on`, inscriptions |

## [[Environment/Light System|🌡️ Environment]]

| Doc | What it covers |
|-----|---------------|
| [[Environment/Light System\|Light System]] | 0-100 scale, light levels, restrictions per level, sanity decay, ghost immunity |
| [[Environment/Temperature System\|Temperature System]] | Area temperature, heat propagation (status), effects on vitals |
| └ [[Environment/Temperature/Body Temperature\|Body Temperature]] | Per-player core temp vital, separate from room temp |
| └ [[Environment/Temperature/Environment Temperature\|Environment Temperature]] | Room `environment.temperature` property, defaults |
| └ [[Environment/Temperature/Equipment & Temperature\|Equipment & Temperature]] | `insulation` property, how gear shifts effective ambient temp |
| └ [[Environment/Temperature/Trigger Integration\|Trigger Integration]] | `temperature_below` / `temperature_above` trigger conditions |
| └ [[Environment/Temperature/UI & Display\|UI & Display]] | Temp vital bar, display ranges and formatting |
| [[Environment/Time & Weather\|Time & Weather]] | Tick advancement, in-game clock, day/night cycle status, weather status |

## [[Rules Engine/Triggers & Effects|⚙️ Rules Engine]]

| Doc | What it covers |
|-----|---------------|
| [[Rules Engine/Triggers & Effects\|Triggers & Effects]] | Trigger types, effect types, trigger editor, conditions, multi-effect |
| [[Rules Engine/Combat System\|Combat System]] | Turn-based combat, damage, initiative, weapon system, death |
| [[Rules Engine/Conditions System\|Conditions System]] | Conditions, application/removal/ticking, library, UI badges |
| [[Rules Engine/Trait & Condition System (Design)\|Trait & Condition System (Design)]] | The v2 trait/condition design — how traits, conditions and their treatments compose |

## [[Library System/Library System Overview|📚 Library System]]

| Doc | What it covers |
|-----|---------------|
| [[Library System/Library System Overview\|Library System Overview]] | Directory structure, per-file format, load/save helpers, import mechanics, API |
| [[Library System/Tags System\|Tags System]] | Tag library, what tags do (container/furniture/heat/light), stranger labels from character tags, tag API |
| [[Library System/Domain & Role Tags\|Domain & Role Tags]] | The tag vocabulary that marks who and what something is |
| [[Library System/Library 2.0 - Unified Library Design\|Library 2.0 Design]] | The unified-library design: one registry, typed entries, the diff that shows what changed |
| [[Library System/diff-modal\|diff-modal]] | The diff surface the library uses to show what a save or push actually changed |

## [[AI & Narration/LLM Providers|🤖 AI & Narration]]

| Doc | What it covers |
|-----|---------------|
| [[AI & Narration/LLM Providers\|LLM Providers]] | Provider configs, API keys, rate limiting, retry logic, fallback models |
| [[AI & Narration/Agent Engine\|Agent Engine]] | Agent loop, prompt building, turn queue, action validation, simple NPC diff |
| [[AI & Narration/Turn-Based System\|Turn-Based System]] | Off/sequential/random/initiative modes, turn queue, tick application on wrap |
| [[AI & Narration/Memory System\|Memory System]] | Memory types, importance, retrieval, context window, editor, generator, `memory_emotions` |
| [[AI & Narration/Memory Dynamics\|Memory Dynamics]] | How memory became dynamic: activation, confidence, reinforcement, non-uniform decay, belief-category memories, contradiction links, and the structured recall block |
| [[AI & Narration/Narration System\|Narration System]] | 3 narration modes, room/action narration, emote command |

## [[UI & Settings/Inspector Panels|🖥️ UI & Settings]]

| Doc | What it covers |
|-----|---------------|
| [[UI & Settings/Inspector Panels\|Inspector Panels]] | 10 inspector sub-views, dispatch by node type, auto-refresh, context menus |
| [[UI & Settings/Settings & Configuration\|Settings & Configuration]] | Backend routes, ConfigManager, toggleable settings, profile system, save/load |
| [[UI & Settings/Engine Config\|Engine Config]] | Task-304: server-side engine tuning constants (sound/heat/light) editable in the Settings menu, persisted to `data/engine_config.json`, applies live |
| [[UI & Settings/Rendering & UI Modules\|Rendering & UI Modules]] | lit-html via `window.Lit`, the classic-vs-deferred-module bootstrap race + fix, graph module split, file-size rule |
| [[UI & Settings/Event Log Export\|Event Log Export]] | Markdown event-log export, filter-respecting rows, Turn vs tick labeling, stream formatting + emote ordering |
| [[UI & Settings/Event Stream\|Event Stream]] | The turn-by-turn log with filters and search |
| [[UI & Settings/NL Editor\|NL Editor]] | Describe a change in prose; see a plan before it is applied |
| [[UI & Settings/Recent Edits & Undo\|Recent Edits & Undo]] | What changed, and undoing it — four surfaces over one snapshot stack |
| [[UI & Settings/Validator & Issues\|Validator & Issues]] | Scenario lint, mismatches, authoring blockers |
| [[UI & Settings/Soak Lab\|Soak Lab]] | Automated long runs, live tuning, telemetry |

## ✍️ Scenario & authoring

| Doc | What it covers |
|-----|---------------|
| [[ScenarioCreationGuide\|Scenario Creation Guide]] | The create wizard and the text-to-scenario path |
| [[Scenario Catalogue\|Scenario Catalogue]] | What the shipped scenarios are and what each one is for |
| [[Scenario Workflows & UI Audit\|Scenario Workflows & UI Audit]] | The authoring workflows, audited against the UI as it actually behaves |
| [[Templates/trigger-effect-template-items\|Trigger/effect template]] | The authoring template for trigger and effect definitions |

## ✅ Testing & verification

| Doc | What it covers |
|-----|---------------|
| [[testing/manual-test-plan\|Manual test plan]] | The scripted-by-hand pass over a running world |
| [[UI & Settings/Soak Lab\|Soak Lab]] | Long automated runs with live tuning and telemetry |

## 🗺️ World data & reviews

| Doc | What it covers |
|-----|---------------|
| [[World Building/Millbrook Falls Town Map\|Millbrook Falls Town Map]] | The painted town map data and how it maps onto the graph |
| [[World Building/Generated Scenario Review (2026-08)\|Generated Scenario Review (2026-08)]] | What the generator produced, and what a human had to fix |
| [[design/Character Pursuits\|Character pursuits]] | How goals, pursuits, schedules, short-term plans, and activities fit together |
| [[Welcome\|Welcome]] | Start here if you have never run the engine |

---

## 📋 Active Tasks

> **📥 Todo** · **🔧 In Progress** · **👀 Review** · **✅ Done** — each is a folder under `dev_tasks/`
>
> Tasks live in the `dev_tasks/` folder in this vault. Each task file is an `.md` with notes, design decisions, and code references. Tasks are grouped by category (characters, environment, items, gameplay, triggers, graph, ui, prompting, testing, refactor) within each status folder. The folder-move workflow: `todo/` → `inprogress/` → `review/` → `done/`.

---

## Quick Links

- **API health check**: `GET /api/health` → `{"status":"ok"}`
- **API restart**: `GET /api/restart` — resets world from `world_template.json`
- **Game root**: `http://127.0.0.1:4444`
- **Run the app**: `python app.py`
- **Tests**: `python -m pytest -q` — baseline is ~3,239 passing with ~60 known pre-existing failures (see `AGENTS.md`); targeted run: `python -m pytest tests/test_<name>.py -q`
- **JS lint / typecheck**: `npm run lint` · `npm run typecheck`
- **Export-log lint**: `node tools/log_lint.cjs data/exports/<log>.txt` (or `npm run loglint -- <path>`)
- **Dev tasks**: `python tools/tasks.py list` · `python tools/tasks.py validate`

*Last updated: 2026-10-05*

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Emotion & Mood — Whole-System Analysis]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]], [[Patch Notes 2026-09-28]], [[Patch Notes 2026-09-30]]

<!-- connected:end -->
