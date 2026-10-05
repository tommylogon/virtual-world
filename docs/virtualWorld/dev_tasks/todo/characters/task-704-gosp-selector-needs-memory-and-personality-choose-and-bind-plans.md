---
type: task
status: todo
area: characters
priority: medium
related: [task-426, task-409, task-685, task-699, task-701, task-702]
blocked_by: [task-701, task-702, task-705]
---

# task-704: Pursuit selection from goals, needs, memory, perception, and world time

**Clarified:** 2026-10-05

## Goal

Choose or propose a suitable **pursuit** when needs, a goal, an accepted mission, a meaningful event, or a schedule reminder makes one relevant. A pursuit has a character's reason and longer-term objective; its short-term plan handles the present situation; an Activity begins when the character reaches a place and performs something over time.

Selection must read the actor's real state and knowledge. Needs, personality, memories and perceptions shape what the character wants and believes; calendar conditions, seasons, weather, daylight, moon, routes, people, items, and available actions constrain what is possible. Use the existing VirtualWorld world-time and environment sources.

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
