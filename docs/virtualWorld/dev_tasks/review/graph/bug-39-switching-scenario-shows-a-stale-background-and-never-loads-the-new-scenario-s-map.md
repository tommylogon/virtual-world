---
type: bug
status: review
area: graph
priority: high
---

# bug-39: Switching scenario shows a stale background and never loads the new scenario's map

**Filed:** 2026-09-22
**Related:** bug-38, task-451 (multiple images), task-408 (scenario naming)

## Symptom

Reported live: switching scenarios through the **Scenario Manager** did not switch the
graph's background image to the new scenario's. The old map did not come back correctly
either - the layer simply ended up hidden, and the new scenario's own map never appeared
even though it existed on the client.

## Root cause

`_restore()` (`static/js/graph/graph-background.js`) read the world's block as:

```js
let record = (worldState?.data?.graph_background) || null;
if (!record && identity && storage) { record = await storage.get(STORE, state.key); }
if (!record) { if (state.image || state.rect) reset(); return; }
```

A scenario with no map **still serializes the key**, as `{}`
(`engine/serialization.py:494` stores `background if isinstance(background, dict) else {}`,
and `:236` writes it back). In JavaScript **`{}` is truthy**, so an empty block was taken as
a real record. That single mistake broke both halves of the rest of the function:

- the `if (!record)` branch never ran, so the previous scenario's image was **never cleared**;
- the IndexedDB fallback was **never consulted**, so the new scenario's locally-cached map
  could never be restored;
- `state.rect = record.rect || null` then set `rect` to `null` while `state.image` still held
  the old image, and `_render()` computes `has = !!(state.image && state.rect)` - so the layer
  was hidden and the old map appeared to vanish.

Net effect: the world's missing map was read as "a map with nothing in it", which is a
different thing from "no map".

Data corroboration: only `data/scenarios/kraktooth_goblin_camp.json` carries a
`graph_background` block. Every other scenario file has none, while
`static/images/backgrounds/` holds five images - i.e. per-scenario maps exist locally but the
world block is empty, which is exactly the failing input.

## Fix

A record now has to actually contain something. Added `_hasBackground(record)`: true when it
has an `image`, a `rect`, or non-empty `positions`. The world block is used only if it passes
that test, and the same test guards the cached record before it is accepted. The clear branch
therefore runs for a genuinely empty world, and the per-scenario cache is reachable again.

Also hardened while in there: the outgoing image is dropped when the incoming source differs,
so the new scenario's rect is never drawn with the previous scenario's pixels while the new
image decodes; and a record with no image clears `state.image`/`state.imagePath` rather than
leaving a transform pointing at nothing.

## Verification (live, in the running app; the tester's world was not reloaded)

Probed through the real `state:updated` -> `_onWorldRefetched()` -> `_restore()` path:

| probe | input | result |
|---|---|---|
| T1 | fabricated previous map on screen + world block `{}` | cleared: `image=false`, `rect=false`, layer `none` |
| T2 | world block `{}` + a cached record under the new scenario's key | restored **from cache**: `image=true`, `rect=true`, `opacity=0.42`, layer `block` |
| T3 | the real block put back | restored: `image=true`, `rect=true`, `imagePath=/static/images/backgrounds/…`, layer `block` |

T1 and T2 are the two behaviours the bug destroyed. The probe record was deleted and the live
scenario (`kraktooth_goblin_camp`) confirmed intact afterwards.

## Acceptance

- [ ] Switching to a scenario with no map clears the previous map (no stale pixels, layer hidden).
- [ ] Switching to a scenario whose map lives only in the local cache restores it.
- [ ] Switching to a scenario whose map lives in the world/file restores it.
- [ ] No flicker of the previous scenario's image under the new rect.
- [ ] Rapid successive switches settle on the last scenario's map.

## Files

- `static/js/graph/graph-background.js` - `_hasBackground()` and `_restore()`

## Note for task-451

When backgrounds become a **list**, the emptiness test must move with them: an empty list or
an empty block must still clear. The predicate is `_hasBackground()`, kept as one place so the
list form has a single thing to extend.
