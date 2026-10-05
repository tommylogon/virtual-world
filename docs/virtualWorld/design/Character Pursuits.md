---
type: doc
tags: [system/docs, system/characters]
---

# Character pursuits, schedules, plans, and activities

This is a game-design model for what characters mean to do, how they choose a longer undertaking, how they act on the immediate situation, and what other people can witness in the world.

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
- `engine/background_plans.py` currently runs a small set of assigned, actor-bound pursuit templates (`haul`, `gather`, and `rally`) using `Player.plan` for current steps. These are partial background pursuits, not the full LLM or general NPC system.
- `engine/pursuit_templates.py` and `data/library/pursuit_templates/` hold the current generic template slice.
- `engine/serialization.py` promotes older saved actor-bound `type: "plan"` template assignments into the pursuit shape on load, keeping their opaque node ids.
- The active pursuit is not yet supplied as a separate structured block to LLMs. Pursuit steps do not yet start a persistent Activity such as sleeping, and the specific-bed spatial relation is not yet represented by this slice.
- The game already has date, time, seasons, weather/forecast, moon phase, sun, and daylight groundwork. Selecting pursuits from those conditions and presenting them to the character are follow-up wiring, not new calendar work.

The next work is captured in tasks 699 and 701–705, with task-409 preserving the legacy clock scheduler and task-426 providing the current background plan case. Keep these layers distinct while connecting them through the same actor, world, perception, action, condition, and serialization sources of truth.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[background-simulation|Background simulation]] (#28)

<!-- connected:end -->
