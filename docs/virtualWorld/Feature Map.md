---
type: index
area: docs
tags: [system/docs, topic/validation]
---

# Feature Map

**Start here.** This is the guide to what you can *do* in VirtualWorld — in a
game and in the editor — grouped the way you meet it, not the way the code is
filed. Every entry links to the page that explains it. If you want the honest
columns (status, coverage, what is `unwired`), that is the [[Feature Ledger]] —
this page is the map, that one is the ledger.

A **feature** is something you do, interact with or use. A **mechanic** is how
it works — the operations and rules inside a feature. A **system** is the
implemented whole. The verbs you type (`go`, `take`, `attack`) are a feature's
*mechanics*, not features of their own: you *do* movement; you do it *by* typing
`go`.

**78 features** — 45 you can do in a game, 33 in the editor.

---

## Getting around

- [[World Building/Movement|Movement]] — **traverse the world.** `go`, `dash`, `crawl`, `climb`, `jump`, `approach`. Size, load, ability and the way's own rules decide whether you pass.
- [[World Building/Ways|Ways]] — **the passages themselves.** Doors, arches, ladders, portals, forest paths. Their states, what they refuse, and how light and sound spill through them.
- [[Rooms & Areas]] — **the places.** What is on the far side of a way.
- [[World Scopes]] — **nested worlds.** Towns inside a world, interiors inside a town.
- [[Gameplay/Character Spatial Position|Character Spatial Position]] — **where you stand.** Being *at* a thing versus crossing past it.

## Things you do to things

- [[Items Overview]] — **items.** Take, drop, give, put in, search, read, write, use on.
- [[Environment/Light System|Light]] — **light and dark.** Sources, ambient levels, seeing in the dark, what a lamp does to a room.
- [[Rules Engine/Triggers & Effects|Triggers & effects]] — **the rules that fire.** Conditions on any node, and what they do.
- [[Library System/Tags System|Tags]] — **the vocabulary on every node.** What tags are, what they do, and which ones the engine actually reads.
- [[Rules Engine/Conditions System|Conditions]] — **what is wrong with you.** Prone, grappled, blind, frightened, and how they gate what you can do.

## Fighting

- [[Rules Engine/Combat System|Combat]] — **attack, grapple, restrain.** Hit dice, armour, damage, injury, and dragging someone with you.

## Looking and knowing

- [[Rooms & Areas]] — **look around.** Light, temperature, sound, smell, who is here, what they are doing.
- [[Gameplay/Search & Forage|Search & forage]] — **forage tables, skill-gated draws, regrowth.**
- [[Gameplay/Per-Agent Knowledge (Fog of War)|Per-agent knowledge]] — **what you have actually found.** A map that only shows what you know.

## Talking

- [[NPC Behavior System]] — **speech.** Talk, whisper, shout, sing, scream — audibility as a channel.
- [[Features/the-commons|The Commons]] — **character messaging across distance.** Public posts, private groups, and direct messages.
- [[Relationships System]] — **who you are to each other.** Closeness, labels, and what moves them.

## Being a body

- [[Vitals System]] — **vitals and needs.** Hunger, thirst, energy, warmth, social, entertainment, sanity.
- [[Equipment & Paperdoll]] — **what you wear and carry.** Slots, bulk, weight, insulation.
- [[Activities & States]] — **multi-tick activities.** Sleeping, bathing, sitting, and being busy.
- [[Skills System]] — **skills.** Proficiency, checks, growth by use.
- [[Traits System]] — **traits.** What you are, and how it changes the rules.
- [[Emotion & Affect System]] — **emotion.** Affect, reflection, residue.
- [[Memory System]] — **memory.** What a character remembers and how recall works.

## The world around you

- [[Environment/Time & Weather|Time & weather]] — **calendar, clock, forecast,** and weather that reaches the world.
- [[Environment/Temperature System|Temperature]] — **heat.** Body and room temperature, clothing, equipment, heat propagation.
- [[Environment/Light System|Light]] — **light.** (See also the section above.)
- The **sky** — time of day, date, moon phase, season. Part of [[Environment/Time & Weather|Time & weather]].

## Making things

- **Crafting** — make, combine, split, teach. Recipes, tools, results. *(No page yet — this is a real feature with no note; see the [[Feature Ledger]].)*

## How the world runs

- [[NPC Behavior System]] — **NPC behaviour.** Autonomous states: idle, forage, eat, flee, hide.
- [[Background Simulation]] — **everyone off-screen.** The background tier and the coarse social layer.
- [[Gameplay/Turn Queue & Human Turns|Turns]] — **whose turn it is.** Initiative, the human's slot, timeskip, the turn composer, and the modes.
- [[Time & Weather]] — **spectator mode.** Watch the simulation run without acting.
- [[AI & Narration/Narration System|Narration]] — **the prose you are told** on a turn.
- [[LLM Providers]] — **the calls.** Every character and narration call, and which provider served it.
- [[LLM Providers]] — **prompt lens.** See exactly the context an agent would be given, with no call.
- [[Character Images & Expression Packs]] — **character art,** auto-description, and expression packs.

## Building a world (the editor)

- [[WorldPainter]] — **paint a world** on a grid: 8 tools, 3 modes, 4 layers.
- [[Grid to Graph]] — **compile** painted cells into areas, ways, gateways, buildings.
- [[Graph System]] — **the graph.** Canvas, map layout, levels layout, physics.
- [[Inspector Panels]] — **node inspectors.** The 12 panels that edit any node.
- [[World Building/Ways|Ways]] — **way authoring.** Create and edit ways, doors, cardinals. (See [[World Building/Way Properties|Way Properties]] for the full key set.)
- [[UI & Settings/NL Editor|NL editor]] — **describe a change in prose;** see a plan before it is applied.
- [[Library System Overview]] — **the library.** The content registry, and pushing/pulling nodes in both directions.
- [[ScenarioCreationGuide]] — **scenario creation.** The wizard and the text-to-scenario path.
- [[UI & Settings/Settings & Configuration|Settings]] — **engine config,** saves, and every slider.
- [[Inspector Panels]] — **world lore.** The lore of a place, with tags gating who may read it.

## Working on it

- [[UI & Settings/Event Stream|Event stream]] — **the turn-by-turn log,** with filters and search.
- [[UI & Settings/Event Log Export|Export]] — **graph and play-session exports** (Markdown / plain / JSON / JSONL).
- [[UI & Settings/Soak Lab|Soak lab]] — **long automated runs,** live tuning, telemetry.
- [[UI & Settings/Recent Edits & Undo|Recent edits / undo]] — **what changed, and undoing it.**
- [[UI & Settings/Validator & Issues|Validator & issues]] — **scenario lint,** mismatches, authoring blockers.
- [[UI & Settings/Rendering & UI Modules|The rest of the UI]] — command palette, help centre, agent overview, the action menu, and report a bug.

---

## Where to go next

- New to VirtualWorld? Start with [[Simulation Model]] — the four processing levels, and a turn as a *timeframe*.
- Want to build a world? [[WorldPainter]] → [[Grid to Graph]] → [[Rooms & Areas]] → [[World Building/Ways|Ways]].
- Want to write a scenario? [[ScenarioCreationGuide]] → [[Rules Engine/Triggers & Effects|Triggers & effects]] → [[NPC Behavior System]].
- Want to know what is *not* done? [[Feature Ledger]] — it names the `unwired` row and the rows that are code-evidence only.

<!-- changelog:start -->
## Changelog

*Generated by `python tools/page_changelog.py` from the task cards whose `wiki:` points at this note. Never hand-edit inside the markers.*

| When | Task | Status |
|---|---|---|
| 2026-10-12 | [[task-797-require-wiki-on-task-cards-and-generate-per-feature-changelogs\|Require wiki on task cards and generate per-feature changelogs]] | `done` |
| 2026-10-12 | [[task-796-module-header-contract-gate-docs-demote-powers\|Module header contract: gate @docs, demote @powers]] | `done` |
| 2026-10-12 | [[task-795-re-home-the-deep-docs-into-the-three-tiers\|Re-home the deep docs into the three tiers]] | `done` |
| 2026-10-12 | [[task-793-collapse-commands-to-a-single-index-page\|Collapse Commands to a single index page]] | `done` |
| 2026-10-12 | [[task-792-feature-map-as-guide-index-coverage-as-generated-ledger\|Feature Map as guide index; coverage as generated ledger]] | `done` |
| 2026-10-12 | [[task-791-feature-mechanic-and-system-page-standard\|Feature, mechanic and system page standard]] | `done` |
<!-- changelog:end -->

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Dev tasks** — [[dev_tasks/done/docs/task-791-feature-mechanic-and-system-page-standard|task]], [[dev_tasks/done/docs/task-792-feature-map-as-guide-index-coverage-as-generated-ledger|task]], [[dev_tasks/done/docs/task-793-collapse-commands-to-a-single-index-page|task]], [[dev_tasks/done/docs/task-795-re-home-the-deep-docs-into-the-three-tiers|task]], [[dev_tasks/done/refactor/task-796-module-header-contract-gate-docs-demote-powers|task]], [[dev_tasks/done/refactor/task-797-require-wiki-on-task-cards-and-generate-per-feature-changelogs|task]] … +1 more

**Neighbouring notes** — [[Commands]], [[Emotion & Mood — Whole-System Analysis]], [[Feature Ledger]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]], [[Patch Notes 2026-09-28]]

<!-- connected:end -->
