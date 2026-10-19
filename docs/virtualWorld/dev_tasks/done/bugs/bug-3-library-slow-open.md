# Bug 3: Library browser is noticeably slower to open and interact with

**Filed**: 2026-07-23
**Priority**: High
**Status**: Fixed (frontend only — parallel fetches + no duplicate)

## Summary

Opening the library browser and switching tabs is noticeably slower than before. The delay is several seconds.

## Root Cause

Two compounding performance issues:

### 1. Sequential API calls + duplicate item fetch

`libraryBrowser.open()` calls `refreshAll()` which makes **6 sequential** API calls (`GET /api/library/items`, `characters`, `areas`, `traits`, `conditions`, `behaviours`). Then `switchTab('items')` calls `itemLib.open()` which calls `itemLib.refresh()` → another `GET /api/registry/items`. Items data is fetched **twice** on every open.

Fix: run `refreshAll()` fetches in parallel with `Promise.all`. Skip `itemLib.refresh()` in `itemLib.open()` when data already exists from `refreshAll()`.

### 2. Server reads individual files per entry

`routes/helpers.py:load_registry()` calls `os.listdir()` then opens and `json.load()` each file individually. For 231 items, that's 231 file I/O operations per request.

Fix: add a simple in-memory LRU cache keyed by `(data_dir, filename)` with ~60s TTL, so repeated requests within a short window don't re-read all files.

### 3. (Minor) renderList re-renders entire list HTML on every interaction

`library-browser.js:renderList()` builds the entire list HTML from scratch every time a tab is switched or an entry is selected. For 231 items this is fast, but it adds up with the double-fetch.

Fix: virtual list or debounce, but this is secondary — the main wins are #1 and #2.

## Files

- `static/js/library-browser.js:55-63` — sequential fetches
- `static/js/item-library.js:72-85` — `open()` re-fetches items
- `routes/helpers.py:50-71` — `load_registry()` per-file I/O

---
_Audited 2026-08-03 � duplicate file consolidated into this record._
