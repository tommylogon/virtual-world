# Folder authoring → compiled scenario (task-408)

Authoring a whole scenario as one JSON is fragile (especially for an LLM).
This format authors it as small per-entity files and compiles them to the
single-file shape the runtime already loads.

## Layout

```
<scenario>/
  scenario.json      manifest: name + runtime config + world_lore / world_scopes
  rooms/*.json       one area per file   ("areas/" is accepted as an alias)
  ways/*.json        one way per file
  items/*.json       one item per file
  characters/*.json  each becomes a player AND a canonical player node
  triggers/*.json    optional logic triggers
```

`rooms/hall.json` is enough: the compiler derives `area_hall` from the name
(filenames may also use the canonical id, or the file may set `"id"`).

## Manifest (`scenario.json`)

Any of these runtime keys pass straight through:
`active_player`, `clock_start_hour`, `clock_start_minute`, `game_time`,
`ghost_mode`, `narration_mode`, `time_per_tick_minutes`, `turn_order`,
`world_state`, `world_lore`, `world_scopes`, `schedules`, `simultaneous_mode`,
`turn_interval_ms`, `simultaneous_act_limit`, `knowledge`, `world_events`,
`population`, `events`. `name` becomes `_scenario_name`.

## Character → player rules

- The character's canonical graph node id is `player_<Name>` (task-316), so one
  node per character — never a `character_*` duplicate.
- In the compiled `players` block, `current_area` is the area **display name**
  (engine convention: `engine/room_perception.resolve_area_node` matches by
  name), so the authored area id is translated automatically.
- `player_key` overrides the roster key (defaults to the character name).

## Compile

```bash
python tools/compile_scenario.py --input data/scenarios/src/goblin \
    --output data/scenarios/goblin.json
```

Deterministic: files are read in sorted order, ids come from filenames/names,
and output is written with sorted keys — compiling the same folder twice is
byte-identical.

## Relationship to the other tools

- `tools/build_scenario.py` — the component assembler this reuses for graph
  normalization and connection/trigger edges (now accepts alternate folder names
  and bare (unprefixed) filenames).
- `tools/generate_scenario.py` — procedural assembly from library area pieces.
- `tools/compile_scenario.py` — the human/LLM-authored folder → one JSON build
  step. Runtime loading stays single-file; this is a build step, not a runtime
  change.

## Tests

`tests/test_compile_scenario.py`: determinism, id/player compilation, way
connection edges, and a full `/api/load` round-trip with no duplicate
characters.
