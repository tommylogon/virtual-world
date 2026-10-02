#!/usr/bin/env python3
"""The character-loadout rule declaration.

This is the single place the loadout rules are named, rated and explained. It is
consumed by ``tools/character_loadout_check.py`` (the executable) and pinned by
``tests/test_character_loadout_check.py`` (the contract), the same split
``tools/way_properties.py`` uses to feed ``tools/way_property_index.py``.

Keeping the *reasons* here rather than inline in the checker means the valuable
part of each rule — why bad data is a defect and not a style nit — is
referenceable by the docs and the tests, not buried in the scanner.
"""

#: ERROR = the data breaks a code path (crash, silent drop, unresolvable id).
#: WARN  = suspicious or inconsistent, but every reader survives it.
ERROR, WARN = "ERROR", "WARN"

#: check id -> (severity, label, why)
CHECKS = {
    "equipped_dict_entry": (
        ERROR,
        "equipped slot holds a dict, not a node-id string",
        "refresh-to-world writes this verbatim and is_exposed() calls "
        "graph.get_node() on it -> GET /api/state 500s. Use the node-id string.",
    ),
    "equipped_slot_not_list": (
        ERROR,
        "equipped slot is not a list",
        "import skips non-list slots outright (library_ops.py:567), so the "
        "equipment is dropped with no error.",
    ),
    "equipped_id_not_in_inventory": (
        ERROR,
        "equipped node id has no matching inventory entry",
        "import resolves strings against item names on the carrying edges, so "
        "an id with no inventory entry leaves the slot empty. Either add the "
        "item to inventory or drop it from equipped.",
    ),
    "missing_node_id": (
        WARN,
        "inventory entry has no node_id",
        "import mints a random id instead, so any equipped reference to it "
        "cannot be written by hand.",
    ),
    "missing_properties": (
        WARN,
        "inventory entry has no properties",
        "import materialises the item with no props: no equip_slots, no "
        "weight, no actions. See task-519 on lossy materialization.",
    ),
    "slot_not_declared": (
        WARN,
        "equipped in a slot the item does not declare in equip_slots",
        "equip_item may refuse, or may place it somewhere the rest of the "
        "engine does not read. See task-654 on declared-vs-used slots.",
    ),
    "name_does_not_match_file": (
        WARN,
        "internal name does not match the file name",
        "the registry keys on the file, and a browser save writes "
        "<Live Name>.json -- so a mismatch produces a duplicate entry on the "
        "next save. See task-665.",
    ),
    "unknown_library_id": (
        WARN,
        "inventory library_id is not an item library entry",
        "import auto-registers it into items.json on first use, which means "
        "the canonical definition is whatever this character happens to carry.",
    ),
}
