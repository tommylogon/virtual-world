---
type: task
status: review
area: characters
priority: medium
---

# task-566: Let the simulation seek a place by function (a bed, a forge, a bath)

**Filed:** 2026-09-27
**Related:** task-561 task-563

## Goal

A painted town is a service directory (The Stag Inn for travellers, The Crooked Mug for locals, the Silver Lily, a smithy, a bathhouse, a ferry), but nothing in the sim asks where any of that is: there is no venue concept at all, so a tired traveller walks the streets instead of seeking a bed. This is the difference between a painted map and a living town, and it is the item that makes a settlement matter to the simulation rather than to the eye. Needs a place lookup by kind (task-561's building types) and a need->venue mapping, then a decision about how a character chooses among several inns. Deliberately separate from the authoring tasks: it touches needs/background_sim, not the compiler.

## Acceptance

## Acceptance

- [x] **There is a venue concept now**: `engine/venues.py`, a lookup of *places by
      what they provide* — `rest`, `meal`, `drink`, `bath`, `work`, `worship`,
      `care`.
- [x] **A place lookup by kind, and it needed no new vocabulary.** A venue is a
      set of tags plus a preference order, and task-561's building types already
      carry the tags: `sleeps` on an inn and a cottage, `food`/`drink` on a
      tavern, `craft` on a smithy, `worship` on a temple, `medical` on an
      infirmary. A building becomes a venue for free by being tagged.
- [x] **Tags *or* name are both read**, which was not obvious until it was tested:
      task-568's rooms carry a *purpose* tag (`service`, `sleeping`) and express
      what they are through their **id** (`bathroom`, `guest_room`), so a
      tag-only match could not find a bathroom. Checked: the bathroom in the test
      town is found once names are read too.
- [x] **A need → venue mapping, wired into the decision chain.** The branch that
      matters is the one the task names: at `REST_SEEK_ENERGY` a tired character
      asks where a bed is and walks there, one hop at a time, and the log says so.
      It sits **above** `ENERGY_THRESHOLD` and well above the critical 15, so a
      character that is not tired yet does not cross town to book a room, and
      seeking a bed never competes with "lie down now".
- [x] **A character chooses among several inns, and the rule is explicit**
      (`choose_venue`), in four tiers, each earning its place:
      1. **fewest hops** — a character with a bed next door does not cross town for
         a better one;
      2. **familiarity** — among equally near places, one this character has used
         before, more-used first. This is what makes a town feel inhabited: a
         regular goes back to *their* inn, a newcomer goes to the nearest;
      3. **preference tier** — among those still equal, the nicer kind (an inn
         before a barn), as the venue declares;
      4. **node name, last** — a total order, so the same world answers the same
         way every turn.

      Checked: nearest wins over nicer, memory wins an exact tie (`3 visits` beat
      `1` between two places two hops away), an inn beats a bunkroom at one hop
      each, and five calls return one answer.
- [x] **Nearest-first is the default and familiarity only breaks ties** —
      deliberately, and the module says why: a character with a bed in the next
      room is not going to the best inn in the city because it is better. The
      tiers are a preference among equals, not a shopping list.
- [x] **A venue is never somewhere a character is routed that the player could
      not go.** The reachability walk is the same
      `build_exits_for_area(include_hidden=True)` BFS the rest of the sim uses, so
      the direction returned is one `movement.move_to_area` accepts.
- [x] **A shut door is a routing problem, not an absent bed.**
      `current_state` is deliberately not consulted: a locked building everyone
      has a key to is still the building, and whether the door opens is the
      traversal layer's job (which already refuses it).
- [x] **The log says where and why** — "Ari walks to The Stag Inn — is looking
      for a bed" — because a character teleporting for unexplained reasons is the
      thing this task exists to stop.
- [x] **A world with no venues behaves exactly as before.** No candidate, no
      choice, no log line; `_seek_venue` returns False and every caller falls back
      to what it would have done anyway. Checked across all seven venues on an
      empty world. A town should be something a character *walks* to, and its
      absence must not leave characters standing in the road waiting for a
      building nobody painted.
- [x] **Familiarity lives on the character** (`venue_visits`, a counter per area),
      so it travels with a save, and a character who has never been anywhere has
      nothing to be loyal to. The counter moves on **arriving** and on **sleeping
      somewhere** — standing one room from the inn is not a visit.

## Notes

- **Deliberately separate from the authoring tasks**, as the file says: this
  touches `background_simulation`, not the compiler, and needs nothing from the
  painter beyond the tags that already ship.
- `meal` and `drink` venues exist and are wired to the lookup, but the *needs* that
  drive them still serve themselves from items and water areas first — the venue
  is the fallback for a character who finds nothing here, which is the case the
  task describes ("a painted town is a service directory"). Food and drink were
  left alone deliberately: changing how a character eats is a different decision
  from teaching it where a bed is, and doing both at once would make the need
  thresholds untestable.
- The venue table is a plain dict, so a world can extend it without touching this
  module — which is the same "vocabulary, not code" shape as task-568's room tags
  and task-525's `merge:` rules.
