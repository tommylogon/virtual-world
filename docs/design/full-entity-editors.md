# Full-Surface Entity Editors — Design

**Status:** proposal — approved in principle, phased below into dev tasks
**Area:** ui
**Relates to:** `docs/virtualWorld/UI & Settings/Inspector Panels.md`, `task-251` (the 3-tab restructure this builds on), `task-512` (added the Images tab)
**Tasks:**

| Phase | Task |
|---|---|
| 0 — correct the current docs | `task-672` |
| 1 — EntityEditor frame | `task-673` |
| 2 — item action matrix | `task-674` |
| 3 — character three-column body | `task-675` |
| 4 — area split view + mini-map | `task-676` |
| 5 — deep links | *not filed — see Open Questions #2* |

## Mockups

![[entity-editors.html]]

One viewable page covering all four phases, side by side against the measured current state.
Every number in it is a measurement, not an illustration — see the provenance note at its head.
Open it in VS Code with `Ctrl+Shift+V`, or in any browser; it needs no build and no server.

## Question

Should character, item, and area editors become full-screen pages, so each entity type can
get a purpose-built layout instead of sharing one 380px column?

**Recommendation: yes — but as a second tier, not a replacement.** Keep the contextual peek in
the right panel. Add an explicit full-surface editor that the same view modules render into.
Do not add new routes and do not fork the view modules.

## The measured problem

Measured live in Chromium against the Kraktooth Goblin Camp scenario (659 nodes, 207 areas,
361 ways, 34 items, 23 characters) at a 1600×1000 viewport.

| Editor | Panel box | Content height | Vertical overflow | Sections | Controls |
|---|---|---|---|---|---|
| Character (Bio tab) | 379 × 960 | 3346px | **3.5×** | 15 | 85 buttons, 57 fields |
| Item (Black Short Shorts) | 379 × 497 | 1665px | **3.4×** | 9 | 17 buttons, 24 fields |
| Area (Abandoned Farm) | 379 × 960 | — | — | 14 | 21 env controls |

`#right-panel` is `width: 380px; min-width: 300px` (`static/css/style.css:152-153`), dropping to
320px below a 1200px viewport. Below 900px it becomes `max-height: 300px`
(`style.css:2293-2316`) — a 300px-tall editor for a 3346px document.

Three specific failures fall out of that number:

1. **The item action grid has nowhere to go.** `ALL_ACTIONS` in `item-view.js:38-40` is **15
   actions** (`examine take use open close eat drink read light activate equip unequip throw
   break drop`). The markup uses `class="checkbox-grid actions-grid"`, but only `.actions-grid`
   is styled — and it is `display: flex; flex-wrap: wrap` (`style.css:1515-1517`), not a grid.
   So 15 icon+label chips wrap in 373px, and `action_costs` (Energy/Hunger/Thirst/HP per action)
   is a *separate* grid elsewhere. The data is a 15×5 matrix presented as two stacked chip
   piles. `.checkbox-grid` has no CSS rule at all — dead class.

2. **The area editor's relational sections are orphaned from spatial context.** Exits, agents
   present, item visibility, and the area event log are all inherently spatial, and all sit
   in a 379px column with no map. The environment block compounds it: light/temp/air/smell/noise
   plus weather/wind/humidity and a presets scope picker, all vertical. There are **zero
   `input[type=range]`** in the whole area view, so the "sliders" in the current docs do not exist.

3. **The character editor exhausts vertical space before it exhausts its 15 sections.** Nothing
   is broken; it is simply 3.5 screens of scroll with no landmarks, no sticky section nav, and
   no persistent identity header. You lose your place between Memories and Recipes.

Worth naming explicitly, because it is the argument *against* treating this as purely cosmetic:
the current right-panel docs have drifted badly from reality. They describe 7 agent tabs
(actual: 4 — Inventory/Bio/Images/Advanced), 7 item actions (actual: 15), and a `showNode`
dispatch switching on `room`/`door` node types that **do not exist** in the graph. Hand-written
prose about these surfaces does not survive contact with the code. A design doc plus a shared
view-module layer is the structural fix for that, and the design work is the cheap moment to do it.

## Why not routes

`/editor/character/<id>` was the first option and it loses more than it gains.

- **It severs canvas context.** The graph is `vis.js` — canvas, no DOM. Clicking a node and
  seeing it is the primary navigation gesture of the whole editor. A route throws that away.
- **It creates two entry points for one entity**, which is a second source of truth for "what am
  I editing" — the specific thing AGENTS.md warns against.
- **It does not compose with the sim.** Watching the event stream update a character while you
  edit that character is a real workflow, and a route breaks it.

The same reasoning rules out a modal in the strict sense: a modal that dims and blocks is wrong
for a long-form editing session.

## Architecture

**One set of view modules, two mount points.** This is the load-bearing decision.

```
                    ┌─────────────────────────────┐
                    │  agent-view.js              │
                    │  item-view.js               │
                    │  area-view.js               │  (existing modules, unchanged)
                    └──────────────┬──────────────┘
                                   │ returns a lit TemplateResult
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
        InspectorPanel.render()            EntityEditor.mount()
        (static/js/inspector/panel.js)     (new, writes #entity-editor)
        writes #inspector-panel            its OWN container
```

Hard constraints, inherited from the current architecture:

- **`#entity-editor` must be a different element from `#inspector-panel`.** `Inspector Panels.md`
  states no file other than `panel.js` may write to `#inspector-panel`, because mixing
  `innerHTML` writes with lit's `render()` corrupts lit part tracking. The full editor gets its
  own container and never touches the panel's.
- **No forked view modules.** If the item editor needs a different *layout*, that is a layout
  function taking the same data — not a second copy of the form. The repo's stated pattern is
  "move, don't copy" (`Rendering & UI Modules.md`, file-size rule).
- **The peek stays the default.** Click a node → panel. Expand (⛶) → full editor. Esc or the
  backdrop returns to the panel with scroll position and active tab preserved.

### Entry points

| Surface | Trigger |
|---|---|
| Expand button in the inspector header | always present, all three editors |
| Double-click a node on the canvas | opens the full editor for that node |
| Deep link | `#editor/character/<nodeId>` — optional, see Open Questions |

### Shared chrome

Every full editor gets the same frame, so the three layouts differ only in their body:

- **Header** — entity kind badge, name (inline-editable), node id (copyable), dirty/saved
  indicator, expand-collapse, close.
- **Left rail** — sticky section nav, grouped, reflecting the sections actually rendered.
- **Body** — the per-entity layout below.
- **Focus trap + restore.** On open, focus moves to the header name; on close, focus returns to
  the element that opened it. Esc closes from anywhere except an open dropdown.

## Per-editor layouts

### Character

The 15 Bio sections fall into three natural columns. This is the editor that most clearly wants
to be wide.

| Column | Sections |
|---|---|
| Identity & persona | Name, Description, Personality, Appearance (+ first-impression preview), Emotion, Tags, Aliases |
| Mechanics | Stats, Skills, Traits, Recipes, Vitals |
| Knowledge | What I See, Latest Thoughts, Memories, Relationships, Interest Tags, Fear Tags |

- The existing 4 tabs (Inventory / Bio / Images / Advanced) become a segmented control in the
  header, so the 3-column body is scoped to whichever is active. Bio uses all three columns;
  Images and Inventory are already narrow and stay single-column.
- Appearance's "First impression" live preview is a *dependent* field — it must sit adjacent to
  the description it derives from, not in a separate column.
- Relationships is a list with scores; give it its own row under Knowledge rather than a
  column cell, so it can scroll independently.

### Item

The matrix becomes the centrepiece, because the matrix *is* the data.

```
                  │ enabled │ Energy │ Hunger │ Thirst │ HP │ skill
  🔍 examine      │   ☑     │    0    │    0    │    0    │ 0 │ —
  ✋ take          │   ☑     │    1    │    0    │    0    │ 0 │ —
  ⚡ use           │   ☐     │    2    │    1    │    0    │ 0 │ Arcana 12
  …
```

- 15 rows, one per `ALL_ACTIONS`, each row = toggle + 4 numeric cost cells + optional skill/DC.
- Rows keep their existing `ACTION_COLORS` / `ACTION_ICONS` as the row label, so the colour
  vocabulary survives.
- `INVERSE_ACTIONS` (take↔drop, equip↔unequip) needs visible affordance — a linked-row indicator
  — because today the coupling is invisible until you toggle one.
- Left column: identity, description, weight/uses, state, equip slots, skill check, tags, lock.
- Triggers stay a disclosure at the bottom; they are a different task, not part of the matrix.

### Area

Split view, because the two halves are genuinely different modalities.

| Left — properties | Right — place |
|---|---|
| Name, description, tags, aliases | Mini-map of the area and its ways |
| Environment: light, temp, air, smell, noise, weather, wind, humidity, presets | Exits list |
| Floor, scope, graph physics | Agents present · Items visible |
| | Area event log |

- The right column is the payoff: exits, agents, and item visibility stop being text lists and
  become spatial. Item view already has a `VISIBLE ITEMS IN <AREA>` selector per way side
  (measured live, 207 options), which is a strong signal that visibility is inherently spatial.
- Event log stays in the right column, read-only, scroll-locked to the top of the session.

## Cross-cutting

### Save model — the one decision that changes behaviour

Today every field saves on change: `@change=${(ev) => api.updateNode(...).then(() => worldState.fetch())}`.
A designed full editor invites the opposite — dirty state, explicit Save, Cancel/Discard.

**This is a semantics change, not a layout change**, and it is the decision most likely to cause
churn. Recommendation: **keep save-on-change in the full editor for phase 1.** Reason: the peek
and the full editor must not be able to disagree, and one model is easier to reason about than
two. Revisit only if profiling shows `worldState.fetch()` churn is a real cost — note each field
triggers a full `/api/state` poll of ~2.48 MB.

If save-on-change is kept, the header's dirty indicator should show *in-flight* state, not
*unsaved* state, and debounce is not appropriate (it would reintroduce the two-model problem).

### Responsive

- ≥1200px: 3-column character body, matrix + left column for items, split for areas.
- 900–1200px: drop to 2 columns; matrix scrolls horizontally within its own container.
- <900px: single column, and the current `max-height: 300px` right-panel rule must not apply to
  the full editor — it becomes a true full-viewport surface.

### Accessibility

- The action matrix is a real `<table>` with `<th scope="col">` / `<th scope="row">`, not a grid
  of divs — it is tabular data and must be navigable and announced as such.
- Section nav is a `<nav>` with real links; arrow-key roving tabindex if it becomes a tablist.
- Every colour-coded action chip keeps a text label; colour is never the only channel. This is
  already true in `ACTION_COLORS` usage and must survive the matrix.
- `prefers-reduced-motion` respected on panel expand/collapse.
- Expand/collapse state and active tab persist per entity, as today.

## Phasing

Each step is independently shippable and independently verifiable in a live browser.

1. **Frame only** (`task-673`). `EntityEditor` mount/unmount, shared header, Esc/backdrop, focus
   management, wired to the existing panel for all three types. No layout change — proves the
   two-mount-point architecture and the lit constraint before any styling depends on it.
2. **Item matrix** (`task-674`). Highest value, self-contained, and the clearest before/after.
   Fix `.actions-grid` naming while in there.
3. **Character three-column body** (`task-675`), with the tabs promoted to a header segmented
   control.
4. **Area split view** (`task-676`) with the mini-map. Largest new surface; depends on 1.
5. **Deep links** — *not filed.* Worth it for reload-mid-edit; costs a URL scheme and history
   handling, and the decision is Open Question #2. Filing it now would describe a choice nobody
   has made.

Phase 0, `task-672`, is independent of all of the above and can land at any time: it corrects
the existing `Inspector Panels.md` against measured behaviour, which is what the measurements in
this document were taken to establish.

## Non-goals

- Not a replacement for the contextual peek. It stays the default and the fast path.
- Not a new persistence model. Same endpoints, same `updateNode`/`updateCharacter` calls.
- Not a re-architecture of the inspector. The panel keeps owning `#inspector-panel`.
- Not a redesign of the graph, left panel, or event stream.
- Not a new templating approach — lit-html via `window.Lit`, per `Rendering & UI Modules.md`.

## Open questions

1. **Save-on-change vs explicit Save** — recommended keep save-on-change, but this is a
   product call and it changes behaviour.
2. **Deep linking** — worth it for reload-mid-edit; costs a URL scheme and history handling.
3. **Multi-entity compare** — is editing two characters side by side a real workflow? It decides
   whether the full editor must support 2-up or can stay strictly single-entity.
4. **Mobile** — is <900px a real target, or a formality? It decides whether phase 4's split view
   needs a stacked variant or a different composition entirely.
5. **Does the way editor get a fifth full-surface layout?** It has 4 tabs and 6 selects and
   survived the 380px column well (measured). The argument for including it is consistency; the
   argument against is that it does not need the space.
