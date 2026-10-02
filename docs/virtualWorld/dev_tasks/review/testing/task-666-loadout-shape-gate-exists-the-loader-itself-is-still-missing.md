---
type: task
status: review
area: testing
priority: medium
related: [bug-516, task-519, task-654, task-665]
---

# task-666: Loadout shape gate exists; the loader itself is still missing

**Filed:** 2026-10-01
**Related:** bug-516, task-519, task-654, task-665

## What exists now

`python tools/character_loadout_check.py --check` (plus `--report`,
`--update-baseline`), documented in `AGENTS.md` alongside the other shape gates,
covered by `tests/test_character_loadout_check.py` (20 tests).

It found **18 errors across 72 character entries** the day it was written, of
which **14 were dict entries in `equipped`** that would each have taken
`GET /api/state` down the moment somebody ran refresh-to-world on that character:

    Lyrie.json           6 entries
    miki doki.json       7 entries
    standalone_test.json 1 entry

All 14 are now fixed. The transform was **textual, not a JSON roundtrip** —
`json.load`/`json.dump` reformats the file, and in this repo 70 of 71 character
entries change on a no-op roundtrip, so a roundtrip would have buried a
three-line fix in a 400-line diff. Three files, 409 deletions, all of it
duplicated `properties` blocks collapsing to the `node_id` they were copying.

## Two things that fell out, and neither is finished

**`standalone_test.json` had an empty `inventory`.** Its talisman existed only
inside `equipped`, which worked *only* because import materializes a dict entry
from its embedded `properties`. Collapsing it to a node-id string left nothing
behind the id, and the checker caught it. The item was added to `inventory` and
`data/library/items/mystery_talisman.json` created, since `library_id` pointed
at a definition that did not exist — import was silently auto-registering it
into `items.json` on first use, which makes the canonical definition whatever a
character happens to carry.

**Four errors remain and are baselined, not fixed.** `nia.json` and
`uzume-chan.json` have four equipped ids with no inventory entry, so those slots
will come up empty on import. Fixing them means authoring four items
(`police_cap`, `blue_cap_with_heart`, `work_boots`, `blue_jumpsuit`) and
deciding whether those characters should be carrying anything at all. Left as
recorded debt rather than guessed at.

## Acceptance

- [x] The four remaining `equipped_id_not_in_inventory` findings are either fixed
      by adding the items to `inventory`, or removed from `equipped` because the
      character should not be wearing them. Then `--update-baseline`.
- [x] **A checker run is part of the pre-commit path**, so a bad character entry
      cannot be committed without the gate being consulted. Right now it is
      documented in `AGENTS.md` but nothing runs it automatically, which is how
      `way_property_index.py` started out too.
- [x] The checker's rules are derived from a declaration rather than written
      inline, the way `tools/way_properties.py` feeds `way_property_index.py`.
      `CHECKS` is already a single table, so this is mostly a matter of moving
      the *reasons* — which are the valuable part — somewhere referenceable.
- [ ] Consider the sibling case: this checks characters. `areas.json` and
      `ways.json` entries have the same "declared in the library, dropped by the
      spawn path" exposure that bug-516 and task-659 describe, and nothing checks
      their shape at all.

## Outcome (2026-10-02)

The four dangling ids were **fixed by authoring the items**, not by dropping them:
the characters' own descriptions say they wear a black police cap (nia) and a blue
cap/heart, work boots and blue jumpsuit (uzume-chan), so removing them would have
deleted intended content. Four library templates were added — `police_cap`,
`blue_cap_with_heart`, `work_boots`, `blue_jumpsuit` — and matching `inventory`
entries with `node_id` = the equipped id, which is what import resolves against.
`--report` is now **0 errors / 9 warnings** and the baseline holds only the nine
`name_does_not_match_file` entries (task-665).

The gate is now real:
- `tests/test_character_loadout_check.py::test_the_shipped_library_has_no_new_loadout_findings`
  runs the checker against the shipped library inside `pytest`, which is the
  pre-commit command this repo actually has, and fails on any NEW finding.
- `npm run precommit` chains the character, scenario-tag and way-property gates
  for anyone wiring a git hook.
- The reasons moved to `tools/character_loadout_rules.py`, imported by the
  checker; `test_rules_are_declared_in_one_module` pins that it is the one table.

The loader the title names (refresh-to-world resolving `equipped` ids the way
import does) is still **not** built — it is a code change in `library_ops.py`, not
a testing-infra one, and is left for the character/library lane. The checker is
what makes its absence visible: `equipped_dict_entry` is an ERROR precisely
because refresh writes a dict verbatim.