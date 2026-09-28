---
type: task
status: review
area: characters
priority: low
---

# task-490: Incorporeal undead: damage resistance and condition immunities

**Filed:** 2026-09-23
**Related:** task-309

## Goal

Complete the still-open part of task-309: D&D-style damage resistance/immunity for incorporeal undead (resistance to nonmagical weapons, immunity to cold/necrotic/poison) and condition immunities (grappled/restrained/prone/exhausted/...). Engine hooks: engine/combat.py damage resolution and engine/conditions.py application.

## Acceptance

- Incorporeal undead take reduced or no damage from nonmagical weapons and are immune to cold/necrotic/poison.
- Condition immunities: grappled/restrained/prone/exhausted (and the rest of the 5e ghost list) cannot be applied to them.
- Keyed off the incorporeal/undead identity from task-309 (`engine/combat.py`, `engine/conditions.py`).
- Tests covering resistance/immunity and condition application.

## Implementation — 2026-09-28 (WT-C)

### What task-309 had already done

The identities: an `undead` tag (not alive, corporeal) and a `ghost` tag
(incorporeal, unseen until manifested), with `is_undead` / `is_incorporeal` /
`is_undead_ghost` in `engine/player_manager.py`, wired into visibility and the
skipping of vitals. What it left out is the other side of the coin: **what those
identities do to an attacker.** A ghost could be cut, chilled, poisoned and
grabbed, because nothing here existed.

### Files

- `engine/undead.py` — **new**. The defence profile and its arithmetic.
- `engine/combat.py` — damage resolution hook.
- `engine/conditions.py` — `apply_condition` immunity gate.
- `tests/test_undead_resistance.py` — **new**, 57 tests.

### A separate profile, and why

`aggregate_bonuses` already produces a `resistances` dict, but it is a **flat
subtraction** assembled from equipped items (`resisted_damage` does
`base - resist`). 5e resistance *halves* and immunity *negates*, and a halved
point of damage is nothing — none of which is a flat number. Folding undead into
that aggregate would also make a sword do less damage to a ghost, which is not
what either rule means. So a profile is its own explicit thing with its own
arithmetic: `resist` halves, `immune` zeroes, and `damage // 2` is written as
integer division on purpose.

### The rule I got wrong first, worth writing down

The 5e rule is resistance to damage **from nonmagical weapons** — about the
*weapon*, not the injury. The first cut keyed the resistance on damage types
(`slashing` and friends), so a mundane sword did full damage to a ghost because
`slashing` was not in the resist table, while `lightning` and `force` — which
were — halved damage no matter what struck with them. That is the rule exactly
backwards.

Now the profile carries a `NONMAGICAL_WEAPON` sentinel, and
`apply_damage_resistance` takes a `from_nonmagical_weapon` flag, because only the
caller knows where a hit came from. A bare fist is *not* a nonmagical weapon: a
ghost is hard to hurt with a sword, not with a fist going straight through it.
A weapon with no stated magicalness counts as mundane — the world has to say a
weapon is enchanted for it to be, and defaulting the other way would make every
mundane sword useless against ghosts without anyone having decided that.

### Immunity beats resistance, and neither is a wound

An immune blow applies no region injury either. Wounding a ghost for touching it
would be the engine disagreeing with itself in two places — `engine/body_parts`
and `engine/undead` — and the first of those to be wrong wins.

### Ghost versus zombie

The two profiles are genuinely different, and the difference is the interesting
part:

| | ghost (undead + ghost) | zombie (undead) | mortal |
|---|---|---|---|
| cold / necrotic / poison | immune | immune | — |
| nonmagical weapons | resist (halve) | — | — |
| lightning / thunder / force | resist | — | — |
| grappled / restrained / prone | immune | **vulnerable** | — |
| exhausted | **vulnerable** | immune | — |

5e says a ghost is immune to *all conditions except exhaustion*. `exhausted` is
therefore deliberately **not** in the ghost list, and a test asserts the two
lists differ by exactly `{exhausted}` — so a well-meaning edit that "fixes" the
asymmetry fails instead of silently rewriting the rule.

A zombie is not a ghost: it has a body, so it can be grappled and it bleeds. It
is only immune to exhaustion and the sensation set. The module checks **both**
tags rather than reusing `is_undead_ghost`, which is the broad "spectral entity"
alias and would wrongly hand a zombie the ghost profile.

### The condition hook is loud

`apply_condition` now returns `False` on a refusal, where it previously returned
`None`. A refusal has to be distinguishable from a missing player, or a caller
cannot tell that the grapple bounced. The immunity check is wrapped so it can
never break condition application, and `allow_immune=True` bypasses it for a
caller that has already established the target is a ghost.

### The visibility gate comes first, and the tests had to be honest about it

task-309 made an unmanifested ghost invisible, and combat refuses to strike what
it cannot see — so an unmanifested ghost never reaches the damage hooks at all.
The first version of the combat test passed *for the wrong reason*: it saw
"passes straight through" in the message and concluded the resistance worked,
when that line was the visibility gate. The test now manifests the ghost (the
state in which the resistances apply) and a separate `TestVisibilityGateStillWins`
pins the two gates and their order: see it, then hurt it.

### Handed to WT-0

Nothing. No hub file was touched.

### Verify

`python -m pytest tests/test_undead_resistance.py -q` — 57 tests. And
`tests/ -q -k "combat or condition or ghost or undead or damage"` — 413 pass, the
single failure being the pre-existing `test_mcp_misc::test_ghost_mode` FastMCP
wrapper mismatch.

Covering: the identities agree with task-309's tag checks; immunity negates and
resistance halves (and a halved 1 is 0); immunity beats resistance; a mundane
blade is resisted at every damage type and a magical one is not; a fist is not a
nonmagical weapon; a magic sword still is not a cold weapon; an immune blow
causes no region injury; an ordinary character is untouched; every listed immune
condition is a real condition in the catalog; the ghost and zombie lists differ
by exactly exhaustion; and the visibility gate is honoured ahead of the damage
gate.

### Not done, deliberately

No authoring surface. Nothing in `data/library` or a scenario carries a
`["undead", "ghost"]` character yet, so the mechanic is reachable only from code.
`data/library/characters/` and the scenarios are not this lane's to populate, and
doing so would also want task-457's canonical node first.
