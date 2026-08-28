# VirtualWorld Wiki

This is the Obsidian vault for **VirtualWorld** — a Flask + JS text-based game engine for AI beings. This wiki documents every system, how it works, how it's wired, and where the code lives.

> **Main repo**: `F:\AI\viwo\virtual-world`  
> **Code conventions**: See `AGENTS.md` (referenced here but not present in this checkout)  
> **Design specs**: `docs/superpowers/specs/`

---

## [[World Building/Rooms & Areas|🏠 World Building]]

| Doc | What it covers |
|-----|---------------|
| [[World Building/Rooms & Areas\|Rooms & Areas]] | Area nodes, environment properties, descriptions per light level, area concept |
| [[World Building/Doors & Connections\|Doors & Connections]] | Way nodes, 6 states, connections, hidden doors, unlocking, auto-close, pass_message |
| [[World Building/Graph System\|Graph System]] | WorldGraph, Node/Edge dataclasses, 5 node types, 7 edge types, serialization |

## [[Characters/Characters Overview|🧑 Characters]]

| Doc | What it covers |
|-----|---------------|
| [[Characters/Characters Overview\|Characters Overview]] | Player class, 3 character types, import/export, registry, library format |
| [[Characters/Traits System\|Traits System]] | Trait definitions, library format, how traits modify gameplay |
| [[Characters/Skills System\|Skills System]] | Skill checks, progression, action resolution, combat integration |
| [[Characters/Vitals System\|Vitals System]] | HP, energy, hunger, thirst, sanity, decay per tick, death, ghost mode |
| [[Characters/Equipment Loadouts\|Equipment Loadouts]] | Per-character generated equipment lists by slot |
| [[Characters/NPC Behavior System\|NPC Behavior System]] | Simple NPCs, behavior types, action intervals, LLM agent vs scripted |
| [[Characters/Relationships System\|Relationships System]] | Closeness model, what moves it (speak/give/combat), labels, guidance, grapple modifier |
| [[Characters/Emotion & Affect System\|Emotion & Affect System]] | Multi-dimensional affect map, semantic emotion mapping, mental-vital coupling, relationship valence, self- & social-recall re-feel |

## [[Items & Inventory/Items Overview|📦 Items & Inventory]]

| Doc | What it covers |
|-----|---------------|
| [[Items & Inventory/Items Overview\|Items Overview]] | Item class, states, actions, placement, containers, matching, locked_with |
| [[Items & Inventory/Inventory\|Inventory]] | Edge model, take/drop, context menus, API client, weight system |
| [[Items & Inventory/Equipment & Paperdoll\|Equipment & Paperdoll]] | 13 equipment slots, paperdoll grid, equipping, LLM appearance gen |
| [[Items & Inventory/Item States & Toggleables\|Item States & Toggleables]] | Toggleable items, active effects, room modification, drain per tick |

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

## [[Library System/Library System Overview|📚 Library System]]

| Doc | What it covers |
|-----|---------------|
| [[Library System/Library System Overview\|Library System Overview]] | Directory structure, per-file format, load/save helpers, import mechanics, API |
| [[Library System/Tags System\|Tags System]] | Tag library, what tags do (container/furniture/heat/light), stranger labels from character tags, tag API |

## [[AI & Narration/LLM Providers|🤖 AI & Narration]]

| Doc | What it covers |
|-----|---------------|
| [[AI & Narration/LLM Providers\|LLM Providers]] | Provider configs, API keys, rate limiting, retry logic, fallback models |
| [[AI & Narration/Agent Engine\|Agent Engine]] | Agent loop, prompt building, turn queue, action validation, simple NPC diff |
| [[AI & Narration/Turn-Based System\|Turn-Based System]] | Off/sequential/random/initiative modes, turn queue, tick application on wrap |
| [[AI & Narration/Memory System\|Memory System]] | Memory types, importance, retrieval, context window, editor, generator, `memory_emotions` |
| [[AI & Narration/Narration System\|Narration System]] | 3 narration modes, room/action narration, emote command |

## [[UI & Settings/Inspector Panels|🖥️ UI & Settings]]

| Doc | What it covers |
|-----|---------------|
| [[UI & Settings/Inspector Panels\|Inspector Panels]] | 10 inspector sub-views, dispatch by node type, auto-refresh, context menus |
| [[UI & Settings/Settings & Configuration\|Settings & Configuration]] | Backend routes, ConfigManager, toggleable settings, profile system, save/load |
| [[UI & Settings/Engine Config\|Engine Config]] | Task-304: server-side engine tuning constants (sound/heat/light) editable in the Settings menu, persisted to `data/engine_config.json`, applies live |
| [[UI & Settings/Rendering & UI Modules\|Rendering & UI Modules]] | lit-html via `window.Lit`, the classic-vs-deferred-module bootstrap race + fix, graph module split, file-size rule |
| [[UI & Settings/Event Log Export\|Event Log Export]] | Markdown event-log export, filter-respecting rows, Turn vs tick labeling, stream formatting + emote ordering |

---

## 📋 Active Tasks

> [[dev_tasks/todo/|📥 Todo]] · [[dev_tasks/inprogress/|🔧 In Progress]] · [[dev_tasks/review/|👀 Review]] · [[dev_tasks/done/|✅ Done]]
>
> Tasks live in the `dev_tasks/` folder in this vault. Each task file is an `.md` with notes, design decisions, and code references. Tasks are grouped by category (characters, environment, items, gameplay, triggers, graph, ui, prompting, testing, refactor) within each status folder. The folder-move workflow: `todo/` → `inprogress/` → `review/` → `done/`.

---

## Quick Links

- **API health check**: `GET /api/health` → `{"status":"ok"}`
- **API restart**: `GET /api/restart` — resets world from `world_template.json`
- **Game root**: `http://127.0.0.1:4444`
- **Tests**: `node ../tools/test_all.cjs` (requires running server)

*Last updated: 2026-08-27*
