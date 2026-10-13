---
type: task
status: review
area: ui
priority: medium
related: [task-714, task-729, task-736, task-756, task-820, task-821]
---

# task-787: Mind panel: migrate the remaining mind surfaces out of the Bio and Advanced tabs

**Filed:** 2026-10-12
**Related:** task-714, task-729, task-736, task-756, task-820, task-821

<!-- deps:start -->
**Related:** [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-729-move-relationship-emotional-state-and-memory-add-edit-generate-controls-into-the-mind-panel]], [[task-736-per-character-cognitive-map-a-belief-based-memory-of-places-and-routes-in-the-mind-panel]], [[task-756-move-emotion-editing-into-the-mind-view-the-memory-edit-modal-is-not-its-home]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]], [[task-821-mind-panel-relocate-the-gimp-goal-editor-out-of-the-bio-tab]]
<!-- deps:end -->

## What

Inventory the character inspector's Bio and Advanced sections, classify each as mind state or definition, and move the mind surfaces into the Mind panel. From **Bio**: `✨ Interest Tags`, `😨 Fear Tags`, `🧪 Recipes`, `👁️ What I See`, `📋 Plan`, and `💭 Latest Thoughts`. From **Advanced**: `🧠 Knowledge`, `📜 Timeline`, `🧠 Conversation Memory`. Keep in Bio (definition/body): stats/skills/traits, personality, appearance, tags, aliases. The 🧠 Mind entry point moved to the always-visible status row (it used to sit inside the Bio memories section header). `known-by.ts` stays shared for areas. Each moved surface gets one home — the Mind panel — and leaves its old tab.

**Not in this card:** the delegated Bio `🧠 Memories` list/editor. It is the memory **editor** (add / generate / suppress / delete / filter), and task-729 owns moving those edit controls into the Mind panel. The Mind panel's Memories tab already carries the *display* half (task-714). So the Bio section stays until 729; removing it here would have dropped the only add/generate/delete/suppress controls.

## Why

`agent-view.ts` grew both surfaces out of the same `_renderBioTab` / `_renderAdvancedTab` strings, so the character's *runtime mind* (what they pay attention to, fear, perceive, think, plan, know and remember) is authored next to their *definition* (personality, appearance, stats). The Mind panel is becoming the single mind surface (task-714 display, task-729 edit, task-820 container), so these mind blocks belong there and not split across two tabs. Resolved 2026-10-13: Bio keeps only definition/body; every runtime-mind block moves.

## How

Move each block's render and wiring from `agent-view.ts` into the Mind panel (`mind-view.ts`) as a tab pane, reading the same runtime source it reads today: `Player.interest_tags` / `fear_tags`, `worldState` area for what-I-see, `charState.detailedTimeline` / `events` for the timeline and latest thoughts, `PlanTracker.getPlan` for the plan, `KnownBySection.buildKnownChips` for knowledge, `agent.getDisplayHistory` for conversation memory, `player.memories` for memories. Mount them under the tabs from task-820. Remove the moved sections from `_renderBioTab` and `_renderAdvancedTab`. Re-host the deferred wirings (knowledge chips, interest/fear multiselects) inside the panel. No store changes, no second copy.

**Landed.** Tab assignment: **Mind** gains `📋 Plan`, `💭 Latest Thoughts`, `✨ Interest Tags`, `😨 Fear Tags` (with `Pursuit & plan`); **Perception** gains `👁️ What I See`, `🧠 Knowledge` (chips + 🎛 Manage), `🧪 Recipes` (replacing the weaker read-only `crafting_known` summary that task-714 had there); **Memories** gains `📜 Timeline`, `🧠 Conversation Memory`.

**Entry point.** The only opener used to be the 🧠 Mind button inside the Bio memories section header (`memory-view.ts: renderMemoriesHtml`). Since 787 moves the display blocks out of Bio, the button now also lives in the agent **status row** (always visible, above the tabs) and calls `window.InspectorMindView.open(name)`. The Bio section keeps its own 🧠 Mind button (memory-view unchanged, task-729's target). `agent-view.ts` no longer reads `window.KnownBySection` / `window.PlanTracker` (verdicts recorded in `tools/window-usage-reviewed.json`).

## Steps to verify

1. Open a character and visit every Mind tab.
   - expected: interest tags, fear tags, recipes, what-I-see, latest thoughts, plan, knowledge, timeline and conversation memory each render once, on their Mind tab, and are gone from Bio/Advanced. (The Bio `🧠 Memories` editor stays: task-729.)
   - observed: Arix (25 memories, 10 interests, 8 fears, 4 goals). Agent panel `innerText` contains none of `Interest Tags | Fear Tags | Recipes | What I See | Latest Thoughts | Plan | Knowledge | Timeline | Conversation Memory` (only the Bio `Memories` editor remains, by design); the 🧠 Mind button is present. Mind tab renders interest/fear/thoughts/goals; Perception renders what-I-see/knowledge/recipes + knowledge chips (10 chips from `Player.known`); Memories renders timeline + conversation memory; People renders profiles. Plan/Activity render only when the character has one (Arix has none), by design.
2. Run a turn for the character, then reopen the Mind panel.
   - expected: timeline and latest-thoughts update from `charState`; values match `/api/state`.
   - observed: timeline/latest-thoughts read `events.getCharacterState(name)` per open (same source as the old Advanced tab); the tag editor round-trip below proves the panel is live, not a snapshot.
3. Round-trip a moved editor.
   - expected: an edit made in the panel writes the same store and survives a reload.
   - observed: typing a tag into the Mind panel's interest-tag multiselect → `ApiClient.updateCharacter('Arix', {interest_tags})` → `/api/state` reads 11 tags including the probe, then removed (restored to the original 10).

## Acceptance

- [x] Each listed surface renders on a Mind tab and is gone from Bio/Advanced; nothing renders in two places.
- [x] Every moved block reads its existing runtime source; no new store, no UI-only copy.
- [x] Deferred wirings (KnownBySection chips, interest/fear multiselects) still mount.
- [x] Known-by stays shared for areas (untouched).
- [x] `npm run build:ts`, `npm run typecheck`, `node tools/unit/run.cjs` pass; `python tools/ts_convert.py check` green.
- [x] Live-verified on localhost:4444 for one character with populated data.

## Files

- `static/js/inspector/mind-view.ts` (destination — new renderers `_interestTagsHtml` / `_fearTagsHtml` / `_whatISeeHtml` / `_latestThoughtsHtml` / `_planHtml` / `_knowledgeHtml` / `_recipesHtml` / `_eventsTimelineHtml` / `_conversationHtml`, mounted into the task-820 tabs and wired per render)
- `static/js/inspector/agent-view.ts` (`_renderBioTab`, `_renderAdvancedTab`, status row entry point)
- `static/js/inspector/known-by.ts` (knowledge chips)
- `static/js/agent/` (`getDisplayHistory`), `PlanTracker`
- `tools/window-usage-reviewed.json` (two reviewed prefix drops)
