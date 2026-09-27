---
type: task
status: review
area: graph
priority: medium
---

# task-526: Map rendering scale: dots vs cards at low spacing + auto spacing

**Filed:** 2026-09-26
**Related:** task-523 task-496 task-548 bug-53

## Goal

A compiled area renders as a card whose width is its **name** plus padding, and
the name does not shrink with the map pitch the way the padding does. So one
global pitch cannot serve both a 6×8 camp and a 200×133 world: at the old 40px
default the cards overlap into what looks like a physics blob, and the only fix
was dialling the spacing control to ~200 by hand. Make the map view
scale-aware — compact dots below a spacing threshold, full cards above it — and
derive the default pitch from the painted extent, with the manual stepper kept
as the override.

## Acceptance

- [x] **Marks follow the pitch at both ends.** `mapScale()` was clamped to
      `>= 1`, so a tight pitch kept a full-size box that is bigger than its own
      cell. Now clamped to `MAP_SCALE_MIN` (0.4) below and 2.5 above: the
      drawing tracks the pitch, the spacing always followed it.
- [x] **Compact dots below `MAP_CARD_MIN_PITCH` (140px/cell).** An area becomes
      a `dot` sized from the *cell* (`mapDotSize`, 55% of the pitch, clamped
      6–28px), so it always fits its own cell at any pitch and stays visible when
      a 200-cell world is zoomed out. 140 is where the clamped card box still
      fits its cell — the switch happens where the boxes stop colliding.
- [x] **Names are hidden while compact**, through the existing label LOD
      (`_nodeLabelPolicy`), so a dot does not carry a name wider than its cell.
      The tooltip, inspector, search and badges still identify every place.
- [x] **Compact is Map-layout only.** `mapCompact()` is false in the graph view
      and Levels at every pitch: those layouts are not a cell lattice and have no
      overlap to solve.
- [x] **Auto pitch derived from the painted extent.** `paintedExtent()` measures
      the drawn cells (areas only — ways sit on the lattice between them and a
      hand-authored area has no cell), then `autoMapSpacing()` aims for
      `AUTO_SPAN_PX` (1600px) across the longest side, clamped to 24–300px and
      rounded to a tidy multiple. No painted cells → `null`, and the current
      pitch stands.
- [x] **Decided before anything reads it.** `applyAutoMapSpacing()` runs at the
      top of `loadGraphData`, because node sizes, the lattice *and* the
      background art are all derived from the pitch; a pitch settled afterwards
      would leave them disagreeing (the bug-52 shape). A pitch that moves also
      re-fits the art.
- [x] **The stepper is the override, and it is visible.** Nudging the stepper
      sets `graphMapSpacingAuto=false` (persisted), so a person who wants 40px/cell
      on a 200-cell world keeps it through reloads and scope switches. The value
      shows `80 auto` while derived, an `A` button hands the pitch back, and the
      menu says why the places are dots.
- [x] **An existing hand-set pitch counts as a choice.** Found by running it:
      with the flag simply defaulting to "auto", a session whose stored pitch was
      a hand-tuned 260 was silently re-derived to 55 on the next load. A stored
      pitch that differs from the built-in 40 default *is* a decision, so that is
      now what auto-on means until the stepper says otherwise.
- [x] **The art follows the pitch in the whole-world view.** Also found by
      running it: a layer's rect is in **px**, so an auto-pitch left every picture
      drawn at the old scale over areas laid out at the new one — the bug-52
      shape reached from the other side, and the ordinary per-scope reconcile
      cannot help because the whole-world view has no single grid.
      `reconcileAllForGapChange()` re-derives **every** mounted reference from
      *its own* scope's grid and offset, then reframes the camera (the previous
      framing was computed for the old pitch). It writes nothing: this is a load
      path, so `fitToPaintedGrid` — which persists the fitted rect — is the wrong
      call here and is still used only for a deliberate manual nudge.
- [x] **Tests.** `tools/unit/test_graph_layout_engine.js`: the two-ended clamp,
      the threshold in both directions, the dot staying inside its cell, the
      extent measurement, and the auto pitch fitting a small zone and a big one
      (including "nothing painted → no opinion"). The old "never below 1"
      assertion was replaced — it pinned the bug.

## Notes from the real data

Checked against the goblin camp's actual painted scopes:

| scope | extent | auto pitch | marks | on screen |
|---|---|---|---|---|
| `world` | 20×9 | 80 | dots | ~1600px |
| `deep_woods_2` | 20×8 | 80 | dots | ~1600px |
| `west_woods` | 20×30 | 55 | dots | ~1650px |

Every one of them lands in dots mode, which is the honest answer rather than a
tuned one: a 20-cell-wide map at a card pitch would be 2800px of canvas, so
there is no pitch at which *both* the whole map is on screen and the cards do
not overlap. Cards need ~140px/cell, so they come back by raising the pitch one
notch — which is what the stepper and its `A` button are for.

The draw cost is why the dot is not "a smaller card": the label LOD already
existed for dense maps (task-527's subject), and this reuses it rather than
adding a second mechanism.

## Verified in the running app

Whole world, Map layout, 137 painted areas over 430 nodes:

| state | pitch | marks | art |
|---|---|---|---|
| author's stored pitch | 260 | cards + names | as fitted before |
| `A` pressed (auto) | 55 (`20×30` extent) | dots, 28px, no names | re-derived per zone, reframed |
| reload | 55 auto | dots | unchanged (idempotent) |

The art check is the interesting one: before the whole-world reconcile, the
pictures stayed at the 260px scale — one image covering everything — while the
areas moved to 55. After it, each zone's picture is re-derived from its own grid
at 55 and its dots sit on its own cells.
