---
type: task
status: done
area: refactor
priority: high
---

# task-454: Save list must not parse every save file on each modal open

**Filed:** 2026-09-22
**Related:** task-401, task-402

## What

`GET /api/save-games` walks `saves/` and fully `json.load`s every file on each modal open to read `_save_metadata` and count `len(data['players'])` / `len(data['areas'])` — an O(total bytes) parse of the whole saves directory every time you open Save/Load. The list already carries saves in the hundreds of KB; task-401/task-402 are moving toward megabyte worlds with many of them. Preferred fix: a metadata index keyed by filename (option 1) plus storing `players`/`areas` counts in `_save_metadata` at save time (option 2), verified against `mtime`+`size`, falling back to a parse only when the index is missing or stale. A stale or corrupt entry must self-heal and never crash the list.

## Options

1. **Metadata sidecar / index.** Write a small `<file>.meta.json` (or one
   `saves/index.json`) at save time holding filename, name, scenario, timestamps,
   tick/turn/player, version, schema_version, players, areas, size. List reads only
   those; invalidate by comparing mtime+size.
2. **Extend the in-file metadata.** Store `players`/`areas` counts in `_save_metadata`
   at save time, then list only needs the metadata. A full parse is still required to
   reach it unless combined with a small header read, so combine with (1) or (3).
3. **Lazy per-row detail.** Return filename + cheap `os.stat` fields for the list and
   fetch metadata only for rows the user expands. Bigger UI change.

Prefer (1) with (2): a metadata index keyed by filename, verified against
`mtime`+`size`, falling back to a parse only when the index is missing/stale. A stale
or corrupt entry must self-heal, never crash the list.

## Acceptance

- [ ] Opening the modal with N large saves does not read the full body of every file;
      a benchmark or log makes the difference visible (ties to task-402).
- [ ] The rendered list is unchanged for existing saves (stats, autosave pinned top).
- [ ] Adding/overwriting/renaming/deleting a save updates or invalidates its index
      entry; an out-of-band file edit (external agent, git checkout) is detected and
      refreshed.
- [ ] A malformed save or index entry degrades gracefully (row still appears, no 500).

## Files

- `routes/saveload.py` — `list_save_games` (248-283)
- `routes/helpers.py` — write the index/metadata at save/autosave time
- `tests/test_saveload.py` — index hit/miss/stale coverage

## Why

Opening Save/Load is one of the most common things a player does, and today it pays for the size of every save on disk rather than for the screen it is drawing. The cost is invisible until it is not: a directory of large saves turns a modal open into a wait, and it gets worse as worlds grow because the work is O(total bytes), not O(rows). Editors and agents hit the same endpoint on every scenario switch. A metadata index keyed by filename, verified against `mtime`+`size`, makes the list bounded by metadata size and self-heals: a save written by another process or checked out from git is detected and refreshed, and a malformed save or index entry degrades to a safe row instead of a 500. Reuse the save-time path that already writes `_save_metadata` — extend it rather than add a second writer — so the index and the file cannot drift. Player experience: the same list, same stats, autosave pinned at the top, just fast. Editor experience: adding, overwriting, renaming or deleting a save updates its row immediately, with no stale index entry left behind.

## How

1. In `routes/helpers.py`, write the index at save/autosave time alongside the existing `_save_metadata` write — one writer, so the index and the file cannot drift. Index entry per save: filename, name, scenario, timestamps, tick/turn/player, version, schema_version, players, areas, size, mtime.
2. In `list_save_games` (`routes/saveload.py:248-283`), read the index first; verify each entry against `mtime`+`size`, and only parse the full file when an entry is missing, stale or corrupt. A malformed save renders a safe row and never 500s.
3. Invalidation: adding/overwriting/renaming/deleting a save updates or removes its index entry; an out-of-band edit (external agent, git checkout) is detected by mtime/size mismatch and refreshed on the next open.
4. Verify with a benchmark or log that ties to task-402: opening the modal with N large saves does not read the full body of every file.

**Dedup / reuse / quality / experience (added 2026-10-16).** Reuse the save-time path that already writes `_save_metadata` rather than adding a second writer that can drift from it — the index is an extension of metadata the file already carries, not a parallel store. Quality: the rendered list is unchanged for existing saves (same stats, autosave pinned at the top), so this is a performance change with zero behavioural delta. Agent/editor experience: the endpoint stays cheap no matter how big scenarios get, so scenario switching and save management stop scaling with world size. Player experience: Save/Load opens instantly instead of parsing every save on disk, with the same rows and the same autosave-at-top behaviour.

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Browser UI and intended live verification

Intended UI home: Game menu → Save/Load modal → open the save list with many large saves present; inspect rendered rows and request timing/network activity.

Current availability: the card records that `GET /api/save-games` parses every full save file on each modal open. The metadata index/cache and invalidation behavior are planned; no performance improvement is claimed as shipped.

Live steps when available:
1. Prepare N large saves, open Save/Load, and capture the `/api/save-games` request duration and bytes read using the browser Network panel/server trace.
   - expected: list latency and bytes read stay bounded by metadata/index size rather than total save-body size; autosave remains pinned at the top with the same stats line.
2. Add, overwrite, rename, and delete a save from the modal, reopening the list after each operation.
   - expected: the corresponding row and metadata update immediately; no stale index entry remains.
3. Edit a save file out of band and reopen Save/Load.
   - expected: the index detects the changed file and refreshes that row's metadata.
4. Include one malformed save and one malformed index entry.
   - expected: the list still renders a safe row or explicit error state and the endpoint does not return 500.

This section is not a claim that the metadata index or its cache is implemented today.
