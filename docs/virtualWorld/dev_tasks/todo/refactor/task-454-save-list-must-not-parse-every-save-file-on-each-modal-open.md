---
type: task
status: todo
area: refactor
priority: medium
---

# task-454: Save list must not parse every save file on each modal open

**Filed:** 2026-09-22
**Related:** task-401, task-402

## Goal

Make `GET /api/save-games` cheap regardless of how big the saved worlds get.

`list_save_games` (`routes/saveload.py:248-283`) walks `saves/` and **fully
`json.load`s every file** to read `_save_metadata` and to count
`len(data['players'])` / `len(data['areas'])`. That is an O(total bytes) parse of the
whole saves directory on every modal open. The list already carries saves in the
hundreds of KB; `task-401`/`task-402` are explicitly moving toward large worlds where
one save is megabytes and the directory holds many.

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
