---
type: task
status: todo
area: ui
priority: medium
---

# task-714: Character Mind panel: connect memories, motives, and current pursuits

**Filed:** 2026-10-05
**Related:** task-409, task-426, task-691, task-699, task-701, task-702, task-703, task-704

## Goal

Extend the existing character Mind view into one readable surface for why a character cares, what they are pursuing, how they currently plan to act, what activity is visibly underway, and which memories or schedule cues inform it.

## Acceptance

- Start from the existing 🧠 Mind entry point and Memory Mind dashboard from task-691. Give the character inspector one coherent Mind surface while retaining the existing memory timeline, filters, people profiles, dynamics, and detail view.
- At a glance, a designer can answer: what matters to this character, why it matters, what they are undertaking, what they plan to do next, what they are doing over time right now, and which memories inform that choice.
- Show concise character-facing prose alongside inspectable facts. Read facts from their existing runtime sources (`Player` needs and state, `active_pursuit`, `plan`, `activity`, the calendar/schedule system, and the character's memories). Do not persist a second UI copy or invent a unified Goal record to fill a blank.
- Keep the layers visibly distinct:
  - **Motive / goal:** why the character cares, drawn from authored motive, current needs, and relevant memories when available.
  - **Mission:** who asked for what and whether the character accepted it; an accepted mission can become the character's own pursuit.
  - **Pursuit:** the character's longer undertaking and reason, with its target/place, time window, requirements, supplies, checked progress, and finish/report/return conditions when those fields exist.
  - **Schedule:** the relevant time, date, season, weather, or routine cue and whether it is due. Present it as a reminder to consider, not an order that decides the character's response.
  - **Short-term plan:** the current ordered approach, next step, destination, and any interruption/adaptation. A changed plan can leave the pursuit intact.
  - **Activity:** the ongoing thing visibly happening at a place, including its current state/effects and duration or stop condition when available. Keep its world recipe separate from the pursuit and the activity.
- Make missing, unknown, completed, paused, refused, and interrupted information legible without fabricating values. Show a specific object or location only when the runtime actually identifies it.
- Use the same labels and facts for LLM-driven and simple NPCs. Where available, show whether a pursuit/plan was chosen by the character, assigned, or selected by deterministic background rules; neither representation turns a pursuit into a forced script or an artificial reward contract.
- Exercise the view with authored content that demonstrates the separation between layers: Vekka's scouting pursuit (remembered tracks, supplies, return/report to Zikka, and a conversation that interrupts travel); Grandma's 06:00 food reminder; and James traveling home for the sleeping Activity on a bed until rested. Show the plan changing or being reconsidered while the pursuit's reason remains understandable.
- Verify the Mind entry point from a selected character and inspect the complete view at the top and bottom, including empty and populated states. Memory-focused controls must continue to work, and the view must refresh from the current character/runtime state after a turn or interruption.

## Current verified surface

In the live Kraktooth goblin camp, the character inspector has four tabs: Inventory, Bio, Images, and Advanced. The Bio tab contains 27 inspector sections and 95 visible controls. Its 🧠 Mind button opens a separate **Memory Mind — Vekka** dashboard with memory totals, people derived from memories, a timeline and filterable memory list, memory detail, and activation/accessibility information. This task grows that existing memory-centered entry point into the broader character Mind described above; it does not repeat task-691's memory-dashboard work.

## Sequencing and design references

Build against the runtime data provided by pursuit selection/execution (tasks 704 and 702), the existing schedule cue layer (task-409), and Activity state. Use [[Character Pursuits]] as the vocabulary and prompt-format reference. Keep [[Activities & States]] as the Activity behavior reference. The UI may present only fields that are actually implemented and available; it must not imply that the future pursuit prompt block or all pursuit fields are already wired.
