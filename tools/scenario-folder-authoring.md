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
`population`, `events`. `name` becomes `_scenario_name` and (with `title`, if
given) `name` / `meta.title`; `meta` is passed through.

## Character → player rules

- The character's canonical graph node id is `player_<Name>` (task-316), so one
  node per character after load.
- Alongside it the compiler emits the authored `character_<slug>` node holding
  the prose (`description`, `base_description`, `personality`), `tags`, `traits`
  and the `in` edge to the character's area.
  `engine/character_identity.collapse_character_identity` merges that node into
  the anchor at load time and keeps the retired id resolvable as a graph alias,
  which is what `tests/test_character_identity.py` asserts for the camp. The
  authored count is therefore twice the player count **in the file** and equals
  it **after load** — that is the contract, not a duplicate.
  `tools/author_character_aliases.py` restores the node in a checked-in file
  that was collapsed on disk.
- In the compiled `players` block, `current_area` is the area **display name**
  (engine convention: `engine/room_perception.resolve_area_node` matches by
  name), so the authored area id is translated automatically. The `in` edge on
  the authored node uses the area **id**, which is what the graph needs.
- `player_key` overrides the roster key (defaults to the character name).

## Way endpoints

A way's `area_from` / `area_to` must be the area **node id**. The compiler
rejects a display name outright (`build_scenario.normalize_way`), because
strict-id pathfinding would then silently fail.
`tools/canonicalize_way_ids.py` rewrites name-addressed endpoints in an existing
file and cross-checks each resolution against the `connection` edges, which are
the truth about which areas a way touches.

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
- `tools/scenario_refs.py` — the `AreaResolver` shared by the migration tools:
  area reference → canonical node id, with ambiguity as an error.
- `tools/canonicalize_way_ids.py` — rewrite name-addressed way endpoints to ids.
- `tools/author_character_aliases.py` — restore the authored `character_*` node
  in a file that was collapsed on disk.
- `tools/attach_traits.py` — attach a `data/library/traits/` trait to the
  characters selected by tag.
- `tools/set_scenario_title.py` — stamp `name` / `meta.title`.
- `tools/generate_scenario.py` — procedural assembly from library area pieces.
- `tools/compile_scenario.py` — the human/LLM-authored folder → one JSON build
  step. Runtime loading stays single-file; this is a build step, not a runtime
  change.

## Tests

- `tests/test_compile_scenario.py` — determinism, id/player compilation, title,
  the authored alias and its collapse, way connection edges, and a full
  `/api/load` round-trip with no duplicate characters.
- `tests/test_scenario_data_integrity.py` — the checked-in camp scenario: one
  goblin file, one character per person after load, canonical way endpoints, no
  dangling edges, strict-id water/food reachability without the
  name-normalizing fallback.
