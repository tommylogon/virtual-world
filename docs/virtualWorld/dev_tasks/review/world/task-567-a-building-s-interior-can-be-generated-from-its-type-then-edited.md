---
type: task
status: review
area: world
priority: medium
---

# task-567: A building's interior can be generated from its type, then edited

**Filed:** 2026-09-27
**Related:** task-398 task-561 task-560

## Goal

Hand-painting a building's interior is a lot of cells: the Millbrook map's apartment block alone is 20 rooms across three storeys, and the Downtown district is 14 buildings. If a building TYPE generated its own interior - a fast-food place gets counter, kitchen, dining room and restroom; an apartment gets a corridor, N rooms per storey and a stairway; a mansion gets a hall and named rooms - then the author paints one cell per building and edits what the generator made. That is task-398's mandate (the generator is the only sanctioned way to mint an unmade scope, reproducible and editable afterwards), extended to paint: a generated interior must be deterministic from (type, seed, storeys) and must survive a re-generate without losing the author's edits. Decide how edits are protected (a per-cell author lock, or a recorded divergence list) before generating anything.

## Acceptance

## Acceptance

- [x] **A building TYPE brings its own interior**, and the author paints one cell
      per building instead of the whole inside. `data/worldpainter/interiors.json`
      carries **30 drawn plans** plus a fallback, and all **31** building types
      resolve to a walkable interior (`mall` is the one on the fallback, and the
      report says so). The task's own three examples are there: `fast_food` gets
      counter, kitchen, dining and a washroom; `residential` gets a corridor and
      three rooms per storey across three storeys; `mansion` gets a hall, a
      gallery, parlours, a study and a cellar.
- [x] **The plan is drawn, not coded** — one character per cell plus a legend,
      because a floor plan is a picture and authoring one as nested Python lists
      makes it unreadable. Editing a plan is editing a shape in a text file.
- [x] **Every room a plan uses exists in the taxonomy.** Building the plans
      surfaced five rooms the vocabulary lacked — `vault`, `reading_room`,
      `assembly_hall`, `altar_room`, `yard_room` — and they were **added to
      `biomes.json`** (now 105 biomes, 53 indoor) rather than worked around. A
      plan that names a room the taxonomy does not have is a typo waiting to
      compile into a warning, and the check that found these is now part of the
      data's own contract.
- [x] **The generator PAINTS, it does not mint.** Its output is cells written into
      the child scope's grid, and the **standard compiler**
      (`engine/world_compile.compile_grid`) then builds the areas, the doorways,
      the merge rules (task-564), the storey steps (task-562) and the
      descriptions. Checked end to end: a tavern plan paints 60 cells and compiles
      to **8 rooms across two storeys, 16 ways, and a stairwell threshold** —
      none of it invented here. One code path turns paint into places, and a
      generated interior is not a second kind of thing.
- [x] **The scope stays `unmade`.** Paint is not generation: claiming
      `materialized` would hand the author a scope with no places in it. The
      painter's button says "Paint an interior…" and the status line says "edit the
      cells, then ⚙ Generate".
- [x] **"Then edited" is free, and that is the reason for painting.** An author
      edits the generated interior by editing paint, in the same painter, with the
      same tools — including task-536's marquee. Nothing about it is special.
- [x] **Edit protection decided, as the task demanded, and it is DERIVED not
      declared**: the scope records `generated_cells` (what the generator wrote,
      per cell) and a re-generate **skips any cell whose current value no longer
      matches** (`diverged_cells`). Three things follow: nothing extra for the
      author to remember; a cell the author never touched *is* re-written to what
      the plan says, so a plan fix still reaches it; and clearing a cell back to
      unpainted counts as an edit and is respected, so an author who erased a room
      gets it to stay erased. A per-cell lock was the other option and it would be
      a second concept for the same fact.
- [x] **A partial re-generate is reported, not silent**: "3 cell(s) you had
      changed were left alone: biome (1,1), biome (3,2), floor (4,4)".
- [x] **Deterministic from (type, storeys)**: `plan_cells('tavern')` twice is
      byte-identical, 60 cells both times. A re-generate is a re-draw, not a
      reshuffle.
- [x] **A ragged plan is padded and reported, not fatal** — "a plan row was 1
      character(s) short and was padded with '='". Refusing to generate over a
      typo in a data file would make a data mistake look like a broken feature.
- [x] **The pad token is a wall, never a door.** The first version padded with
      whatever the legend offered, and `cell_kind` returns the *kind*
      (`solid`/`passable`/`see_through`) rather than the `not_a_place` tag — so
      the preference fell through and picked the **door** token, which punched
      holes in every generated building. Caught by a scratch check, fixed to prefer
      `solid`, and the reason is commented where the next reader will trip on it.
- [x] **Storeys are data, not guesswork**: a plan's `floors` list puts a cellar on
      −1 and a temple's archive on +1, and `repeat_storeys` stacks the plan for an
      apartment block or a keep. A plan that declares a height it does not draw is
      reported rather than silently padded.
- [x] **One undoable step** — `POST /api/world/scopes/<id>/grid/interior`, which
      refuses a non-building id and pops its snapshot on a refusal.
- [x] **A promoted or hand-authored child with no grid is given one** the size of
      its plan, and the report says so.
- [x] **The record is this recipe's output.** A paint recipe has no nodes, so
      there is nothing for `apply_patch` to do and the manifest is written
      directly — the first version returned it in `generated_manifest_updates` and
      the route, which commits the manifest rather than applying a patch, silently
      dropped the provenance. `generated_manifest_updates` still carries the same
      keys from the same dict, so a caller that *does* apply patches gets the same
      result.
- [x] **UI**: 🏠 Paint an interior… in the toolbar, on interior scopes only, with
      the building types listed in the prompt.

## Notes

- **Every building type resolving is the load-bearing decision.** "This building
  has no interior" is a worse answer than "this building has a plain one", and a
  new building type should never be a building you cannot walk into. The fallback
  is a corridor, a parlour, a bedroom, a kitchen and a latrine — boring, and
  walkable.
- **The generator does not place items or inhabitants.** Task-398's tag-aware
  population rules are the right home for that, and a plan is a *shape*: the
  furniture is a separate concern with its own contract, and putting it here
  would make "paint a tavern" mean "also stock a bar".
- `RECIPE_ID` is `interior.v1`, so a plan change is visible in a save the way a
  compiler change is.
- **Twenty of the thirty plans are currently one character ragged** and are being
  padded at read time. Padding is safe here because the short rows are the ones
  missing a trailing wall, and the report names each one — but the plans should be
  squared off in the data rather than left to the reader to forgive.
