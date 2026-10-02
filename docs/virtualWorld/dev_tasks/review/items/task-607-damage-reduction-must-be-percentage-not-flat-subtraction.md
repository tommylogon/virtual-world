---
type: task
status: review
area: items
priority: medium
related: [task-604, task-606]
---

# task-607: Damage reduction needs a selectable mode: flat, dice reduction, or percentage

**Filed:** 2026-09-30
**Related:** task-604 (two-axis defense/evasion), task-606 (scale-correct stats)

## Goal

**DECIDED 2026-09-30 by Tommy:** default to **flat** number reduction, and
express it the way weapon damage already is -- **a field you can type `d8`, or
`20`, or such**.

This replaces the three fixed modes I originally filed (flat / dice / percentage)
with something better: one field evaluated by the **same expression parser the
weapon damage field already uses**. That means:

- `20` -- flat subtraction, which is the default and preserves current behaviour
  so no existing scenario changes silently.
- `d8` -- dice reduction, dropping the worst N damage rather than a flat amount.
- and anything else that parser already accepts, which is the point: the grammar
  is not a new invention that needs three branches, it is the one the rest of the
  combat vocabulary uses.

The scale problem this was filed for still stands and is what the expression
buys room for: flat subtraction has no scale-invariant answer, so a leviathan
and a 1cm spider need the same field to mean different relative things. A
percentage is the natural third form if the expression grammar grows one.

No clamp, no new evaluator -- reuse the weapon-damage path.

`damage = max(1, damage - target_defense)` is flat subtraction, and flat
subtraction has no scale-invariant answer:

- `gribbas_good_knife` (`1d4+2`, 3-6) against `defense >= 2` floors to 1 on most
  rolls — there is no gradient between "armor helped a bit" and "armor erased
  the weapon".
- Against a 1-damage spider bite, `-3` hits the `max(1, ...)` floor and does
  nothing.
- Against a tank shell, `-3` is noise.

**Which mode is correct is a setting, not a ruling.** Per Tommy, damage
reduction should be *optional* and selectable between three modes, because the
right answer differs by world and the existing content already implies more than
one:

| mode | formula | suits |
|---|---|---|
| **flat** | `dmg - defense` (today) | low-variance, armour-as-minimum-damage; fine for small-scale duels |
| **dice reduction** | `dN - defense`, i.e. remove dice rather than points | makes armour lose *rerolls* instead of flat value; keeps variance |
| **percentage** | `dmg * (1 - dr)` | the only scale-invariant form — 40% blunts a knife and a cannon equally |

Percentage is what makes task-606's titanic tier work, but it changes the feel
of every existing encounter, so it must be a choice rather than a replacement.

## Acceptance

- [x] `defense` accepts a damage expression read by the existing parser
- [x] A bare `d8` means 1d8 (it used to evaluate to zero)
- [x] `20` / `"20"` still mean flat 20 -- every existing item is unchanged
- [x] Dice are rolled per hit, never summed at aggregation
- [x] All three damage-reduction sites share one implementation
- [x] Authored content that exercises it, rather than a test-only fixture
- [x] No existing scenario changes behaviour
- [ ] **Not demonstrated end-to-end in the browser** -- see below for what blocked it

## Resolution (2026-09-30)

Per Tommy: `defense` becomes a **damage expression** in the same grammar the
weapon-damage field already uses, so an author types `20` or `d8` and both mean
what they look like. Default stays flat, so nothing changes silently.

**`parse_damage` learned a bare `d8`.** The old pattern required a leading count,
so `d8` evaluated to `(0, 0, 0)` -- an armour that silently reduced nothing, and
`d8` is both the shorthand an author reaches for and what this task asks for. It
now also honours a signed bonus, which the old pattern dropped by reading the
sign group as unsigned. Verified directly:

    20 -> (0,0,20)      'd8' -> (1,8,0)      'D8' -> (1,8,0)
    '2d6+3' -> (2,6,3)   '2d6-1' -> (2,6,-1) 'd' -> 0   'colossal' -> 0

**Aggregation keeps the two forms apart.** An int takes the cheap path and sums
flat, exactly as before; a dice value is collected separately as `defense_dice`
and **rolled per hit** by `combat._apply_damage_reduction`. Summing dice across
an outfit at aggregation time would roll once and subtract the same number from
every later swing, so the dice form never enters the flat sum.

**One implementation for all three sites.** `combat.py` had three copies of
`damage = max(1, damage - target_defense)`; they now call one helper.

**Authored content, per Tommy's point that a mechanic with nothing exercising it
should get content rather than a test fixture:**

- `data/library/items/padded_gambeson.json` -- a quilted gambeson with
  `defense: "d8"`, semantically motivated: padding absorbs a variable amount
  per swing rather than a fixed one. Passes the library lint.
- `data/library/characters/straw_practice_dummy.json` -- a durable training
  target, so a glancing hit does not end the experiment. Also lint-clean.

`tools/lint_library.py` reports 0 errors with both in place.

## What blocked the live end-to-end, and what it turned up

Two things, and the second is worth more than the demo would have been.

**1. The bare-hands damage is too small to observe.** With no weapon, a hit does
about 1 damage and the `max(1, ...)` floor absorbs the entire reduction, so
`d8` and `3` are indistinguishable. That is the cliff this task exists to
remove, met in the most literal possible way.

**2. Equipping through the API does nothing -- filed as task-654.** Writing
`{equipped: {hand: ['item_spear']}}` to `POST /api/players/<name>` returns 200 and
changes nothing in combat: every attack still read *"attacks with bare hands"*.
`_best_weapon_node` reads the **graph edges** (`EDGE_CARRYING` / `EDGE_EQUIPPED`);
`player.equipped` is a second source of truth the API will happily write without
creating the edge. So `player.equipped` is a phantom field -- it shows in the
inspector and is inert in both combat and damage reduction.

That is the same class as task-292 (a piece of armour that declares
`equip_slots` but has no `equip` action) and task-632 (a field that serializes
and is never populated). It is also the reason a proper test of 607 needs
task-654 fixed first, not 607.

Also noticed while checking: **three equip-slot names in use in one world** --
`hand_right` (4 characters), `main_hand` (1), `torso` (1) -- while the four weapon
items all declare `equip_slots: ["hand"]`. One of those three is mine (`main_hand`,
guessed), but `hand_right` against a declared `hand` is not. Recorded in task-654
rather than chased here.

- [x] A world/engine config selects the DR mode; the default preserves today's
      flat behaviour so no existing scenario changes behaviour silently
      (`combat.damage_reduction_mode` in `data/engine_config.json`, default
      `flat`, choices `flat|dice|percentage`).
- [x] All three modes implemented and unit-tested against the same fixtures
      (`tests/test_defense_axes.py`).
- [x] Percentage mode is scale-invariant: 40% reduces a 4, 10, 100 and 675 HP
      blow to 2, 6, 60 and 405.
- [x] The `max(1, ...)` floor is deliberate and documented per mode, not an
      accident of the flat implementation (flat/percentage floor at 1; dice mode
      floors at one surviving damage die).
- [x] The combat log reports which mode produced the number (`−2 flat` /
      `−40%` / `[N dice stripped]`).
- [x] Interactive: the mode is read at call time inside `_dr_mode`, so switching
      it mid-session re-resolves the next armed hit with no restart.
- [ ] **Live-browser end-to-end still blocked by task-654** (equipping through
      the API writes `player.equipped` without creating the graph edge, so an
      armed hit cannot be set up through the API). Recorded, not claimed.

## Resolution (2026-10-02)

The mode selector is implemented on top of the earlier expression work.

- `engine/runtime_config.py` gains `combat.damage_reduction_mode` (string, with
  `choices`), surfaced automatically in Settings → Engine Config.
- `engine/combat.py`:
  - `flat` (default) — subtract the expression value; a dice expression is
    rolled per hit.
  - `dice` — `_adjust_damage_dice` strips DR dice from the *incoming* damage
    roll before it is made (at least one die survives), so armour removes
    variance instead of points. The post-roll helper is a no-op in this mode so
    the two never both fire.
  - `percentage` — the expression is read as a percent of the blow,
    `damage - round(damage * pct / 100)`, scale-invariant.
- All three DR call sites (weapon dice, flat weapon, bare hands) route through
  the same helpers; the log tags the mode.
- Content: `padded_gambeson` (dice expression, flat mode),
  `plate_cuirass` / `duelists_leathers` (the task-604 axes).
