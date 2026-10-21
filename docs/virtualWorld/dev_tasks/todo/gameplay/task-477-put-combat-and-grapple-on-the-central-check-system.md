---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Rules Engine/Combat System]]"
---

# task-477: Put combat and grapple on the central check system

**Filed:** 2026-09-23
**Related:** task-472, task-475

## What

Migrate attack rolls and grapple onto engine/checks.resolve and checks.opposed so combat inherits ability modifiers, condition-driven advantage/disadvantage and the degree/critical ladder, replacing the bespoke rolling in engine/combat.py and engine/grapple.py; expose the d20 breakdown in the combat log.

## Acceptance

- [x] `engine/checks.py` exposes one central resolver pair - `resolve()` (:354)
      and `opposed()` (:429) - that computes ability modifiers,
      condition-driven advantage/disadvantage, auto-fail, and the
      degree/critical ladder.
- [ ] `engine/combat.py` resolves its attack and defence rolls through
      `checks.resolve()` instead of its own `skills.roll_dice(1, 20, ...)`.
- [ ] `engine/grapple.py` resolves the grab check and the escape check through
      `checks.resolve()` / `checks.opposed()` instead of its own d20.
- [ ] A condition that grants advantage affects a combat or grapple roll
      exactly once, through the central path, and the log names the condition
      responsible.
- [ ] The combat log shows the d20, the modifier, the total, the degree and the
      critical branch for every attack and grapple.
- [ ] Identical inputs resolve to the same result class whether they are made
      inside or outside combat (the central resolver is the only roller).

## Why

Combat and grapple are the last two places in the engine that roll their own
d20, and that means they are the last two places where a condition can fail to
do what it says. A blinded attacker, a frightened grappler and an exhausted
guard all resolve differently depending on which roller they meet, and the
reader of the combat log is shown a bespoke breakdown that no other subsystem
produces. Putting both on `engine/checks.py` makes the ability modifier, the
condition-driven advantage, the auto-fail and the degree ladder a property of
the character rather than a property of which verb was used, and it means a
combat roll and a non-combat roll of the same kind are comparable - which is
the only way to tune a difficulty curve against real play.

## How

The central system is already in place and already used elsewhere; this is a
migration, not a design.

- `engine/checks.py:resolve()` (:354) takes a player, a `kind` (a skill name,
  an ability, or a label a condition can gate such as `"attack"`), a `dc`, and
  advantage/disadvantage flags. It derives the ability and skill modifiers
  itself, adds condition-driven advantage and auto-fail from the character's
  conditions, rolls the d20 (`roll_d20`), and returns a `CheckResult` carrying
  `faces`, `kept`, `mode`, `modifiers`, `total`, `success`, `tier` and a
  human-readable `message`. The degree/critical ladder is `_degree()` (:342):
  `crit_success` on a kept 20, `crit_fail` on a kept 1, otherwise
  `strong_success` / `success` / `fail` against the DC.
- `engine/checks.py:opposed()` (:429) rolls two checks and returns
  `(attacker_result, defender_result, attacker_wins)`, with ties to the
  defender. It is the shape theft-vs-Perception and social-vs-Insight already
  use.
- A worked example of a non-combat caller: `engine/traversal.py:230` calls
  `checks.resolve(player, kind=skill, dc=dc, roll_fn=roll_fn, ...)` and uses
  the result directly. `engine/crafting.py:591` and `engine/skills.py` use the
  same path.

Measured 2026-10-20: `engine/combat.py` and `engine/grapple.py` contain **0**
calls to `checks.resolve` or `checks.opposed`. `engine/combat.py` imports only
`ability_mod` from `engine.checks` (:334) and still rolls its own d20 through
`self.skills.roll_dice(1, 20, attack_stat_mod + attack_mod)` (:344), keeping
the raw roll in `attack_raw` (:350) and comparing it against `defense_total`
(:358). `engine/grapple.py` does the same in `_grappler_grab_check()`
(:124-136) with `self.skills.roll_dice(1, 20, 0)`.

The remaining change:

1. **Attack and defence.** Replace the `roll_dice` pair in `engine/combat.py`
   with two `checks.resolve()` calls - one for the attacker with
   `kind="attack"` (or the relevant ability) and one for the defender with
   `kind="defense"` - and compare the two `CheckResult.total` values instead of
   `attack_roll >= defense_total`. The attacker's STR and the defender's DEX
   modifiers must come from the resolver, not from a local computation, so a
   condition that alters a save or a skill is honoured.
2. **Grapple.** Replace the grab check in `engine/grapple.py:_grappler_grab_check()`
   with `checks.resolve(grappler, kind="Athletics", dc=dc)` and the escape
   check in `escape()` with the same. Where the grapple is a genuine contest
   between two characters, use `checks.opposed()` so the degree of both sides
   is visible.
3. **Advantage must land exactly once.** `checks.resolve()` already ORs the
   caller's advantage flag with the condition-derived one
   (`advantage = bool(advantage or cond_adv)`, engine/checks.py:383) and
   cancels the two against each other. The migration must therefore *not* also
   apply condition advantage locally, or a blinded attacker would get
   advantage twice.
4. **The d20 breakdown in the log.** The bespoke breakdown already exists in
   the combat log (`engine/combat.py:479-482` and the HIT/MISS variants at
   :492, :544, :591, :603): "Attack d20(...) + STR + mod = ... vs d20(...) +
   DEX = ...: HIT". The migration should keep that shape but source every
   number from the `CheckResult`, so the log shows the same fields the central
   resolver shows - d20, modifier, total, degree (`tier`) and the critical
   branch - and adds the condition source for an advantaged roll, the way
   `checks.resolve()` already does (`[advantage: <condition>]`).
5. **One roller.** After the migration, `engine/combat.py` and
   `engine/grapple.py` should import nothing from `engine.checks` except the
   resolver functions, and should hold no local d20 logic.

## Steps to verify

1. Central resolver exists
   - expected: `engine/checks.py` exposes `resolve()` and `opposed()`, and the
     degree ladder distinguishes crit success, crit fail, strong success,
     success and fail.
   - observed: PASS 2026-10-20 by inspection - `engine/checks.py:354`
     `resolve()`, `:429` `opposed()`, `:342` `_degree()` (kept 20 -> crit_success,
     kept 1 -> crit_fail, `total - dc >= 5` -> strong_success).
2. Combat migrated
   - expected: an attack resolves through `checks.resolve()` and the log shows
     d20, modifier, total, degree and any critical branch; the bespoke roller
     is gone.
   - observed: NOT run live. Measured 2026-10-20: `rg` for `checks.resolve`
     and `checks.opposed` in `engine/combat.py` and `engine/grapple.py` returns
     0 hits; `engine/combat.py:334` imports only `ability_mod` and `:344`
     still calls `self.skills.roll_dice(1, 20, ...)`.
3. Grapple migrated
   - expected: the grab check and the escape check resolve through the central
     resolver, and an opposed grapple shows both sides' rolls and modifiers.
   - observed: NOT run live. Measured 2026-10-20: `engine/grapple.py:128`
     still rolls `self.skills.roll_dice(1, 20, 0)` inside
     `_grappler_grab_check()`; no call to `checks.resolve` or `checks.opposed`
     exists in the file.
4. Condition advantage lands once
   - expected: a condition that grants advantage changes a combat roll once,
     through the central path, and the log names the condition responsible.
   - observed: NOT run live - this is the behaviour the migration has to
     produce, and it does not exist yet. The mechanism it must use is present:
     `engine/checks.py:381-384` reads condition advantage and auto-fail, and
     `:396-402` puts the source condition in the message.
5. Same inputs, same result class
   - expected: the same character and the same check resolve to the same
     result class inside and outside combat.
   - observed: NOT run live. Measured 2026-10-20: the comparison cannot be made
     because combat does not call the central resolver at all.

## Files

- `engine/checks.py` - `resolve()` (:354), `opposed()` (:429), `_degree()`
  (:342); the condition advantage and auto-fail block is at :381
- `engine/combat.py` - `ability_mod` import (:334), the bespoke d20 (:344),
  the raw-roll bookkeeping (:350), the hit comparison (:358) and the combat
  log entries (:479, :492, :544, :591, :603)
- `engine/grapple.py` - `_grappler_grab_check()` (:124), the grab roll (:128),
  the escape check (:318)
- `engine/skills.py` - `roll_dice()` (:33), the thin delegate to
  `engine.checks`
- `engine/traversal.py` - the worked example of a non-combat caller of
  `checks.resolve()` (:230)
- `engine/crafting.py` - the other worked example (:591)
- `engine/npc_behaviors.py` - `process_simple_npcs()` (:464), where a hostile
  or a grappler's next turn is taken
- `tests/test_checks.py` - the central resolver's own regression, to extend
- `tests/test_combat.py` - combat regression, to extend
- `tests/test_grapple.py` - grapple regression, to extend

## Browser UI and intended live verification

Intended UI home: game view → choose **Attack** or **Grapple** against a valid target → inspect the resulting combat event/log detail and character conditions.

Current availability: the card proposes moving combat and grapple from bespoke rolls to `checks.resolve`/`checks.opposed`, including ability modifiers, advantage/disadvantage, degree/critical results, and a visible d20 breakdown. This unified check presentation is not claimed as implemented.

Live steps when available:
1. In a scratch combat, attack a target with a known ability modifier and record the event log.
   - expected: the log shows the d20, modifier, final result, degree, and any critical branch used by the central check resolver.
2. Add a condition that grants advantage, then repeat the attack with the same seed and character state.
   - expected: the condition contributes through the central check path and the log identifies the advantage result; the bespoke combat roller is not also applied.
3. Grapple the same target with known opposed modifiers, then repeat with a disadvantage condition.
   - expected: attacker and defender rolls/modifiers and opposed degree are visible; disadvantage affects the appropriate side once.
4. Compare attack/grapple outcomes with the same central check configuration outside combat.
   - expected: identical inputs resolve through the same degree/critical ladder and produce the same result class.

## Reconnaissance (2026-10-20) - still valid

Re-checked the cited code on 2026-10-20. Newer tasks 472 (central dice/checks) and 479 (surface skill/DC/dice breakdown) landed, but combat and grapple have not been migrated:

- `engine/combat.py` and `engine/grapple.py` contain 0 calls to `checks.resolve` or `checks.opposed`.
- `engine/combat.py` imports only `ability_mod` from `engine.checks` (line 334) and still rolls its own d20 (`attack_raw`, `defense_raw`, `random.randint` for stun).
- `engine/checks.py` exposes `resolve()` (line 354) and `opposed()` (line 429) which combat does not call.

Verdict: card accurate as written. Kept in todo.
