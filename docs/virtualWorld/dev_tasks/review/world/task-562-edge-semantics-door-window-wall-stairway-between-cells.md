---
type: task
status: review
area: world
priority: high
---

# task-562: Edge semantics: door, window, wall, stairway between cells

**Filed:** 2026-09-27
**Related:** task-560 task-561 task-563 task-564 task-525 task-552

## Goal

Painting a plan needs to say how two cells connect, not only what each cell is. A
Japanese high-school plan (brown hallways that merge, 4 gray cells that merge into
one classroom, yellow blanks that are impassable, blue windows that show outside but
do not open, a red stairway to the next storey) exposed that walls, windows and
doors are properties of the **boundary**, while every painted cell compiled to an
area and every adjacency became an open way. Also: cells that are not places.

## Acceptance

- [x] **The vocabulary decides what a cell is to movement.**
      `biomes.cell_kind()` reads a `not_a_place` tag plus a namespaced
      `cell_kind:` tag — `place` / `solid` / `see_through` / `passable` — so the
      compiler asks a question instead of knowing that `wall` is special. A
      modder can add a `hedge` without touching the compiler. Four values ship:
      `wall`, `void` (both `solid`, because they read differently to an author and
      identically to movement, and inventing a distinction the engine cannot act on
      would be a lie in the data), `window`, `door`.
- [x] **Cells that are not places never compile to areas.** The wall that *was* a
      room is the reason a floor plan read as its own inverse.
- [x] **A wall works by occupying a cell**; the rooms either side are no longer
      adjacent, so no way exists. **A door** occupies the same cell, so its route
      is built explicitly, joining the places on **opposite** sides — the only
      reading available, since any three of four cardinal neighbours contain an
      opposite pair.
- [x] **A door with a place on one side leads nowhere, and the report says so.**
      Invisible in the node counts, and nearly always a mis-painted door.
- [x] **A passable cell between two storeys is a `stairwell`, not a `door`.** The
      storey is the stronger signal; a "door" that quietly climbed a floor would be
      a lie in the pass message.
- [x] **A window is not a route but its place knows about it** — recorded in
      `properties.windows` with the direction it faces. A window with a place on
      two sides is a passage in disguise; one with none is a window onto nothing,
      which is still a window.
- [x] **A storey step is a `climb`, not a stride.** Every way carries `kind`
      (`open`/`door`/`stairs`) and `floor_step` (the storeys the edge crosses), so
      task-525's gate and task-563's `in` read a number rather than re-derive one.
      The pass message says which, too.
- [x] **The storey is part of a region's identity.** Found by compiling the
      two-storey plan: merging is 8-neighbour and was storey-blind, so a classroom
      above a classroom became one place with a staircase inside it.
- [x] **Four cardinals, not eight**, for "which place does this window face" and
      "which two places does this door join" — a diagonal place is a corner of the
      room, not the other side of a wall. (Found by the end-to-end run: a window in
      an outside wall was claiming the room across the corridor.)
- [x] **Authorable and visible.** Structure is its own palette section, has its own
      colours (a hash colour would make a wall look like a biome), and the cell
      inspector says "not a place — solid, nothing passes it".
- [x] **The report counts structure**, since it is invisible in the node counts,
      and **names unknown biome ids** with a WARNING.
- [x] **Tests.** `tests/test_world_compile.py` (a wall separating two rooms while a
      door joins others, a void, a dead door, a window, a window that is really a
      passage, a storey step, a stairwell, a door with places all round, a region
      never spanning two storeys, the sealed-room rescue, and the whole plan
      end-to-end); `tests/test_biomes.py` (the vocabulary reads, and the wild-country
      contract is now "wild country" in name); `tools/unit/test_worldpainter.js`
      (the cell kind through the vocabulary, and the four colours).

## Two decisions I got wrong first

- **An unknown biome id was going to read as `solid`**, so a typo in a
  hand-edited taxonomy would delete the author's cells — a wall where their
  classroom was. It reads as a `place` now, with a WARNING in the compile report.
  Failing loudly in the report beats failing silently in the data.
- **"A door with places on three sides is ambiguous" was dead code**: with four
  cardinal neighbours, any three contain an opposite pair, so the opposite-pair
  rule always decides. Removed rather than left as a claim that cannot happen.

## Not here

- **A wall still does not block island linking** — a sealed room gets one rescue
  way to the nearest place. Deliberate (`link_islands` is a reachability
  guarantee), and making a sealed room unreachable belongs with task-563.
- **Windows are not yet perception.** A place records them; nothing looks through
  one, because what is on the other side is scenery rather than a place. That is
  its own piece of work.
- **A building cell is still not a door.** Entering one with `in` from any side is
  task-563; this gives it the edge to hang on.
- **Merge rules are still one toggle** for the scope, not per kind — task-564.
- The high school plan has no *room* vocabulary yet: `classroom`, `hallway` and
  `stairway` are not in the taxonomy, so the tests use real ids and the plan test
  accepts the WARNING. A room/interior vocabulary is worth filing.
