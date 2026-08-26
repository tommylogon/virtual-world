---
group: Pleasure System
---

# Pleasure / Body / Injury System — Audit & Open Questions (v1)

**Filed**: 2026-08-16
**Status**: Review / Design Discussion
**Purpose**: Consolidate blockers before building tasks 206-215. None of this code
exists yet; all of tasks 206-215 are still `todo/`. This doc lists stale references,
schema mismatches, and the genuine design gaps we need to resolve first.

---

## 0. TL;DR

The whole pleasure/arousal set (task-206 → 215) is greenfield. The condition
system it plugs into is mature and ready (verified). But two things are **not
designed** and are the core of "bodies & injuries":

1. **No body-part-targeted damage** — combat routes all damage to `HP`; there is
   no `where`/body-part concept and no `interact` vs `attack` branch.
2. **Two competing sources of truth** for body state (numeric `body_state` dict
   vs body-part-tagged *conditions*) — the design uses both and never picks one.

Everything else is fixable line-reference nits.

---

## 1. Out-of-date references (fix in the existing task files)

| Task | Claimed | Actual | Fix |
|------|---------|--------|-----|
| task-211 | `grab → grapple (routes/action.py:641)`; `grope/fumble (action.py:541)` | `grab` at `action.py:689`; `grope/fumble/feel around` at `action.py:33` + `:589` | Update refs. NOTE: these verbs are already claimed — new intimacy verbs must not collide. |
| task-215 | "humidity tracked under task-195" | task-195 is **cancelled** | Point at **task-232** (humidity) instead. |
| task-213 | DESIGN trait shape: `"multipliers": {"body_part:nipple": 3.0}`, `"decay_modifiers"` | real schema `TRAIT_DEFINITIONS` = `effects: {VITAL_MULTIPLIER: {...}}` + `conflicts` (`traits.py:90`); `player.traits` is a **dict** `{trait_id: param}`, not a list | Task already flags this; decide on a `body_part_multipliers` parallel key. |

---

## 2. Confirmed accurate (no change needed)

- task-207 `sync_vitals_with_tags()` exists at `player.py:274` (currently only Mana/magic).
- task-206 mature toggle: **no config.toml in this repo**. The right pattern is a
  world attribute mirroring `ghost_mode` (`virtual_world_engine.py:61`) + routes at
  `routes/settings.py:13-35`. Confirmed.
- task-209 condition fields (`attack_mod`/`defense_mod`/`auto_fail_checks`/`stack`/
  `excludes`/`periodic`) all map onto the real catalog `player.py:30`. The plumbing
  the pleasure conditions plug into is ready.
- `tick_turn()` at `tick_manager.py:83`, `conditions.process_tick()` at `:108`,
  `_update_equipment_description()` at `engine/equipment.py:519`.

---

## 3. Genuine gaps — need a design decision before coding

### GAP A — Body-part-targeted injury/damage does NOT exist
- `engine/combat.py` `player_attack()` (line 62) takes `(attacker, target, weapon)`
  and subtracts damage straight from `target.vitals["HP"]`. No `where` body-part.
- task-190's `injured` is a *generic leveled condition* (light/moderate/severe,
  `ends_on:["fix"]`). task-207's `body_state` just carries a per-part `injury: null`.
- Nothing connects: combat hit → a body region → an `injured`/`bleeding` condition,
  dropped items, or action blocking. This is the biggest hole for "tackle bodies & injuries."

**Decision needed:** Add a body-region damage routing system, or lean on HP + generic
conditions? (featured in task-253 below)

### GAP B — `where`/`intensity`/`type` don't exist in the action schema
- AGENTS.md: action struct = `{action, item, target, speech, volume, emote, memory}`.
- No `interact` vs `attack`, no body-part resolver, no intensity parser.
- task-211/212 assume this pipeline is greenfield.

### GAP C — `body_state` dict vs body-part *conditions*: two sources of truth
- task-207: body parts are "NOT graph nodes, quick numeric lookups in a dict".
- Design doc §1 also defines a *condition* `bodypart_sensitive` (multi-instance,
  `body_part` key, `sensitivity_mult`).
- **Unanswered:** which stores sensitivity — the numeric dict or conditions? And who
  *writes* the numeric dict (hardness/flush/wetness/erection)? One model must have primacy.

### GAP D — Non-erotic involuntary body reactions split awkwardly
- task-166 (involuntary speech/emote: hiccup/burp/yelp/stutter) is broad.
- task-213 adds goosebumps/shivers/cough/sneeze/itch as *condition-driven flavor*.
- task-213 already says "extend task-166 rather than duplicating" but leaves it vague
  which live as conditions vs speech-postprocessing. Needs a final cut.

---

## 4. Open questions (runbook for the next working session)

1. **Body part taxonomy** — what regions exist? Design name-drops lips/face/breast/
   nipple/genitals/balls. Do we also need head/torso/arms/legs for injury? (Injury needs a
   fuller skeleton than erogenous zones.)
2. **Dict OR conditions?** — pick one owner for body state, or define the exact sync
   between them. (GAP C)
3. **Damage routing** — full body-region combat (GAP A), or keep HP-only and add
   conditions as a side effect? (task-253)
4. **`where` in the schema** — verbatim from the design, or restricted to a resolve-able
   region set? How does it interact with `_normalizeStructuredAction()` on the JS side?
5. **Mature-toggle scope** — the design lists tick/action/conditions/perception/traits.
   Is body-part INJURY also gated, or always-on (non-sexual)? Recommend: injury is generic
   and NOT mature-gated; only arousal/pleasure intimacy is.
6. **Trait shape** — adopt `body_part_multipliers` as a real catalog key, or fold into
   `effects`? (GAP from task-213)
7. **Friction trickle** — task-208 & task-215 both read clothing `friction`; confirm the
   item prop goes on the graph node and the read lives in ONE place (task-208's
   `_apply_clothing_friction`), with task-215 only seeding defaults.

---

## 5. Related tasks (link map)

- **task-253 (NEW)** — Body-part targeted injuries & regenerated actions (GAP A).
- task-206 mature toggle · task-207 body_state + vitals · task-208 release/edging/friction
- task-209 arousal conditions · task-210 description enrichment · task-211 intimacy verbs
- task-212 verb multipliers · task-213 mature traits/body reactions · task-214 NPC perception
- task-215 environmental clothing · task-190 more conditions (injured/bleeding/etc.)
- task-166 involuntary actions (body reactions overlap)