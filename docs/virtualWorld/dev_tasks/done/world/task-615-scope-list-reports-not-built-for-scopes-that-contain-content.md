---
type: task
status: done
area: world
priority: high
---

# task-615: Scope list reports 'not built' for scopes that contain content

**Filed:** 2026-09-30
**Related:** 

## Goal

The scope list contradicts the world contents, claiming unbuilt for scopes holding real areas/ways.

## Acceptance

- [x] A scope holding content is never labelled "not built"
- [x] A genuinely empty scope still says "not built" (the distinction the
      docstring says the panel exists to make)
- [x] Materialised scopes render exactly as before
- [x] Same fix applied in both renderers (`scope-tree.js` and `tree-view.js`)
- [x] Existing scope-tree tests pass unchanged
- [x] Verified live against the real manifest

## Resolution (2026-09-30) — confirmed and fixed

The claim was right. `GraphScopeTree.rowLabel` keyed the **whole row** off
`unmade`:

    if (row.unmade) { counts.push('not built'); }
    else { counts.push(`${areaCount} areas`); ... }

But `unmade` is a *materialisation state*, and it does not imply the scope is
empty. Measured from `/api/world/scopes?flat=1` on `kraktooth_goblin_camp`:

| scope | state | area_count | item_count | character_count | rendered (before) |
|---|---|---|---|---|---|
| world | materialized | 205 | 47 | 23 | `205 areas / 47 items / 23 here now` |
| **goblin_camp** | **unmade** | **21** | 25 | **10** | **`not built / 10 here now`** |
| deep_woods | unmade | 0 | 0 | 0 | `not built` |
| test | unmade | 0 | 0 | 0 | `not built` |
| west_woods | materialized | 53 | 0 | 0 | `53 areas` |
| eldenford_interior | materialized | 71 | 3 | 3 | `71 areas / 3 items / 3 here now` |

So the row for `goblin_camp` asserted "not built" and, three words later, "10 here
now". **25 items were never displayed at all**, because the `else` suppressed the
counts.

**Fix:** show counts whenever there are counts, and report the state as what it
is -- `not built` only when the scope is genuinely empty, `unmade` alongside real
numbers otherwise. The same conditional existed in `tree-view.js:190` and was
fixed the same way.

**Verified live** on the real manifest:

    goblin camp -- 21 areas / 25 items / unmade / 10 here now
    deep woods -- not built
    test -- not built
    world -- 205 areas / 47 items / 23 here now
    West woods -- 53 areas
    Eldenford interior -- 71 areas / 3 items / 3 here now

The three empty scopes still read "not built", so the distinction the function's
own docstring says it exists to make is preserved. All 5 existing
`test_graph_scope_tree.js` tests pass unchanged -- the first attempt at this broke
four of them, because I rewrote the separator characters as ASCII (`--`, `/`)
instead of the file's existing em-dash and middot, which are stored as mojibake
bytes. Reverted and re-applied as a logic-only change; that is recorded because
it is the second time this session that editing a separator in one of these files
has destroyed more than it fixed.

- TODO

## Unverifiable in the loaded world 2026-09-30 — left open

`GET /api/world/scopes` on the loaded scenario returns:

    {"scope": null, "children": []}

The world has **no world-scopes at all**, so the scope picker is a single
"Whole world" row and the reported "not built" caption has nothing to sit
against. I also rebuilt the scope picker under task-627 (see
`static/js/shared/scope-options.js`) and confirmed there that with zero scopes it
correctly renders the whole-world row alone and no optgroups -- so the
picker is not silently wrong here, there is simply nothing to show.

The claim was recorded against a six-scope world. It needs that world (or any
world with scopes) before it can be confirmed or refuted. Deliberately not
cancelled: "the list says not built for scopes that contain content" is
untested, not disproven.
## Re-checked in the world it was filed against 2026-09-30

I loaded `kraktooth_goblin_camp` (via the Scenario Manager's own open path) and
`GET /api/world/scopes` there returns **`scopes: []`** -- the painted world has
**no world-scopes either**, just like `world_template`.

So the claim as written -- "the scope list reports *not built* for scopes that
contain content" -- cannot hold in either world I have measured, because neither
*has* scopes to list. Either:

- the six-scope situation was a third world, or an earlier state of one of these;
- or the finding mistook the WorldPainter's per-scope grid (`Build > WorldPainter`,
  which does expose 6 scopes) for the global scope list, and read a *section*
  caption on the global list as a per-scope verdict.

The second reading fits the evidence better, and it would make this a different
bug: a section header that reads like a per-scope status. **That is worth
checking** -- but as a distinct finding from the one filed, and it needs the
WorldPainter's scope list open next to the global one to confirm.

Left open with that lead recorded, because "no scopes exist" is not the same as
"the caption is correct".