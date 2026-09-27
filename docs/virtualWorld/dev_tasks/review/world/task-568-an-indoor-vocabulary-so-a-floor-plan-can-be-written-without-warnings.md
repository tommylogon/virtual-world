---
type: task
status: review
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

## Acceptance

- [x] **The ids a plan needs exist in the vocabulary**: **48 indoor records** —
      circulation (`hallway`, `corridor`), the vertical (`stairway`, a passable
      stair cell), sleeping (`bedroom`, `bunkroom`, `guest_room`), living
      (`hearth_room`, `parlour`, `great_hall`, `gallery`), cooking (`kitchen`,
      `scullery`), eating (`dining_hall`, `mess_hall`, `taproom`), storage
      (`storeroom`, `cellar`, `pantry`, `armory`, `stacks`, `hayloft`,
      `animal_pen`, `tack_room`), workshop (`workroom`, `forge`, `mill_room`),
      worship (`oratory`, `crypt`, `nave`, `vestry`), records/study (`classroom`,
      `study`, `archive`, `counting_house`), trade (`stall`, `shopfront`,
      `office`), civic (`council_chamber`), service (`guardroom`, `washroom`,
      `bathroom`, `latrine`, `laundry`, `ward`, `cell_block`, `dungeon`), and the
      outdoor-ish openings a plan punches through a wall with (`porch`,
      `courtyard`, `balcony`).
- [x] **Coverage was walked against the 31 building types, not just the eleven
      purpose headings.** Every building now has the rooms it actually has — the
      first pass covered the purposes and was missing 19 rooms, including
      `bathroom` (which this task's own Goal names) and `hearth_room` /
      `taproom`, which are the *main room* of a cottage, an inn and a tavern.
- [x] Each is `terrain: "indoor"` with a **purpose tag** the palette groups by,
      a `surface`, and two `descriptions`. Every one has a name, tags and
      descriptions — `validate` fails on a record missing any of the three.
- [x] **A floor plan compiles with no unknown-id note.** Painted with only these
      ids, `compile_grid` warns about nothing: the taxonomy is the only thing that
      decides whether a biome id is real, and these are all in it.
- [x] `stairway` is a **passable** cell tagged `stair`, and it produces the same
      `kind: "stairs"` way a passable cell between two storeys does. Both
      spellings agree — checked on a plan whose stairway is drawn on one storey,
      where the floor layer says nothing (task-562's half and this one cannot
      disagree, or the same plan compiles two different ways).
- [x] A same-storey stairway is **nameable**: `handle: "stairs"` with
      `aliases: ["stairs","stairway","up","down","in","out"]`, and a pass message
      that says "You take the stairs to X" rather than "You climb 0 storeys".
- [x] The **palette groups** them — "— Rooms —" with a purpose sub-heading each,
      between the wild terrain and the buildings, so a floor plan is not chosen
      from one flat column of 100.
- [x] **Rooms are indoors by construction and do not forage.** No indoor record
      carries a `forage_skills` tag, and none appears in `resource_distribution`
      or `hostile_distribution`. Buildings stay exempt exactly as before.

## Notes

- **This is a seed set, not a closed vocabulary.** 48 covers every building type
  in the taxonomy today; the next building that gets a type will want a room that
  is not here yet. That is the point of it being *vocabulary* — a new room is one
  JSON record with the same four keys, no code, and it appears in the palette.
- `stairs` as a second id was considered and **rejected**: two ids for one thing
  is how a vocabulary starts disagreeing with itself. `stairway` is the id, and
  it agrees with the stairwell the compiler mints on its own.
- `cave` and `mine` were first added as *biomes* and then removed. A cave is not a
  place you stand in, it is a way in — which is a **feature** on a placement, so
  those phrases live in `features` (see task-529) rather than here.
- `study` is a room **and** a purpose tag (a school room is a study of a subject).
  The palette groups by the tag, so a `classroom` and a `study` both land under
  "— Study —", which reads correctly for a school plan.
