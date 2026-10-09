---
type: task
status: todo
area: ui
priority: high
---

# task-753: Reduce /api/state server build time: gzip done, but the payload still takes 5-6s to serialize

**Filed:** 2026-10-09
**Related:** bug-531 (image decode on refresh), task-752 (NL overlay tokens), task-439 (area identity)

## Goal

`GET /api/state` was 13.35 MB / 9.2 s on the 627-area camp world. First-pass fixes
(shipped 2026-10-09) took it to **7.87 MB / 6.6 s**, and gzip took the wire to
**0.49 MB**:

- gzip added in `app.py` `after_request` (API JSON, when the client accepts it).
- `handle_get_state` drops `rooms` (an exact duplicate of `areas` — `serialization.py`
  emits the same dict under both keys) and `areas_by_id` (no HTTP consumer; the
  browser reads `worldState.areas`). `to_dict` is unchanged, so
  `tests/test_area_identity.py` still sees `areas_by_id`.

What remains is **server build time (~5–6 s)**, which gzip does not address — it is
Python assembling and encoding the payload. Dominant contributors measured:

- `graph` ~3.2 MB / 2739 nodes / 6285 edges (`graph.to_dict()`).
- `areas` ~2.8 MB (full per-area records).
- `world_scopes` ~1.3 MB, `world_index` ~0.47 MB.

Also relevant: `worldState.startPolling` refetches the **full** state every 1.5 s in
spectator mode (`world-state.ts:105`); a 5 s build stacks requests, so the server is
always mid-serialize. An in-flight guard was added (skip a tick while a fetch is
outstanding), but the build time is the root cause.

## Plan

1. Profile `to_dict`/`jsonify` to split build vs encode (the two together are the 5 s).
2. Scope or trim the payload: send `graph` and `areas` for the active scope (or a
   slim area projection: id/name/tags only) and fetch detail on demand
   (`get_node`/area inspector already do this).
3. Consider making the spectator poll condition on `log_revision`/SSE `world_changed`
   rather than a blind 1.5 s full fetch.

## Acceptance

- [ ] Build time split measured (assembly vs JSON encode) and recorded.
- [ ] Full `/api/state` server build materially under the current ~6 s on the camp
      world (target ≤1–2 s), with the wire payload ≤1 MB gzipped.
- [ ] No feature regression: area inspector, exits/look, item/way views still read
      what they need (fetch-on-demand where detail is dropped).
- [ ] Spectator polling does not saturate the server on a large world.
- [ ] `tests/test_area_identity.py` and the full suite unaffected.
