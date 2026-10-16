---
type: task
status: inprogress
area: world
priority: high
wiki: "[[World Building/World Scopes|World Scopes]]"
related: [task-401, task-402, task-715, bug-545, bug-536]
blocked_by: [bug-536, bug-545, task-715]
---

# task-855: Character-focused runtime state scales by scope, not world size

**Filed:** 2026-10-16
**Related:** task-401, task-402, task-715, bug-545, bug-536

<!-- deps:start -->
**Blocked by:** [[bug-536-get-read-paths-race-mutating-requests-on-the-shared-graph]], [[bug-545-worldpainter-paint-is-seconds-per-cell-every-single-cell-paint-serializes-the-whole-world-for-undo-then-rebuilds-the-full-payload]], [[task-715-live-update-transport-will-not-scale-to-multiple-clients-sse-per-tab-1-5s-full-state-poll]]
**Related:** [[task-401-chunk-persistence-and-gateway-ways]], [[task-402-world-scale-projection-benchmark]], [[task-715-live-update-transport-will-not-scale-to-multiple-clients-sse-per-tab-1-5s-full-state-poll]], [[bug-545-worldpainter-paint-is-seconds-per-cell-every-single-cell-paint-serializes-the-whole-world-for-undo-then-rebuilds-the-full-payload]], [[bug-536-get-read-paths-race-mutating-requests-on-the-shared-graph]]
<!-- deps:end -->

## What

Replace the browser's unconditional whole-world runtime snapshot with a server-backed working set for the characters currently under attention. When a character is selected or becomes active, resolve their current area's owning scope and provide the complete live state needed to interact with that scope: its areas and ways, present residents and items, the selected character's authoritative Player state, and the relevant global clock and world metadata. When a character moves across a scope boundary or focus changes, update the working set; with several attended characters, cover the union of their scopes without duplicating or losing canonical state. The browser's working set is a projection, not a second world or a replacement source of truth.

## Why

A full /api/state serializes and transfers the entire graph and area projections on refresh. Its cost grows with the whole world even when a person is acting in one room. At million-area scale across thousands of scopes, this makes ordinary character selection and actions depend on unrelated world size. Existing /api/world/scopes/<id>/subgraph is a graph-editor projection, not a complete runtime snapshot, and filtering a fully materialized graph does not make server work bounded. Meanwhile backsim, timeskip, and soak must continue to advance the authoritative world, including residents outside the browser's focused scope; a scoped client fetch must never make those effects disappear or imply that unrequested scopes are unchanged.

## How

Build on chunk persistence, stable location identity, the global scope index, gateway loading, and cross-chunk ownership rules (tasks 581-584). Add a runtime snapshot/read path keyed by stable character identity that derives its working set from authoritative character location and scope ownership, rather than the graph editor's selected scope. Include only the current interaction scopes and the live records required by their systems; preserve scope boundary gateways and a route for requesting the next scope on transition. Keep the browser's global/editor projection separate from the active-character snapshot so replacing a local working set cannot erase or misrepresent the world. Define how external edits and server ticks invalidate or refresh focused snapshots without forcing a whole-world transfer. Keep ticks, backsim, timeskip, and soak server-authoritative and correct for loaded and unloaded scopes; scoped browser state is not a simulation boundary. Benchmark server lookup/serialization and wire payload against synthetic worlds with at least one million areas in thousands of scopes, and demonstrate work and response size are bounded by the requested working set rather than total world size.

## Browser UI and intended live verification

Intended UI home: Live turn interface ? select or hand off to a character, act, cross a scope boundary, then inspect the loaded scope in the map/scene.

Current implementation: selecting an active character sets the runtime focus before the active-player update; human and autonomous turns use the same focused endpoint, and focus follows turn handoffs. The focused projection is merged into the existing editor cache; it does not replace the global world snapshot or unload/change the authoritative world graph. Startup and graph-editor loading remain separate whole-world operations. The latest active-selection/handoff change builds, but has not yet been rechecked in the live browser.

Live steps when available:
1. Select a character in one scope and inspect Network responses.
   - expected: only that character's required scope data and live state are returned.
2. Move through a gateway into another scope; switch focus to a character elsewhere.
   - expected: the working set follows authoritative locations and retains every attended scope.
3. Run a timeskip/soak while another scope is outside the browser working set, then inspect that scope after loading it.
   - expected: the authoritative server advances the world and the fetched scope reflects those changes without transferring all scopes.
4. Compare response counts and timing with the million-area benchmark fixture.
   - expected: payload and server work scale with the requested working set, not the whole world.

## Steps to verify

1. Load Kraktooth, select an autonomous character, run a turn, then repeat with a human-controlled character; inspect focused and whole-state requests.
   - expected: both controllers and active-character selection use the focused endpoint during gameplay; startup/editor operations may still request whole state.
   - observed (2026-10-16): In the live Kraktooth browser (629 areas, 2,766 loaded nodes), selecting Arix and running an autonomous step produced successful `/api/runtime/state?character_id=ddb12446` responses. Whole-world `/api/state` requests also occurred during the same turn window, so the original implementation did not yet satisfy the expected behavior. Focus was then wired to active-character selection and retained/synchronized through handoff; the TypeScript build passed, but this final change was not re-tested in the browser.
2. Load Kraktooth, compare `/api/state` with a focused runtime read after evicting scopes through the production store.
   - expected: report actual area/scope/node/edge counts, whole-state and focused response bytes, load timings, and confirm only the selected scope is rematerialized for the focused read.
   - observed: See task-583; the benchmark reports the Kraktooth run. A million-area fixture remains a future scale target, not a prerequisite for completing the production loader.
3. Move the character across a gateway into another scope, then select a second character in a different scope.
   - expected: the working set follows authoritative locations, includes every attended scope once, and preserves player identity/state without duplicate or stale locations.
   - observed: TODO; the live movement stayed within `goblin_camp`.
4. Run backsim, a world timeskip, and a character soak with scopes outside the browser working set; later load an affected scope and inspect state.
   - expected: authoritative server simulation advances the intended world/residents and the fetched scope reflects those changes without transferring all scopes to the client.
   - observed: TODO
5. Perform an action in the focused scope while a state refresh overlaps a mutation/event notification.
   - expected: the caller receives a coherent post-mutation snapshot; no stale budget, missed focused update, or whole-world refetch is required.
   - observed: TODO

## Acceptance

- Human and autonomous controllers for the same character derive the same interaction scope from authoritative location; active selection and turn handoff keep ordinary gameplay refreshes on the scope-bounded endpoint. Live verification must confirm no whole-world `/api/state` request is initiated during that focused gameplay window.
- Scope transitions and multi-character focus update the working set correctly; stable IDs preserve one authoritative character/item location and boundary gateways remain traversable.
- The runtime snapshot is distinct from the graph editor's subgraph and from any cached global world snapshot; consuming a scoped payload cannot silently replace a full-world model with a partial one.
- Back-simulation, timeskip, and soak remain server-authoritative and correct for scopes outside the browser working set; when those scopes are requested, their state is current.
- A reproducible Kraktooth benchmark reports whole-world and focused response records/bytes and timings, and verifies that only the requested scope is rematerialized after eviction. A synthetic million-area benchmark is a separate future scale target.
- Focused updates do not require fetching and deserializing the entire world after every action; failures and stale revisions are surfaced rather than treated as successful empty or partial state.
- Startup and graph-editor loading are still whole-world operations; these are separate from gameplay runtime refreshes and are not required to unload scopes from the authoritative server graph.

## Files

- `routes/action_handlers.py` and new runtime snapshot route/operations
- `engine/serialization.py`, `engine/world_scopes.py`, `engine/world/index.py`, `engine/world/graph.py`
- `static/js/world-state.ts`, `static/js/agent-engine.ts`, `static/js/agent/human-turn-composer.ts`
- focused snapshot, scope-transition, simulation-correctness, and scale benchmark tests/tools
- `docs/virtualWorld/World Building/World Scopes.md`
