# Trait & Condition System (Design)

**Status**: Design — agreed 2026-08-07. **Phase 1 (condition catalog + per-condition storage) implemented 2026-08-07**; Phases 2–4 pending (see dev_tasks). Advantage/disadvantage explicitly **deferred**.

---

## Philosophy: two concepts, one vocabulary

| Concept | Question it answers | Durability | Source |
|---|---|---|---|
| **Trait** | *What are you?* | Durable identity | Assigned at creation, acquired through experience |
| **Condition** | *What is happening to you?* | Temporary (until countered or duration ends) | Traits, triggers, items, environment, combat |

- **Conditions** are a **standardized catalog** — D&D Appendix A-*inspired* (vocabulary, not ground truth; realism wins). Each condition has ONE canonical definition (what it does, how it ends) so `blinded` means the same thing whether it came from a trait, a flashbang trigger, or the dark. Conditions **stack as instances** (5 vials of poison = 5 `poisoned` instances, drains sum); gates/mods are presence-based, and the catalog `stack` field decides whether re-application accumulates, refreshes, or no-ops.
- **Traits** are identity. A trait may:
  1. **Grant a permanent condition** while active (`blind` trait → permanent `blinded`; `paranoid` → near-permanent `frightened`),
  2. Have **bespoke mechanics** no condition covers (`medium` → can't fit tiny ways, `ghost` → unlocks vanish/manifest, `glutton` → hunger decay ×2),
  3. Carry an optional **LLM behavior prompt** attached to personality,
  4. Subscribe to **world events** (`save_on`) for consequences — the claustrophobic flow.
- One code path applies conditions regardless of source (`player.add_condition`); the catalog makes them data, not scattered checks.
- The catalog is a **vocabulary, not a library** — each entry defines only what a condition fundamentally *is* (poisoned, prone, restrained, charmed...). All variation comes from the instance (`duration`, `source`, `level`, `periodic` overrides, `extra_conditions`, `ends_on`) — never a new catalog entry per poison/disease. A worse poison is a new instance, not a new word.

---

## Part 1 — The Condition Catalog

Conditions live as data: a `CONDITION_DEFINITIONS` registry (currently partially hardcoded in `player.py` — `CONDITION_HIERARCHY`, `BLOCKING_CONDITIONS`, `PERIODIC_CONDITIONS`, `CONDITION_EXCLUSIONS`). The design moves each condition's behavior into one definition dict.

### Condition definition schema

```jsonc
{
  "id": "blinded",
  "name": "Blinded",
  "description": "A blinded creature can't see and automatically fails any check that requires sight.",
  "blocks_actions": false,        // can't take actions (incapacitated)
  "blocks_movement": false,       // speed effectively 0
  "blocks_speech": false,         // can't speak
  "auto_fail_checks": ["sight"],  // sense-based checks auto-fail (sight, hearing)
  "auto_fail_saves": [],          // ability saves that auto-fail (e.g. STR, DEX)
  "attack_mod": 0,                // your attack rolls get -N
  "defense_mod": 0,               // YOUR defense; subtracted from incoming attacks (negative = easier to hit)
  "speed_mult": 1.0,
  "movement_mode": null,          // "crawl" (prone) — only movement mode allowed
  "drops_held_items": false,      // unconscious: drop what you carry
  "periodic": {},                 // per-tick vital drains, e.g. {"Hunger": -2}
  "ends_on": [],                  // actions that end it: ["stand"] (prone), ["wake"] (unconscious)
  "known": true,                  // self-evident to the agent (grappled/blind/mute/...) vs hidden (poisoned/sick/charmed)
  "symptoms": {},                 // progression-keyed perception lines the AGENT sees, not the flag:
                                  //   {"5": "A queasy twist in your stomach.", "3": "Cold sweat and cramps.", "1": "Everything spins."}
                                  //   key = min ticks remaining (or `level` for leveled diseases); highest threshold reached wins
  "default_duration": null        // ticks; null = until countered
```

> **Agent perception.** Agents never see raw condition names for hidden conditions — the prompt renders the `symptoms` line for the current stage (`known: false`), or a physical description for `known: true` ones. A freshly-stabbed poisoned agent feels nothing yet; the "you feel sick" only arrives as the timer drops. The agent's reaction memory is their knowledge; the system state is the source of truth.

> **No advantage/disadvantage for now.** Each condition maps to concrete engine hooks (`attack_mod`, `defense_mod`, `auto_fail_*`) instead. If a real advantage system ever lands, the catalog slots it in without changing the data shape.

### Proposed catalog (engine mapping)

| Condition | Engine behavior (no-advantage flavor) | Ends by |
|---|---|---|
| `blinded` | auto-fail sight checks; `attack_mod` −2; `defense_mod` −2 (attackers +2) | duration / remove |
| `deafened` | auto-fail hearing checks; can't benefit from audio cues (sound wakes, `recent_hearing`) | duration / remove |
| `charmed` | can't attack the charmer (needs `source` ref); charmer gets `defense_mod` +2 vs you in social checks | source leaves / removed |
| `exhaustion` (6 levels) | L1 check −2 · L2 speed half · L3 attack/saves −2 · L4 HP max half · L5 speed 0 · L6 death; levels accumulate | long rest, food+drink, raise |
| `frightened` | check/attack −2 while source present; source-type gates: **way** — won't use that passage again, **area** — won't re-enter, **item** — won't touch, **character** — can't attack them & won't enter an area they're in (unless the source is known gone) | source gone / remove |
| `grappled` | speed 0; escape = STR save (already in `grapple.py`) | escape / grappler incapacitated |
| `incapacitated` | `blocks_actions` | varies |
| `invisible` | `defense_mod` +3 (hard to target); heavy-obscured for hiding | attack / reveal |
| `paralyzed` | `blocks_actions`+`blocks_movement`+`blocks_speech`; auto-fail STR/DEX saves | duration |
| `petrified` | incapacitated; damage resistance; immune poison/disease | remove / magic |
| `poisoned` | check/attack −2 | duration / antidote |
| `prone` | `movement_mode: "crawl"`; attack −2; `defense_mod` −2 (attackers +2) | `stand` |
| `restrained` | speed 0; attack −2; `defense_mod` −2; auto-fail DEX saves | escape |
| `stunned` | incapacitated; can't move; faltering speech; auto-fail STR/DEX | duration |
| `unconscious` | incapacitated; drops held items; auto-fail STR/DEX; `defense_mod` −5 (attackers +5) | `wake` / damage / timer |
| `sleeping` *(engine, existing)* | lighter than unconscious — blocks actions, must be woken; `recent_hearing` limited | `wake`, damage, loud noise (WIS save), full energy |
| `mute` *(engine addition)* | `blocks_speech`; can't `speak`/`whisper`/`shout`/`scream` | duration / remove |
| `sick` *(engine, existing)* | periodic Hunger/Thirst drain | duration |

### Storage change (flagged)

Today `player.conditions` is a **set** — no per-condition metadata. Charmed/frightened need a `source`, exhaustion needs a **level**, conditions need per-instance durations. The design moves to `player.conditions: dict[condition_id, {duration, source, level}]` (serialized in `to_dict`/`serialization.py`). `has_condition`/`add_condition`/`remove_condition` keep their API shape so call sites stay stable. **Done (Phase 1)** — the catalog lives in `player.py` (leaf module; `engine/conditions.py` consumes it), `state_timer` is now a backward-compat property over the state condition's duration, and `process_tick` expires each timed condition independently (the old shared-timer bug is gone). Instances also carry optional `periodic` overrides, `extra_conditions`, and `ends_on` so one catalog entry covers infinite variation (see the task file's condition-instance reference examples).

---

## Part 2 — Trait definition schema (v2)

Current traits (see [[Characters/Traits System]]) already carry `effects` (vital multipliers, dark vision, slots, etc.). The schema grows:

```jsonc
{
  "id": "claustrophobic",
  "name": "Claustrophobic",
  "category": "mental",
  "params": null,

  // existing mechanical effect keys (unchanged)
  "effects": { "vital_multiplier": { "Sanity": 0.5 } },

  // permanent conditions while this trait is active
  "grants_conditions": [],

  // world-event consequences (Part 3)
  "save_on": [
    {
      "event": "crawl_tight_way",
      "stat": "WIS",
      "dc": 12,
      "on_fail": [
        { "condition": "frightened", "duration": 3 },
        { "vital": "Sanity", "amount": -10 }
      ]
    }
  ],

  // LLM behavior text — appended to personality (hidden by default; only
  // what the character shows is visible to others)
  "behavior_prompt": "You feel your chest tighten in small, enclosed spaces. You need open air and an escape route nearby.",

  // mutually exclusive with
  "conflicts": ["agoraphobic"]
}
```

**Existing effect keys** (`engine/traits.py`): `action_cost_mod`, `vital_multiplier`, `vital_mod_per_tick`, `dark_vision`, `is_slasher`, `hostile`, `allergic_to`, `immune_to_condition`, `block_sense`, `disable_slot`, `hp_regen_multiplier`, `energy_curve`, `group_energy_drain`, `social_gain`, `no_entertainment_decay`, `wake_threshold`.

**New keys to add** (small, mechanical): `skill_check_mod` (`{"Stealth": 2, "Athletics": -2}`), `save_bonus` (`{"DEX": -2}`), `move_cost_mod`, `carry_capacity_mod`. These plug into the task-159 `saving_throw`/`skill_check` paths and movement costs — no new systems.

---

## Part 3 — Trait × world consequences (`save_on`)

The engine emits **event hooks** at natural moments; traits with a matching `save_on` entry fire a save, and failures apply listed effects. Fully data-driven — no trait-specific code in the movement/combat/narration modules.

### Event catalog (v1)

Every event carries a `source` and a `source_type` in context so trait-fears land
on the right gate (way/area/item/character). A `save_on` entry may declare a
`source_type` to restrict itself to one kind of source.

| Event | Fires when | `source` / `source_type` |
|---|---|---|
| `crawl_tight_way` | crawling through a tight/small passage (task-187) | the way / `way` |
| `climb_way` | attempting a climb (success or failure) | the way / `way` |
| `jump_way` | attempting a jump (success or failure) | the way / `way` |
| `enter_area` | entering an area whose tags match the trait's `area_tags` | the area / `area` |
| `see_item` | an item with a matching `item_tags` becomes visible | the item / `item` |
| `loud_noise` | loud noise in the current area (extends the task-131 wake-on-noise hook) | `area` / `area` |
| `takes_damage` | character takes damage (extends the task-131 wake-on-damage hook) | attacker name (combat) / `character`; `damage` (traps/effects) / none |
| `alone_in_dark` | ambient light < threshold AND no other character in area | — / none |

### Reference flow — the claustrophobic crawl

1. Character with `claustrophobic` crawls through a `tight` way (`crawl <direction>`).
2. Movement emits `crawl_tight_way` with `{passage_size: "tiny"}`.
3. Trait resolver finds the matching `save_on` entry → **WIS save DC 12** (uses `world.skills.saving_throw`).
4. **Fail** → applies `frightened` (3 ticks) + Sanity −10, logs *"The walls close in around you. Your heart pounds."*.
5. **Success** → flavor-only line, no mechanical effect.
6. The `frightened` condition then affects the character's checks/attacks until it ends — a real, visible spiral.

More examples:

| Trait | Event | Save | Failure result |
|---|---|---|---|
| `acrophobic` | `climb_way` | WIS | `frightened` + Sanity loss; falls prone on failure |
| `agoraphobic` | `enter_area` (tag `open`) | WIS | Sanity drain per tick while in the area (via `periodic` or repeated hook) |
| `hemophobic` | `see_item` (tag `blood`/`corpse`) | WIS | `nauseated`/`poisoned`-style condition + Sanity loss |
| `pyrophobic` | `see_item` (tag `fire`) | WIS | `frightened` |
| `paranoid` | `loud_noise` | WIS | `frightened` + forced `examine` the source |
| `cowardly` | `takes_damage` | WIS | forced retreat (move away) on fail |

---

## Part 4 — Acquired / dynamic traits

Traits are no longer creation-only. The trigger system (which already applies conditions) gains an **`apply_trait` effect**:

```json
{ "type": "apply_trait", "params": { "trait": "trauma_near_death", "target": "self" } }
```

Acquisition patterns:
- **Experience**: first time HP hits < 10 and survives → `scarred`/`grizzled`. Starvation stretches → `frail`. Long confinement → `claustrophobic`.
- **Items/places**: repeated use of an alchemy bench → `calloused`; living in the mansion too long → `mansion_haunted` flavor trait.
- **Reverse**: `remove_trait` effect; traits can decay (a healed phobia fades after enough exposure).
- Acquired traits feed the same prompt pipeline, so the LLM *lives* the change — no manual JSON edits mid-playthrough.

---

## Part 5 — Prompt / personality integration

- Each trait's `behavior_prompt` is appended to the character's personality text consumed by `buildTraitBehaviorContext` (`static/js/agent/prompt-builder.js`) — the LLM reads it as identity.
- **Traits are inherently hidden.** What others perceive comes from `description`/`base_description` and behavior — never from the trait list. A character pretending to be blind is caught by agents watching them act, not by a system flag. (`hostile`/`is_slasher` remain internal threat markers.)
- No trait-based "you notice X" discovery mechanic — observation is the agents' job.

---

## Part 6 — Phased roadmap

1. **Condition catalog + storage refactor** — `CONDITION_DEFINITIONS` data, `player.conditions` set → instances (`{duration, source, level}`), keep API shape. Map existing conditions (sleeping/sick/blind/deaf/etc.) into the catalog. Add `mute`.
2. **Trait schema v2** — `grants_conditions`, `behavior_prompt`, `conflicts`, new effect keys (`skill_check_mod`, `save_bonus`, `move_cost_mod`, `carry_capacity_mod`) wired into saves/checks/movement; editor/library fields for the new keys.
3. **`save_on` event hooks** — event emitter in movement/combat/area/narration + trait resolver; the claustrophobic crawl flow as the reference implementation + tests.
4. **Acquired traits** — `apply_trait`/`remove_trait` trigger effects + a few scripted acquisitions + serialization.
5. **Deferred** — real advantage/disadvantage dice mechanic.

---

## Related

- [[Characters/Traits System]] — current implementation
- [[Characters/Activities & States]] — persistent activities (wake-on-damage/noise hooks reused by `save_on`)
- [[Rules Engine/Triggers & Effects]] — effect vocabulary, where `apply_trait` joins
- [[dev_tasks/review/characters/task-trait-condition-system-v2|task: Trait & Condition System v2]]
