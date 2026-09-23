# History

VirtualWorld has **two repositories and one lineage**. This doc covers the whole
lineage: the 15 months of work that happened *before* this repo existed, where the
current public repo picks up, and how to re-derive either from git.

- **Pre-history** lives in the private monorepo `C:\Projects\code`
  (`github.com/tommylogon/code`), under `virtual_world/`.
- **This repo** (`github.com/tommylogon/virtual-world`) starts fresh on
  **2026-08-26** as the initial public release.

For version-by-version detail of the public era, see [`CHANGELOG.md`](../../CHANGELOG.md).
This doc is about the shape of the whole thing.

---

## 📜 The short version

| When | What happened | Where |
|------|---------------|-------|
| 2025-05-25 | First commit anywhere: a world of rooms and items | `code` root |
| 2025-05 → 07 | **Aura** — an LLM desktop assistant (chat UI, websockets, OCR, triggers) | `code` root |
| 2025-07-18 → 24 | **APSE** — Agentic Procedural Story Engine: Gemini + RAG, LM Studio, level generation from prompts | `code` root |
| 2025-08 → 2026-02 | Dormancy, then the 3D graph-editor experiments | `code` root |
| **2026-02-21** | **The monorepo reorg** — projects split into `virtual_world/`, `APSE/`, `Experiments/`, `utils/` | `code` |
| 2026-02-25 | First real *VirtualWorld*: a text-based simulation engine | `code/virtual_world` |
| 2026-02-28 | Web UI, JSON save/load, action costs, an LLM agent with tool definitions | `code/virtual_world` |
| 2026-03 | Flask factory pattern, doors as first-class state machines, skill checks | `code/virtual_world` |
| 2026-04 → 06 | Graph API, observability dashboard, player management, turn-based initiative | `code/virtual_world` |
| **2026-07** | **The great build-out — 384 commits in one month** | `code/virtual_world` |
| 2026-07-21 | The modularization: three monoliths split into 22 engine + 13 route + 52 JS modules | `code/virtual_world` |
| 2026-07-26 | `rooms`→`areas`, `doors`→`ways` — the vocabulary the code still uses | `code/virtual_world` |
| **2026-08** | Systems deepen: conditions/traits v2, grapple, diseases, event-stream redesign | `code/virtual_world` |
| **2026-08-26** | **Public split** — this repo's initial release (6,042 files, 267,511 lines) + MIT license | **here** |
| 2026-08-27 → 09-22 | 121 commits: time model rebuilt, schedules, structures, identity by id, log lint | **here** |

The through-line: **a room-and-item toy (May 2025) → an LLM story engine (APSE,
Jul 2025) → a graph-based world simulator (Feb 2026) → the modular engine we have
now (Jul 2026 onward)**. Every pivot kept the previous idea as a subsystem.

---

## 🧪 Era 1 — Before the engine (May–July 2025)

The first commit in `code` is
`20b36c87` — *"Add initial implementation of virtual world game structure with
rooms and items"* — on **2025-05-25**. The name was already right; almost nothing
else was.

The first months were not spent on the world at all. `code` was a scratchpad for
**LLM tooling**, and two projects dominated:

**Aura** (Jun–Jul 2025) — a desktop AI assistant. Multi-chat with an activity log,
websocket handling, OCR of the screen (`WindowActivity`), a unified message class so
knowledge-graph and stateful dialogue could be added later, keypress triggers,
streaming summarization. Seven pull requests landed in this window (PRs #1–#7), the
only sustained branching workflow in the repo's history. It was later stripped down
(`8d76ef9b`, "Remove OCR and window logging functionality", 2025-07-16).

**APSE — the Agentic Procedural Story Engine** (2025-07-18 → 07-24) — the pivot that
made the world project possible. In eight days it gained:

- hierarchical `Location`/`World` classes and an interactive shell with `look`/`goto`
- world generation from prompts — `generation.py` creating characters, items and locations
- Gemini API integration and a RAG architecture (`e17848d6`, `240246de`)
- LM Studio integration via the `lmstudio` package, plus goal-setting for characters
- a documented how-to explaining the RAG architecture

APSE is the direct ancestor of the agent loop in this repo. Its agents, reflection
and memory modules were later renamed into `APSE/` proper (see the `Rename
reflection_agent.py to APSE/reflection_agent.py` series on 2025-07-22).

Then the repo goes quiet — **no commits from 2025-07-24 until 2026-02-08**, apart
from three stray commits in April 2026.

---

## 🕸️ Era 2 — Three.js and the 3D graph (February 2026)

Work resumed on **2026-02-08** with an unrelated detour that turned out to matter:
`modelcompare` (evaluating one model with another), `warhammer-tracker`, and then a
week-long sprint on **`graph-editor`** — a 3D graph editor built on Three.js with a
physics simulation, node selection, local-storage persistence, and a
"detailed person data model".

That last part is the point. The 3D graph editor is where the world stopped being a
list of rooms and became a **graph** — nodes, edges, undo/redo, an inspectable data
model. Everything downstream (the WorldGraph, `Node`/`Edge` dataclasses, the vis.js
map, the trigger graph) descends from these February experiments.

## 🗂️ Era 3 — The monorepo reorg (2026-02-21)

`0179f987` is the structural hinge of the whole project: it introduced `APSE`,
`Neural Wanderer`, `graph-editor`, `modelcompare` and `Council`, and refactored the
existing code into `Experiments/`, **`virtual_world/`** and `utils/`. From this
commit on, the world project has its own directory and its own history —
**671 of the repo's 830 commits touch `virtual_world/`**.

Four days later (`6ce88abc`, 2026-02-25): *"add initial implementation of
VirtualWorld text-based simulation engine"*. Three days after that, on 2026-02-28,
the engine got a web UI, JSON save/load, an action-cost system, and — the important
one — a **connected agent with API interaction and tool definitions**. The agent
loop existed in embryo.

## 🧱 Era 4 — Flask, doors and skill checks (March 2026)

March is where the architecture we still live with was laid down:

- **Flask factory pattern** and modularized error handling (`1b8187f9`)
- **door nodes as first-class entities with state machines** (`1bd06bff`) — the
  direct ancestor of today's 6-state `Way` model
- item weight, skill-check mechanics, the `mansion2` scenario, the `fumble` command
- streaming LLM output with a real-time token display and a UI toggle
- a turn-management / message-routing refactor, and unit tests for the multi-agent
  dialogue system

## 🔌 Era 5 — Graph API, observability, turns (April–June 2026)

A quieter stretch, but two things landed that define the current backend:

- **2026-04-29** — `9a1c222a`: *"add graph API and refactor to observability
  dashboard"*. The old environment editor was deleted the day before
  (`7c34d9eb`, "removal of old environment"). The graph became the API surface.
- **2026-06-30** — `dc665ded`: the **turn-based system** with a separate turn
  endpoint and initiative UI.
- **2026-06-19** — message branching and streaming for narration regeneration.

Between them: edge-update API, node inspector, character inventory, legacy build
endpoints for room/item/door creation, and player-management API + modal UI.

## 🚀 Era 6 — The great build-out (July 2026, 384 commits)

July is roughly half the project. 394 of the repo's 830 commits fall in this one
month, and 384 of them touch `virtual_world/`. It is worth reading as four strands
that converged:

**Agent cognition.** Emotion, relationship and memory systems (`922f6cdc`); planning
folded into the agent engine; cosine-similarity memory retrieval; a rewrite of the
reactive pipeline into **observe-decide-act** (`0725badf`); ghost mode and hidden
exit discovery; local providers (LM Studio, Ollama); decision-time speech; thought
bubbles and raw-LLM phase messages in the stream.

**World and items.** Containers and locked containers; toggleable items with
depletion triggers; item states with graph colouring; fuzzy item matching and item
disambiguation; candle/light triggers; an actions-and-triggers grid with a costs
matrix in the item inspector; the Item Library modal with AI generation.

**Vitals and survival.** Bladder, Sanity, Entertainment and Temperature added to the
vitals set, with per-vital `decay_rates`, grouped Physical/Mental display, vital
detail modals, and eventually insulation and heat propagation between areas.

**UI.** An event-driven front-end (`AppEventBus`), paperdoll equipment grid with
LLM-generated appearance, context menus on inventory and slots, stack-expansion
badges, a cardinal-direction map view replacing a broken SVG overlay, light spill
through open doors, LLM request/response logging into the event stream.

Then, on **2026-07-21**, the structural moment:

> `aa87a9c3` — split `app.py` into 13 route modules (**2232 → 107 lines**), extract
> engine subsystems into 12 engine modules
>
> `1c1c1ab0` — final engine split: `virtual_world_engine.py` **4652 → 433 lines**.
> 22 engine modules, 13 route modules, 52 JS modules

Every monolith was pushed under 1000 lines. The `*_ops.py` + thin-registrar route
split that `AGENTS.md` still mandates is a direct product of that day. Testing
followed immediately — `104/104 passing` → `144 tests across 3 suites` → `145 total`
with a real LLM test — along with an art-heist end-to-end test.

Four days later, **2026-07-26**, the vocabulary changed forever:

> `c1fbe62d` — rename `rooms`→`areas`, `doors`→`ways` + container system + edge
> label toggle

(`2fd1e55f` is literally titled *"commit before the massive rename of rooms to
ways"*.) The mansion scenario was restructured to a graph-based format the same day.

The month closes with AGENTS.md rewritten for the monorepo, threat-aware
replanning, anonymous first contact, 44 clothing items, a sound-propagation
refactor, and the Frozen Thicket / Morphocene scenario work.

## 🧬 Era 7 — Systems deepen (August 2026, 243 commits)

August is refinement rather than foundation. The systems that had been sketched in
July got real schemas:

- **Conditions & traits v2** — a condition *catalog* with multi-instance stacking,
  per-instance fields, a sign flip, `sleeping`/`busy`, and a trait schema with
  `grants_conditions`, `save_on` event hooks, conflicts, and acquired traits
  (scripted `scarred`/`frail`/`claustrophobic`).
- **Grapple** — grab / escape / struggle with saves and combat modifiers, later
  reworked to be edge-based.
- **Size and passage** — crawl / climb / jump, and a fix so those moves stop scaling
  the way's cost.
- **Diseases** — `give_item` spread, carried-item `on_tick` spread, plague carrier.
- **Event stream redesign** — turn cards, skill badges, three themes, tick + time.
- Persistent multi-turn activities; a unified save & reaction system; carry capacity;
  the trigger validator with an editor alerts panel; per-direction beyond-visibility;
  the agent lens; selective library refresh with a DiffModal; lit-html conversion of
  every inspector view; intimacy design docs.

By 2026-08-13 the engine had all of its major organs.

**The last sprint (2026-08-22 → 08-26).** Five dense days closed out the pre-history:
semantic memory embeddings and a multi-dimensional emotion system, character emotional states
with auto-memory and turn autopilot, polarity-aware vitals across the stats readout and the UI
(with **51 `adjust_vital` drive effects sign-flipped** to match the new semantics), room
perception invariants single-sourced, per-door sound barriers, `item_actions` split into
verb-family mixins, event stream v2, and fixes for bug-23 through bug-26. On 2026-08-26, hours
before the split, the largest engine and route files were decomposed into handler packages - a
**second** modularization wave, followed by an urgent script-tag fix. Two days later it became
public.

For the whole month as release notes - all eleven releases, the graph map background, weather
and sky, crafting and gear, the mature-content system, the performance work - see
[[Patch Notes 2026-08-22 to 2026-09-22]].

## 🌍 Era 8 — This repository (2026-08-26 →)

`170d5f1` — *"VirtualWorld: initial public release — game engine and simulation for
AI-agent-driven NPCs"* — imports **6,042 files and 267,511 lines** as a single
commit, followed immediately by the MIT license (`645ce53`). The import is a
snapshot: the pre-history was intentionally left behind in `code`, so this repo's
git history begins at the finished product rather than the toy.

Since then, 121 commits in 28 days, in three bursts (Aug 26–Sep 8, then Sep 18–22 where
64 of them land). The themes:

- **The time model was rebuilt.** Per-minute decay scaling, absolute vital costs, an
  explicit `consumes_time`, then the reframe: *a turn is a timeframe filled by an
  action flow* (task-436), with one owner for the clock.
- **Schedules and the background tier** — authored daily schedules plus a planner
  (task-409), one action per turn matching the live tier.
- **Novelty, recreation, hygiene** — Entertainment unpinned from 0, perception
  novelty bounded by a daily budget, goblins that actually wash.
- **Renewable sources** — plants feeding the camp, foraging that sees containers.
- **The graph became the only copy** — scenario files 28% smaller.
- **Structures** — capture and materialize a connected region as a reusable template.
- **Identity by id, never by name** — task-446/449, so duplicate display names work.

Version-by-version detail is in [`CHANGELOG.md`](../../CHANGELOG.md).

---

## 🔎 Provenance and how to re-derive any of this

Every date and figure above comes from commit metadata, not from memory. The
commands, if you want to check or extend:

```bash
# the pre-history repo
cd C:\Projects\code

git log --until=2026-08-26 --pretty=format:"%ad|%h|%s" --date=short -- virtual_world
git log --virtual_world --oneline | Measure-Object -Line     # 671
git shortlog -sne                                            # author spellings
```

| Figure | Value |
|--------|-------|
| `code` commits, all refs / on `main` | 830 / 821 |
| `code` history span | 2025-05-25 → 2026-09-21 |
| Commits touching `virtual_world/` | 671 (2026-02-21 → 2026-09-21) |
| `virtual_world/` commits by month | 11 / 17 / 2 / 5 / 8 / **384** / **243** / 1 (Feb→Sep 2026) |
| Commit types across `code` | 287 feat, 105 fix, 78 docs, 52 refactor, 40 chore, 243 loose |
| Authors | 3 spellings of one address, 808 commits; `google-labs-jules[bot]` 22 |
| This repo | 2026-08-26 →, 121 commits in the first 28 days |

**Two caveats.** First, `virtual_world/` as a path only exists from 2026-02-21;
the very first commit (2025-05-25) suggests world code existed at the repo root
before the reorg, so a strict path filter may miss the oldest months — use
`git log --follow` on individual files to chase them across the move. Second, the
`virtual_world/` commits continue *after* 2026-08-26 (including the September
Kraktooth scenario work), because `code` stayed a live scratchpad after the split;
only commits up to the split date are pre-history.

*Written 2026-09-22.*
