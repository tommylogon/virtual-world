# Bug-16: Creating a New Way Without an ID Overwrites an Existing Node

**Status:** In Review — implemented 2026-08-16, in `routes/graph.py` `build_connect_legacy`: no manual ID now generates a unique id (`base`, `base_2`, ...) via a `get_node` collision loop + `_slugify_node_id(dir1)`. Regression test added in `tests/test_way_connect_repair.py` (`test_build_connect_no_way_id_generates_unique_id`), all 941 pytest pass.
**Area:** Graph editor — way creation
**Observed:** `create new way without setting a id will overwrite a existing node, not create a new way with a unique ID`
**Repro:** Create one way with no manual Way ID (the auto-generated id is stored),
then create a second way likewise with no manual Way ID — the second one replaces
the first instead of being a new node.

## Root cause

`routes/graph.py` `build_connect_legacy` (lines ~428-431):

```python
way_id = data.get('way_id', '') or ''
way_id = _slugify_node_id(way_id)
if not way_id:
    way_id = f"way_{_slugify_node_id(room1)}_{dir1}"
```

When no way ID is supplied the route always generates the same deterministic id
from `(room1, dir1)`. Creating a *second* way with the same pair (or two ways
between the same areas) regenerates that identical id.

Then `graph.add_node` (`graph.py:66-80`) only auto-suffixes **items, doors, and
logic_triggers** on id collision:

```python
if node.type in ('item', 'door', 'logic_trigger'):
    suffix = str(uuid.uuid4())[:8]
    node.id = f"{node.id}_{suffix}"
```

`way` is **not** in that list, so the collision falls through and
`self.nodes[node.id] = node` silently overwrites the existing way node (and the
route then rewires the stale edges for that id). No error, no unique id.

## Expected

Creating a way without specifying an ID should generate a unique way ID
(e.g. `way_<room>_<dir>` with a numeric suffix `_2`, `_3`, ... on collision),
preserving the existing node — consistent with the `way_<room>_<dir>_<suffix>`
handling used by other node types, and with the lowercase/node-id conventions
(`build_item` already reuses/finds case-insensitive matches to avoid dupes).

## Fix options

1. In `build_connect_legacy`, when `way_id` is empty, loop for a free id:
   `base = f"way_{slug(room1)}_{slug(dir1)}"`, then `base`, `base_2`, `base_3`,...
   until `graph.get_node(candidate)` is None.
2. Also `slugify(dir1)` in that fallback so the generated id has no spaces
   (currently the raw dir string is embedded).
3. Optionally return/log the actual id so the UI shows what was created.