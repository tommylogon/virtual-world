# Player Actions Reference

Human players use free-text commands; LLM agents emit the same commands serialized from a
structured action object (see `agent-engine.js:_normalizeStructuredAction`).

| Action | Syntax | Example | Notes |
|---|---|---|---|
| Move between areas | `go [exit]` | `go north` | Exit names work directly too (`north`, `stairs`, `doorway`) |
| Dash two areas | `dash [exit]` | `dash north` | Extra energy cost |
| Open a closed door | `open [exit]` | `open cellar_way` | Some ways need force first |
| Close a door | `close [exit]` | `close north` | Keeps others out / cold out |
| Take item | `take [item]` | `take key` | Auto-finds items in pockets/bags/containers ("from the backpack") |
| Drop item | `drop [item]` | `drop sword` | Drops to the area floor |
| Use item | `use [item]` | `use candle` | Self-use: Create Flame, candles |
| Use item on target | `use [item] on [target]` | `use key on cellar_way` | Unlock ways, inscribe items, etc. |
| Eat | `eat [item]` | `eat burrito` | Bare `eat` auto-picks a carried/reachable food item (task-335) |
| Drink | `drink [item]` | `drink soda` | Bare `drink` auto-picks a carried/reachable drink item (task-335) |
| Put in container | `put [item] in [container]` | `put key in pocket` | Requires `container` tag; capacity-checked |
| Place on/under surface | `put [item] on [surface]` | `put pen on table` | Also `place`. Prepositions: `on`, `under`, `beside`, `behind`, `at` |
| Give item | `give [item] to [character]` | `give key to Lyrie` | Same-area target; moves carrying edge |
| Steal item | `steal [item] from [character]` | `steal key from Miki` | Sleight of Hand vs Perception |
| Examine | `examine [item/exit]` | `examine desk` | Shows contents + spatial relations ("On the table: Ink Pen") |
| Inventory | `inventory` | `inventory` | Also `i`, `inv` |
| Look | `look` | `look` | Full room description + items + exits |
| Stats | `stats` | `stats` | Also `status` |
| Rest | `rest [minutes]` | `rest 10` | Also `sleep`. Restores Energy. |
| Wear/Equip | `wear [item]` | `wear backpack` | Equip to its compatible body slot |
| Remove/Unequip | `remove [item]` | `remove backpack` | Also `unequip`, or by slot |
| Emote | `do [description]` | `do kisses Alice gently` | Pure RP, no game effect |
| Speak | `say [text]` | `say Hello` | Also `speak`. Normal volume. |
| Whisper | `whisper [text]` | `whisper Psst` | Only your current room hears |
| Shout | `shout [text]` | `shout Hey!` | Passes through a closed door |
| Scream | `scream [text]` | `scream Help!` | Carries furthest |
| Attack | `attack [player]` | `attack Miki` | Bare-handed PvP |
| Fumble | `fumble around` | `fumble around` | Blind search in darkness |
| Relieve | `relieve` | `relieve` | Uses a toilet if available |
| Manifest | `manifest` | `manifest` | Ghost only |
| Vanish | `vanish` | `vanish` | Ghost only |

## Rules
- **One action per turn.** Do not combine commands.
- **`go` always needs a destination.** `go north`, not just `go`.
- **Only use `take`.** Not `pick up`, `grab`, `get`.
- **Examine only on listed items.** If it's not in the `Items:` list, you can't interact with it.
- **`use [item] on [target]`** unlocks ways with keys and attacks players with weapons.
- **`put`/`place`** need a spatial relation: `on`, `under`, `beside`, `behind`, `at`, or `in`.
  `in` only works on things tagged `container`.
- **`give`/`steal`** need a target character in the same area.
- Items placed on/under/beside/behind/at a surface are visible via `examine <surface>` and
  can be `take`n (they are reachable through the surface's spatial edges).
