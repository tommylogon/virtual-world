---
group: Agent AI & Behavior
---
# Stateful Actions Over Time

**Filed**: 2026-07-30  
**Priority**: Medium  
**Status**: In Review — implemented 2026-08-07, verified live against the running server (rest → tick → stand, sleep → blocked movement → wake) and 612-test suite. Pending browser E2E (agent turns skip busy characters, activity line in prompt).

---

## What was built (verified implementation)

- **`Player.activity`** field (dict: `type`, `started_at_tick`, `target_item`, `duration_ticks`, `elapsed_ticks`, `visible`) + serialization in `to_dict`/`serialization.py`.
- **`engine/activities.py`** — `ActivitySystem`: start/end/interrupt, per-tick progress (`tick_activity`), wake (command/damage/loud-noise perception save/natural/full energy), instant `strip_to_pile` / `dress_from_pile` with `clothing_pile` container nodes, `bathe` chain (strip → pile → bathing → auto-dress).
- **Commands** (`routes/action.py` + facade): `rest`/`sleep [N] [on item]`, `wait [N]`, `meditate [N]`, `bathe [in item]`, `sit`, `lie down`, `stand`, `wake [name]`, `stop`, `strip`/`undress`, `dress`.
- **Central activity gate** in `/api/action`: sleeping/bathing block most commands; resting/waiting/meditating/sitting/lying-down auto-interrupt when the character does anything else.
- **Tick integration** (`tick_manager.py`): activities advance once per `tick_turn`; loud noise can wake a sleeper (WIS save DC 10). Damage wakes sleepers / interrupts activities (`effects.py` `handle_damage` + `combat.py`).
- **Visibility**: turn events "[name] is sleeping in the bed." for other characters (WITNESSED), activity flavor in the area "people here" list, `players_in_area` now carries `activity`, agent prompts include `Activity:` in `=== YOUR STATE ===` and the people list.
- **Turn/agent handling**: `agent-engine.js` `_isBusy` skips busy/sleeping characters; simple NPCs (`npc_behaviors.py`) skip when sleeping/unconscious/in an activity.
- New states `resting`/`meditating`/`busy` added to `CONDITION_HIERARCHY` (additive).

## Deviations from the original spec (owner-approved 2026-08-07)

- **No fast-forward anywhere** — the old `rest()` loop (tick_manager.py:456) that simulated N ticks synchronously was removed. The clock advances once per full turn cycle for everyone.
- `sleep` stays state `"sleeping"` (existing machinery) rather than the task's `"unconscious"` mapping.
- **Strip/undress are instant** but now drop clothes into a `clothing_pile` container node (graph-based, Option A). Full stateful one-layer-per-turn dress/undress is a deferred follow-up.
- The D&D conditions table (prone/frightened/charmed/...) was **not** added — activities use the existing conditions/state machinery.

---

## Summary

Handle character actions that set a state over time — bathing, sleeping in a bed, waiting, meditating — where the character enters a continuous state that progresses turn-by-turn until complete or interrupted.

---

## Problem

Currently all actions are atomic single-turn commands: `wear hat`, `go north`, `take apple`. There's no way to do something that takes multiple turns or sets a sustained state. Sleeping in a bed should restore energy over several ticks. Bathing should set the character to be using the bath, preferably after undressing (which mans we need a way to also quicly dress or undress so charatcers dont need 15 turns to get undressed for a bath. )

When multiple characters act in turn, stateful actions also need to be interruptible and coexist with others. other should see a charatcer use a item, take a bath or sleeping in a bed or chair etc

## Requirements

### Action States
- `resting` — energy regen per tick, can be interrupted by danger
- `sleeping` — faster energy regen, unaware of surroundings, must be woken up
- `bathing` — multi-stage: undress → wash → dry → dress, hygiene increases per stage
- `waiting` — advance time, do nothing, interrupted by anything
- `meditating` — sanity regen, reduced awareness
- `sitting` / `lying down` — minor energy regen

### Quick Dress/Undress (Graph-Based, Time-Based)
- Stripping/undressing is itself a **stateful action** that takes multiple turns
- Each turn removes one layer: outermost → innermost (reverse order of `player.equipped[slot]`)
- A `strip all` command starts the undress chain — character is "busy undressing" for several turns
- Dropped clothes form a **pile** in the room — a single connected group rather than scattered items:
  - Option A: Create a `clothing_pile` graph node that acts as a container, with edges to each item
  - Option B: Tag dropped items as `pile: "clothing_pile_<char>"` so they render/group as one
  - Option C: Use the edge refactor's new semantics to link items into a cluster
- The pile is physical — others can examine it, pick items from it, steal from it
- A `dress` command reverses the process: pick up the pile and re-equip layer by layer per turn
- The `bathe` action can trigger auto-undress → bathe → auto-dress as a chained sequence
- Being caught mid-undress (interrupted) leaves partially dressed with some items in the pile
- No `player.stripped_items` array — the graph IS the state via edges

### Visibility to Other Characters
- Stateful actions should be visible to others in the same room via area events
- Sleeping in a bed → event: `"[name] is sleeping in the bed."`
- Bathing → event: `"[name] is bathing in the bath."`
- Sitting → event: `"[name] sits by the fireplace."`
- Using an item continuously (e.g. reading) → event: `"[name] is reading a book."`
- These events persist in the area for the duration of the activity
- When the activity ends, a follow-up event is logged: `"[name] finished bathing."`

### Implementation

Two distinct layers:

**`player.activity`** — what the character is *doing*. Visible to others, drives prompt context.  
**`player.conditions`** — what the character is *experiencing*. Mechanical effects on capabilities.

Activities *cause* or *require* conditions, but they're separate concepts. Example: sleeping is an activity that applies the `unconscious` condition. Being unconscious doesn't mean you're sleeping — you could be KO'd.

#### player.activity (what are you doing)
```python
player.activity = {
    "type": "sleeping",       # sleeping, resting, bathing, undressing, dressing, meditating, waiting
    "started_at_tick": 123,
    "target_item": "bed",     # the object being used (bed, bath, chair, etc.)
    "visible": True           # whether other characters can see this activity
}
```
- Visible to others in area events: `[Lyrie] is sleeping in the bed.`
- Injected into prompts: "You are currently sleeping in the bed."
- Cleared when the activity ends or is interrupted
- Purely descriptive — no mechanical effects

#### Conditions (what are you experiencing)
Standardized conditions with D&D-style definitions (from existing system + expansions):

| Condition | Effects | Applied by |
|-----------|---------|------------|
| `blinded` | Can't see, fails sight-based checks | Blindfold, darkness magic, eye injury |
| `deafened` | Can't hear, fails hearing-based checks | Loud explosion, ear injury |
| `unconscious` | Incapacitated, unaware of surroundings, drops held items, auto-fails STR/DEX saves, attacks at advantage, crits at 5ft | Sleeping, KO, extreme damage |
| `paralyzed` | Incapacitated, can't move/speak, auto-fails STR/DEX saves, crits at 5ft | Poison, magic, spinal injury |
| `petrified` | Incapacitated, unaware, turned to stone, resists all damage, immune to poison/disease | Basilisk gaze, magic |
| `poisoned` | Disadvantage on attack rolls and ability checks | Poison, toxic environment, bad food |
| `restrained` | Speed 0, disadvantage on attacks and DEX saves, attackers have advantage | Grapple, bonds, webs |
| `prone` | Crawl-only movement, disadvantage on attacks, melee attackers have advantage | Trip, shove, fall |
| `frightened` | Disadvantage on checks/attacks while source in LoS, can't move closer | Fear effect, horror |
| `charmed` | Can't attack the charmer, charmer gets social advantage | Persuasion, magic |
| `invisible` | Impossible to see, stealth advantage, attacks against have disadvantage | Spell, item, stealth |
| `stunned` | Incapacitated, can't move, speaks falteringly, auto-fails STR/DEX saves | Strong hit, magic |
| `exhaustion` | 6 levels: 1=disadvantage on checks, 2=speed halved, 3=disadvantage on attacks/saves, 4=HP halved, 5=speed 0, 6=death | Starvation, exposure, overexertion |
| `grappled` | Speed 0, ends if grappler is incapacitated or target is moved out of reach | Grapple action |

#### Activity → Condition mapping

| Activity | Causes condition | player.state |
|----------|-----------------|--------------|
| `sleeping` | `unconscious` + energy regen | `"unconscious"` |
| `resting` | `prone` + minor energy regen | `"resting"` |
| `bathing` | (none — just busy) + hygiene regen | `"busy"` |
| `undressing` | (none — just busy) + per-tick layer pop | `"busy"` |
| `dressing` | (none — just busy) + per-tick layer equip | `"busy"` |
| `meditating` | (none — reduced awareness) + sanity regen | `"meditating"` |
| `waiting` | (none — just advancing time) | — |

- Conditions process per tick via the existing `PERIODIC_CONDITIONS` / `ConditionsSystem`
- Multiple conditions stack independently (blinded + poisoned + prone all apply)
- Activities are interruptible — damage, loud noise, or another action cancels both activity and its associated condition
- `unconscious` from sleeping lifts on: damage, loud noise, `wake` command, or natural timer
- Conditions can chain via triggers: undressing completes → triggers bathing → triggers dressing

### Multi-character
- Agent turn queue must skip characters engaged in multi-turn activities or handle them specially
- Sleeping characters don't act until woken
- Threat detection: if danger enters the area, sleeping characters should get a perception check to wake up
- Other characters in the same room see the active character's state in their witnessed events
- The witnessed event includes the item/object being used (e.g. "the bed", "the bath")

## Related

- [[todo/gameplay/task-104-multi-action-command-sequences|task-104: Multi-action command sequences]]
- [[todo/gameplay/task-90-delayed_event_queue|task-90: Delayed event queue]]
- `engine/tick_manager.py`
