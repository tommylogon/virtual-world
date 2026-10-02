---
type: task
status: todo
area: testing
priority: medium
---

# task-444: Playwright persistence, error-boundary and CI-runner suites

**Filed:** 2026-09-21
**Supersedes:** task-358 Phases 3–5 (Phases 1–2 shipped; that task is closed)
**Related:** `tools/test_helpers.cjs`, `tools/test_regressions.cjs`, `tools/test_all.cjs`

## Goal

The Playwright suite currently checks **presence and API responses**, not that the UI
persists state or degrades gracefully. Finish the three unstarted phases.

## Verified state (2026-09-21)

- Phases 1–2 landed: `tools/test_helpers.cjs` (103 lines) exports `startSession`,
  `checkConsoleErrors`, `switchTab`, `showAgent`, `api`, `getState`, `gameCmd`;
  `tools/test_regressions.cjs` (181 lines) covers the ten filed bugs.
- **Phase 3 (persistence): not started** — `grep 'page.reload' tools/` → 0 hits.
- **Phase 4 (error boundaries): not started** — `grep 'page.route' tools/` → 0 hits.
- **Phase 5 (runner): not started** — no `--suite` flag, no JUnit output.
- Corrected counts: `tools/` holds **28** `.cjs` files (not 12), and the helper is adopted
  by **2** of them (`test_regressions.cjs`, `test_trigger_search_select.cjs`); ~15 files
  have their own inline `pageerror` capture and ~10 have none. `tools/test_ways.cjs`
  **does not exist** (task-358 named it).

## Phase 3 — persistence (edit → save → reload → verify)

Cover the paths that actually lose data: edit a description field and reload; change a
dropdown; toggle a checkbox and confirm the backend changed; delete a trigger and confirm
it is gone; equip an item and confirm the paperdoll slot; move a character and confirm the
room changed. Pattern is already written in task-358's Phase 3 block — a test must fail
when persistence breaks, not merely exercise the handler.

## Phase 4 — error boundaries

Use `page.route()` to return 500s and assert the user sees a readable message rather than
a raw traceback; kill the server mid-session and assert a "connection lost" state rather
than an infinite spinner; send malformed data and assert client-side validation catches it.

## Phase 5 — CI runner

`--suite` (smoke / regression / full) plus JUnit XML. The smoke suite should cover the
critical paths in under 30 seconds.

## Acceptance

- [x] At least one persistence test per Phase-3 bullet, and it fails if the save/reload path is
  broken.
- [x] A mocked 500 produces a friendly message — the assertion explicitly rejects `Traceback`
  or `File "` in user-visible text.
- [x] `--suite smoke` completes in <30s and writes JUnit XML.
- [x] Any file the helper is wired into still passes.

## Outcome (2026-10-02)

New files: `tools/test_runner.cjs` (Phase 5), `tools/test_persistence.cjs`
(Phase 3), `tools/test_error_boundaries.cjs` (Phase 4), `tools/test_smoke.cjs`.

**Phase 3 — persistence** (`tools/test_persistence.cjs`, one test per bullet):
1. description edit → save-game → mutate → load-game (a real disk round-trip).
2. narration dropdown change reaches the backend and survives reload.
3. ghost-mode checkbox change reaches the backend.
4. deleting a trigger is persisted (create → reload → delete → reload).
5. equipping an item is reflected in the paperdoll and persists.
6. moving a character changes the room and survives reload.

**Phase 4 — error boundaries**: a mocked JSON 500 and a mocked **non-JSON** 500
both assert the UI shows `Request failed (500 …)` and **never** `Traceback` or
`File "`; malformed data surfaces a short error rather than a stack trace. This
required a real fix: `ApiClient.post`/`get` did `return resp.json()` without
checking `resp.ok`, and the command bar logs `data.error` verbatim, so a Flask
500 traceback was rendered to the player. `ApiClient._errorMessage` now
substitutes a status message (`static/js/api.js`).

**Phase 5 — runner**: `node tools/test_runner.cjs --suite smoke|full [--junit f]`.
Auto-starts the server on `VW_PORT` if the URL is unreachable and stops it after.
`smoke` = boot + one persistence + one error boundary.

**Live evidence** (server on `VW_PORT=4470`):
- `--suite full`: **11/11 passed in 9.2s**, JUnit written.
- `--suite smoke`: **4/4 passed in 2.8s** (<30s), JUnit written.
- `node tools/unit/run.cjs`: 485 passed / 0 failed; `npx eslint static/js/api.js` clean.

**Helper change**: `tools/test_helpers.cjs` now takes the base URL from
`VW_URL`/`VW_PORT` (parallel worktrees must not fight over 4444) and navigates
with `domcontentloaded` instead of `networkidle` — the app holds an SSE
connection to `/api/events`, so `networkidle` always timed out. `switchTab`
selected `[data-tab-btn]`, which no element carries; it now matches `[data-tab]`.

**Known gaps (honest):**
- The "kill the server mid-session → connection lost" bullet is not covered; it
  needs a second server lifecycle and a UI state assertion that does not exist
  yet. Filed as follow-up.
- `tools/test_regressions.cjs` still fails 2 of 14 on `Tab "Bio" not found`: the
  Bio tab no longer exists in the UI. This predates the helper change (the old
  `[data-tab-btn]` selector matched nothing either) and is UI drift, not a
  helper regression. Not fixed here — `test_regressions.cjs` is a standalone
  harness and rewriting its tab targets is a separate task.

## Non-goals

- **Wiring the helper into the remaining ~26 `.cjs` files.** Task-358 itself called this
  "mechanical, low value"; do it only where a file is being touched for another reason, or
  delete the file if it is dead. The two adopters are the ones that matter.
- Re-running the historical `153/153` / `14/14` counts — point-in-time, nothing contradicts
  them.
