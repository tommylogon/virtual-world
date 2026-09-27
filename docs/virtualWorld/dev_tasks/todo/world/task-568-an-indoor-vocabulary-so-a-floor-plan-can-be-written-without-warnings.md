---
type: task
status: todo
area: world
priority: high
---

# task-568: An indoor vocabulary, so a floor plan can be written without warnings

**Filed:** 2026-09-27
**Related:** task-562, task-561, task-564, task-567

## Goal

A building interior (task-563) is somewhere you can be *in*, but there is
nothing to paint it with. `classroom`, `hallway`, `stairway`, `corridor`,
`kitchen`, `bedroom`, `bathroom` are not in the taxonomy, so a real floor plan
compiles to a grid of bare places and a report full of unknown-id warnings
(task-562 made the warning visible; it is a symptom, not the disease).

Add the interior vocabulary the 31 building types imply — the rooms those
buildings actually have — with the same shape as task-561's building records:
`name`, purpose `tags`, and descriptions written as *places* rather than as
rooms, so the prose composes the same way an outdoor cell does.

## Why it is a task and not a note

Every interior today is a grid of same-kind cells that merge into one place. A
2×3 block of `classroom` is one classroom, which is usually wrong (task-564 will
say when a kind merges and when it does not), and a plan drawn with 30 unknown
ids is indistinguishable from a plan drawn with 30 `sparse_forest` — including in
the generate report, which is the only place a typo is visible.

## Scope

- The room vocabulary itself, per the building types of task-561: sleeping,
  cooking, eating, storage, workshop, worship, trade, service, circulation, and
  the outdoor-ish ones a plan needs to punch through a wall (`porch`,
  `courtyard`, `balcony`).
- The **circulation** kinds are the interesting ones. `hallway` and `corridor`
  are what two rooms have *between* them, so they want merge rules rather than a
  size — a run of corridor is one place, however long. That decision belongs to
  task-564; this task supplies the ids so 564 has something to write rules
  against.
- `stairway` / `stairwell` need a word of their own: task-562 mints a stairwell
  from a *passable cell between two storeys*, so the id is a claim the author can
  also make directly, and the two should agree.

## Acceptance

- A one-floor plan painted with real ids compiles with **no unknown-id warning**.
- Every id has a name, at least one purpose tag, and descriptions that read as
  prose about a place.
- `hallway` and `corridor` are present so task-564 can write merge rules for them.
- `stairway` authored directly and a passable cell between two storeys produce
  the same `kind: "stairs"` way, with `floor_step` set from the real delta.
- The palette groups them so an author is not choosing from one flat column.
- Buildings stay exempt from forage, resource and hostile rules; rooms are
  indoors by construction and must not forage either.
