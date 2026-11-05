---
type: task
status: todo
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-580: Unmade-scope Generate affordance and generation preview

**Filed:** 2026-09-28
**Related:** task-397, task-398

## What

Expose task-398's deterministic generation through the UI: a Generate action on an unmade scope card that carries a recipe, and a preview of the patch the recipe would apply (areas, items, and any missing tag candidates from the report) before anything is written.

## Why this is needed

task-397 step 5 (the `Generate` affordance on an unmade scope card) and the
preview half of task-398 are the last two items both tasks left open, because
both depended on a generator existing. `apartment.v1` landed in task-398, so
this is now unblocked. The backend is done: `engine/generation_recipes.py` holds
the recipe and `engine/library_nodes.py` the public materialisation service, and
`tests/test_apartment_recipe.py` covers determinism, no-duplicate re-runs,
save/reload and manual-edit survival. Only the surface is missing.

## Requirements

- A `Generate` action appears on a scope card **only** when the scope is unmade
  and carries a `recipe`. A made scope must not offer it.
- The preview is a *preview*: it renders the patch (areas, items, ways, the seed
  and recipe version) and the report's missing tag candidates, and writes
  nothing until the user confirms.
- A second press on an already-made scope is a no-op with an explanation, not an
  error and not a second node set.
- Generation goes through `engine/library_nodes.py`, never a UI-side mutation of
  the graph, so a hand edit in the editor still wins afterwards.

## Acceptance

- An unmade `apartment_3b` in Pines shows `Generate`; generating it from the UI
  produces the same three areas `tests/test_apartment_recipe.py` produces, and
  Hallway 3 can walk into all of them.
- The preview lists the recipe's areas and items and the report's missing tag
  candidates before confirmation.
- Confirming twice creates no duplicate nodes, ways or items.
- A made scope offers no `Generate`.
- A manual edit to a generated item, then a reload, survives; a second
  generation attempt does not erase it.

## Non-goals

- Chunk eviction or scope unloading (task-401).
- Authoring new recipes; `apartment.v1` is the one this hangs off.

## Blocked in the inspector-ui lane (2026-10-02)

Not attempted. The surface this task needs does not live in this lane's files
(`static/js/inspector/**`, `static/js/help/**`, `templates/index.html`): the
"scope card" is `static/js/graph/scope-tree.js` and the alternative home
(the per-scope `⚙ Generate`) is `static/js/worldpainter/editor.js`.

`static/js/graph/scope-tree.js` is being changed by the **in-progress
task-592**, which *deliberately* replaced the scope-row Generate with a
**🖌 Paint** jump ("generating lives in the painter, per scope-tree.js's own
rule - no Generate button on a scope row"). Re-adding a Generate there now
would directly collide with that live work and reverse its documented decision.
Implementing instead in the WorldPainter means editing another cluster's owned
file.

When this task is picked up it needs: (1) a preview endpoint on
`routes/world_grid_ops.py` that builds the patch from `engine/library_nodes.py`
without writing, returning areas/items/ways/seed/recipe version plus the
report's missing tag candidates; (2) the Generate button + preview modal on the
chosen surface; (3) the no-op-on-made-scope guard. Recommend resolving the
scope-tree vs painter ownership question with task-592 first.

## Plan position (2026-10-20): the planned surface was ruled out by newer work

**This card's original approach no longer holds as written, and the reason is
task-592** - a *newer* card, still open, that deliberately removed the surface
this card planned to use.

The card was filed 2026-09-28 to put a `Generate` action on an unmade scope
card, and to preview the patch before it is written. task-592 (the outline
hierarchy card) carries a rule that forbids exactly that:

- `static/js/graph/scope-tree.ts:23-24` states it in the file's own header:
  *"There is no Generate button here. Generating a scope is task-398's recipe
  flow and lives in the WorldPainter; a card that offered one would be a
  promise the graph does not keep."*
- task-592's own acceptance records it as a carried-over rule: *"**No Generate
  button on a scope row.** What a row *may* offer is the honest 'open in
  WorldPainter' jump."* The row renders `🖌 Paint`
  (`scope-tree.ts:316-323`), which calls `VW.worldPainter.open(row.id)`.

So the scope card is **not** available as the home for this affordance, and
re-adding a Generate there would reverse a documented decision made by a card
that is itself still in flight. The 2026-10-02 note in this card already
caught the collision; what was missing was the *decision*, and the decision now
has an obvious answer:

**The WorldPainter already owns the surface.** `static/js/worldpainter/editor.ts`
carries a per-scope `⚙ Generate` today (`:564` renders the report beside it,
`:607` warns `⚠ N to fix before Generate`, `:1516` refuses to place a second
area on an occupied cell). That is the surface task-592's rule points at and
the surface this card's own 2026-10-02 note identified as the alternative.

**What the newer work changed, precisely:**

| | Original plan (2026-09-28) | After task-592 (2026-10-20) |
|---|---|---|
| Surface | a `Generate` action on the unmade scope card | the per-scope `⚙ Generate` in the WorldPainter |
| Scope row | gains a button | gains only the `🖌 Paint` jump, and must keep it that way |
| Preview | a modal on the scope card | a modal on the WorldPainter's Generate |
| Backend | unchanged - `engine/library_nodes.py` is still the materialisation path | unchanged |

**What this card still owns, unchanged:** the *preview*. The WorldPainter's
`⚙ Generate` writes the patch; nothing today shows the author the patch first.
A dry-run path that builds the same patch without writing, plus the no-op
guard on an already-made scope, is the remaining work - and it belongs on the
WorldPainter's Generate, not on a scope row.

**Verdict: the approach is narrowed, not replaced.** The card survives as a
distinct piece of the plan, with its surface moved. It should not be closed,
and it should not be re-litigated as "add a button to the scope card".

## Why

The generation engine is done; the surface is not. task-398 landed
`apartment.v1`, `engine/generation_recipes.py` holds the recipe and
`engine/library_nodes.py` the public materialisation service, and
`tests/test_apartment_recipe.py` covers determinism, no-duplicate re-runs,
save/reload and manual-edit survival. What is missing is the last hop - the
author clicks something and sees what will change before it changes.

That hop matters more than a button. Generation writes a set of areas, items
and ways into the world graph, and a hand edit made afterwards has to win. The
preview is the mechanism that makes that guarantee legible to an author: they
see the exact patch, the seed and the recipe version, then confirm. Without
the preview, "Generate" is a button that mutates the world with no stated
contract, and the manual-edit-survival guarantee becomes something the author
has to trust rather than something they can check.

The reason it is still open is a design collision, not missing work. The
surface this card originally planned for has been ruled out by newer work (see
the plan position below), so the open question is *where* the affordance
lives, not *what* it does.

## How

The backend work is specified by the 2026-10-02 note above and does not need
re-deciding. Three things have to land, and the first is a choice, not a
construction:

1. **Settle the surface.** The scope card is `static/js/graph/scope-tree.ts`,
   and task-592 (newer, still open) has deliberately ruled a `Generate` button
   out there - see the plan position below. The alternative home is the
   per-scope `⚙ Generate` in the WorldPainter
   (`static/js/worldpainter/editor.ts`), which is where scope building already
   lives. Recommend the WorldPainter: it is the surface the rule already points
   at, and it avoids re-adding a button another card deliberately removed.
2. **Add a preview endpoint** on `routes/world_grid_ops.py` that builds the
   patch from `engine/library_nodes.py` **without writing**, returning areas,
   items, ways, seed and recipe version plus the report's missing tag
   candidates. A dry-run path through the same materialisation service, not a
   second implementation of it, so the preview cannot drift from what Apply
   does.
3. **Add the button and the preview modal** on the chosen surface, plus the
   no-op-on-made-scope guard: a second press on an already-made scope explains
   itself rather than erroring or writing a second node set.

Generation must continue to go through `engine/library_nodes.py`, never a
UI-side mutation of the graph, so a hand edit in the editor still wins
afterwards.

## Steps to verify

1. Confirm the scope-tree Generate button is ruled out and the WorldPainter
   is where scope building already happens.
   - expected: the surface choice is settled before any button is added.
   - observed: CONFIRMED as a live constraint. `static/js/graph/scope-tree.ts`
     carries the rule in its own header comment: *"There is no Generate button
     here. Generating a scope is task-398's recipe flow and lives in the
     WorldPainter; a card that offered one would be a promise the graph does
     not keep."* The row instead renders a `🖌 Paint` jump
     (`scope-tree.ts:316-323`) that calls `VW.worldPainter.open(row.id)`.
     The surface is therefore **not** free to choose without a decision.
2. Confirm the generation engine and its tests are in place.
   - expected: the recipe, the materialisation service and the determinism
     tests exist, so only the surface is missing.
   - observed: CONFIRMED. `engine/generation_recipes.py` and
     `engine/library_nodes.py` exist and `tests/test_apartment_recipe.py`
     covers determinism, no-duplicate re-runs, save/reload and manual-edit
     survival.
3. Confirm there is no preview endpoint yet.
   - expected: a dry-run that builds the patch without writing.
   - observed: NOT DONE. No preview path exists on `routes/world_grid_ops.py`;
     the recipe is reachable only through the materialisation service's
     writing path.
4. Confirm no Generate affordance exists on a scope row.
   - expected: the button is absent today, which is why this card is open.
   - observed: CONFIRMED. `scope-tree.ts` renders a `🖌 Paint` jump, not a
     Generate button, per the rule quoted in step 1.
5. Live: open the WorldPainter on an unmade scope, generate it, and inspect the
   result and the event stream.
   - expected: the three areas from `apartment.v1` appear, Hallway 3 can walk
     into all of them, and a second attempt creates no duplicates.
   - observed: not run. The affordance does not exist yet, so there is nothing
     to exercise.

## Files

- `static/js/graph/scope-tree.ts` - the scope row, the "no Generate button
  here" rule (`:23-24`), and the `🖌 Paint` jump (`:307-323`) that stands in
  for it today
- `static/js/worldpainter/editor.ts` - the alternative home, where scope
  building already lives
- `routes/world_grid_ops.py` - where the dry-run preview endpoint belongs
- `engine/generation_recipes.py` - the `apartment.v1` recipe
- `engine/library_nodes.py` - the public materialisation service the preview
  and Apply must both go through
- `tests/test_apartment_recipe.py` - determinism, no-duplicate re-runs,
  save/reload, manual-edit survival

## Browser UI and intended live verification

Intended UI home: Outline/Scopes → select the unmade `apartment_3b` scope in Pines → its Generate action and recipe preview. The preview is the confirmation surface before generation changes the world.

Current availability: The card describes task-398's deterministic recipe but no Generate control or preview is claimed as implemented.

Live steps when available:
1. Load Pines, select the unmade `apartment_3b` scope, and open its generation preview.
   - expected: Generate is offered; the preview lists the recipe's three areas, items, and missing tag candidates before any node is written.
2. Generate the scope once, then inspect the graph and select Hallway 3.
   - expected: the same three areas as `tests/test_apartment_recipe.py` exist, with the recipe's ways and items, and Hallway 3 has a walkable connection into each generated area.
3. Confirm generation a second time and compare node, way, and item IDs with the first result.
   - expected: no duplicate areas, ways, or items appear.
4. Edit one generated item's description, reload Pines, and request generation again.
   - expected: the manual edit survives reload and the second generation does not overwrite it; a made scope no longer offers Generate.

## Reconnaissance (2026-10-20) - still valid

Re-checked on 2026-10-20. No Generate affordance on an unmade scope card and no generation preview modal exist:

- `static/js/graph/scope-tree.ts` explicitly states (line 23) "There is no Generate button here" and (line 307) building a scope is the WorldPainter's affordance.
- `rg` for "Generate" in `scope-tree.ts` returned only those two comment lines.

Verdict: card accurate. Kept in todo. The scope-tree vs painter ownership question noted in the card is still unresolved.
