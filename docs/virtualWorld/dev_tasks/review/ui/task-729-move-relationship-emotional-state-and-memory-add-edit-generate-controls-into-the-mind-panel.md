---
type: task
status: review
area: ui
priority: medium
related: [task-42, task-691, task-714, task-820, task-821]
---

# task-729: Move relationship, emotional-state, and memory add/edit/generate controls into the Mind panel

**Filed:** 2026-10-07
**Related:** task-42, task-691, task-714, task-820, task-821

<!-- deps:start -->
**Related:** [[task-42-proper_memory_editor]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]], [[task-821-mind-panel-relocate-the-gimp-goal-editor-out-of-the-bio-tab]]
<!-- deps:end -->

## What

The character Mind surface becomes the single place to read AND edit a character's inner state: relationships, emotional state, and memory add/edit/generate controls currently scattered across the Bio tab and the Memories tab move into the Mind panel, so viewing why a character feels/pursues is also where a designer corrects it. Display half is task-714; this is the editing half and must not duplicate it.

## Current surfaces (measured 2026-10-07)

The Mind surface today is `static/js/inspector/mind-view.ts`, opened by the 🧠 Mind
button (task-691 stage 4). It is **read-only**: timeline ribbon, category filters,
dynamics badges, a detail pane with connections (contradicts / derived-from /
same-entity), per-person profiles from `GET /api/players/<name>/memories/people`
(`engine/derive.py`), and an accessibility panel. Its own header states it
complements `memory-view.ts` — the editor.

The editing controls live elsewhere (as filed):

- **Relationships** — `static/js/inspector/agent-view.ts`, Bio tab "Relationships"
  section: per-other closeness slider, free-text label input, a
  "knows name" checkbox, add and remove. Writes via
  `ApiClient.updateCharacter(agent, { relationships: { [other]: {...} } })`
  (the card's original `{ lns }` was the wrong field name).
- **Emotional state** — `static/js/inspector/agent-view.ts`, the emotion selector
  row: a `player-emotion` select plus an `emotion-intensity-*` range, writing
  `{ emotion: { current, intensity } }` via `ApiClient.updateCharacter`.
- **Memories** — `static/js/inspector/memory-view.ts`: `+ Add Memory`
  (`addMemory`), `✨ Gen Memory` (`generateMemory`), Edit (`showMemoryEditor`),
  suppress / unblock / clearExpired, the filter, plus the multi-emotion picker
  (`_attachEmotionSelector`), entity selector, and tag multiselect, rendered by
  `renderMemoriesHtml` in the **Bio** tab (`agent-view.ts`).

Note (2026-10-13): task-787 moved the eight *display* surfaces out of Bio and left
this editor section in place, because deleting it would drop the only
add/generate/delete/suppress controls. This card then moved it. The handlers
finish with `worldState.fetch()` + `VW.inspector._reRender()`, which refreshes the
*inspector*, not the Mind modal — so the relocation also re-renders the Mind panel
on the `worldState` `update` event.

## Scope

Relocate those three edit surfaces into the Mind surface so reading why a character
feels and pursues is also where a designer corrects it. This is the **editing half**;
the display half is task-714. Do not duplicate task-714's display work, and do not
create a second source of truth — call the existing handlers and endpoints and keep
`player.relationships` / `player.emotion` / `player.memories` authoritative.

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
- RESOLVED 2026-10-13: the Mind surface is the sole editor; the Bio and Memories
  tabs drop the moved controls (task-756 makes the same cut for per-memory
  emotion). The Mind surface is a modal over the inspector panel, not a separate
  route.
- `lns` vs the affect map: confirm against task-652 (one emotional model) which
  store relationships and feelings are edited against before moving the controls.

## Why

Reading *why* a character feels and pursues, and correcting it, should be the same surface. Today the read half (task-714) is in the Mind panel but the write half — relationship sliders, the emotion select/range, memory add/edit/generate — is in the Bio and Memories tabs, so editing means leaving the panel you were reading. Resolved 2026-10-13: Bio survives as the character's definition/body surface, so these mind editors move out and the Mind panel becomes their sole home. No duplicate editor: task-756 makes the same cut for per-memory emotion editing.

## How

Re-host the existing controls and call the existing handlers; do not re-implement an endpoint or persist a UI copy.

- **Relationships** — lift the per-other slider / label / knows-name rows and `_removeRelationship` from `agent-view.ts` into the Mind panel, still writing `ApiClient.updateCharacter(agent, { relationships: { [other]: {...} } })`. (The card's earlier `{ lns }` was wrong — the runtime store field is `relationships`, and the Bio code already wrote it.)
- **Emotional state** — lift the `player-emotion` select + `emotion-intensity-*` range, writing `{ emotion: { current, intensity } }` via `ApiClient.updateCharacter`.
- **Memories** — lift `+ Add Memory` (`addMemory`), `✨ Gen Memory` (`generateMemory`), Edit (`showMemoryEditor`), suppress / unblock / clearExpired, the multi-emotion picker (`_attachEmotionSelector`), entity selector and tag multiselect from `memory-view.ts` into the Mind panel's Memories tab.

Then remove the moved editors from Bio and the Memories tab so there is one home. `player.relationships` / `player.emotion` / `player.memories` stay authoritative.

**Landed (2026-10-13).**
- **Relationships** → Mind panel **People** tab, as a `Relationships - authored store` block above the derived profiles. Rows carry the same `data-agent`/`data-other` attributes, so the panel reuses `InspectorAgentView._bindRelationshipSliders(_container, name)` verbatim (same store, same `{ relationships: {...} }` payload); the remove ✕ is delegated to `_removeRelationship`. The Bio section is deleted.
- **Emotional state** → Mind panel **Perception** tab, a `Set feeling` row under `Feeling`. Writes the same `{ emotion: { current, intensity } }`. It is **mirrored, not moved**: the header `#player-emotion` selector stays (always-available quick control). Both write the same store.
- **Memories** → the Brain panel **Memories** tab gains a toolbar (`+ Add Memory`, `✨ Gen Memory`, `🧹 Clear Expired`, `🗑 Clear All`) and the detail pane gains `✕ Edit` / `🚫 Suppress | 🔓 Unblock` / `🗑 Delete`. All call the existing `InspectorMemory` handlers. `renderMemoriesHtml` + `filterMemories` were deleted from `memory-view.ts` (now unreachable — the Mind panel's card list is the one list).
- **Refresh**: `mind-view` subscribes once to `worldState.on('update')` (`_ensureSubscribed`) and re-renders while open, so a mutation whose handler ends in `worldState.fetch()` (memory save, relationship add/remove, tag/emotion change) reflects in the panel. Without this the handlers only refreshed the inspector behind the modal.

## Steps to verify

1. From the Mind panel, drag a relationship closeness slider, then reload.
   - expected: `updateCharacter({ relationships })` persists; the same value renders in the Mind panel and `/api/state`.
   - observed: on `Kaelen Voss` (cold-start scenario), People tab: the add-select created `Lyrie` → `/api/state` `relationships.Lyrie.closeness 0`; the slider set to 60 → `…closeness 60` in `/api/state`; the delegated ✕ removed the entry (`relationships.Lyrie` gone). Row count 7 on `Arix` (goblin-camp).
2. From the Mind panel, add a memory, generate one, and edit an existing.
   - expected: `addPlayerMemory` / `generateMemory` / `updatePlayerMemory` fire; the list and detail update; the Memories tab no longer duplicates the editor.
   - observed: `+ Add Memory` opens the `memedit-modal`; content + 💾 Save → `addPlayerMemory` → `/api/state` finds the probe memory (then deleted, count back to 10). The detail pane shows Edit / Suppress / Delete for a selected card. `renderMemoriesHtml`/`filterMemories` are removed, so there is no second list.

## Acceptance

- [x] The Mind surface offers the three edit affordances, invoked through the existing handlers (`addMemory`, `showMemoryEditor`, `generateMemory`, the relationship controls and `_removeRelationship`, the emotion select/range). No endpoint is re-implemented and no UI-only copy of state is persisted.
- [x] An edit made from Mind round-trips: saved, refreshed from `/api/state`, and the Mind surface re-renders the new value (via the `worldState` `update` subscription).
- [x] Every relocated control is accounted for: relationships moved out of Bio; the memory toolbar + per-memory actions moved out of Bio (`renderMemoriesHtml` deleted); the emotion selector is intentionally mirrored (header + Mind).
- [x] The relationships and emotional state shown by task-714 and edited here are the same runtime values (`player.relationships`, `player.emotion`), not a second copy.
- [x] Works for LLM-driven and simple NPCs alike (the panel reads the same Player payload for any character).
- [x] Memory-focused controls at the existing entry points keep working (`InspectorMemory.addMemory` / `editMemory` / `saveMemory` / `deleteMemory` façade in `inspector.ts` untouched); task-691's dashboard still renders.
- [x] `npm run build:ts` and `node tools/unit/run.cjs` pass; `python tools/ts_convert.py check` is the front-end gate for the touched `.ts`.

## Files

- `static/js/inspector/mind-view.ts` (destination — `_relationshipsHtml` / `_emotionEditorHtml` / `_memoryToolbarHtml`, detail-pane actions, `_ensureSubscribed`, wiring)
- `static/js/inspector/agent-view.ts` (relationship section + memory call removed from `_renderBioTab`)
- `static/js/inspector/memory-view.ts` (`renderMemoriesHtml` / `filterMemories` deleted)
- `static/js/api-client` (`updateCharacter`, `addPlayerMemory`, `updatePlayerMemory`)
- `tools/window-usage-reviewed.json` (`InspectorMemory` drop reviewed)

## Browser UI and intended live verification

Intended UI home: Character Inspector → 🧠 Mind. Relationships live on People, the current feeling editor lives on Perception, and add/edit/generate/suppress memory controls live on Memories. The status-row emotion selector is an intentional quick control over the same `Player.emotion` value.

Current availability: The card records live round-trips for relationship add/edit/remove and memory add/edit on localhost:4444. It also records that emotion editing is mirrored in the status row; both controls write the same player field.

Live steps when available:
1. Open Mind → People for Arix, add Lyrie, set closeness to 60, and remove the relationship.
   - expected: `/api/state` shows `relationships.Lyrie.closeness` as 60 after the edit and no `relationships.Lyrie` after removal; no second relationship record appears in the inspector.
2. Open Mind → Perception, change the current emotion and intensity, then use the status-row quick selector.
   - expected: both controls show the same selected feeling and intensity from `Player.emotion`; changing either updates that same field.
3. Open Mind → Memories, add a memory, generate one, edit its text, and use the detail actions to suppress and unblock it.
   - expected: the existing memory handlers update the selected character's `Player.memories`; the card list and detail refresh in the Mind panel, and no duplicate memory list remains in Bio.
4. After each save, switch to another Mind tab and back.
   - expected: the panel re-renders from current world state and retains the saved value without a page reload.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
