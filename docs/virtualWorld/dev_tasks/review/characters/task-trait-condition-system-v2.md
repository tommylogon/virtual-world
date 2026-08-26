---
group: Characters
---
# Trait & Condition System v2

**Filed**: 2026-08-07
**Priority**: High
**Status**: Complete — Phases 1-4 implemented 2026-08-07 (conditions system, trait schema v2, save_on hooks, acquired traits; 695 tests). Moving to review for audit.

---

## Vision (one paragraph)

Traits are **what you are** (durable identity with mechanics + optional LLM personality text); conditions are **what is happening to you** (a standardized D&D-inspired catalog with one canonical definition each). Traits may grant permanent conditions (`blind` → `blinded`), have bespoke mechanics (`medium` → can't fit tiny ways, `ghost` → vanish/manifest), and subscribe to **world events** (`save_on`) so personality has consequences — the claustrophobic crawl is the reference flow. Traits are inherently hidden; what others see comes from descriptions and agent observation, never system flags. No advantage/disadvantage dice for now.

## Decisions (owner-confirmed 2026-08-07)

- **Traits and conditions are separate concepts.** No merged effect system. Conditions = standardized catalog; traits = identity that grants/performs.
- **D&D is inspiration, not ground truth.** The catalog borrows the *vocabulary* (Appendix A condition names, one-canonical-definition idea) but rules bend to simulation realism: conditions stack as instances, drains accumulate, and anything that "feels right" for a living world beats a tabletop edge case.
- **Conditions stack as instances — drains accumulate, gates don't.** `poisoned` can have N concurrent instances (5 vials of different poisons = 5 instances each ticking its own `periodic`; 4 rat-poisons eaten back-to-back = 4 doses, HP drain sums). Gates/mods are **presence-based**: any instance of `blind` makes you blind — one `attack_mod`/`blocks_*`/`+X if target has condition`, never multiplied per instance. The catalog `stack` field controls re-application: `"accumulate"` (poisoned/sick → append), `"refresh"` (stunned/exhausted → extend duration / bump level), `"noop"` (grappled/restrained/blind/... → can't grab a grappled person or blind a blind person). `duration`/`source`/`ends_on` stay per-instance — a broken leg (`ends_on: [fix]`) is cured by `fix`; a knock-down `prone` (`ends_on: [stand]`) ends when you stand.
- **Agent perception — symptoms, not flags (owner 2026-08-07).** Agents never see raw condition names for hidden conditions. Each condition carries a `symptoms` dict keyed by progression (min ticks remaining, or `level` for leveled diseases) — the engine renders only the symptom line for the current stage, so a freshly-stabbed agent feels *nothing yet* and only "starts to feel sick" as the timer drops. `known: true` conditions (grappled/blind/mute/prone/stunned/paralysed/restrained/unconscious) are self-evident and render an immediate physical description instead. Instances can override `symptoms`/`known` (a fast needle venom gets its own onset curve). The agent's reaction memory ("I feel sick after that needle") becomes their knowledge — system state stays the source of truth (character-vs-system knowledge split). Optional follow-up: a Perception/Survival check to *diagnose* the condition name, otherwise the agent guesses from symptoms.
- **Atlas shows every instance (owner 2026-08-07).** Clicking a condition in the UI lists one entry per stacked instance — 4 vials = 4 cards under `poisoned`. Each card shows: what (condition + per-tick drain), how long (remaining vs forever), why (source), level, `ends_on`, and the current symptom line.
- **Traits hidden by default**; visibility comes from description fields. **No trait-based discovery mechanic** — agents discover by observing behavior.
- **Advantage/disadvantage deferred.** Conditions map to concrete hooks (`attack_mod`, `defense_mod`, `auto_fail_*`).
- Acquired traits via triggers: **agreed**. Traits can be mechanical and/or LLM prompt text attached to personality: **agreed**.
- Trait × environment consequences (`save_on`, owner-clarified 2026-08-07): `save_on` is a **trait** field — *when this world event fires, roll a save to keep it together; on failure, apply the listed effects* (uses task-159 `saving_throw`, e.g. WIS vs DC 12). For `claustrophobic` the owner's instinct is the spec: crawling through a small tunnel/air duct **rapidly drains Sanity** (and can apply `frightened`); the save is the character's chance to fight through the panic, not a gate that stops the drain.
- **Vocabulary, not library (relaxed 2026-08-07).** The catalog stays small (~20 conditions). All *variation* — dose, quantity, duration, drain strength, bundled extras — lives in the instance (`duration`, `source`, `level`, `periodic` override, `extra_conditions`, `ends_on`): 5 vials of poison are 5 stacked `poisoned` instances, 4 rat-poisons in a row are 4 doses. **But "no new condition" is a guideline, not a hard rule** — a genuinely *new effect*, something no existing condition covers, can still earn its own catalog entry. - disagree on no new condition per instance of a cndition
- **Instance schema grows** beyond `{duration, source, level}`: optional `periodic` (per-instance drain override), `extra_conditions` (bundled conditions applied as separate instances), `ends_on` (overrides the catalog default, e.g. broken leg → `["fix"]` not `["stand"]`).
- **Rule of thumb:** "new condition?" → first ask "new instance of an existing one?" Only add a catalog entry when the effect changes *what you can do* (prone, charmed, mute).
- **Trigger-level composition:** `apply_condition` passes `periodic`/`extra_conditions`/`source`/`level`/`ends_on` through; `process_tick` reads `instance.periodic` first then falls back to the catalog; resolution is `ends_on`/`source`-driven, not per-command.
- **Conditions stay a Python catalog** — not JSON-editable. Authoring happens in trigger params (already JSON in item/trap/way files).
- **`defense_mod` is YOUR defense (corrected 2026-08-07).** Combat applies `attack roll + attack_mod − target_defense_mod` — higher defense = harder to hit (the armor intuition). Helpless conditions (unconscious/sleeping/paralysed/stunned/blind/prone/restrained) use a **negative** `defense_mod` (−2 to −5), so the same formula hands the attacker +X: "if the target has the condition, attacker +X". Equipment armor stays separate (damage absorption via `_get_target_defense`).

## Phases

### Phase 1 — Condition catalog + storage refactor
- `CONDITION_DEFINITIONS` registry in `engine/conditions.py` (schema: `blocks_actions/movement/speech`, `auto_fail_checks/saves`, `attack_mod`, `defense_mod`, `speed_mult`, `movement_mode`, `drops_held_items`, `periodic`, `ends_on`, `default_duration`).
- `player.conditions` set → instances: `dict[condition_id, {duration, source, level}]`. Keep `add_condition`/`remove_condition`/`has_condition` API shape (call sites stay stable).
- Migrate existing conditions (`sleeping`, `sick`, `blind`, `deaf`, `paralysed`, `stunned`, `grappled`, `restrained`, `exhausted`, `unconscious`, ...) into the catalog; add `mute`.
- Serialization for per-condition instances (`to_dict`/`serialization.py`).
- Wire the hooks each condition maps to (movement mode for prone, drop-holds for unconscious, save auto-fails, attack/defense mods into combat).

**Phase 1 status — implemented 2026-08-07:**
- `CONDITION_DEFINITIONS` lives in `player.py` (leaf module — importing it from `engine/conditions.py` would be circular), re-exported/consumed by `engine/conditions.py`. Existing constants (`CONDITION_HIERARCHY`, `BLOCKING_CONDITIONS`, `PERIODIC_CONDITIONS`, `CONDITION_EXCLUSIONS`, `CONDITION_DEFAULT_TIMERS`) are now derived from the catalog.
- `player.conditions` is now `{condition_id: {"duration", "source", "level"}}`. `add_condition` keeps its signature (+ optional `duration`/`source`/`level`), exclusions still enforced, `state` property unchanged.
- `state_timer` is now a backward-compat **property** that reads/writes the current state condition's duration (call sites in tick_manager/combat/activities unchanged).
- `engine/conditions.py`: `apply_condition` sets per-instance duration; `process_tick` decrements each timed condition's own duration and expires them independently (fixes the old shared-timer bug where poisoned+stunned shared one countdown). Unconscious/sleeping stay engine-managed (tick_manager/activity wake logic owns their countdown).
- New helpers in `engine/conditions.py`: `get_condition_mods(player)`, `auto_fails_checks(player, sense)`, `auto_fails_saves(player, stat)`, `can_speak(player)`.
- Combat: condition `attack_mod`/`defense_mod` now feed the attack roll (combat.py). Saving throws: conditions with `auto_fail_saves` auto-fail (skills.py).
- `mute` condition added (`blocks_speech: true`); speech commands blocked in routes/action.py.
- Serialization: `conditions` serialized as instance dicts; legacy list-of-names saves migrate on load (`Player.load_conditions`).
- Tests: 16 new (instances, independent expiry, mute, mods, auto-fail, serialization round-trip, legacy migration). Suite: 628 passed, 1 skipped.

**Deferred from Phase 1**: ~~wiring `movement_mode` (prone) and `drops_held_items` (unconscious) into movement/inventory~~ — **implemented 2026-08-07**: prone forces `go` → crawl (climb/jump refused), `effective_speed` gates dash (`< 0.5` = too winded) and blocks movement entirely at 0 (exhausted level 6), and `drops_held_items` fires on unconscious/dead/sleep (hand items fall into the area via `ItemActions.drop_held_items`).

**Phase 1 follow-up (confirmed 2026-08-07):**
- **Catalog shrink:** remove `sleeping`/`resting`/`meditating`; add `prone`, `frightened`, `charmed`, `busy` (the single "occupied" condition for rest/meditate/wait/sit/lie/bathe — the activity carries the regen mix: rest = Energy +2 & Sanity +1, meditate = Sanity +2 & Energy +1). Final catalog: `awake, dead, unconscious, paralysed, stunned, grappled, restrained, exhausted, sick, poisoned, blind, deaf, mute, prone, busy, frightened, charmed`.
- **`sleep` is an activity that applies `unconscious`** — instance `{source: "sleep", ends_on: [wake, damage, loud_noise, energy_full], blocks_speech: false, drops_held_items: true}` (held items drop, mumbling allowed). Being attacked while asleep auto-fails saves like any unconscious character; the activity system owns waking.
- **`defense_mod` sign flip in combat** (no new math): `attack_mod += attacker_mods["attack_mod"] − target_mods["defense_mod"]`; helpless conditions carry negative `defense_mod` (−5 unconscious/sleeping/paralysed/stunned, −2 blind/prone/restrained) so the target's own reduction IS the attacker's +X.
- **`paralysed` keeps its grip** (`drops_held_items: false`) — only unconscious drops what it holds.
- **`exhausted` scales with the instance `level`** (D&D 1–6: speed ×0.5 → 0, Energy drain −1 → −4).
- **Instance schema:** `periodic` / `extra_conditions` / `ends_on` / `symptoms` / `known` + gate overrides (`blocks_speech`, `drops_held_items`, ...). Wire `process_tick` instance-first periodic, `handle_apply_condition` param passthrough (engine/effects.py), `Player.add_condition` accepting the new fields, serialization round-trip for the new fields.
- **Multi-instance stacking (owner-confirmed):** `player.conditions[cid]` becomes a **list of instances** (`poisoned: [vial_1, vial_2, ...]`). `has_condition` = any instance present; gates/mods presence-based (one `+X`, never per-instance); `process_tick` sums each instance's `periodic` drain and expires instances independently; `ends_on` resolution removes only the matching instances. Serialization round-trips the list.
- **State transitions stop wiping conditions** — `state` setter becomes add/remove instead of full-replace, so wake / energy-collapse / end-activity no longer clears poisoned, blind, etc.
- Example: broken leg = `prone`, permanent, `ends_on: ["fix"]`; a `fix`/`treat` command removes conditions whose `ends_on` includes `"fix"`.
- ✅ **Implemented 2026-08-07** (650 tests passing): multi-instance storage, instance fields, defense sign flip, sleep→unconscious + busy activities, `fix`/`stand` (via `end_instances`), **agent perception** (`perceived_conditions` in `/api/state` → prompt-builder renders symptoms/descriptions, never raw ids), the **atlas per-instance UI** (condition chips expand to every stacked instance: why/left/level/per-tick/ends on), **exhausted level scaling** (level-periodic drain + speed multipliers), and the **movement/inventory wiring** (prone crawl, speed-gated dash, held-item drops on unconscious/dead/sleep).

### Phase 2 — Trait schema v2 ✅ implemented 2026-08-07
- Trait definition fields: `grants_conditions`, `behavior_prompt`, `conflicts` — **done**:
  - `grants_conditions` — trait-sourced conditions stay in sync via `TraitSystem.sync_granted_conditions` (called on apply/remove AND once per turn, so any path that mutates `player.traits` — triggers, inspector — reconciles within a tick). `blind`/`deaf` traits now grant their conditions; new traits `paranoid` (→ frightened), `chronically_ill` (→ sick with periodic override), `narcoleptic` (→ exhausted).
  - `behavior_prompt` — data-driven LLM personality text, exposed as `player.trait_behavior` in `/api/state` and rendered by `buildTraitBehaviorContext` (legacy hardcoded hints kept as fallback).
  - `conflicts` — mutually exclusive traits (night_owl↔morning_person, introvert↔extrovert, light↔heavy_sleeper, fast↔slow_healer); `handle_apply_trait` refuses with a message.
- New effect keys: `skill_check_mod` (per-skill dict or flat int → `skill_check`), `save_bonus` (flat or per-stat dict → `saving_throw`), `move_cost_mod` (additive on move/dash costs in `apply_action`), `carry_capacity_mod` (multiplier on the new `BASE_CARRY_CAPACITY` 100 kg player limit enforced in `take_item`). Example traits: `sprinter`, `strong_backed`, `sharp_eyed`, `iron_will`, `jittery`.
- Editor/library UI: trait editor fields for `effects`/`grants_conditions`/`conflicts`/`behavior_prompt`; inspector trait chips show behavior prompt + conflicts on hover.
- Verified: 665 tests passing (new `TestTraitSchemaV2`, `TestTraitWiring`, `TestTraitSchemaV2Mods`).

### Phase 3 — `save_on` event hooks ✅ implemented 2026-08-07
- **`engine/save_on.py`** — `SaveOnResolver.emit(player, event, context)`: finds the player's matching `save_on` entries, rolls the save (`world.saving_throw`), and on failure applies `on_fail` effects (conditions via `add_condition` with context `source`, vital deltas). Successes are flavor-only. Fully data-driven — no trait-specific code outside the trait definitions.
- **Event catalog wired:** `crawl_tight_way` (tight/crawl-only ways), `climb_way` / `jump_way` (movement by kind), `enter_area` (with `area_tags` filter), `see_item` (`item_tags` filter, fired on examine), `loud_noise` + `alone_in_dark` (tick_manager environmental hooks), `takes_damage` (extends the wake-on-damage hook).
- **Reference implementation:** `claustrophobic` → crawl a tight way → WIS save DC 12 → fail: `frightened` (3 ticks, source = the way node, `source_type: "way"`) + Sanity −10 + narration. Verified live end-to-end.
- **`frightened` source-type gates (owner-defined, refined 2026-08-07):** the instance's `source` + `source_type` decide what the character refuses to do until the condition clears:
  - `way` — won't use that passage again ("You're too afraid to use the X again."); crawl/climb/jump fears now source the **way**, not the far area.
  - `area` — won't re-enter the area (legacy untyped sources behave like area).
  - `item` — won't touch it (`take`/`use`/`use_on` refuse).
  - `character` — can't attack them, and won't enter an area while they're in it.
  Combined with the prompt nudge (perceived description names the source), system state and character behavior agree.
- **World-authored fear saves:** new generic `save` trigger effect (`{"type": "save", "params": {"stat": "WIS", "dc": 12, "on_fail": [...], "on_success": [...]}}`) — the "fleshy orifice door" is a normal way whose `on_enter` trigger rolls a WIS save and applies `frightened` (source auto-defaults to the way's name) on failure. `source_type` threads through `add_condition` → `apply_condition` → `handle_apply_condition` → `SaveOnResolver` → triggers.
- **`save_on` events are source-typed too:** every event carries a natural `source`/`source_type` — crawl/climb/jump → the way (`"way"`), `enter_area`/`loud_noise` → the area (`"area"`), `see_item` → the item (`"item"`), `takes_damage` from combat → the attacker (`"character"`, traps/effects stay generic). Trait entries may declare `source_type` as a filter (only that kind of source triggers them) — so `cowardly` fears the character who hurt them, `hemophobic` fears the bloodied item, `claustrophobic` fears the passage, `agoraphobic` fears the open area.
- Example traits: `claustrophobic`, `acrophobic` (climb+jump), `hemophobic` (see_item blood/corpse), `agoraphobic` (enter_area `open`, conflicts claustrophobic), `nyctophobic` (alone_in_dark), `cowardly` (takes_damage) — all with library JSONs.
- Verified: 675 tests passing (new `tests/test_save_on.py`: reference flow, save success, tag filters, every event type, the area gate).

### Phase 4 — Acquired traits ✅ implemented 2026-08-07
- `apply_trait` / `remove_trait` trigger effects (join `apply_condition`; registered in `TRIGGER_EFFECT_TYPES`) — already existed, hardened in Phase 2 with conflicts + `grants_conditions` sync.
- **Scripted acquisitions** — `TraitSystem.check_scripted_acquisitions(player)`, called once per turn per player in tick_manager:
  - near-death (HP ≤ 10% and still alive) → `scarred`
  - starvation (Hunger at 0) → `frail`
  - long confinement (5+ consecutive ticks restrained/grappled) → `claustrophobic`
  - Acquisitions are one-way; healing a phobia uses the `remove_trait` trigger effect.
- **Serialization** — `player.traits` already round-trips through saves (serialization.py), so dynamically acquired traits persist. Verified with a round-trip test.
- New traits: `scarred` (behavior_prompt), `frail` (Hunger decay ×1.5) + library JSONs.
- Verified: 681 tests passing (new `TestAcquiredTraits`).

### Phase 5 (deferred)
- Real advantage/disadvantage dice mechanic — deferred; owner: not needed yet.

## Condition instances — reference examples

| Scenario | Catalog condition | Instance params |
|---|---|---|
| Viper bite | `poisoned` | duration 8, HP −5/tick, source `viper` |
| Zombie rot | `sick` | duration 20, HP −2 + Hunger −3/tick, source `zombie` (disease, not poison) |
| Bad mushroom | `poisoned` | duration 60, HP −2/tick + extra_conditions `[blinded 3t, paralysed 2t]` |
| Rat poison ×4 | `poisoned` | 4 stacked instances, HP −2 each/tick → −8/tick total, source `rat_poison` |
| Broken leg | `prone` | duration permanent, `ends_on: [fix]`, source `broken_leg` |
| Zip tie | `restrained` | duration permanent, source `zip_tie`, STR save to escape |
| Stun baton | `stunned` | duration from weapon `stun_duration` |
| Haunted | `frightened` | duration permanent, source `butchers_ghost`, `ends_on: [lay_to_rest]` |
| Vampire's gaze | `charmed` | duration permanent, source `vampire`, `ends_on: [sunrise]` |

## Disease instances (owner brainstorm 2026-08-07)

Poison = toxin (`poisoned`, ends on `antidote`); disease = infection (`sick`, ends on `cure`) — an antidote never cures a disease, medicine never cures venom. ~90% of diseases are `sick` instances; the instance fields do all the differentiation (`periodic` = which stats drain and how hard, `level` = severity/progression, `duration: none` = chronic, `extra_conditions` = bundled symptoms, `ends_on` = the cure can be any action). Contagion is the trigger system's job, not conditions. Diseases that change *what you are* end as a **trait** (zombie, lycanthrope, vampire, possessed).

| Disease | Word | Instance params |
|---|---|---|
| Common cold | `sick` | duration 4, `{Energy −1}` |
| Flu | `sick` | duration 8, `{Energy −3, Hunger −2, HP −1}` + `extra_conditions [exhausted]` |
| Food poisoning | `sick` | duration 5, `{Thirst −3, Hunger −2, HP −1}`, source `rotten_food` |
| Dysentery | `sick` | duration 8, `{Thirst −4, HP −2}` |
| Cholera | `sick` | duration 5, `level 3`, `{Thirst −5, HP −3}` — deadly |
| TB / consumption | `sick` | duration none (chronic), `{Hunger −2, Energy −2, HP −1}`, `ends_on [cure]` |
| Tetanus | `sick` | duration 10, `{Energy −2}` + `extra_conditions [paralysed]` (lockjaw) |
| Rabies | `sick` | duration none, `level 1→4`: restless → hostile → `paralysed` → death |
| Plague | `sick` | duration 6, `level 4`, `{HP −3, Hunger −3, Thirst −3}` |
| Gangrene | `sick` | duration none, `{HP −2}`, `ends_on [amputate]` |
| Mummy rot (curse) | `sick` | duration none, `{HP −2, Sanity −2}`, `ends_on [remove_curse]` |
| Zombie rot | `sick` | duration 20, `{HP −2, Hunger −3}`, `level 1→3` → final stage applies `zombie` trait |
| Lycanthropy | `sick` → trait | bite = fever `sick`; then `lycanthrope` trait (moon transformation, bespoke like ghost) |
| Vampirism | trait | blood thirst + sun aversion — bespoke mechanics, identity not condition |
| Possession | `sick` → trait | `sick` burns out the mind, then the demon takes the body |
| Basilisk gaze | `petrified` (new) | stone state — genuinely new catalog entry |

## Reference examples (from design doc)

| Trait | Event | Save | Failure |
|---|---|---|---|
| `claustrophobic` | `crawl_tight_way` | WIS 12 | `frightened` 3t + Sanity −10 |
| `acrophobic` | `climb_way` | WIS | `frightened` + Sanity; prone on climb fail |
| `agoraphobic` | `enter_area` (open) | WIS | Sanity drain while inside |
| `hemophobic` | `see_item` (blood/corpse) | WIS | nausea + Sanity loss |
| `pyrophobic` | `see_item` (fire) | WIS | `frightened` |
| `paranoid` | `loud_noise` | WIS | `frightened` + forced examine |
| `cowardly` | `takes_damage` | WIS | forced retreat |

## Files likely touched

- `engine/conditions.py`, `player.py`, `engine/traits.py`
- `engine/movement.py` (crawl/climb/jump hooks), `engine/combat.py`, `engine/area_description.py`, `engine/tick_manager.py`
- `engine/effects.py` (`apply_trait`), `engine/trigger_system.py`
- `static/js/agent/prompt-builder.js` (`buildTraitBehaviorContext`), inspector/library editors
- `data/library/traits/*.json`, tests

## Related

- [[Rules Engine/Trait & Condition System (Design)|Trait & Condition System (Design)]]
- [[Characters/Traits System]] — current implementation
- [[Characters/Activities & States]] — wake-on-damage/noise hooks reused by `save_on`
