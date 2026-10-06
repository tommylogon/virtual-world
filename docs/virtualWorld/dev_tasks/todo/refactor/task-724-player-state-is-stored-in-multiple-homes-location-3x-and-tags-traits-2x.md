---
type: task
status: todo
area: refactor
priority: low
---

# task-724: Player state is stored in multiple homes: location (3x) and tags/traits (2x)

**Filed:** 2026-10-06
**Related:** task-625, task-446, task-716, task-725

## Goal

Investigate and consolidate the redundant homes for a character's state: location stored as player.current_area (name) + player.current_area_id + graph 'in' edge, tags/traits present on both the Player object and the character node's properties, and `personality`/`description` present only on the node while the LLM prompt and Mind read them off the Player. Do NOT merge the Player model with the character node - that split is intended (task-463). Coordinate with task-446 (id-first identity), which moves these keys.

## Measured evidence (2026-10-06)

Read from `POST /api/save-scenario`, which returns `world.to_scenario_dict()` without
writing (the committed payload). World: `kraktooth_goblin_camp`.

- `players` block: **28** entries. `graph` nodes: **876**, of which **28** are `type ==
  "character"`. The count is 1:1. This is the intended split, not a duplicate: the
  character node is identity + position + node-level definition
  (`properties`: `base_description`, `description`, `expressions`, `personality`,
  `profile_image`, `tags`, `traits`, `x`, `y`), while the `Player` carries **58** runtime
  fields (`vitals`, `memories`, `relationships`, `plan`, `schedule`, `emotion`,
  perception, `soak`, `patrol_route`, …). Do not merge these.

- **Location has three homes.** Example, a single character (`Arix`):

  ```
  player.current_area      = 'Cooking Area'
  player.current_area_id   = 'area_cooking_area'
  graph 'in' edge target   = 'area_cooking_area'
  ```

  All three are consistent today. The `in` edge alone suffices as the positional source;
  the two `player` fields are redundant copies. Related positional fields on the Player
  (`at_way_id`, `entered_from_way`, `spatial_position`, `facing`) may overlap this concept
  — scope them during investigation.

- **`tags` and `traits` exist on both** the `Player` object and `node.properties`. The key
  overlap was measured; the values were **not** diffed (unknown whether they can drift).
  This is the same shape AGENTS.md warns about ("`engine/fear.py` matched against the node
  for a long time"). Note the invariant text says a character node "carries no `tags`,
  `traits` or definition" — the serialized data disagrees; the node does carry them.
  Update the invariant or the writer, whichever is wrong.

- **`personality` and `description` are on the node only, and the prompt reads them off
  the Player.** Verified against the live `/api/state`: `players["Rikka"]` has **no
  `personality` key and no `description` key** (60 keys, neither present), while the
  character node `player_Rikka.properties` carries both with real text
  (`personality: 'You are Rikka, the Kraktooth entertainer…'`). But the prompt builder
  reads the Player: `room-context.ts:143` (`buildCharacterPreamble` →
  `player.personality`) and `room-context.ts:606` (`player.description`). Plan generation
  passes the raw state player (`plan-manager.ts:93,97`:
  `state.players[charName]`). Consequence: **personality and appearance are silently
  absent from every LLM prompt**, and the character Mind/Bio surfaces that read
  `player.personality` show blank. `player.py:186` declares `self.personality` and
  `player.py:1304` serializes it, but the live world payload does not carry it for these
  characters — so the authoring path writes the node, the read path reads the Player.
  This is the definition-data half of the same split and is the reason a live prompt for
  Rikka began at the room description with no "You are Rikka. Personality: …" preamble.
- **Equipment may also be missing from the read path.** Live `/api/state` shows `Rikka`
  with **zero** `carrying` edges, so the prompt's `Wearing:`/`Carrying:` block is empty
  for her even though the slice expects her to carry gear. Determine whether this is
  authored data absent or a second read-path gap before concluding.

- **Name-keyed duplicate identities.** Three `players` keys carry a `__` suffix:
  `james__e17658`, `zombie__9dcb3e`, `zombie__c4d808`. These are created by
  `PlayerManager._unique_key` (`engine/player_manager.py:180`) appending `__<id[:6]}` on a
  name collision. This is the name-as-key problem owned by **task-446**; do not solve it
  here, only reference it.

## Acceptance

- Decide the single authoritative home for a character's location, and either feed or
  retire the other two (the `in` edge is the candidate).
- Decide whether `tags`/`traits` on the character node are authoritative, a mirror, or a
  leak; make the AGENTS.md invariant statement match reality.
- Decide the authoritative home for `personality`/`description` and make the LLM prompt
  read path and the Mind/Bio read path agree with it (either serialize them onto the
  Player in the live payload, or read them from the character node). Prove it with a live
  prompt that contains the "You are <name>. Personality: …" preamble.
- Record the count of redundant fields removed/retained; add a regression test proving the
  remaining home is the one read.

## Non-goals

- Merging the `Player` model with the character node (intended split, task-463).
- Retiring `__`-suffixed identities (task-446).
- The general duplicated-concept inventory (task-625).
