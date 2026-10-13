---
type: task
status: review
area: ui
priority: medium
wiki: "[[Inspector Panels]]"
related: [task-691, task-714, task-729, task-787, task-788]
---

# task-820: Mind panel: one tabbed mind surface and one entry point

**Filed:** 2026-10-13
**Related:** task-691, task-714, task-729, task-787, task-788

<!-- deps:start -->
**Related:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-729-move-relationship-emotional-state-and-memory-add-edit-generate-controls-into-the-mind-panel]], [[task-787-mind-panel-migrate-the-remaining-mind-surfaces-out-of-the-bio-and-advanced-tabs]], [[task-788-mind-panel-fullscreen-mode]]
<!-- deps:end -->

## What

Restructure `static/js/inspector/mind-view.ts` from a memory-shaped modal — a fixed 3-column grid (`250px 1fr 380px`) opened from the Memories section header and titled "Memory Mind" — into one **tabbed** mind surface, retitled "🧠 Mind — <name>" with a tab strip:

- **Mind** — MOSIAC, Disposition, Actions, Goals + history, Obligations, Schedule, Pursuit & plan.
- **Perception** — Activity, Feeling, World knowledge, Recipes.
- **Memories** — the memory dashboard: timeline, filters, search, list, detail, accessibility.
- **People** — the derived per-person profiles.

The card's proposed **Attitudes** tab (relationships, interests, fears) is deferred until task-729 / task-787 move those surfaces out of the Bio tab - there is no content for it yet. The 🧠 Mind entry button stays in the Bio tab (resolved 2026-10-13). The panel re-renders from `worldState.players[name]`; the tab shell changes only where each block mounts.

## Why

The modal now carries the whole mind (MOSIAC task-812, Goals task-714, history task-811, Obligations task-813, Schedule task-814) but is still named and reached as if it were only memories, and its left column accreted one block per task with no container. The relocation cards (task-729, task-756, task-785, task-787, task-821) have nowhere coherent to land until the panel is tabbed. This card is that container, not another block.

Resolved 2026-10-13: the inspector **Bio** tab survives as the character's body/definition surface — personality, appearance, stats/skills/traits, tags, aliases — and keeps the 🧠 Mind button. Everything mind moves into this panel. Bio is not retired.

## How

In `mind-view.ts`, `_render()` now builds a `.mind-tab` strip (Mind / Perception / Memories / People) and a per-tab pane, mounting each existing renderer exactly once - Mind: `_mosiacHtml`, `_dispositionHtml`, `_actionsHtml`, `_goalsHtml`, `_goalHistoryHtml`, `_obligationsHtml`, `_scheduleHtml`, `_pursuitHtml`; Perception: `_activityHtml`, `_feelingHtml`, `_worldKnowledgeHtml`, `_recipesHtml`; Memories: `_timelineHtml` / `_cardHtml` / `_detailHtml` / `_accessibilityHtml`; People: `_peopleHtml`. `MindState` gains `tab`, defaulting to `'mind'`; a `.mind-tab` click sets it and re-renders. No renderer was rewritten. The title changed from "Memory Mind" to "Mind"; the entry button (the 🧠 Mind button in the Bio tab's Memories section) is unchanged.

## Steps to verify

1. Open a character, click the 🧠 Mind entry, and switch every tab.
   - expected: each tab renders only its own pane; the memory dashboard (timeline, filters, detail, accessibility) still works; no doubled blocks.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. Title "🧠 Mind — Arix", tabs [Mind, Perception, Memories, People]. Mind shows MOSIAC / Disposition / Goals + history; Perception shows Activity / Feeling / Known recipes (with injected data); Memories shows the filters + list + "Memory detail" + accessibility; People shows the profiles header. Tab switching re-renders each pane.
2. Narrow the window.
   - expected: the tab strip wraps; panes stay readable.
   - observed: the tab strip has `flex-wrap: wrap` and each pane grid uses `repeat(auto-fit, minmax(330px, 1fr))`, so panes collapse to one column on a narrow window.

## Acceptance

- [x] The mind surface is tabbed; no mind block is stacked ungrouped.
- [x] One entry point opens it - the 🧠 Mind button in the Bio tab header.
- [x] No renderer is duplicated; each existing `_*Html()` mounts once.
- [x] Bio still renders personality, appearance, stats/skills/traits, tags, aliases.
- [x] `python tools/ts_convert.py check` green; live-verified on localhost:4444.

## Files

- `static/js/inspector/mind-view.ts` (the tab shell)
- `static/js/inspector/memory-view.ts` (the entry button - unchanged)
