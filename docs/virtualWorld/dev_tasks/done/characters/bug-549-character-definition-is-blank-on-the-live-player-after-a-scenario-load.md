---
type: bug
status: done
area: characters
priority: high
wiki: "[[Character Pursuits]]"
blocked_by: [task-457]
---

# bug-549: Character definition is blank on the live Player after a scenario load

**Filed:** 2026-10-12
**Related:**

<!-- deps:start -->
**Blocked by:** [[task-457-character-nodes-are-the-canonical-character-record-human-agent-simple-npc]]
<!-- deps:end -->

## What

After loading a scenario, `Player.personality` / `base_description` / `description` are empty for every character even when the character **node** carries the prose. `_deserialize_player` (engine/serialization.py:406-408) reads the definition from the players block, but `to_scenario_dict` (603-609) strips those three keys from the players block and keeps them on the node as the single persisted home (comment at 151). A scenario load therefore leaves the live Player blank; only the `_serialize_player` payload (175-177, node-first) and node readers recover it. A savegame load masks it because `to_dict` keeps the players block.

## Why

The definition lives on the node, and the API payload reads it node-first - so the prompt path (built client-side from `/api/state`) is fine. But a server-side consumer reads the raw `Player` attribute: `engine/dressing.py:169` (`personality`) and `:177` (`base_description`) build the auto-dress payload from `player.personality`, which is blank after a scenario load. A savegame load hides it (`to_dict` keeps the players block), so the defect only bites a fresh scenario start - which is exactly when a designer first meets the character.

## How

Make `_deserialize_player` read the definition from the character node (the persisted home, engine/serialization.py:151), falling back to the players block for legacy saves. Mirror the precedence `_serialize_player` already uses:

- `_node = self.graph.get_node(self.player_manager._player_node_id(pname))`; `_props = _node.properties if _node is not None else {}`
- `p.personality = _props.get("personality") or pdata.get("personality", "")`
- `p.base_description = _props.get("base_description") or pdata.get("base_description", "")`
- `p.description = pdata.get("description", "") or _props.get("description", "")` (the Player value wins, because equipment regenerates `description`)

Confirm the graph is deserialized before `_deserialize_player` runs, so the node exists at that point; otherwise hydrate after graph load.

## Steps to verify

1. Load a scenario whose nodes carry the definition.
   - expected: every Player has a non-empty `personality` / `base_description` matching the node.
   - observed: kraktooth_goblin_camp 27/27 blank; mansion 9/9 blank (before fix).
2. Load a legacy scenario that only carries it in the players block.
   - expected: still non-empty, via the players-block fallback.
   - observed: TODO
3. Payload and dressing.
   - expected: `/api/state` and the `engine/dressing.py` auto-dress payload both carry the prose.
   - observed: `/api/state` payload carries it; the dressing payload reads the blank attribute.

## Acceptance

- [x] After load_from_dict of a scenario, Player.personality / ase_description are non-empty for a character whose node has them.
- [x] A legacy (players-block-only) scenario still loads the definition.
- [x] The auto-dress payload (engine/dressing.py) carries personality.
- [x] 	ests/test_serialization.py green; no scenario round-trip regression.

## Files

- `engine/serialization.py` - `_deserialize_player` (397-408); the precedence comment (151) and payload (175-177); the strip (603-609)
- `engine/dressing.py` (169, 177) - a server-side reader of the blank attribute
- `engine/character_appearance.py:97` - `personality(node)`, the node-reader pattern to mirror
- Repro: load `data/scenarios/kraktooth_goblin_camp.json` and `data/scenarios/mansion.json` via `app.world.load_from_dict`

## Note: a related data loss, repaired 2026-10-12

A scenario can also *lose* the definition on save: `to_scenario_dict` strips the players block, relying on the node. Where a character's node never carried it (never migrated off the players block), the strip discards it permanently. Found this session: mansion (9) and world_template (3) had it in neither place, and kraktooth's `player_james` in neither. All 13 were restored onto their nodes from `data/library/characters/` (the authored source) and the `/api/state` payload now carries them. Three kraktooth characters - Cullen Rutherford, Eldenford Blacksmith, Eldenford Elder - have no library entry at all, so their prose lives only on the node and cannot be restored from the library.

## Browser UI and intended live verification

Intended UI home: load a scenario in the game, select one character in the
graph, and inspect its Bio/personality view and a live character prompt or
turn. The graph node's character definition is authoritative; the Player is a
runtime projection and must receive the same prose after scenario loading.

Current availability: this card records a scenario-load bug where definition
fields remain on the character node but the loaded Player is blank. It also
records that loading a savegame masks the issue. No fresh browser reproduction
is recorded here.

Live steps when available:
1. Load a scenario containing a character node with non-empty `personality`,
   `base_description`, and `description` properties. Select the character and
   inspect the Bio view and `/api/state` player entry.
   - expected: the loaded Player has personality and base description from the
     node; its generated description follows the documented Player-vs-node
     precedence.
2. Start one live character turn or open the prompt preview for that character.
   - expected: the prompt contains the authored personality and appearance
     rather than blank definition fields.
3. Load a legacy fixture with those values only in the players block, then
   repeat the Bio and prompt checks.
   - expected: legacy prose still populates the Player when the node fields are
     absent.
4. Save, reload the scenario, and inspect the graph node and Player values.
   - expected: the node remains the single persisted definition home and the
     loaded Player is hydrated from it; no duplicate players-block copy is
     required.

These steps describe the visible consequence of scenario deserialization; the
card's core acceptance remains the node-to-Player load path.

This section is not a claim that planned UI exists or works today.
