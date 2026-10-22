---
type: bug
status: review
area: bugs
priority: medium
effort: S
wiki: "[[Items & Inventory/Items Overview]]"
---

# bug-21: Give and steal must keep transferred items visible in a scoped graph

**Filed:** 2026-08-23
**Updated:** 2026-10-21

## What

`give` and `steal` raised an `AttributeError` when resolving another character's graph node through the `VirtualWorld` facade. That resolver fix is present. Browser verification exposed a second failure in the same transfer flow: after `give`, the item had a `carrying` edge to the recipient in the world graph, but the scoped graph omitted the item because it was no longer attached to an area by an `in` edge. A scoped view also did not reload when a character's carrying edges changed.

The scope projection now derives membership from physical graph relations. Items attached by `in`, `on`, `under`, `behind`, `beside`, or `at` to an in-scope area, character, way, or included item appear in the scope. Items carried or equipped by an in-scope character also appear, with their attached contents. The client reloads the scoped projection when membership changes or an edge between loaded nodes changes. Items do not receive a scope property, and the Player inventory array is not a source of truth.

## Why

The browser command path passes the `VirtualWorld` facade into item transfer actions. Test doubles exposing only the player-manager method names did not reproduce that call shape. The helper must resolve the opaque graph node ID from the object the live caller actually supplies so a transfer can update the existing containment and carrying edges.

## How

Keep `engine/character_spatial.py::_pm_get_player_node_id` as the shared resolver. It checks `get_player_node_id`, then the facade's public `player_node_id`, then `_player_node_id`, then the deterministic `NodeIDHelper.player_node_id` fallback. Both `give_item` and `steal_item` in `TransferActionsMixin` use the resolver for the other character. `engine/world_scopes.py::project_subgraph` computes a recursive closure over physical spatial edges and character holding edges. `GraphNetwork.syncGraphData()` reloads the active scoped projection when membership or an edge between loaded nodes changes. Knowledge and action links such as `known`, `unlocks`, and `triggers` do not pull unrelated nodes into a physical scope; they remain visible when both endpoints are already included. Connections are handled by way membership, which includes a way only when both endpoint areas are in the scope.

The node ID remains the source of truth for character identity. Display names are resolved before this helper is called. Do not add a second player-node lookup path to the transfer verbs.

## Browser UI and intended live verification

Intended UI home: the always-available `Enter game command` field at the bottom of the event stream, and each character's Inspector > Inventory tab.

Current availability: the `give` and `steal` command paths and the Inventory tab are present. The `kraktooth_goblin_camp` scenario authors Gribba and Zikka in the Cooking Area, with Gribba carrying Hardtack Biscuits. The top-bar Play Mode control runs a transient sandbox and restores the prior world when stopped.

Live steps when available: use Play Mode so item transfers do not persist to the regular scenario. Run each verb in a fresh Play Mode session because the first transfer changes who carries the biscuits. The Inspector may briefly show its pre-command inventory; after a transfer, reselect the recipient or reopen the Inventory tab after the state refresh before judging the result. Compare `/api/state` graph edges with the scope subgraph when diagnosing a mismatch: the first shows world state, and the second proves what the selected scope receives.

1. Load `kraktooth_goblin_camp`, start Play Mode, and select Gribba in the Agents list. Confirm Gribba and Zikka are both in the Cooking Area.
   - expected: Play Mode is active and the regular scenario is protected by the transient sandbox.
2. With `goblin camp` selected in the graph scope control, enter `give Hardtack Biscuits to Zikka` in `Enter game command` and press Enter. Inspect the graph and select Zikka to open Inspector > Inventory.
   - expected: the event stream reports `You hand the Hardtack Biscuits to Zikka.`; the graph shows the Hardtack Biscuits node connected to Zikka by a `carrying` edge, with its old `in` edge to the area removed; and Inventory lists Hardtack Biscuits. No server error appears.
3. Stop Play Mode, start a fresh Play Mode session, and select Zikka. Enter `steal Hardtack Biscuits from Gribba` and press Enter.
   - expected: the event stream reports the normal steal result. A successful roll moves the biscuits to Zikka; a noticed attempt leaves them with Gribba. Neither result is an `AttributeError` or HTTP 500.
4. Stop Play Mode.
   - expected: the transient item changes are discarded and the regular scenario returns to its prior state.

The original screenshot showed the successful handoff message beside a stale one-item Inventory panel. A read-only check then confirmed the world graph's `carrying` edge targeted `player_Zikka`, while a query of the `goblin_camp` scoped subgraph confirmed Zikka was included and the biscuits were omitted. The scoped projection and refresh path are now fixed. Browser verification of the updated scoped graph remains pending.

## Steps to verify

1. In Play Mode with `goblin camp` selected, give Gribba's Hardtack Biscuits to Zikka, then inspect the graph edge and Inventory.
   - expected: the item node remains in the scope, its edge changes from `in` the area to `carrying` by `player_Zikka`, and Inventory lists Hardtack Biscuits.
   - observed: TODO. Before the fix, `/api/state` showed the world carrying edge to `player_Zikka`, while `/api/world/scopes/goblin_camp/subgraph` omitted the item. The projection and scoped refresh fix are implemented; live browser confirmation is pending.
2. In a fresh Play Mode session, try `steal Hardtack Biscuits from Gribba` as Zikka.
   - expected: a normal contest result, either success or noticed, with no `AttributeError` or HTTP 500.
   - observed: TODO
3. Add or update a targeted regression test that passes the `VirtualWorld` facade into both transfer paths, then run `python -m pytest tests/test_item_actions.py`.
   - expected: both verbs resolve the other character's node through the public `player_node_id` method and the targeted test passes.
   - observed: TODO

## Acceptance

- [x] `_pm_get_player_node_id` checks the `VirtualWorld.player_node_id` method.
- [x] The give and steal paths use the shared resolver for the other character's graph node ID.
- [x] A scoped graph includes items through in-scope character holding relations and refreshes when those relations change.
- [x] Targeted scope projection tests cover all six spatial relations, carrying, equipped items, and nested contents.
- [ ] A targeted regression test exercises both verbs with the `VirtualWorld` facade call shape.
- [ ] Browser give path in a selected scope shows the Hardtack Biscuits carrying edge retargeted to Zikka and Inventory lists the item.
- [ ] Browser steal path returns a normal contest outcome with no `AttributeError` or HTTP 500.
- [ ] Stopping Play Mode restores the regular scenario without retaining the test transfer.

## Files

- `engine/character_spatial.py` - shared player-node ID resolver.
- `engine/items/transfer_actions.py` - give and steal call sites.
- `engine/world_scopes.py` - scoped graph membership derived from item relations.
- `static/js/graph/network-manager.ts` and `.js` - reload scoped graph when a loaded character's holding edges change.
- `tests/test_world_scopes.py` - scoped inventory membership regression.
- `virtual_world_engine.py` - facade method `player_node_id`, reference only.
- `routes/action_handlers.py` - browser command dispatch, reference only.
- `static/js/inspector/agent-view.ts` - Inventory tab, reference only.
- `data/scenarios/kraktooth_goblin_camp.json` - authored browser fixture, reference only.
