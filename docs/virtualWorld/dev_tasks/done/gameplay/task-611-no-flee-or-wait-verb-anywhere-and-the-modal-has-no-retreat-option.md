---
type: task
status: done
area: gameplay
priority: medium
---

# task-611: flee verb does not exist; wait does (retraction of half the claim)

**Filed:** 2026-09-30
**Related:** 

## Goal

CORRECTED 2026-09-30 after live testing. The original claim said "no flee or wait";
only half of that is true. `wait` DOES exist and answers "You start waiting
(until woken)", and `retreat` cancels it. Only `flee` is missing: it falls
through to the emote catch-all and answers "player_human_explorer flee." -- the
exact gibberish task-629 just fixed everywhere else. With combat resolving at
42.8% attacker hit rate against DEX 11 (task-603), retreat is often the correct
play and there is no verb and no HTC menu entry for it.

## Acceptance

- [x] `flee` is a real verb, not an emote
- [x] It costs the turn and moves through the real movement layer
- [x] `flee <direction>` steps away from that direction
- [x] Honest answer when there is nowhere to go
- [x] Verified live

## Resolution (2026-09-30)

Live before, on `kraktooth_goblin_camp`:

    flee     -> "Belne flee."          (emote catch-all)
    run      -> "Belne runs."
    retreat  -> "Belne retreat."
    disengage-> "Belne disengage."

All four fell through to the emote catch-all — the same gibberish task-629
removed everywhere else. And `retreat` only *appeared* to work because the
**waiting** state string-matched the word "retreat" to cancel itself; on its own
it was an emote too.

**Added** `flee` / `disengage` / `withdraw` as real verbs, routed through the
existing movement layer (`_collect_exits` + `move_to_area`, the same path `go`
uses). Fleeing costs the turn and moves one step along an exit, preferring an
exit whose handle does **not** contain the word you typed, so `flee north` steps
away from the north. No exits means an honest "There's nowhere to run to."

**DESIGN ASSUMPTION, flagged rather than assumed.** There is no threat model in
the engine, so this is *get out of here*, not *evade this attacker*. Real
evasion is grapple-side and lives in `engine/grapple.py`. If it should behave
differently, the rule to change is the exit choice and nothing else.

**Verified live:**

    flee          -> "You step off the forest trail onto the hidden approach
                      to the goblin camp entrance."   Camp Entrance
    disengage     -> Chief's Pit
    withdraw north-> Sleeping Halls
    flee          -> Chief's Pit

One implementation note: the first attempt used `world.gs`, which does not exist
— the accessors are `world._get_current_area_id()` and
`world.movement.name_matcher`. It 500'd on every call until corrected.

- TODO
