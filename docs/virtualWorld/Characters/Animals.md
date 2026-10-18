---
type: doc
tags: [system/characters]
---

# Animals

## What it is

An animal in VirtualWorld is a character, not a second kind of thing. A rabbit, a rat, a boar, a wolf, a bear, a frog, a raven and a worg are all `Player` objects with the same vitals, conditions, memories and tick loop as a goblin or a human. What makes them animals is data: an `animal` tag, a `species` string, a small `size`, and usually a scripted behaviour instead of an LLM driver. A rabbit in a burrow and a goblin in a camp run through the same turn.

## What you can see and do

In play you meet animals the way you meet anyone. They appear in the area description ("an animal is here"), they wander between areas, they flee, they can be attacked, and when killed the ones marked as meat leave a carcass you can take and eat. A rabbit burrow quietly adds rabbits while the meadow holds fewer than four. A rat in the Kitchen squeaks, flees to cover, hides, then creeps back out to gnaw a crust when Hunger drops below 80. A boar standing unbothered in a goblin bedroom is the current authoring gap, not the design. See [[Animal Fear]] for why that happens.

As an author you can add any library animal to a scenario, write a new one as `data/library/characters/<name>.json`, set `species`, `size`, `tags`, `carcass`, `simple_npc` and `npc_behavior`, give it `fear_tags` and behaviour trees, gate spawns with `tagged_count`, and tune need servicing per species.

## How it works

### Identity: species, tags, size

`species` (`engine/species.py`, task-549) is a free-text kind on the `Player`, normalised to lowercase. `None` means no profile applies and every service is permitted. Compound names inherit from the last word, so `forest goblin` reads as `goblin`. Profiles only declare exclusions. `animal`, `beast` and `quadruped` cannot use `relief` fixtures. `undead` and `construct` cannot use `food` or `drink`. `goblin`, `human` and `elf` can use everything. An unknown species permits everything rather than nothing.
`tags` is where `animal` lives, plus the specific kind. `is_animal()` (`engine/vitals.py`) is one check: `animal` in tags. Animals skip the Social, Sanity and Entertainment low-need handling.

`size` (`engine/size.py`) is `tiny`, `small`, `normal`, `huge`, `giant` or `titanic`. Rabbit, rat and Fluffy are `tiny`. Silver-Talon is `small`. Old Iron-Back is `huge`. Size feeds way `max_size` gating, per-area occupancy footprints (task-653), and the scale-correct ability curve (task-606).

Library animals today, 11 of 74 character files carry `animal`:

- `rabbit.json`: species rabbit, tiny, wander, `carcass: carcass`, tags animal, rabbit, small, prey. The task-427 template.
- `rat.json`: species unset, tiny, stationary, `simple_npc true`, tags animal only. Richest scripted animal: enter-area squeak, proximity flee, hide, forage, eat, ambient chatter.
- `Tusker.json`: species boar, normal, wander, tags male, animal, boar.
- `Rag-Tail.json`: species wolf, wander.
- `Old Iron-Back.json`: species bear, huge, wander.
- `Croak-Mother.json`: species unset, tags female, animal, frog.
- `Silver-Talon.json`: species bird, small, tags animal, bird, raven.
- `Shadow-Pelt.json` and `shadow_pelt.json`: species unset, tags male, animal, worg, predator, pack. Duplicate files, and `pack` without a colon so not a real pack.
- `fluffy.json`: species sheep, tiny, idle, tags animal, sheep, small, illusory, companion, `carcass null`. Conjured, not meat.
- `whiskers.json`: species unset, tags animal, cat.

Four files have `species None`: rat, Croak-Mother, Shadow-Pelt x2, whiskers. They behave as default characters with no relief exclusion and lifespan 80.
### Needs: the same ladder, one exemption

Background animals run the same survival ladder (`engine/background_simulation.py`) as everyone else: drink, eat, relieve, forage, rest. Two differences.

Relief (task-551 permits relief anywhere): species decides whether a fixture helps. An animal in a latrine still relieves where it stands, pays the same dignity cost, gets no comfort, and the lived log records `why=species:animal`. Recorded, not announced.

`ANIMAL_SKIPPED_VITALS`: Social, Sanity and Entertainment low-need branches do not fire for tagged animals.

### Fear and packs

Fear is a separate note because it is the live tension question. See [[Animal Fear]]. In short: `fear_tags` on the afraid character intersected with the source's tags, co-presence only, source-gated `frightened` for 30 game minutes, flee or hide or freeze or shout. The camp boar is ignored because no goblin fears `animal` or `boar` and the scenario copies dropped `species`.

Packs (`engine/pack.py`, task-354) are dormant by design. Identity is a `pack:<name>` tag, awareness is `packmates_in` over the same area or N graph hops. The coordinated target comes from the nearest packmate and is stamped by `call_for_help` one room out, throttled per pack per 10 ticks. No movement, no formation, no flanking, by scope. Nothing shipped carries a real `pack:` tag, so the surface is inert and a test pins that.
### Spawners, caps, death, meat

Spawning is a separate note because the trigger pattern deserves its own home. See [[Creature Spawners]]. In short: a spawner is a source item, not a creature. Growth counter plus `tagged_count rabbit < 4` plus `spawn_character rabbit` into the burrow's own area. Death with `carcass_item` set drops a fresh library food item with an authored depleting `on_eat`. Only rabbit sets `carcass` today.
### Space, age, control

Occupancy (task-653, `engine/occupancy.py`) sums footprints from size tiers, non-linear, default budget 100 per area. Ghosts cost 0. A tiny spider still costs 1. Dead characters do not count. Report only, never a movement gate.

Lifecycle (`engine/lifecycle.py`, task-735) tracks `birth_tick`, `life_stage` (child, adolescent, adult, elder) and an annual old-age roll past `SPECIES_LIFESPAN` (human 80, elf 300, dwarf 200, goblin 45, default 80). No animal row exists, so a rabbit has a human lifespan. Pregnancy and birth moved to task-846 and are not built.
The read model `lifecycle.status()` serves `age`, `life_stage`, `lifespan` and `birth_tick_known` on `GET /record`. None of this is surfaced in the Mind persona tab today.
Control tiers: `simple_npc true` runs scripted `process_simple_npcs` with `npc_behavior` (wander, flee, stationary) plus authored `behaviors[]` trees. `simple_npc false` means human-driven (`autonomy false`), LLM agent, or background simulation (`simulation_mode background`). All three share the `Player` class.

Explicit non-goals from task-427, still true: no ecology, no predator-prey simulation, no breeding genetics, no taming, no multi-species food webs.
## Where it lives

Identity and services: `engine/species.py`, `player.py` (`species`, `size`, `tags`, `fear_tags`, `carcass_item`, `simple_npc`), `engine/size.py`, `engine/vitals.py` (`is_animal`), `engine/character_record.py` (task-457 audit).
Behaviour: `engine/npc_behaviors.py` (`process_simple_npcs`, `slasher_hunt`), `engine/background_simulation.py` (survival ladder, relief wiring, `run_fear_pass` first), `engine/background_social.py` (threat, social, approach, theft passes), `engine/fear.py`, `engine/pack.py`, `engine/combat.py` (generic, no animal branch), `engine/occupancy.py`, `engine/lifecycle.py`, `engine/foraging.py`.
Death and spawning: `engine/ghost.py` (`spawn_body_item`, `_spawn_carcass`), `engine/effects.py` (`_hydrate_character` copies `carcass`), `engine/effect_handlers/spawn.py` (spawn into the triggering item area).
Triggers: `engine/triggers/condition_tree.py` (`tagged_count`). Saves: `engine/serialization.py` (both serializers carry `species`, `size`, `fear_tags`, `carcass_item`, `simple_npc`).
Data: `data/library/characters/*.json` (11 animal-tagged), `data/library/items/rabbit_burrow.json`, `data/library/items/carcass.json`, meat and trap items, `data/scenarios/kraktooth_goblin_camp.json` (the camp animals).
API: `POST /api/players/<name>` accepts `species`, `size`, `tags`, `fear_tags`, `simple_npc`, `npc_behavior`, `npc_action_interval`, `behaviors`. It does not accept `carcass_item`. `GET /api/state` serves `species`, `size`, `fear_tags`, `carcass_item`, `birth_tick`, `life_stage`. `GET /record` serves `lifecycle` status.
UI: Character Inspector Bio and Mind, Mind persona tab backed by `GET /record`. No lifespan, species detail, or carcass control is surfaced there today.

Tests: `tests/test_species.py` (20), `tests/test_creature_spawners.py` (14), `tests/test_pack_logic.py` (32), `tests/test_fear_threat_response.py` (21), `tests/test_occupancy.py` (40), `tests/test_lifecycle.py` (9).

## See also

- [[Characters Overview]] - the three control tiers sharing one `Player` class
- [[NPC Behavior System]] - scripted simple NPCs and behaviour trees
- [[Background Simulation]] - the survival ladder and social passes animals run
- [[Traits System]] - traits including `slasher`, `hostile` and size traits
- [[Vitals System]] - needs, decay, and the animal exemptions
- [[Gameplay/Search & Forage]] - skill-gated finds, not live hunts
- [[Rules Engine/Conditions System]] - `frightened` and how it gates behaviour
- [[Library System/Tags System]] - the vocabulary including `animal`, `predator` and `pack:`

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Activities & States]], [[Animal Fear]], [[Background Simulation]], [[Character Images & Expression Packs]], [[Characters Overview]], [[Creature Spawners]]

<!-- connected:end -->
