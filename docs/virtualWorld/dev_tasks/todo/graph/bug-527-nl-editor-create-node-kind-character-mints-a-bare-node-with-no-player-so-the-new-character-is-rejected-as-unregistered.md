---
type: bug
status: todo
area: graph
priority: high
---

# bug-527: NL editor create_node kind=character mints a bare node with no Player, so the new character is rejected as unregistered

**Filed:** 2026-10-08
**Related:** 

## Goal

Repro (live 2026-10-08): NL editor 'add Zoe Mercer to the foyer' stages create_node {kind:character} -> handle_create_node (routes/graph_ops.py:123) writes a bare character_* node; attach succeeds; the inspector then rejects it (inspector.ts:294, 'has no player state ... not a registered player'). Characters are Player-backed; the canonical creation path is PlayerManager.add_player (engine/player_manager.py:182), exposed by handle_create_player (routes/player_ops.py:381), which mints a player_<name> type=character node. The NL editor bypasses it. Fix: register a Player (a create_character op applied via handle_create_player, then attach the player_<name> node to the area), drop character from create_node's kind enum, and guard that the editor never creates a character_* node. Verify: add Zoe Mercer -> she appears in the inspector WITH player state and is present in the foyer.

## Acceptance

- TODO
