---
group: Tech Debt & Testing
---
# Task 97: Upgrade Playwright Tests — Actually Test Things

**Status**: In Progress (partial)  
**Priority**: High  
**Filed**: 2026-07-24  
**Updated**: 2026-07-31  

## The Problem

We have ~434 Playwright tests across 12 files, but bugs still slip through because the tests check **presence** and **API responses** — not actual **UI interactions**. The 10 recently-filed bugs (typos, method name mismatches, missing constructor attrs, CSS issues) are all things a click-through test should have caught.

## Test Pattern Analysis

**Current pattern** (checks function exists):
```javascript
await t('TriggerEditor.open exists', async () => {
    const ok = await page.evaluate(() => typeof TriggerEditor?.open === 'function');
    if (!ok) throw 'TriggerEditor.open not found';
});
```

**What we need** (actually click the button, catch the error):
```javascript
await t('Add Trigger button opens editor without errors', async () => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.click('.add-trigger-btn');
    await page.waitForTimeout(500);
    if (errors.length > 0) throw 'Console errors: ' + errors.join(', ');
});
```

## Plan: 5-Phase Upgrade

### Phase 1: Console Error Capture (Foundation)
**Goal**: Every test should fail if it triggers a console error, uncaught exception, or rejected promise.

- [ ] Add `page.on('pageerror')` capture to every test file's setup
- [ ] Add `page.on('console', msg => if (msg.type() === 'error') ...)` capture
- [ ] Create shared `startSession()` helper that wires up error capture + navigation
- [ ] Run existing tests with error capture enabled — they should all still pass (no bugs currently showing)

**Blocks**: None
**Bug coverage**: Would catch bug 1 (typo), bug 7 (method mismatch), bug 10 (missing attr) — the JS runtime errors

### Phase 2: Click-Through Tests for Bug-Prone Areas
**Goal**: Convert the 10 bug reports into regression tests that click real buttons.

| Bug | What to test | Approach |
|-----|-------------|----------|
| Bug 1 | Trigger editor: open from item, check no console errors | Click "Add Trigger" → verify modal appears → check error count |
| Bug 7 | Generate from Equipment button | Click "Generate from Equipment" → verify no 500 → verify textarea populated |
| Bug 10 | Turn advance: step through all characters, verify no crash | POST `/api/turn/apply` repeatedly until wrap-around → verify 200 |
| Bug 2/6 | Choices.js dropdowns visible | Click multi-select → verify `.choices__list--dropdown` has proper text color |
| Bug 4 | Initiative order display | Get state → verify turn queue shows correct agent order |
| Bug 5 | HP display formatting | Inspect character → verify HP value matches state |
| Bug 8 | Max steps limit | Set maxSteps=X → run agents → verify agent stops after X actions |
| Bug 9 | Settings tabs | Click each tab → verify tab content loads, no errors |

**Blocks**: Phase 1 (need error capture first)

### Phase 3: UI State Verification
**Goal**: After clicking/interacting, verify the DOM actually reflects the change.

- [ ] Edit a text field → click Save → reload → verify text persisted
- [ ] Change a dropdown → verify value stuck in the DOM
- [ ] Toggle a checkbox → verify state changed in the backend
- [ ] Delete a trigger → verify it's gone from the list
- [ ] Equip an item → verify paperdoll slot shows it
- [ ] Move a character via inspector → verify room changed

**Pattern**:
```javascript
await t('Edit description persists', async () => {
    const original = await page.inputValue('#inspector-description');
    await page.fill('#inspector-description', 'Test description change');
    await page.click('.save-btn');
    await page.reload();
    await page.waitForTimeout(1000);
    const after = await page.inputValue('#inspector-description');
    if (after !== 'Test description change') throw 'Description did not persist';
    // Cleanup
    await page.fill('#inspector-description', original);
    await page.click('.save-btn');
});
```

### Phase 4: Error Boundary / Resilience Tests
**Goal**: Verify the UI handles backend errors gracefully instead of throwing unreadable errors.

- [ ] Mock backend 500 → verify user sees friendly error message, not raw traceback
- [ ] Kill the server mid-session → verify UI shows "connection lost" not infinite spinner
- [ ] Send malformed data → verify form validation catches it before submission

**Pattern**:
```javascript
await t('Backend 500 shows user-friendly error', async () => {
    // Use page.route to intercept and return 500
    await page.route('**/api/action', route => route.fulfill({
        status: 500, contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
    }));
    await page.fill('#command-input', 'look');
    await page.press('#command-input', 'Enter');
    await page.waitForTimeout(500);
    const errorDisplay = await page.textContent('.error-message, .toast, #event-stream');
    // Should show something readable, not a traceback
    if (errorDisplay.includes('Traceback') || errorDisplay.includes('File "')) {
        throw 'Raw traceback shown to user';
    }
});
```

### Phase 5: CI-Ready Test Runner
**Goal**: Make it easy to run a meaningful subset of tests quickly.

- [ ] Add `--suite` flag to filter tests by category (smoke, regression, full)
- [ ] Add JUnit XML output for CI integration
- [ ] Create a "smoke suite" that runs in <30s covering the critical paths
- [ ] Create an "everything suite" that takes longer but covers all phases

## Project Structure

New file: `virtual_world/tools/test_helpers.cjs` (shared helpers):
```javascript
// startSession(browser, url) — launches page with error capture
// checkConsoleErrors(errors) — throws if any errors accumulated
// switchTab(label) — clicks tab by data-tab-btn content
// showAgent(name) — opens agent in inspector
// api(command) — POST /api/action shorthand
// getState() — GET /api/state shorthand
```

Existing files get upgraded in-place rather than rewritten:
- `test_all.cjs` — gets Phase 1 error capture + Phase 3 state verification
- `test_ui.cjs` — gets Phase 2 click-through + Phase 4 error resilience
- `test_ways.cjs` — gets Phase 3 state verification

## Requirements
- [x] Phase 1: Console error capture — `tools/test_helpers.cjs` created (`startSession`, `checkConsoleErrors`, `switchTab`, `showAgent`, `api`, `getState`, `gameCmd`); error capture (pageerror + console.error, filtering browser "Failed to load resource" noise) wired into `test_all.cjs`; `test_all.cjs` now closes the browser (runnable headless)
- [x] Phase 2: Bug-regression click-through tests — `tools/test_regressions.cjs` maps the 10 known bugs to real UI click tests (settings tabs, trigger editor open, generate-from-equipment, turn advance, max-steps, initiative order, HP display, dropdown readability)
- [ ] Phase 3: UI state persistence verification (edit → save → reload → verify) — only basic checks so far
- [ ] Phase 4: Error boundary/user-friendly error display tests (`page.route()` 500-mocking) — not implemented
- [ ] Phase 5: Test runner improvements (suites, CI output) — not implemented

---

## Status Update (2026-08-02)

**What's done:**
- `tools/test_helpers.cjs` — shared helper module with error-capturing `startSession()` and UI/API wrappers. Filters browser-injected `Failed to load resource` messages (expected from intentional 4xx/5xx failure-path tests) so only genuine page errors and `console.error()` calls are captured.
- `tools/test_all.cjs` — error capture added (pageerror + console.error), network-resource noise filtered, final "No JS/console errors" check added to the results, and `browser.close()` at the end. **Result: 153/153 passed.**
- `tools/test_regressions.cjs` — new click-through regression file mapping the 10 bug reports: settings tabs open without errors, trigger graph editor opens without JS errors, Generate-from-Equipment runs without errors, `/api/turn/apply` succeeds repeatedly, max-steps input updates `config.maxSteps`, initiative queue sorts players, HP display matches state, tag-multiselect dropdown text is readable. **Result: 14/14 passed** (several checks skip gracefully on the minimal test world — no item nodes / single player / no Choices.js dropdowns present).

**Remaining:**
- Wire error capture into the remaining ~12 `.cjs` test files via the helper (mechanical, low value — most already have basic `pageerror` capture).
- Phase 3: persistence verification pattern.
- Phase 4: `page.route()` 500-mocking and connection-loss error-boundary tests.
- Phase 5: `--suite` flag (smoke <30s / full) and JUnit XML output.
