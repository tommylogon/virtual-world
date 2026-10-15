---
type: doc
tags: [system/docs, system/characters]
---

# Character pursuits, schedules, plans, and activities (MOSIAC)

This is a game-design model for what characters mean to do, how they choose a longer undertaking, how they act on the immediate situation, and what other people can witness in the world.

## The system is called MOSIAC

**MOSIAC** — **M**otivation, **O**bligations, **S**chedules, **I**ntentions, **A**ttention, **C**hoice — is the name of the system this page specifies. A character's behaviour emerges from those competing pieces of their life rather than one giant goal list trying to run the whole person, and a mosaic is separate pieces forming one coherent whole.

The vocabulary below are MOSIAC's **inputs**: Motivation is why a character moves at all (needs, drives), Obligations what they owe others (missions, promises), Schedules what the calendar expects, Attention what they notice (perception, salient events), Intentions what they are committed to (goals, pursuits). **Choice** is where they resolve — the selector that binds a plan and an action. The character decides; the world resolves the consequences.

> **Revised 2026-10-12** — the sentence above is the pre-revision wording and is kept for history only. **Needs moved out of Motivation into Attention** (a need is a signal, not an aspiration), and **Choice** is now the set of *available* actions rather than the selector. The current letters are in [The architecture: MOSIAC, GIMP and the disposition](#The%20architecture:%20MOSIAC,%20GIMP%20and%20the%20disposition%20(2026-10-12)) below, which wins wherever the two differ.

## The vocabulary

| Term | Game-design meaning | Example |
|---|---|---|
| **Need** | A pressure the character feels. It can prompt or interrupt other intentions. | Thirst makes a goblin pack water before scouting. |
| **Goal** | A wanted outcome, together with the character's reason for wanting it. | “I want to feed my family before winter.” |
| **Mission** | A request or charge offered by another character or an item. The recipient can accept, alter, refuse, or forget it. An accepted mission can become a pursuit. | Zikka asks Vekka to learn where the human tracks lead. |
| **Pursuit template** | A reusable, recipe-like description of a kind of longer undertaking. It carries purpose, timing, place, requirements, resources, progress, stop conditions, and possible steps. It is character-agnostic. | “Scout a route and return with a report.” |
| **Pursuit** | One character's chosen or assigned undertaking, filled with their target, reason, knowledge, timing, and current progress. It can serve a goal, but it is not a command that overrides the character. | Vekka scouts north because she remembers human tracks and wants to warn Zikka. |
| **Schedule** | A calendar rule or routine that says when something is due, expected, or worth considering. It can prompt the character to consider a pursuit. | At 06:00, Grandma is reminded to prepare food for the temple. |
| **Short-term plan** | The current, situation-aware approach for making progress on a pursuit. An LLM can form it on the fly and revise it as the world changes. | Find the pack, take water and a dagger, then follow the known road. |
| **Activity** | An observable, time-spanning thing the character is doing in a place. It has live world state and effects; it can finish or be interrupted. | James is sleeping on a particular bed in the bedroom. |
| **World recipe** | A rule for how a world transformation works. An activity such as cooking can enact it. | Raw fish + heat + cooking surface + ten game minutes → cooked fish. |

The short form is: **goals explain why; pursuits describe what the character is undertaking; schedules say when to consider it; short-term plans decide the next approach; activities are what is visibly happening; world recipes resolve transformations.**

## Pursuit, plan, and activity are different layers

Consider a tired character whose current pursuit is to sleep before morning:

1. The pursuit gives the character a reason and a destination: “I need to be rested before watch, so I am going home to sleep.”
2. The short-term plan works out how to get there using the character's current knowledge and the connected places in the world. If someone speaks to James on the way, the encounter can interrupt that immediate plan. James may talk, keep going, or change his mind.
3. When James reaches the bedroom, the plan starts the **sleeping activity** on a particular bed. The activity occupies the bedroom over time, puts James into the sleeping/unconscious state, and can end when he is rested or be interrupted by waking, damage, or noise.
4. Other characters can perceive “James is sleeping on the bed.” They see a world state, not merely prose claiming an event happened.

The pursuit can remain active while its current plan changes and while its activity runs. If the bed is occupied, James can choose another bed, rest elsewhere, delay, or abandon the pursuit. A plan failing does not automatically erase the reason James wanted sleep.

The present activity system already records activities on `Player.activity`, advances them over game time, applies conditions such as unconsciousness for sleep, and exposes activity descriptions in character state and room context. Its `target_item` is currently a display-name value (for example, `bed`). The pursuit executor still needs to bind a specific world object and expose the actual spatial relationship to it, so observers can tell which bed James is on. The target prompt below is a design example; an active pursuit is not yet rendered by the LLM prompt builder.

## What a pursuit describes

A pursuit template is a reusable description, not a character-specific script. An instance fills in the character, motive, known target, time window, resources, and progress. Its structured side makes the undertaking inspectable and lets the simulation validate completion against world state. Its prose side gives the character and LLM a human reason to weigh against interruptions. Do not turn the reason into an arbitrary reward token or demand that the character obey it.

For Vekka's northern-road scouting pursuit, the data and prose can sit together:

```yaml
pursuit:
  template: scout-and-report
  status: active
  actor: vekka
  goal: learn whether humans are using the northern road
  reason: I remember tracks heading west from the north road. If I learn
    where they lead, I can warn Zikka before the camp is surprised.
  objective:
    observe: human tracks along the known northern road
    report_to: zikka
  when:
    start: after gathering the required supplies
    deadline: tomorrow morning
  where:
    route: known northern road toward the west
    return_to: chief's pit
  requirements:
    carried: [backpack, dagger, water]
    knowledge: [remembered human tracks, known route north]
  progress:
    supplies_packed: validated from inventory
    route_observed: validated from current perception or recorded memory
    report_delivered: validated from the conversation/event record
  stop_when:
    - report delivered to Zikka
    - deadline reached
    - actor chooses to abandon or replace the pursuit
  interruption:
    decide_from: current perception, needs, memory, personality, and danger
```

The prose is not proof that supplies were packed, tracks were found, or a report was delivered. Those are world facts checked by the simulation. Likewise, “I will steal jerky from Rikka” is a character's proposed means; it only succeeds if the item, access, and supported theft action resolve. If another goblin talks to Vekka en route, the event can interrupt her current plan and she decides how to respond. The pursuit can continue afterward with a revised plan.

## How schedules use the world calendar

A **schedule is the timing layer**. It can be a daily time, a weekly event, a seasonal window, a deadline, or a reminder such as “around dawn, consider preparing food.” It can suggest a pursuit or make it timely; it does not define the whole pursuit and does not force the character to perform it.

VirtualWorld already has the world clock and calendar, seasons, weather and forecast, moon phase, sun, and daylight. A pursuit or schedule should read those existing world conditions: for example, a farmer may plant when the season and soil conditions are suitable, work while there is daylight, delay during dangerous weather, and harvest before a forecast frost. A night scout may prefer a particular moon phase. These are inputs for a character's choice and for simulation preconditions; they are not a second calendar stored on the character.

The existing `engine/schedule.py` is the narrower clock routine: HH:MM entries can become due, wrap at midnight, and select an activity according to its current rules. Preserve that behavior as a schedule source. It can prompt a pursuit such as “prepare breakfast for the family”; the pursuit carries the character's purpose, needs, supplies, and next steps, while the cooking activity and world recipe resolve the work.

## Different characters use pursuits differently

| Character kind | How it interacts with a pursuit |
|---|---|
| **LLM agent** | Receives its current pursuit as prose plus structured fields, along with its current activity, perceptions, memories, needs, and immediate plan context. It can accept, adapt, pause, replace, or decline the pursuit. It proposes a grounded next approach; the world validates every action and progress change. |
| **Simple NPC** | Can be assigned a pursuit or choose from suitable templates using authored rules. It follows its current steps by default, starts actual activities at valid places, and uses deterministic rules for needs and interruptions. It does not need an LLM to make progress. |
| **Background character** | Uses the same pursuit and activity vocabulary with coarser decisions and fewer updates. The background runner should not invent a parallel concept. It can travel, carry out work, start an activity, and reconsider when a need, event, or invalid condition matters. |

A pursuit may be self-chosen or arrive as a mission. A farmer's goal “feed my family” can support planting, maintaining tools, tending crops, gathering fuel, cooking, and storing food as separate pursuits. A schoolgirl may pursue good grades, friendship, romance, approval from her mother, or a healthy body for reasons meaningful to her. A cyberpunk ripper may accept or invent a pursuit to take a rival gang boss's cyberarms. The character may see a hoped-for consequence—“Mom may be nicer if I get good grades”—but the simulation determines whether that consequence actually happens through relationships and events.

No generic XP or reward is required. A mission giver may promise payment; then that payment is an authored world consequence. Otherwise, success can mean the actual change the character wanted: food in the pantry, a report delivered, a skill improved, a relationship changed, or an enemy disarmed.

## Activities and recipes

An activity is what another character can witness in the world over time: fishing at the river, cooking at the kitchen fire, bathing at the wash basin, sleeping on a bed, or having sex in a room. The activity has a location, duration or stop condition, visible participants/targets where applicable, and real state effects. It may be interruptible according to the activity's rules.

A world recipe answers a separate question: how does the transformation resolve? The cooked-fish recipe might require raw fish, a cooking surface, and heat; take ten game minutes; and produce cooked fish, possibly with skill-based quality. The **cooking activity** is the visible process underway at the cooking area. A **pursuit** may tell the character to return home and cook today's catch. The recipe determines the actual result.

The same split applies to work and crafting. A pursuit can bring a worker to the field with seed and tools; a work activity occurs there; the world rules determine whether the crop grows. A pursuit can bring a smith to a forge with ore; a crafting activity happens at the station; the recipe resolves the sword.

## Interruptions and character choice

An interruption is something that changes what the character is dealing with now: someone speaks to them, they meet a person on the road, a threat appears, a target moves, weather turns dangerous, a supply is missing, or a need becomes urgent. The event can interrupt the short-term plan or current activity. It does not have to erase the pursuit.

The character's response comes from what they can perceive, what they remember, their needs and personality, and the actual action rules. An agentic character may decide to talk, continue, flee, or replan. A simple NPC may use an authored interrupt rule. An unconscious sleeper cannot decide until the activity's wake conditions fire. No pursuit should contain a scripted reaction for another character, and neither prose nor an LLM assertion can claim a world change that did not resolve.

Short-term steps and activity timers recheck requirements when they begin or finish. If a route, target, bed, tool, recipe ingredient, or permission no longer works, the character can recompose its approach or reconsider the pursuit. Do not keep retrying a stale step forever or use a hidden `on_fail` script to dictate a reaction.

## Prompt shape for an LLM character

The current prompt already separates `=== YOUR STATE ===`, memory, witnessed events, and `=== YOUR PLAN ===`. Current activity belongs in state; the immediate step list remains the plan. The following adds a **proposed `=== CURRENT PURSUIT ===` block** between state and memory. It is an example target format, not a claim that the block is already wired:

```text
=== YOUR STATE ===
You are Vekka, in the Camp Entrance Trail. You are carrying a backpack,
dagger, and water. You feel alert but thirsty.
Activity: none.

=== CURRENT PURSUIT ===
Why I care: I remember human tracks heading west from the northern road. If I
learn where they lead, I can warn Zikka before the camp is surprised.

PURSUIT DATA
Id: vekka.scout_north
Status: active; chosen by Vekka
Objective: observe the known northern road and report findings to Zikka
Where: northern road toward the west; return point: Chief's Pit
When: begin after packing; return by tomorrow morning
Needs / supplies: backpack, dagger, enough water for the trip
Known: tracks were seen heading west; the route is the one Vekka remembers
Progress: supplies packed; road not yet checked; report not delivered
Stop: report delivered, deadline reached, or Vekka changes her mind

You may continue, change, pause, or abandon this pursuit. Your reason matters,
but it does not make an unknown route or missing item real. Check what you can
perceive now and choose what Vekka wants to do next.

=== I REMEMBER ===
...

=== WHAT HAPPENED ===
...

=== YOUR PLAN ===
1. Check that the water is in your pack. (CURRENT)
2. Follow the known northern road.
```

When the pursuit reaches the Sleeping Halls and begins a real sleep activity, the state should change to something observers can ground:

```text
=== YOUR STATE ===
You are in the Sleeping Halls. You are asleep and unconscious.
Activity: sleeping on Bed 2.
Pursuit: get rested before the morning watch. Progress: sleeping; Energy 74%.
```

The world should also expose the selected bed and spatial relation through the normal graph/perception path. Prose is the readable description of that state, not its source of truth.

## Grounded actions and plan steps

The 2026-10-04 Kraktooth event stream showed Vekka proposing “use hanging meat” because the phrase appeared in room flavor text. A short-term plan must ground each step in known nodes, actions, routes, and preconditions. If “hanging meat” does not resolve to an edible item and supported action, reject that step; do not create an item or claim that Vekka ate.

The current background pursuit templates use a smaller typed step set (`travel`, `take`, `drop`). The wider design can use world interactions such as:

| Interaction | Example checks | Result comes from |
|---|---|---|
| **Go** | Known connected route, traversable next way, destination resolves. | Ordinary movement and current world geometry. |
| **Perform** | Registered action, target, permission, skill, and equipment resolve. | The normal action contract. |
| **Observe** | Target is within supported sight, hearing, or other perception. | The actor's perception and memory systems. |
| **Take** | Item exists, is accessible/permitted, and pooled quantity is available. | Existing containment and ownership rules. |
| **Start activity** | Actor is at a valid place with required target/equipment and can begin. | The existing persistent activity system. |
| **Wait** | A relevant time or condition can be checked. | The shared game clock/event path. |

These are ways a plan can interact with the world. They are neither pursuit templates nor ongoing activities themselves.

## Fifteen example pursuits and activities

These cases demonstrate the vocabulary, not fifteen templates already authored. The Kraktooth camp's existing haul content is the one authored pursuit case in this slice; other cases are design targets or grounded examples.

| # | World / character | Pursuit and what happens | What it shows |
|---:|---|---|---|
| 1 | Kraktooth · Mikka | Move scrap from the Scrap Pile to the Workshop so it is available for repairs. Travel, take, travel, drop. | The current background runner can execute a small assigned pursuit using a short-term plan. |
| 2 | Kraktooth · Gribba | Gather enough edible food from a known source and bring it to the Cooking Area. | A quota is checked against real inventory and source state. |
| 3 | Kraktooth · Gribba | Prepare a meal for the camp at the Cooking Area. A cooking activity runs there; the referenced recipe resolves food and quality. | Pursuit, Activity, and recipe are separate. |
| 4 | Kraktooth · Vekka | Eat if she finds a real edible item; she cannot use flavor text as food. | Plans must ground the item and action. |
| 5 | Kraktooth · Vekka | Scout the north because she remembers human tracks; pack a backpack, dagger, water, and perhaps jerky; stay out until tomorrow; return and tell Zikka. | Long pursuit data carries reason, route, supplies, duration, and a report condition. |
| 6 | Kraktooth · Thrazz | A 22:00 reminder may prompt him to go home if tired. On arrival he starts sleeping on a specific bed until rested or morning. | Schedule prompts; pursuit travels; sleeping is an observable Activity. |
| 7 | Kraktooth · Rikka | Entertain the camp at the Chief's Pit because she wants the goblins to enjoy the evening. | Her pursuit cannot guarantee the audience's reaction. |
| 8 | Kraktooth · camp | Zikka calls a rally at a stated place and time; each goblin decides and travels using its own knowledge and needs. | An assigned mission can create independent pursuits. |
| 9 | Kraktooth · Zikka | Practice at the Training Pit before a contest. A training Activity advances only if the training action is supported. | “Training” has real activity and action rules. |
| 10 | Farmer family | Plant in the suitable season, tend fields in daylight when weather permits, harvest before a forecast frost, and store enough food for winter. | Calendar, season, weather, and daylight come from the existing world state. |
| 11 | Schoolgirl | Improve grades because she hopes her mother will be kinder and she wants college options. Studying is an Activity; actual grades and the relationship decide what changes. | Human motives and consequences belong in prose and world outcomes, not XP. |
| 12 | Cyberpunk ripper | Accept a mission to take a rival gang boss's cyberarms, then decide whether to recruit help, scout, and act. | A mission can become a self-owned pursuit, with its own moral and tactical choices. |
| 13 | Vekka on the road | Someone stops to talk while she is heading north. She can talk, ask what they want, or continue toward the road. | A social encounter interrupts the short-term plan; it need not cancel the pursuit. |
| 14 | Farmer in bad weather | A dangerous storm arrives before field work. The farmer may shelter, repair a roof, or change the day's pursuit. | A live world event can change activity without a bespoke schedule reaction. |
| 15 | Mansion · Whiskers | Watch a visible visitor from the doorway, then decide whether to approach or return to resting. | A pursuit may need only one grounded plan step; complexity is not a goal. |

## Current implementation and open work

This design refines the existing seams; it does not claim the complete system is shipped:

- `engine/schedule.py` is the clock-based HH:MM routine and remains the **Schedule** layer.
- `engine/activities.py` and `Player.activity` provide ongoing activities such as sleeping and bathing, with state effects, interruption, and visible descriptions.
- `engine/background_plans.py` currently resumes a small set of assigned pursuit templates (`haul`, `gather`, and `rally`) from the character's own `Player.active_pursuit`, keeping current steps in `Player.plan`. The assignment is **character data, not a graph node** (task-818); these are partial background pursuits, not the full LLM or general NPC system.
- `engine/pursuit_templates.py` and `data/library/pursuit_templates/` hold the current generic template slice.
- `engine/serialization.py` no longer coerces legacy `type: "plan"` / `type: "pursuit"` nodes: the `pursuit` node type is retired (task-818) because a pursuit assignment is character data (`Player.active_pursuit`).
- The active pursuit is not yet supplied as a separate structured block to LLMs. Pursuit steps do not yet start a persistent Activity such as sleeping, and the specific-bed spatial relation is not yet represented by this slice.
- The game already has date, time, seasons, weather/forecast, moon phase, sun, and daylight groundwork. Selecting pursuits from those conditions and presenting them to the character are follow-up wiring, not new calendar work.

The next work is captured in tasks 699 and 701–705, with task-409 preserving the legacy clock scheduler and task-426 providing the current background plan case. Keep these layers distinct while connecting them through the same actor, world, perception, action, condition, and serialization sources of truth.

## Tasks

MOSIAC is built across these cards:

- [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer|task-699]] — this design doc.
- [[task-700-grounded-plan-contract-the-llm-plan-phase-emits-typed-steps-validated-against-world-facts|task-700]] — the grounded (typed, validated) plan contract.
- [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries|task-701]] — the reusable plan/template library.
- [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override|task-702]] — the executor: the engine runs typed plans, with invalidation and needs-override.
- [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes|task-703]] — recipes become plan templates.
- [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans|task-704]] — the **Choice** step: needs, memory and personality choose and bind plans.
- [[task-409-background-schedules-work-and-coarse-social|task-409]] — the **Schedule** layer.
- [[task-426-plan-archetypes-and-group-goals|task-426]] — plan archetypes and group goals.
- [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits|task-714]] — the Mind panel where MOSIAC becomes visible.
- [[task-726-activity-and-pursuit-durations-are-authored-in-ticks-the-game-minutes-path-is-not-wired-end-to-end|task-726]] — durations in game minutes, not ticks.

## Decisions (2026-10-12)

Recorded while naming the system.

- **MOSIAC is one unified decision layer**, used by LLM agents **and** soak/background NPCs alike — not two implementations.
- **Promotion is per scope.** A character out of scope becomes a soak NPC that maintains and acts on its MOSIAC. (The `engine/attention.py` cap/tier selector was rejected and deleted.)
- **Durations are game minutes**, not ticks and not turns, for activities and pursuits.
- **The soak need not be reproducible.** Life is unpredictable within the limits of the world's starting conditions and the butterfly effect.
- **Obligations** (missions, appointments, promises, duties) is a **new** piece with no home in code yet.
- **Attention** needs an improved salience layer for both soak and LLM agents; the earliest such system was the **threat** system (see the mansion killer arriving while characters kept investigating). Example target: a character bathing in a river who is found by another should react, next turn, to being seen naked.
- The LLM's **per-turn plan** ("what do I need to do right now to reach a short-term goal" — `window.PlanTracker` / `buildPlanContext`) is outdated and must be reworked into MOSIAC.
- The weather **forecast** is renamed from "forecast schedule" to just **Forecast**, so "Schedule" means MOSIAC's Schedule only.

## The architecture: MOSIAC, GIMP and the disposition (2026-10-12)

Agreed 2026-10-12. These entries revise the vocabulary and the decisions above; where they
differ, these win. The letters, and the role of each layer, are settled. The score
vocabulary and the coefficients are not - they are the first build item (see the plan).

The manual pages for the two systems are [[MOSIAC]] and [[GIMP]]; the rest of this
document is the design intent behind them.

### The letters, revised

| Letter | Concern | In a line |
|---|---|---|
| **M** | what motivates the character toward a goal | "become chief" - the drive |
| **O** | what the character owes | kill X, collect Y, scout area Z, meet me at the place at this time, deliver this, promise not to cheat on Mia |
| **S** | the schedule or routines of the character | school and work schedules; Tyler running before his shift, home to shower before work |
| **I** | the intention of the pursuit, and why | "date Mia because she is cute"; "because then I am respected and powerful" |
| **A** | what requires attention right now | danger, interests, fear, vitals - whatever is most pressing |
| **C** | the actionable choices available right now | the verbs available to reach the goal |

Proposed: the order becomes **M-O-S-I-A-C** ("MOSIAC"), because **Attention** and
**Choice** are the *lowest, right-now* level, below the standing context of M / O / S / I.

Two shifts sit inside this. **Needs move from M to A**: a need is a signal (hunger,
fear, danger), not an aspiration, so it belongs in the salience filter - which also
means a `drive` animal is A + C and nothing else. And **Motivation and Intention are
both a "why", at different depths**: *become chief* is the motivation; *because then I
am respected and powerful* is the intention.

### Goals live outside MOSIAC

MOSIAC is the *why and how of deciding*. Goals are the *objects of want*, and they get
their own layer:

- **Goal** - what you want to achieve. Set from any variety of need: hand-authored in the
  editor, or created at runtime by a verb or free action ("set a new goal").
- **Pursuit** - how you go about achieving it.
- **Motivation** - the drive, the why ("become chief").
- **Obligation** - may support a goal or get in its way.
- **Schedule** - may mean a character only gets an allotted window to work toward a goal.
  Characters can add, remove and edit their own schedules, as people naturally do.
- **Intention** - a why, but a different one. See above.

Goals can be **linked and blocked** by other goals, characters, events or items, so they
**chain up**. Because the chain is data, it can be **played back**: what a character
achieved, which goals were reached and when, what was blocked, what was dropped, what
changed over time.

### `achieve` - the success predicate (2026-10-13)

`blocks` is only half a mission: it says what must be true to *proceed*. The other half is
**what must become true to finish**, and that is `achieve` - a ref list in the same
`prefix:value` language, resolved by the same registry, in the opposite direction.

- `reached(goal, resolvers)` is true iff the refs resolve true against live world state.
- The combinator is declared per goal: `all` (default) or `achieve_any: true`. A goal whose
  successes are alternatives is unreachable under `all`.
- **A ref must be a fact the world can flip**, not a sentence. `event:thrazz_acknowledges_skill`
  is unqueryable and the goal can never complete; `flag:thrazz_acknowledged` or
  `tag:character:Thrazz:respects_zikka` is a stored fact a trigger or action can set.
- Every prefix needs a **subject**: `tag:` on what - the holder, a named entity, the world?
  Task-705 declares the subject per leaf. `character:X` resolves to *existence*, which is
  permanently true and useless as a gate; co-location is `present:character:X`.
- The flip to `reached` is written by `sync_reached` from the per-turn pass, and lands in
  `goal_log` (task-811). It is a state change, not a projection - unlike `blocked` and
  `progress`, which are computed on read and never persisted.

`goal_alignment(action, active_goal)` - the second term of the score formula - reads these
refs: does the action advance one, or the pursuit's next step toward one. **Owned by
task-704**, which is also what makes `priority` load-bearing (which of a character's active
goals is *the* active one).

### The mind is the character's, and it is not the graph

Agreed 2026-10-12. Nodes are **physical entities in the world** - areas, ways, items,
characters. Goals, pursuits, schedules, GIMP and MOSIAC are none of those: they are the
**private data of the character**, and they live on the character's own record, per
scenario. The only part the world holds is the library - templates of goals, pursuits and
schedules that are **copied onto** a character for quick authoring, never referenced
live.

Consequences:

- Storage follows `Player.schedule` (task-409) and `engine/schedule.py`: an authored list
  on the character's record, normalised on load, never a node. Goals are `Player.goals`
  (`engine/goals.py`, task-807).
- The existing **`pursuit` node type is retired** (task-818). No scenario authors one, and
  a pursuit is a character's intention rather than a thing in the world; it already has a
  home in `Player.active_pursuit` / `Player.plan`. The template library
  (`data/library/pursuit_templates/`) stays.
- Triggers are the same case - a trigger is not a physical entity either - but that is not
  part of this work.

### GIMP - the goal layer

The four things about a want, named **GIMP** - **G**oal, **I**ntention, **M**otivation,
**P**ursuit. Agreed 2026-10-12.

| | Question | Example |
|---|---|---|
| **G** Goal | what do they want to achieve? | "become chief" |
| **I** Intention | why pursue *this* goal? | "because then I am respected" |
| **M** Motivation | why do they move at all? | "I want respect and power" |
| **P** Pursuit | how? | the execution |

Four questions, no two the same: what / why-this / why-at-all / how.

**Motivation** and **Intention** are the same two concepts MOSIAC carries as **M** and
**I** - GIMP is that pair bound to one goal and its pursuit. MOSIAC is the *state of the
decider*; GIMP is the *anatomy of a want*. The overlap is deliberate, but it means GIMP
is **not a second source of Motivation**: there is one Motivation, read by MOSIAC as an
input and named by GIMP on a goal. If GIMP's M and I were ever authored separately from
MOSIAC's, you would have two copies of the same word and the duplication smell that comes
with it.

This replaces the earlier "one **GOAP** layer" framing; that acronym is retired and no longer names a slug or a card.

### GIMP is authored; MOSIAC is runtime

The working split, agreed 2026-10-12:

- **GIMP is the goal layer.** Authored in the editor for a character, and mutated at runtime
  by goal verbs ("set a new goal", free actions). It owns **Motivation** and **Intention**
  (the two words the acronyms share) as well as **Goal** and **Pursuit**.
- **MOSIAC is the runtime state** - per character, per turn. It reads the character's GIMP
  (the active goals, their Motivation and Intention), adds the standing constraints
  (**O**bligations, **S**chedules), computes the moment (**A**ttention, **C**hoices), and
  hands that context to whichever actor is driving - the soak policy or an LLM.
- **MOSIAC informs; the actor acts.** MOSIAC does not decide. The **disposition**
  (personality, morality, memory, trauma) is what the actor uses to rank the options MOSIAC
  assembled.

In one line: **GIMP is what a character wants; MOSIAC is what they are dealing with right
now; the disposition is who is deciding.**

Ownership rule: **Motivation and Intention live in GIMP.** MOSIAC reads them and never
re-stores them.

### The soak disposition - weights, gates, and one dimension space

The LLM is easy: hand it the character's prose and traits and let it reason. The soak has no
brain, so the disposition has to be **numbers** - but the numbers must come from the *same*
authored data, or the two tiers drift apart.

**One dimension space, many characters.** ~~Declare a small vocabulary of decision dimensions
once - say ten: safety, sustenance, rest, social, duty, curiosity, comfort, acquisition,
order, aggression. Every action is scored on how well it serves each dimension; every
character carries a weight on each dimension.~~ Then:

> **Superseded 2026-10-13 by the built registry.** The "ten dimensions" above was a
> pre-spike sketch. Task-799's answer and tasks 800-806 replaced it with
> `engine/disposition.py`: **35 named scores across 4 decisions** (`relieve`, `social`,
> `hunt`, `survive`), each declaring a *kind* (utility / weight / multiplier / gate /
> threshold / salience), a `base`, a range, a `combine` (add / multiply / threshold) and a
> `pick` (argmin / argmax / weighted-draw / threshold-then-utility). The registry is the
> vocabulary; the ten are retired. A proposal that invents a third set of dimension names
> (`status`, `self_improvement`) is drift, not a design - reconcile against the registry's
> own names, machine-checked by `tools/disposition_index.py --check`.

```
score(action) = disposition_weights . action_features + goal_alignment(action, active_goal)
```

- **action_features** - how much the action serves each dimension. Derived from the verb's
  tier and the target's tags where it can be (eat -> sustenance; attack -> aggression +
  safety; examine -> curiosity), authored explicitly only where it cannot.
- **disposition_weights** - the character's numbers, **derived from traits, not hand-authored
  per character**. One table maps a trait to weight deltas (`cowardly` = safety +2,
  aggression -4; `patient` = order +2, comfort +1). A character's numbers are its traits,
  which are already authored.
- **goal_alignment** - from GIMP: does the action advance the active goal or its next step.
  A separate term, so *what they want* and *who they are* stay apart.
- **live modifiers** - emotion, needs, relationships and recent memories nudge the weights
  (fear raises safety, hunger raises sustenance, a memory bound to an entity raises
  avoidance or affinity toward it).

**Weights are soft; gates are hard.** A weight says "rather not"; a gate says "cannot".

- **Capability gates** already exist: action budget, prerequisites, location, the tier gate.
- **Value gates** come from traits and morality: `honest` excludes theft, `nonviolent`
  excludes attack, `loyal` excludes betraying an ally. A gate *removes* the option; it never
  just lowers the score.

**The pick is deterministic** - argmax with a stable tie-break, so a decision is reproducible
for debugging. A seeded jitter can add variety without losing that.

**Why it scales:** the dimension list and the trait-to-weight table are authored **once**. A
new character needs no new numbers - it needs traits, which it already has. A new verb needs
one row. The LLM reads the same traits plus the prose for nuance, so both tiers share one
authoring act and differ only in quality.

This is **task-704** (needs, memory and personality choose and bind plans). Suggested shape:
one module owns the dimension vocabulary and the trait table (a single declaration, in the
manner of `tools/way_properties.py`), and exposes a score + gate + pick the soak runner calls.

### The personality catalogue versus the trait system (2026-10-12)

A **100-trait / 200-modifier catalogue** was proposed: each personality trait is a normalized
float (0..1, default 0.5) contributing `(value - 0.5) * coefficient` to a latent decision
score. The model is sound and matches the sketch above. Three integrations decide whether it
works.

1. **There is already a trait system.** `engine/traits.py` owns `TRAIT_DEFINITIONS`,
   `data/library/traits/*.json`, a data-driven loader and a `_trait_is_active` gate.
   `player.traits` maps `trait_id -> True | str | number`, and a trait carries `effects`,
   `conflicts`, `save_on` hooks, and a `behavior_prompt` - which is the *whisper* half
   (task-487) already. The catalogue is therefore a **second thing sharing the name
   "trait"**. Separate them by role:
   - **`traits`** - capabilities, hooks and flags (dark_vision, hardy, the phobia `save_on`s).
   - **`personality`** - the continuous dials that weight decisions (the catalogue).
   Watch the collision: the `personality` field is currently a **prose string**, so a numeric
   map cannot live under that name. Pick a distinct key.

2. **The target vocabulary must be declared before the 200 rules mean anything.** The
   catalogue's targets (`choice.utility.forceful_action`, `attention.salience.threat`,
   `choice.risk_penalty_multiplier`, `choice.abandon_threshold`, ...) **do not exist in the
   code** - verified by grep. They are also not one kind: utilities, multipliers, thresholds,
   salience weights, belief gates. `add_delta` means something different for each, and "clamp
   the aggregate to its declared range" is undefined until every target declares a **(kind,
   base, range)**. Declare the target registry once (the `tools/way_properties.py` pattern)
   and gate the catalogue against it, or a single typo in 200 strings is silent.

3. **The catalogue is half the model.** It maps character -> target score. The other half -
   **action -> target score** - is missing; without it the weights do nothing. A verb has to
   declare what it contributes to `forceful_action` and friends.

Two cleanups inside the catalogue:

- **Collapse bipolar pairs split into two traits.** optimism/pessimism, sociability/
  introversion, present/future orientation, distractibility/attentional persistence are each
  one axis written as two unipolar traits; two of them invites contradictory authoring
  (0.8 optimism *and* 0.8 pessimism) and inflates the count. The engine already models
  bipolarity with `conflicts` (night_owl/morning_person, observant/oblivious).
- **Watch double-counting on a shared target.** aggression, anger_proneness,
  retaliatory_tendency and vengefulness all push toward conflict; a violent, angry, vengeful
  character stacks four contributions onto one score. Aggregate per target and consider
  normalizing, or the top of the range becomes a caricature.

Keep: the **neutral-0.5 default** (an unauthored character scores exactly average, so existing
characters do not move - a real backward-compat win); targets as **scores, not world writes**
(personality never makes an impossible action possible); and **one shared candidate set** for
soak and the LLM, with the authoritative action validator shared.

Where the catalogue lives: it was produced outside the repo. If adopted, it belongs in-repo
(`data/library/traits/` beside the existing library, or a new `data/personality/`) with a
`schema_version`, and its own `--check` gate like `character_loadout_check.py`.

### What the catalogue actually teaches, and whether the direction is right

The catalogue is **inspiration, not gospel**. Strip the 100 traits and 200 coefficients and
what remains is the durable design:

- **A decision is a function over a declared set of named scores.** Characters weight them,
  candidates contribute to them, the pick is argmax, gates exclude. That pattern - not the
  trait list - is the transferable idea. The traits and numbers are one instantiation of it.
- **The scores are the common currency for every contributor**, not just personality. Traits,
  needs, emotion, memories, relationships, obligations, and GIMP's active goal all write into
  the *same* score set. That is where **GIMP** (goal alignment) and the **disposition**
  (trait weights) meet. Design the registry as that currency and the model is "MOSIAC + GIMP";
  design it as "personality scores" and it is only one contributor.
- **Features must be computed from live state, not authored constants.** The catalogue treats
  a score as a fixed contribution per trait. Loyalty, trauma and need cannot work that way -
  they have to read the world (relationship closeness, a memory bound to an entity, a pressing
  vital) or they cannot be expressed at all.

**Direction, against the requirements.** Right for the **soak side of the disposition**, and
only there.

- It does **not** cover GIMP - goals, intentions, pursuits are separate; the catalogue is the
  disposition.
- It drifts toward a **full cognitive architecture** (belief update, attention switching,
  perception gates). MOSIAC requires a *decision context and a ranker*, not a whole mind.
  Keep the scope on deciding.

So: adopt the **score-registry + two-sided-contribution** pattern; declare the registry first;
compute features from state; keep the scope on deciding; and render the same registry as
**whispers** for the LLM, so soak and LLM share one vocabulary rather than two.

### The open question: what ranks?

What decides which goal a character works on, when, and with what priority? That is the
thing that separates individuals: what they value, what they are like - personality
types, morality, social constructs and expectations, memories and trauma. It is what
makes two characters with the same goals act differently, and it is the **selector** that
sits over the letters.

This is the same question the earlier work called **disposition** (weights for the soak,
whispers for the LLM, both at once). It is not a letter. MOSIAC is what is *on the
table*; the ranking layer is *who is deciding* - and it is where an LLM agent and a soak
NPC use the same context and the same action set but resolve them differently in quality,
never in capability.

### The disposition spike: do three unrelated decisions fit one registry? (task-799, 2026-10-13)

Three decisions, chosen to be as unlike each other as possible. Each names the scores it
turns on and the **kind** of each. Two are already in the engine; the third is proposed.

**1. Where to relieve (the privacy utility).** `engine/relief.score_privacy`:

    w.witness * witnesses  -  w.private * is_private  -  w.fixture * has_fixture

- kinds: **utility** (three weighted terms, summed; lower is better), with per-actor
  **weights** (exported, so task-549 can vary them per species or faction).
- combine: additive. pick: **argmin** (`background_simulation._travel_to_privacy`).
- no gate.

**2. The social pass (who approaches, and how).** `engine/background_social.py` calls
itself "a weighted draw over gated actions".

- kinds: **weight** (each action carries dimension weights, e.g. `{Social, Entertainment}`),
  **multiplier** (a felt emotion multiplies an existing weight,
  `w * (1 + (AFFECT_TILT-1) * strength)`; a trait scales it, e.g. `* 0.35` or `* 2.5`),
  **gate** (an ineligible action is dropped, `weights[name] = 0.0`).
- combine: multiplicative modifiers on a base weight. pick: **seeded weighted draw** seeded
  from `(actor, target, tick, action)` - not argmax.
- asymmetric: the same action scores differently for the two ends (`rel_actor`, `rel_target`).

**3. The wolf deciding to hunt (proposed).**

- kinds: **threshold** (hunger must cross a line before a hunt is on the table),
  **utility** (expected value: prey size and proximity against effort and the chance of
  failure), **gate** (a hard exclusion: injured, or the prey would win), **salience** (a
  pack-mate's kill raises the decision's profile).
- combine: threshold first, then a utility. pick: hunt / stalk / wait.

**The diff.**

| decision | utility | weight | multiplier | gate | threshold | salience |
|---|---|---|---|---|---|---|
| relieve  | yes | per-actor weights |  |  |  |  |
| social   |  | yes | yes | yes |  |  |
| hunt     | yes |  |  | yes | yes | yes |

**Union = {utility, weight, multiplier, gate, threshold, salience}.** Every score one
decision needs is a kind another needs; nothing falls outside the set.

**One registry covers all three - task-800 proceeds.**

**But one *pick* does not.** The three resolve differently:

- relieve: additive utility, **argmin** (deterministic).
- social: multiplicative weights, **seeded weighted draw**.
- hunt: **threshold, then utility**.

A registry that declared a single `argmax` (task-804 as written) would fail the social pass:
a draw is not the maximum. So the registry must declare, per decision, the **combine**
(add / multiply / threshold) and the **pick** (**argmin / weighted-draw /
threshold-then-utility**). Task-804 is "the pick modes", not "the pick".

The worry that one linear currency cannot hold a utility, a probability and a drive at once
is answered: a scalar cannot, but a **registry of kinds** can, because the kind decides how
the scalar is read, not whether it exists.

### Supersedes

- "**Choice** is where they resolve - the selector that binds a plan and an action" is
  superseded: **Choice** here is the set of *available* actions, and the resolution moves
  to the ranking layer above.
- "**Motivation** is why a character moves at all (needs, drives)" is revised: needs moved
  to **Attention**; Motivation is the standing drive.
- The open 9-nouns question is partly answered: **Goal** and **Pursuit** are not letters -
  they live in the goals layer, so the count mismatch with 6 letters is expected.

## Open questions

- This page defines **nine** nouns (Need, Goal, Mission, Pursuit template, Pursuit, Schedule, Plan, Activity, Recipe) but MOSIAC has **six** letters; Mission, Pursuit template, Activity and Recipe map to none. Is the vocabulary a layer *under* MOSIAC, or does the page need reconciling with the name?

<!-- changelog:start -->
## Changelog

*Generated by `python tools/page_changelog.py` from the task cards whose `wiki:` points at this note. Never hand-edit inside the markers.*

| When | Task | Status |
|---|---|---|
| 2026-10-12 | [[task-818-retire-the-pursuit-node-type-a-pursuit-is-character-data-only-its-templates-stay-in-the-library\|Retire the pursuit node type: a pursuit is character data, only its templates stay in the library]] | `review` |
| 2026-10-12 | [[task-814-mosiac-schedules-a-character-can-edit-themselves\|MOSIAC: Schedules a character can edit themselves]] | `review` |
| 2026-10-12 | [[task-813-mosiac-obligations-the-missing-letter-s-data\|MOSIAC: Obligations - the missing letter's data]] | `review` |
| 2026-10-12 | [[task-812-mosiac-per-character-context-assembly-m-o-s-i-a-c\|MOSIAC: per-character context assembly (M O S I A C)]] | `review` |
| 2026-10-12 | [[task-811-gimp-achievement-log-and-goal-replay\|GIMP: achievement log and goal replay]] | `review` |
| 2026-10-12 | [[task-810-gimp-the-goal-graph-links-blocks-and-chaining\|GIMP: the goal graph - links, blocks and chaining]] | `review` |
| 2026-10-12 | [[task-809-gimp-create-goals-at-runtime-from-verbs-and-free-actions\|GIMP: create goals at runtime from verbs and free actions]] | `review` |
| 2026-10-12 | [[task-808-gimp-author-goals-in-the-character-editor\|GIMP: author goals in the character editor]] | `review` |
| 2026-10-12 | [[task-807-gimp-the-goal-model-and-its-serialization\|GIMP: the Goal model and its serialization]] | `review` |
| 2026-10-12 | [[task-806-split-traits-capabilities-from-personality-decision-dials\|Split traits (capabilities) from personality (decision dials)]] | `review` |
| 2026-10-12 | [[task-805-disposition-whispers-render-the-score-registry-as-words-for-the-llm\|Disposition whispers: render the score registry as words for the LLM]] | `review` |
| 2026-10-12 | [[task-804-disposition-pick-argmax-with-a-stable-tie-break\|Disposition pick: argmax with a stable tie-break]] | `review` |
| 2026-10-12 | [[task-803-disposition-value-gates-traits-and-morality-as-hard-exclusions\|Disposition value gates: traits and morality as hard exclusions]] | `review` |
| 2026-10-12 | [[task-802-disposition-character-weights-from-traits-plus-live-modifiers\|Disposition character weights from traits, plus live modifiers]] | `review` |
| 2026-10-12 | [[task-801-disposition-action-features-verb-score-contributions\|Disposition action features: verb -> score contributions]] | `review` |
| 2026-10-12 | [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary\|Disposition score registry: declare the decision-score vocabulary]] | `review` |
| 2026-10-12 | [[task-799-disposition-spike-do-three-unrelated-soak-decisions-fit-one-score-registry\|Disposition spike: do three unrelated soak decisions fit one score registry]] | `review` |
<!-- changelog:end -->

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[background-simulation|Background simulation]] (#28)

**Dev tasks** — [[dev_tasks/review/characters/task-799-disposition-spike-do-three-unrelated-soak-decisions-fit-one-score-registry|task]], [[dev_tasks/review/characters/task-800-disposition-score-registry-declare-the-decision-score-vocabulary|task]], [[dev_tasks/review/characters/task-802-disposition-character-weights-from-traits-plus-live-modifiers|task]], [[dev_tasks/review/characters/task-803-disposition-value-gates-traits-and-morality-as-hard-exclusions|task]], [[dev_tasks/review/characters/task-804-disposition-pick-argmax-with-a-stable-tie-break|task]], [[dev_tasks/review/characters/task-805-disposition-whispers-render-the-score-registry-as-words-for-the-llm|task]] … +14 more

**Neighbouring notes** — [[MOSIAC Character Profiles]]

<!-- connected:end -->
