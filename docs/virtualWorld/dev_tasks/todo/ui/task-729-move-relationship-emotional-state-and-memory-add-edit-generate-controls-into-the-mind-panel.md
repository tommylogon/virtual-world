---
type: task
status: todo
area: ui
priority: medium
---

# task-729: Move relationship, emotional-state, and memory add/edit/generate controls into the Mind panel

**Filed:** 2026-10-07
**Related:** task-42, task-691, task-714

## Goal

The character Mind surface becomes the single place to read AND edit a character's inner state: relationships, emotional state, and memory add/edit/generate controls currently scattered across the Bio tab and the Memories tab move into the Mind panel, so viewing why a character feels/pursues is also where a designer corrects it. Display half is task-714; this is the editing half and must not duplicate it.

## Current surfaces (measured 2026-10-07)

The Mind surface today is `static/js/inspector/mind-view.ts`, opened by the 🧠 Mind
button (task-691 stage 4). It is **read-only**: timeline ribbon, category filters,
dynamics badges, a detail pane with connections (contradicts / derived-from /
same-entity), per-person profiles from `GET /api/players/<name>/memories/people`
(`engine/derive.py`), and an accessibility panel. Its own header states it
complements `memory-view.ts` — the editor.

The editing controls live elsewhere:

- **Relationships** — `static/js/inspector/agent-view.ts`, Bio tab "Relationships"
  section (key `lns`): per-other closeness slider, free-text label input, a
  "knows name" checkbox, add and remove. Writes via
  `ApiClient.updateCharacter(agent, { lns: { [other]: {...} } })`.
- **Emotional state** — `static/js/inspector/agent-view.ts`, the emotion selector
  row: a `player-emotion` select plus an `emotion-intensity-*` range, writing
  `{ emotion: { current, intensity } }` via `ApiClient.updateCharacter`.
- **Memories** — `static/js/inspector/memory-view.ts`, Memories tab: `+ Add Memory`
  (`addMemory`), `✨ Gen Memory` (`generateMemory`), Edit (`showMemoryEditor`),
  suppress / unblock / clearExpired, plus the multi-emotion picker
  (`_attachEmotionSelector`), entity selector, and tag multiselect.

## Scope

Relocate those three edit surfaces into the Mind surface so reading why a character
feels and pursues is also where a designer corrects it. This is the **editing half**;
the display half is task-714. Do not duplicate task-714's display work, and do not
create a second source of truth — call the existing handlers and endpoints and keep
`player.lns` / `player.emotion` / `player.memories` authoritative.

## Acceptance

- [ ] The Mind surface offers the three edit affordances, invoked through the
      existing handlers (`addMemory`, `showMemoryEditor`, `generateMemory`,
      the relationship controls and `_removeRelationship`, the emotion
      select/range). No endpoint is re-implemented and no UI-only copy of state
      is persisted.
- [ ] An edit made from Mind round-trips: saved, refreshed from `/api/state`, and
      the Mind surface re-renders the new value.
- [ ] Every relocated control is accounted for: state per control whether it is
      moved out of its old location or intentionally mirrored, so nothing is
      silently lost from the Bio / Memories tabs.
- [ ] The relationships and emotional state shown by task-714 and edited here are
      the same runtime values (`player.lns`, `player.emotion`), not a second copy.
- [ ] Works for LLM-driven and simple NPCs alike.
- [ ] Memory-focused controls at the existing entry points keep working; task-691's
      dashboard still renders.
- [ ] `npm run build:ts` and `node tools/unit/run.cjs` pass; `python
      tools/ts_convert.py check` is the front-end gate for the touched `.ts`.

## Open questions

- Inline in the Mind surface, or a read/edit mode toggle (precedent: the HTC's
  hover = inspect, click = act)?
- Keep the Memories tab editor as a second editor, or make the Mind surface the
  sole one and retire the duplicate? This pairs with task-691's unresolved
  question (in-inspector panel vs separate route).
- `lns` vs the affect map: confirm against task-652 (one emotional model) which
  store relationships and feelings are edited against before moving the controls.
