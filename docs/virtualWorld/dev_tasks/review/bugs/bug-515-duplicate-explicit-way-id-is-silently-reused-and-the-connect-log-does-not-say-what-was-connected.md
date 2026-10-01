---
type: bug
status: review
area: bugs
priority: medium
---

# bug-515: Duplicate explicit way id is silently reused and the connect log does not say what was connected

**Filed:** 2026-10-01
**Related:** bug-16, task-376

## Symptom (reported live)

In a blank scenario with two rooms and a way whose manual Way ID is `door1`,
making a **second** way with the same id `door1` logs

```
[Tick 2 | 08:00] World  Connected rooms
[Tick 3 | 08:00] World  Connected rooms
```

but no second door appears. Nothing says the way already existed, and nothing
says which areas were connected by which way.

## Root cause

Two independent gaps:

1. **The collision is a silent overwrite.** `Graph.add_node` auto-suffixes only
   `item`/`door`/`logic_trigger`/`character`; a `way` collision falls through to
   `self.nodes[node.id] = node` (`graph.py:162-173`). With an explicit
   `way_id` the route uses the id verbatim (`routes/graph_ops.py`), so the
   existing `door1` is replaced in place.
2. **The response reports nothing.** `handle_build_connect_legacy` returned a bare
   `{"status": "success"}`, and the client logged a fixed string
   (`main.js:224` "Connected rooms"; the task-376 wizard at
   `graph/event-handlers.js:199` "Connected A <-> B"). Neither says whether a way
   was created or an existing one reused, nor which way.

Note the existing tests (`test_build_connect_removes_stale_edges`,
`test_build_connect_replaces_old_side`) show that re-using an explicit `way_id`
is an **intentional update/rewire**, so the fix is honest reporting, not a
refusal. This is distinct from bug-16, which was the no-id case.

## Fix

- `routes/graph_ops.py` — capture whether the way existed before `add_node` and
  return `created`, `way_id`, `way_name`, `area_from`, `area_to`,
  `area_from_id`, `area_to_id`.
- `static/js/main.js` — new `connectSummary(res, payload)` builds the log line:
  - created: `Connected "<A>" <-> "<B>" via way '<name>'`
  - reused: `Way '<name>' already existed — rewired "<A>" <-> "<B>" (no new way created)`
- `static/js/graph/event-handlers.js` — the task-376 wizard uses the same helper.
- `eslint.config.js` — `connectSummary` added to the cross-file globals list.

## Tests

`tests/test_way_connect_repair.py::test_build_connect_reports_created_and_areas`
— first connect with `way_id: door1` reports `created: true` and the two area
names; a second connect with the same id reports `created: false` and the same
areas; exactly one `door1` node exists.

## Verification

- `python -m pytest tests/test_way_connect_repair.py -q` — 6 passed.
- `npm run lint`, `npm run typecheck` — clean.
- `node tools/unit/run.cjs` — 465 passed.
- Live browser check of the new log line: pending.

## Acceptance

- [ ] Connecting with a fresh `way_id` logs the two room names and the way id.
- [ ] Connecting again with an existing `way_id` logs that the way already
      existed and was rewired (no new way created).
- [ ] No connection ever logs a bare "Connected rooms" with no areas/way named.
- [ ] An `area` id collision still raises (unchanged).

## Files

- `routes/graph_ops.py` — `handle_build_connect_legacy` response
- `static/js/main.js` — `connectSummary`, `connectRoomsViaGraph`
- `static/js/graph/event-handlers.js` — `onAddEdge` success log
- `eslint.config.js` — globals
- `tests/test_way_connect_repair.py`
