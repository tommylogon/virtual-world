---
type: task
status: todo
area: engine
priority: high
---

# task-708: Despawn effect: remove a character from the world from a trigger

**Filed:** 2026-10-05
**Related:** task-391

## Goal

An authored trigger can remove a target character from the roster, the graph and both lookup maps - the four-step teardown companions.py already performs privately.

## Acceptance

- **Wired:** a new `despawn_character` effect in `EFFECT_TYPES`, dispatchable
  from any authored trigger, honouring `target` the way every other effect does.
- **Complete teardown, all four steps** — the roster, both player-manager lookup
  maps, the character graph node, and its `in` edge. A half-removed character
  shows up in every subsequent area description, so a partial teardown is worse
  than none.
- `active_player` is restored if the despawned character held it; the removal
  must not leave the session pointing at nobody.
- Message and despawn compose in one trigger. The motivating case is a ghost who
  appears, thanks the player, and leaves — `message` + `despawn_character` on
  `target`, which is two effects and nothing new.
- Negative case stays blocked: despawning an unknown or already-despawned
  target reports the miss and removes nothing.
- Companions stop doing this privately — `_despawn_character` in
  `engine/companions.py:40` becomes a call to the engine path rather than a
  second implementation, so there is one teardown.

## Why this is small

The teardown is **already written**. `engine/companions.py:40` performs the full
four-step removal and says so in its own docstring:

> "There is no engine-level despawn API (nothing else needed one before
> task-391), so this does the full teardown: both lookup maps, the anchor node,
> and its `in` edge."

It is private to illusory companions and callable from nowhere else. This task is
promoting existing, working code to an effect — not writing a removal path.

## The case that needs it

A haunting that ends in the ghost ascending: an authored trigger fires when the
player finds the ring, emits `message`, then `despawn_character`. Every other
beat of that story is already authorable — the elder's dialogue via `llm_respond`,
the reveal via conditions, the delayed appearance via `schedule_trigger`. The
ending is the only piece with no expressible form, which is why it needs an
effect rather than more authoring.

Verified absent 2026-10-05: `EFFECT_TYPES` (engine/triggers/constants.py) has
`spawn_character` and no removal counterpart; no handler in
`engine/effect_handlers/` touches `players.pop` or the player manager.

## Not decided here

Whether an ascended ghost should leave a trace — a memory in the player, an
empty chair, an item. That is a design call about what the ending is worth, not
a mechanic, and it should be settled before this ships rather than after.
