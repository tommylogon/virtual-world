---
type: task
status: todo
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

Inventory the character inspector's Bio and Advanced sections, classify each as mind state or definition, and move the mind surfaces into the Mind panel. From **Bio**: `✨ Interest Tags`, `😨 Fear Tags`, `🧪 Recipes`, `👁️ What I See`, `💭 Latest Thoughts`, `📋 Plan`, and the delegated `🧠 Memories` section. From **Advanced**: `🧠 Knowledge`, `📜 Timeline`, `🧠 Conversation Memory`. Keep in Bio (definition/body): stats/skills/traits, personality, appearance, tags, aliases, and the 🧠 Mind button. `known-by.ts` stays shared for areas. Each moved surface gets one home — the Mind panel — and leaves its old tab.

## Why

`agent-view.ts` grew both surfaces out of the same `_renderBioTab` / `_renderAdvancedTab` strings, so the character's *runtime mind* (what they pay attention to, fear, perceive, think, plan, know and remember) is authored next to their *definition* (personality, appearance, stats). The Mind panel is becoming the single mind surface (task-714 display, task-729 edit, task-820 container), so these mind blocks belong there and not split across two tabs. Resolved 2026-10-13: Bio keeps only definition/body; every runtime-mind block moves.

## How

Move each block's render and wiring from `agent-view.ts` into the Mind panel (`mind-view.ts`) as a tab pane, reading the same runtime source it reads today: `Player.interest_tags` / `fear_tags`, `worldState` area for what-I-see, `charState.detailedTimeline` / `events` for the timeline and latest thoughts, `PlanTracker.getPlan` for the plan, `KnownBySection.buildKnownChips` for knowledge, `agent.getDisplayHistory` for conversation memory, `player.memories` for memories. Mount them under the tabs from task-820. Remove the moved sections from `_renderBioTab` (interest tags ~983, fear tags ~993, recipes ~1001, what-I-see ~1014, latest thoughts ~1028, plan ~1038, memories ~1047) and `_renderAdvancedTab` (knowledge ~1271, timeline ~1288, conversation memory ~1324). Re-host the deferred wirings (knowledge chips, interest/fear multiselects) inside the panel. No store changes, no second copy.

## Steps to verify

1. Open a character and visit every Mind tab.
   - expected: interest tags, fear tags, recipes, what-I-see, latest thoughts, plan, memories, knowledge, timeline and conversation memory each render once, on their Mind tab, and are gone from Bio/Advanced.
   - observed: TODO
2. Run a turn for the character, then reopen the Mind panel.
   - expected: timeline and latest-thoughts update from `charState`; values match `/api/state`.
   - observed: TODO

## Acceptance

- [ ] Each listed surface renders on a Mind tab and is gone from Bio/Advanced; nothing renders in two places.
- [ ] Every moved block reads its existing runtime source; no new store, no UI-only copy.
- [ ] Deferred wirings (KnownBySection chips, interest/fear multiselects) still mount.
- [ ] Known-by stays shared for areas.
- [ ] `npm run build:ts`, `npm run typecheck`, `node tools/unit/run.cjs` pass; `python tools/ts_convert.py check` green.
- [ ] Live-verified on localhost:4444 for one character with populated data.

## Files

- `static/js/inspector/mind-view.ts` (destination)
- `static/js/inspector/agent-view.ts` (`_renderBioTab`, `_renderAdvancedTab`)
- `static/js/inspector/known-by.ts` (knowledge chips)
- `static/js/agent/` (`getDisplayHistory`), `PlanTracker`
