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

| Command | Activity | State | Regen (net after decay) | Ends when |
|---|---|---|---|---|
| `rest [N] [on item]` | resting | resting | Energy +1/tick | interrupted by any action, damage, or duration elapses |
| `sleep [N] [on item]` | sleeping | sleeping | Energy +2/tick | `wake`, damage, loud noise (WIS save DC 10), Energy full, duration elapses |
| `wait [N]` | waiting | — | none | interrupted by anything |
| `meditate [N]` | meditating | meditating | Sanity +1/tick | interrupted, or duration elapses |
| `bathe [in item]` | bathing | busy | Hygiene +5/tick | Hygiene full → auto-dresses from the pile |
| `sit` | sitting | — | Energy +1/tick | `stand` / any action |
| `lie down` | lying down | — | Energy +2/tick | `stand` / any action |
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
