---
group: Combat & Abilities
wiki: "[[Rules Engine/Combat System]]"
---
# Grapple/Restrain System (Hook, Rope, Zipties, Handcuffs)

**Filed**: 2026-07-18
**Priority**: Medium
**Status**: In Progress — grab/drag/escape/release/limits/tracking implemented + verified 2026-08-08 (see below); restraint items (hook/rope/zipties) and the emote validator still pending. Foundation: `grappled`/`grappling`/`restrained` conditions defined in `player.py` with `BLOCKING_CONDITIONS` and `CONDITION_HIERARCHY`.

## Summary

The Butcher's hook should be usable to grapple and restrain characters. This requires a new item subtype for restraint tools. Future items: rope, zipties, handcuffs, chains.

## Items to Support

1. **Hook** (Butcher): Can hook and drag characters
2. **Future**: rope, zipties, handcuffs, chains, manacles

## Requirements

1. **Grapple**: `use hook on [target]` — if in same room, target becomes grappled (can't move)
2. **Restrain**: grappled targets can be tied to furniture/objects (chair, pipe, bed)
3. **Escape**: restrained characters can attempt escape with STR/DEX skill check (DC based on item quality)
4. **Drag**: grappled characters can be dragged through exits by the grappler
5. **State effects**: `grappled`, `restrained`, `bound` states on the character
6. **Break free**: NPCs can attempt to break free each tick

## New States

```
bound: Cannot move, cannot use items, cannot attack. Escape DC varies by restraint.
grappled: Cannot move. Can still use items/attack with penalties.
```

## Implementation

- New `restraint` property on items: `{"type": "hook", "escape_dc": 15, "hp": 20}`
- Restrained characters get `state = "bound"` 
- Each tick, bound characters attempt a STR check vs escape_dc
- If restraint HP is reduced to 0 (by damage), it breaks
- The Butcher's lair (Slaughterhouse) has hooks/chains as environment restraints

**Deferred**: Post-merge feature branch. This branch is refactoring/testing only.

## Design (agreed 2026-08-06) — grab + drag + resist

Two tasks land together: this one and `todo/gameplay/task-159-saves-and-reactions`.

### 1. Grab

- New action `grab <target>` (same area): two things happen:
  - A **``grappled`` edge** (grappler node → target node) records WHO holds whom —
    the single source of truth for the relationship, queryable in both directions
    and visible in the graph editor (edge type `grappled`, ⛓️).
  - The target gets the **``grappled`` condition** for the mechanical effects
    (blocks movement, attack/defense mods, `ends_on: ["escape"]`).
- Movement (`engine/movement.py`) enforces `BLOCKING_CONDITIONS` — grappled/restrained
  characters can't walk off; the grappler's `go`/`dash` drags held targets (mechanical,
  no mid-move resist).
- **Relationship-gated + skill-based** (refined 2026-08-10): the grappler always rolls
  a grab check (`d20 + Athletics` vs DC). The DC is
  `10 + grabber_athletics + rel_mod + extra_targets - target_best_escape_skill`:
  - Target's best escape skill is `max(Athletics, Acrobatics)` — subtracted from the
    DC because a skilled target is harder to grab.
  - Relationship modifier is linear: `-2 per 25 closeness` for friends (lowers DC),
    `+2 per 25` for enemies (raises DC). Clamped to `[-8, +8]`.
  - Friends no longer get a separate fumble check — the unified formula makes the
    grab easy (low DC) but not automatic.
- **Hand limit**: the grappler can hold at most one target per hand — 2 by default, 1
  with `one_armed`/`disable_slot`. Each extra target **raises the grab DC by +2**
  (harder to grab a third while already holding someone) but **lowers the escape DC
  by -2** for each person currently held (the grip on each individual is weaker).
- `release <target>` (or `release` alone) lets go; `release_all_for()` drops everyone
  when the grappler is incapacitated (any `BLOCKING_CONDITIONS`), wired in
  `tick_manager.tick_turn`.

### 2. Move-with (drag)

- Grappler's `go`/`dash` carries the grappled target along (drag).
- **Drag is mechanical**: no mid-move resist roll, the grapple persists. The struggle is
  the target's own turn.

### 3. Escape

- On their own turn, a grappled character rolls their best of Athletics / Acrobatics
  vs DC = `10 + grabber_athletics + rel_mod - extra_targets - target_best_escape_skill`.
  The grabber's extra held targets **lower** the escape DC by 2 each — each grip is
  weaker when split across multiple people. Friends escape easily (low DC), enemies
  wrench hard (high DC).
- The decide prompt surfaces `State: grappled` + a nudge so the agent decides to
  struggle or go willingly.
- Future: restraints (hook/rope/zipties/handcuffs) raise the DC, have HP, and can be cut.

### 3b. Edge-based tracking + sync (2026-08-08)

The relationship is a **``grappled`` edge** (grappler node → target node), replacing
the old `grappled_by` attribute and `grappling` condition entirely. The edge is
authoritative for WHO holds whom; the `grappled` condition stays for the mechanical
effects. `GrappleSystem.sync()` (called each tick) reconciles edge ⇔ condition:
- Legacy `grappling` condition instances → dropped (edges replace them).
- A `grappled` condition with **no** matching edge → orphan, cleared (auto-heals old
  saves like the "Jane grappled by nobody" labs bug).
- A `grappled` edge whose target lacks the condition → condition re-added.
- `serialization._grappled_by()` derives the `grappled_by` API field from the edge, so
  the agent prompt keeps working unchanged.
- Removing `grappled` via the inspector drops the edge in BOTH directions (holding or
  being held).

### 3c. Inspector condition editing (2026-08-08)

- `state` is a **derived read-only label** (most significant condition) — the old
  state dropdown was a selector and only ADDED, so it could never clear `grappled`.
- Conditions are edited directly: `+ condition` select + `add_condition` /
  `remove_condition` API fields on `POST /api/players/<name>`; each condition badge
  has a ✕ Clear button. Removing `grappled` also releases the held targets.

### 4. Emote contract (related fix)

- Decision emotes are strictly **self-only body language** (what you do with your own
  body); grabbing/pulling/escaping go through actions + saves, never narrated by emote.
  This stops agents from claiming world changes (e.g. "grabs Jake and drags him up the
  stairs") that the engine never granted — see the 2026-08-06 mansion sim bug.
- Implemented as **prompt-contract guidance**, not a hard validator: the system prompt
  now states "If you want to GRAB, PULL, or DRAG someone, use the 'grab' action — never
  narrate grabbing another character in your emote." A regex emote validator was
  deliberately avoided (too fragile / false positives on legit emotes like "winks at the
  woman").

### 5. Restraint items

- Restraint items are **already possible via triggers**: the `apply_condition` effect
  (`effects.py:860`) applies `{"condition": "restrained", "target": "self"}` — a
  `use_on` trigger on a hook/rope item can tie a target. The `restrained` condition is
  defined in `player.py` and now **blocks movement** (`movement.py`). No new item
  subtype needed; future rope/zipties/handcuffs are data, not code.
- **Zip tie = a `restrained` instance** (see [[review/characters/task-trait-condition-system-v2|task: Trait & Condition System v2]] reference examples): `{"condition": "restrained", "duration": null, "source": "zip_tie", "ends_on": ["escape"]}` — permanent until the STR-save escape lands. The item's trigger just supplies `source`/`ends_on`; no new catalog entry per restraint.

### 6. Grapple combat modifiers (2026-08-06)

- A **grappled or restrained** attacker fights at `-4` attack.
- A target **grappled by the attacker** takes `+4` attack (can't dodge).
- Constants in `engine/combat.py` (`GRAPPLE_ATTACK_PENALTY` / `GRAPPLE_ATTACK_BONUS`).

## Implementation status (2026-08-08)

Implemented + verified (backend + live):

- `engine/grapple.py` — `GrappleSystem` (grab / escape / drag_all / release /
  release_all_for / sync), DI-wired on the world (`virtual_world_engine.py`) with
  `_grapple_grab`/`_grapple_escape`/`_grapple_release` facade methods.
- Edge-based tracking: `grappled` edge (grappler → target) is the single source of
  truth for the relationship; the `grappled` condition carries only the mechanical
  effects. `sync()` reconciles edge ⇔ condition (drops legacy `grappling`
  conditions, clears orphans, re-adds missing conditions).
- Skill-based saves: `SkillSystem.saving_throw(player, "Athletics"/"Acrobatics", dc)`
  (task-159), logged as `[Save] Athletics vs DC 9: roll 4 + 6 = 10 => success`.
- Relationship-modulated DCs (friends −, enemies +) + hand limits (2, one-armed = 1) +
  harder second grab (+2 DC per extra target).
- Bidirectional `grappling` condition tracking + `sync()` orphan/desync repair, wired
  into `tick_manager.tick_turn` (incapacitated grapplers auto-release).
- `routes/action.py` — `grab <target>`, `escape`/`struggle`, `release [target]`.
- `routes/players.py` — `add_condition` / `remove_condition` API fields (removing
  `grappled` also releases held targets).
- Inspector — `state` is a derived read-only label; conditions edited via
  `+ condition` select and per-badge ✕ Clear buttons.
- `engine/serialization.py` — players expose `conditions` + `grappled_by` so agents
  see the held state (was silently missing from `/api/state`).
- `tests/test_grapple.py` — 27 tests (grappler always rolls grab, escape always rolls
  save, movement block, mechanical drag, release, sync orphan/desync repair, hand limits,
  relationship DCs, best-escape-skill, DC formula, multi-target escape bonus). Suite: all pass.
- `tests/test_combat.py` — grapple-modifier tests (grappled/restrained attacker
  penalty, held-target bonus).

Remaining: restraint items beyond the trigger approach (raised DC / HP for rope/zipties —
data work, not code), grappled penalties on non-combat skill checks (currently only
combat).


## Refactoring Impact (July 2026)

Engine is modular. Create engine/restrain.py following DI. Wire in virtual_world_engine.py. Use existing engine/effects.py for status effects. Commands in routes/action.py. May need new item node properties.
