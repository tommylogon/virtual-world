---
type: task
status: done
area: world
priority: high
---

# task-623: Worldpainter offers 1 of 6 scopes

**Filed:** 2026-09-30
**Related:** 

## Goal

The WorldPainter scope picker exposes only one scope, so most world-scope authoring work cannot be reached through the UI.

## Acceptance

- [x] The chooser lists every scope, not only the root
- [x] Child zones are shown, not just their parent
- [x] A scope nested two deep is shown
- [x] Each card shows state and how much content it holds
- [x] Depth is visible, so a child reads as belonging to its parent
- [x] Verified live against a 6-scope world

## Resolution (2026-09-30) — this gated the Eldenford work entirely

Tommy asked me to open the WorldPainter and finish the Eldenford town map. **I
could not reach Eldenford at all.** The chooser read:

    Choose a scope to open its grid.
    [ world ]  scope Â· materialized
    [+ New root scope]

One scope, no counts. `world` is 205 areas; Eldenford interior is 71 of them.
**5 of 6 scopes were unreachable from the painter**, including the two the
Eldenford map is made of.

**Root cause**, `editor.js:567`:

    const scopes = root.children || [];

`BASE` is `/api/world/scopes`, which answers a tree whose root has the zones as
its children -- so `root.children` is `[world]` and the zones one level down were
never walked. A second defect sat behind it: the *bare* endpoint does not inline
anything past the first level at all, so a scope two deep (`goblin_camp` > `test`)
was absent from the payload too.

**Fixed** in three parts:

1. Walk the whole tree (`ScopeOptions.flattenScopes`) instead of reading
   `root.children`.
2. Point the chooser at `/api/world/scopes?flat=1`, which returns every scope
   with `depth` and `parent_id` -- the complete list, where the bare endpoint is
   not. `BASE` is unchanged for the per-scope grid payloads that expect nested.
3. Each card now shows `state Â· N areas Â· M items`, indented by depth, so the
   chooser is a chooser rather than a list of names -- and, per task-615, never
   implies a scope with content is unbuilt.

**Verified live** on `kraktooth_goblin_camp` (screenshot
`audit/89-painter-scopes.png`):

    world               scope Â· materialized Â· 205 areas Â· 47 items
    deep woods          scope Â· unmade Â· 0 areas
    goblin camp         scope Â· unmade Â· 21 areas Â· 25 items
      test              scope Â· unmade Â· 0 areas          <- depth 2, indented
    West woods          scope Â· materialized Â· 53 areas
    Eldenford interior  scope Â· materialized Â· 71 areas Â· 3 items

Eldenford interior is now openable, which is what made the rest of Tommy's
request possible at all.

**Knock-on:** this was one of ~20 `review/` tasks that could not be live-verified
because the painter would not open their scope. Those are unblocked now.

- TODO
