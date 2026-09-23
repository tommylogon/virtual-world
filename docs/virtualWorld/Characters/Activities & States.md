# Activities & States (task-131)

Characters can enter **persistent multi-turn activities** — resting, sleeping, waiting, meditating, bathing, sitting, lying down. Activities live on `Player.activity` and advance one step per `tick_turn()` (once per full turn cycle — **no fast-forward**, the clock only moves when everyone has acted).

## Data model

```python
player.activity = {
    "type": "sleeping",        # sleeping|resting|waiting|meditating|bathing|sitting|lying down
    "started_at_tick": 123,
    "target_item": "bed",      # the object being used (bed, bath, chair) or None
    "duration_ticks": None,    # optional max length; None = indefinite
    "elapsed_ticks": 0,
    "visible": True,           # whether others see/mention the activity
}
```

Purely descriptive at the data level. Mechanical gating comes from `player.state` (a property over `conditions`, see `player.py:172`) plus the command gate in `routes/action.py`. Serialized in `to_dict` / `serialization.py`, so activities survive save/load.

## Commands

**Regen values are per in-game MINUTE**, scaled by the tick's length
(`world.time_per_tick_minutes`) like every other rate — see
[Vitals System](Vitals%20System.md). The table below used to read "+N/tick",
which was only the same thing at a 1-minute tick.

| Command | Activity | State | Regen per minute | Ends when |
|---|---|---|---|---|
| `rest [N] [on item]` | resting | busy | Energy +0.15, Sanity +0.05 | duration elapses, or interrupted |
| `sleep [N] [on item]` | sleeping | unconscious | Sanity +0.025; Energy via `SLEEP_ENERGY_REGEN` | `wake`, damage, loud noise (WIS save), **Energy full**, or duration |
| `wait [N]` | waiting | busy | none | interrupted by anything |
| `meditate [N]` | meditating | busy | Sanity +0.05 | interrupted, or duration elapses |
| `bathe [in item]` | bathing | busy | Hygiene +1.5 | Hygiene full → auto-dresses from the pile |
| `sit` | sitting | busy | Energy +0.06 | `stand` / any action |
| `lie down` | lying down | busy | Energy +0.25 | `stand` / any action |

**Wake-on-full-Energy is checked before the duration**, so a character who is not
tired cannot sleep — which is why Sanity recovery at full Energy needs a *rest*
(see below), and why the engine's own `rest()` reads are not interchangeable with
`sleep`.

## Timed activities must be registered in `ACTIVITY_INTERRUPTIBLE`

`_tick` only calls `_maybe_end_by_duration` for members of
`activities.ACTIVITY_INTERRUPTIBLE`. **A type missing from it never expires**:
`elapsed_ticks` runs past `duration_ticks` forever and the character is stuck
`busy`, which downstream reads as a mysterious refusal to eat, sleep or wash.
Adding a timed activity means adding it there, and to `ACTIVITY_CONDITIONS`,
`ACTIVITY_REGEN`, `ACTIVITY_LABELS` and `ACTIVITY_SKIP_TURNS`.

## Background recuperation (task-432)

The background tier rests a character whose Sanity is low
(`SANITY_THRESHOLD` 40) for `SANITY_REST_MINUTES` (60) — a **bounded** block on
purpose, because `_act` skips anyone mid-activity and a sprawling rest would stop
them eating. It is a rest rather than sleep because sleep cannot help a character
at full Energy.
| `stand` / `get up` | — | — | — | ends sitting/lying/meditating/waiting/resting |
| `stop` | — | — | — | ends any activity |
| `wake [name]` | — | — | — | wakes a sleeper (self or another) |

## Gating & interrupts

- **Blocking** (`sleeping`, `bathing`): most commands rejected with "You're sleeping in the bed — you can't do that right now." Allowed during both: look/stats/inventory/examine. Bathing additionally allows speech/emote/`stop`; sleeping allows `wake`.
- **Interruptible** (resting/waiting/meditating/sitting/lying down): any non-trivial action auto-ends the activity first ("You stop resting.") and then runs. Look/stats/inventory/examine/speech/emote do not interrupt.
- **Damage** wakes sleepers and interrupts activities (`effects.py handle_damage`, `combat.py`).
- **Loud noise** in the area can wake a sleeper each tick via a WIS save DC 10 (`tick_manager.py`).

## Dress / undress / piles

`strip` and `undress` are **instant** but drop every worn item into a `clothing_pile` container node in the room (id `pile_of_clothes_<name>`; tags `container`, `clothing_pile`). The pile is physical — examinable, takeable. `dress`/`get dressed` re-equips everything instantly (innermost first) and removes the pile when empty. `bathe` chains: instant strip → pile → bathing activity → auto-dress on finish.

Full stateful one-layer-per-turn dress/undress is a planned follow-up.

## Visibility

- Turn events: `"[name] is sleeping in the bed."` (visible to others via WITNESSED, frontend `buildRoomContext`).
- Area description people list: `"John (sleeping in the bed)"`.
- Agent prompts: `Activity: sleeping in the bed` in `=== YOUR STATE ===` and the people list; `state.players_in_area` now carries `activity`.

## Turn/agent handling

- `agent-engine.js` `_isBusy` skips characters whose state is sleeping/resting/meditating/busy or who have an activity — they consume a cheap skip slot, everyone else acts normally, and the round ticks once.
- Simple NPCs (`npc_behaviors.py`) skip while sleeping/unconscious or in an activity.
- `conditions` hierarchy gained `resting`/`meditating`/`busy` (display only; not blocking).
