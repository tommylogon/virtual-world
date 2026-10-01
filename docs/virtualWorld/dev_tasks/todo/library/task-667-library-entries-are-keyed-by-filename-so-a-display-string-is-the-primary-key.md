---
type: task
status: todo
area: library
priority: high
related: [task-446, task-619, task-665, task-660]
---

# task-667: Library entries are keyed by filename, so a display string is the primary key

**Filed:** 2026-10-01
**Related:** task-446 (in progress), task-619, task-665, task-660

## Problem

`load_registry` (`routes/helpers.py:209`) builds every library registry by
listing `data/library/<type>/` and **keying each entry by its filename**:

    key = entry[:-5]
    result[key] = json.load(f)

So the primary key of a library entity is a display string. Everything that
binds a live node to a template therefore binds it *by name*, and a rename is
not a rename — it is a delete and an insert.

The live side is not the problem and should not be changed. `Player.id` is
already a surrogate key (`4be7db75`, `16b8b6ce` for the Eldenford cast),
generated at creation, persisted in the scenario, and never derived from a
display name. `engine/character_identity.py` additionally keeps a retired
authored id resolvable as an alias. That is the id-first contract
`AGENTS.md` requires, and task-446 built it.

**The gap is one-directional: the library has nowhere to record identity.**

### Why the live id cannot simply be copied into the library file

The relation is one-to-many, not one-to-one. `handle_spawn_character` hydrates a
`Player` from a template and mints a **fresh** id for each instance, so one
`Harren Cobb` entry legitimately becomes many live blacksmiths. A library entry
claiming to *be* `4be7db75` would be false the moment a second one spawned.

The working shape is two surrogate keys and a foreign key:

    data/library/characters/Harren Cobb.json
      character_id: "ch_8f2a1c9b"      <- surrogate key for the TEMPLATE
      name: "Harren Cobb"               <- pure display, never identity

    live player
      id: "4be7db75"                    <- surrogate key for the INSTANCE (exists)
      node.properties.library_id        <- foreign key to the template

`library_id` on the node is *already* that foreign key. It is simply pointing at
a filename today.

## What this has already cost, measured

- **A rename silently re-targeted a refresh.** `Refreshed "Eldenford Blacksmith"
  from library` applied **the merchant's** personality and description, because
  `Eldenford Blacksmith` was no longer a key after the rename to `Harren Cobb`
  and the node had no binding to fall back on. Recorded on task-665.
- **Two entries could claim one character.** `Pell Ardin.json` and
  `Eldenford Merchant.json` both carry `name: "Eldenford Merchant"`. Under
  name-based resolution either may claim the live node; there is nothing to
  arbitrate with.
- **Relationships are keyed by display name for the same root reason**
  (task-619): the four unmigrated cast files point at each other by their old
  role names.

## Constraint that shapes the fix: it must be additive

`library_id` values **already in the graph hold filenames** across all four
linkable types (item, way, area, character). Changing what the field means
without accepting the old form would break every bound node in every save.
Resolution must accept both the surrogate key and the legacy filename for as
long as saves exist that use it.

Items are the awkward case: `SPECS["item"].guess == "none"`, so a placed item's
`library_id` is whatever the author chose, and `_hydrate_item` resolves it.
Whatever shape is adopted has to keep resolving those.

## Acceptance

- [ ] Every `data/library/<type>/*.json` entry carries a stable surrogate key
      (`character_id`, `item_id`, …) generated once on creation and never derived
      from a display string. Filename remains a human label, not the key.
- [ ] `load_registry` indexes by the surrogate key **and** by the legacy
      filename, and resolution tries both, so existing saves keep working.
- [ ] `sync.resolve_template_id` and `linked_template_id` are unchanged in
      *order* (explicit -> link -> per-type guess) but a link may now hold
      either form. Add the reason to `engine/sync.py`'s docstring, since the
      field's meaning has changed.
- [ ] The per-type **name guess** (`guess="node_name"` for characters) resolves
      through the entry's `name` field via the surrogate index rather than
      assuming filename == name. It must also be **ambiguity-aware**: when two
      entries share a `name`, the guess must fail loudly rather than pick one.
- [ ] Renaming a library entry (there is already `POST
      /api/library/<type>/<id>/rename`) leaves every bound node resolving
      correctly, with no re-link step. **This is the acceptance that matters** —
      it is the case that broke.
- [ ] A round-trip proves it: rename `Harren Cobb` to anything, refresh the
      blacksmith node, read `player.personality` back and confirm it is the
      blacksmith's and not a neighbour's.
- [ ] Spawning two instances from one entry produces two distinct `Player.id`s
      and neither claims the other.
- [ ] `tools/character_loadout_check.py` does **not** flag `character_id`; and if
      a duplicate `character_id` is possible at all, something checks for it.

## What was done instead, on 2026-10-01

The unblock, not the fix. All five Eldenford nodes were bound explicitly through
the existing sanctioned path — `POST /api/library/refresh-to-world` with
`sections: []`, which applies nothing but still runs `sync.link`
(`routes/library_ops.py:1145`):

    Eldenford Blacksmith          library_id = Harren Cobb
    Eldenford Elder               library_id = Gareth Ollen
    Eldenford Farmer              library_id = Tobin Marsh
    Eldenford Merchant            library_id = Pell Ardin
    Eldenford Road Guard Captain  library_id = Corvin Hale

All five returned `applied: []`, `linked: true`. Sync no longer depends on any
name matching, so the cast can be synced now. That is a pin on today's
filename-shaped keys — it does not survive a future rename, which is exactly
what this task is for.