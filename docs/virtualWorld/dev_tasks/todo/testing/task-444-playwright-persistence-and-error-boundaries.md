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

- At least one persistence test per Phase-3 bullet, and it fails if the save/reload path is
  broken.
- A mocked 500 produces a friendly message — the assertion explicitly rejects `Traceback`
  or `File "` in user-visible text.
- `--suite smoke` completes in <30s and writes JUnit XML.
- Any file the helper is wired into still passes.

## Non-goals

- **Wiring the helper into the remaining ~26 `.cjs` files.** Task-358 itself called this
  "mechanical, low value"; do it only where a file is being touched for another reason, or
  delete the file if it is dead. The two adopters are the ones that matter.
- Re-running the historical `153/153` / `14/14` counts — point-in-time, nothing contradicts
  them.
