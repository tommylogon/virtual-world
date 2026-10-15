---
area: ui
wiki: "[[dev_tasks/level-design-workflow]]"
type: task
status: done
priority: medium
---

# Agent Lens — Left Panel (Area + Agent Preview)

**Filed**: 2026-08-13  
**Priority**: High  
**Status**: In Review — implemented 2026-08-13; Lens tab + area/agent/way preview; narrow-screen layout fix 2026-08-13 (hide alerts/validator on Lens tab, collapse preview settings by default); browser verify pending

---

## Why

Level designers cannot see what an LLM agent (or human `look`) will receive until they run an agent step. Editing areas, ways, and items in the **right inspector** while guessing prompt output is slow and error-prone (labs doors, ladder views, jump pits, clearance doors).

Players never stand *in* a way — perception is always **from an area**. Preview must reflect that.

## What

A **non-blocking** Agent Lens in the **left panel** (new tab or pin-able pane) that updates live while the inspector stays editable on the right.

**Not** an inspector tab. **Not** a modal that covers the inspector.

## UX

### Placement

Add left tab: **👁 Lens** (alongside Agents / Initiative / Outline), or optional **pin open** floating pane docked to left panel bottom.

```
┌ LEFT ──────────┬ CENTER graph ─┬ INSPECTOR ────────┐
│ 👁 Lens        │               │ Area / Way / Agent │
│ (preview)      │               │ (edit as today)    │
└────────────────┴───────────────┴────────────────────┘
```

### Context follows selection

| User selects | Lens mode | Location for room context |
|--------------|-----------|---------------------------|
| **Area node** | Area lens | **This area** (even if no agent is here) |
| **Agent** (list or graph) | Agent lens | Agent's **actual** `current_area` |
| **Way node** | Way lens (optional v1.1) | Snippets for **each connected area** ("From Kitchen…", "From Living Room…") — still area viewpoints, not "inside the way" |
| Nothing | Last context or empty state | — |

### Area lens controls

- **View as:** character dropdown (Kaelen, Lyrie, rat, active player)
- **Way state preview:** toggle exits closed / open / locked **without saving** (preview only)
- **Sections** (collapsible, copy button each):
  1. Area description (light-filtered per character traits)
  2. Items that catch your attention (`buildAttention` — same as agent)
  3. People here (stranger labels, first-impression line)
  4. **Exits block** — exact lines from `buildRoomContext` (`From where you stand…`)
  5. Investigation notes / discovered items (if any for selected character)

### Agent lens controls

Full **next-turn prompt stack** for selected character (client-side, no LLM):

| Block | Builder |
|-------|---------|
| System | `buildCharacterSystemPrompt` |
| Room context | `buildRoomContext` from character's current area |
| Vitals / emotion / relationships / memory | existing context helpers |
| Think-decide user message | `buildReactionPrompt` |
| Footer note | "Reactive mode adds react prompt after action executes" |
| Last action result | `config.lastActionResult[charName]` |

Optional: **"Preview as if in…"** area dropdown (hypothetical placement) — clearly labeled, does not move the character.

### Live update

- Debounce 300ms on inspector edits + `worldState.fetch()` completion
- Subscribe to `appEvents` `state:updated` where available
- Manual 🔄 refresh button

## How

### New files

- `static/js/agent-lens.js` — lens controller, mode switching, render
- `static/js/agent-lens/area-preview.js` — area mode sections
- `static/js/agent-lens/agent-preview.js` — full prompt assembly

### Touch

- `templates/index.html` — left tab + pane `#left-tab-lens`
- `static/js/ui-controller.js` — `switchLeftTab('lens')`
- `static/js/inspector.js` or graph click handlers — notify lens of selection change
- Reuse `PromptBuilder.*` from `static/js/agent/prompt-builder/` (no duplicate string logic)

### v1 scope

- Area lens + Agent lens
- Preview-only way state overrides (local override map, not persisted)
- No LLM call

### v1.1 / blocked on task-201

- See-through toggles (`allow_see_character`, `allow_see_item`) in area lens
- Beyond-way content in exits block

## Steps to verify

- [ ] Select Kitchen in graph → lens shows exits block matching `buildRoomContext` for Kaelen
- [ ] Edit way `visible_in_direction` in inspector → lens updates without agent step
- [ ] Select Lyrie → agent lens shows prompts from **her** area, not selected area
- [ ] Inspector remains usable while lens tab is open
- [ ] Toggle preview closed/open on exit → exits block changes, world state unchanged on refresh without save

## Related

- [[todo/ui/task-201-area-visibility-beyond-ways|task-201]] — see-through flags in lens
- [[todo/ui/task-221-way-authoring-ux-and-tooltips|task-221]] — exit badges (`requires climb`, etc.) shown in lens
- [[dev_tasks/level-design-workflow|Level design workflow hub]]

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Left panel → 👁 Lens tab, beside Agents / Initiative / Outline.

Current availability: The Lens tab and area/agent/way previews are recorded as
implemented on 2026-08-13. The card itself marks browser verification pending;
the UI path below is the acceptance recipe, not a fresh observation.

Live steps when available:
1. Select Kitchen in the graph, open the Lens tab, and expand Exits; edit the
   Kitchen-to-Hall way's `visible_in_direction` text in the right Inspector.
   - expected: the Lens exits preview changes after the state update without
     running an agent or closing the Inspector.
2. Select Lyrie in the Agents list while Kitchen remains selected in the graph.
   - expected: Agent Lens switches to Lyrie's actual current area and prompt
     context; the right Inspector stays usable while Lens remains open.
3. In Area Lens, toggle one exit closed/open, then refresh the world state
   without saving.
   - expected: the previewed exit line changes, but the world way state and
     graph remain unchanged.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
