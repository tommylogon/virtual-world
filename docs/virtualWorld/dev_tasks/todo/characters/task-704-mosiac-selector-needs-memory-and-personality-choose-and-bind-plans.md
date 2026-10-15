---
type: task
status: todo
area: characters
priority: medium
related: [task-426, task-409, task-685, task-699, task-701, task-702]
blocked_by: [task-701, task-702, task-705]
---

# task-704: Pursuit selection from goals, needs, memory, perception, and world time

**System name:** the **MOSIAC** selector — the *Choice* step of MOSIAC (Motivation, Obligations, Schedules, Intentions, Attention, Choice). It reads those inputs and binds a plan.

**Clarified:** 2026-10-05

<!-- deps:start -->
**Blocked by:** [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-705-requirement-condition-leaves-quantity-area-function-knowledge-and-ownership]]
**Related:** [[task-426-plan-archetypes-and-group-goals]], [[task-409-background-schedules-work-and-coarse-social]], [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]]
<!-- deps:end -->

## What

Choose or propose a suitable **pursuit** when needs, a goal, an accepted mission, a meaningful event, or a schedule reminder makes one relevant. A pursuit has a character's reason and longer-term objective; its short-term plan handles the present situation; an Activity begins when the character reaches a place and performs something over time.

Selection must read the actor's real state and knowledge. Needs, personality, memories and perceptions shape what the character wants and believes; calendar conditions, seasons, weather, daylight, moon, routes, people, items, and available actions constrain what is possible. Use the existing VirtualWorld world-time and environment sources.

**This card owns `goal_alignment`** - the second term of the score formula in [[Character Pursuits]]:

```
score(action) = disposition_weights . action_features + goal_alignment(action, active_goal)
```

`goal_alignment` reads the active goal's **`achieve`** refs (task-822) and the bound pursuit's next step: does this action advance one? It is the term that connects GIMP to the pick, and nothing computes it today. **`priority` is this card's input too** - it is declared 1-is-highest in task-822, and choosing *which* of a character's active goals is the active one is this card's job. With several active goals and no ranking, the formula has no `active_goal` to align to.

## Acceptance

- [ ] Selection runs on meaningful triggers—need signals, mission offer/acceptance, Activity completion or interruption, pursuit completion/invalidation, relevant perception/memory, or schedule/calendar cue—not once per simulation tick.
- [ ] Candidate pursuits come from the shared character-agnostic template library or explicit actor-authored content. The selector binds only targets and facts supported by the actor's knowledge and the authoritative world.
- [ ] Each bound pursuit carries a readable character reason and structured objective, where, when, supplies/requirements, stop condition, and progress fields. A character's hoped-for consequence is prose/motive; actual consequences are determined by world and relationship rules.
- [ ] Personality can shape goal weights and soft preferences. It cannot create an item, route, skill, permission, or outcome that the world does not support.
- [ ] Memory can make a goal/pursuit relevant; when perception falsifies the remembered premise, the normal correction path updates knowledge and selection can adapt (task-685).
- [ ] Calendar cues use existing game date, clock, `current_season`, weather/forecast, sun/daylight, and moon phase. Schedules provide timing prompts; they do not become pursuits or Activities.
- [ ] LLM agents receive the current pursuit and candidate information in prose plus structured data. The agent can accept, adapt, pause, replace, or decline without a retry penalty. Its immediate plan is separately generated and can change after interruptions.
- [ ] Simple NPCs can accept assigned pursuits or choose through deterministic rules, then carry them out using the same Activity and world-action systems without LLM calls.
- [ ] Background simulation uses the same pursuit and Activity semantics at coarser decision intervals; there is no parallel “schedule activity” vocabulary.
- [ ] Actor sovereignty holds: selecting one character's pursuit never predicts or sets another character's response.
- [ ] A rejection is a choice, not failure. No retry penalty, replan penalty, or forced re-proposal of the same rejected pursuit in the same selection cycle.
- [ ] Demonstrate conflicting needs with one hungry, lonely goblin that accepts a suggested pursuit and another moment where the same goblin declines it for a stronger personal reason, using the same catalog and no character-specific special case.
- [ ] task-426's haul/gather/rally content is either absorbed as initial pursuit templates or explicitly retired. No second archetype system remains beside the pursuit catalog.

## Why

TODO

## How

TODO

## Steps to verify

1. In a micro-scenario, give the same goblin two competing active goals, a hungry/lonely need state, and two library-backed pursuit candidates; run selection once with a relevant memory and known route.
   - expected: the selected binding names only known, reachable targets, includes a readable reason tied to the active goal's `achieve` refs, and does not create an item, route, permission, or skill.
   - observed: Not run. The selector is not implemented; this card is blocked by tasks 701, 702, and 705.
2. Keep the character and candidates the same, then change the stronger personal reason and repeat the selection cycle with one candidate declined.
   - expected: the character can decline without a retry penalty or same-cycle re-proposal; the other character's response is unchanged.
   - observed: Not run. The selector is not implemented; this card is blocked by tasks 701, 702, and 705.
3. Repeat the fixture with both an LLM agent and a simple background NPC, then change the calendar cue and falsify the remembered route premise.
   - expected: both use the same pursuit template and world-action semantics; the LLM can adapt or decline, while the simple NPC uses the deterministic rule; the stale premise causes reselection rather than an invented destination.
   - observed: Not run. The selector is not implemented; this card is blocked by tasks 701, 702, and 705.

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Select the actor → Inspector → Bio → 🧠 Mind → Goals and Pursuit & plan. The visible world and its normal action surface show whether the selected plan actually moves, gathers, or starts an Activity.

Current availability: The MOSIAC selector is planned and blocked by tasks 701, 702, and 705. The saved Mind surface can display goals and character-side pursuits, but it does not yet demonstrate this selector choosing or declining candidates.

Live steps when available:
1. Load the hungry/lonely goblin micro-scenario, select that goblin, open Mind, and record the two active goals and the candidate reasons; advance the selector trigger once.
   - expected: the selected pursuit and reason appear under Pursuit & plan, and its bound target is visible to that character in the world.
2. Change the fixture so the same goblin has the stronger personal reason, then trigger selection again and inspect the other goblin in the same scenario.
   - expected: the first goblin can decline the suggested pursuit without a retry penalty, and the other actor's plan remains their own choice.
3. Let the accepted pursuit execute through its next step, then inspect the actor and Mind again after changing the remembered route premise.
   - expected: the actor's actual position/Activity and Mind's plan agree; a falsified premise leads to a grounded new choice without erasing the longer pursuit automatically.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
