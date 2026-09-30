---
type: task
status: todo
area: items
priority: medium
related: [task-604, task-606]
---

# task-607: Damage reduction needs a selectable mode: flat, dice reduction, or percentage

**Filed:** 2026-09-30
**Related:** task-604 (two-axis defense/evasion), task-606 (scale-correct stats)

## Goal

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

- [ ] A world/engine config selects the DR mode; the default preserves today's
      flat behaviour so no existing scenario changes behaviour silently
- [ ] All three modes implemented and unit-tested against the same fixtures
- [ ] Percentage mode is scale-invariant: the same DR value produces a comparable
      *relative* reduction against a 4 HP spider, a 100 HP goblin and a 675 HP
      dragon
- [ ] The `max(1, ...)` floor is deliberate and documented per mode, not an
      accident of the flat implementation
- [ ] The combat log reports which mode produced the number, so a soak log shows
      `1d4+2 = 5, -2 flat -> 3` versus `5, -40% -> 3` distinctly
- [ ] Interactive: switching mode mid-session re-resolves an armed hit without
      needing a restart
