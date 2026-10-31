---
type: task
status: done
area: ui
priority: medium
wiki: "[[Settings & Configuration]]"
related: ["task-909", "task-910", "task-304"]
---

# task-925: Settings modal Clean Code MVC refactor and embedding consolidation

**Filed:** 2026-10-31
**Status:** done
**Related:** task-909, task-910, task-304

## What

Refactor the Settings modal and configuration pipeline to follow Clean Code and MVC principles:

1. **Centralized Configuration Schema (`CONFIG_SCHEMA`)**:
   - Define a single source of truth for all 46 config fields in `static/js/config.ts`.
   - Specify storage keys, data types (`string`, `number`, `boolean`), and canonical fallback defaults in one typed dictionary.
   - Prevent default values from drifting across multiple files.

2. **Declarative View Binding & Model Decoupling**:
   - Implement `SettingsView.readForm()` to scan modal controls with `data-config="fieldName"`, coercing types based on `CONFIG_SCHEMA`.
   - Decouple `config.saveFromForm()` from direct DOM queries (`document.getElementById`), delegating to `SettingsView.readForm()`.
   - Stamp declarative `data-config` attributes across form controls in `templates/index.html`.

3. **Subsystem Consolidation & Interaction Parity**:
   - Retire the separate `Embedding` tab button and pane, consolidating embedding settings directly into the `Connection` tab (`tab-connection`).
   - Add a diagnostic `testMemoryConnection()` method and UI button (`#test-memory-btn`) with live latency measurement for the Dedicated Memory Worker, providing diagnostic parity with the Main LLM and Embedding models.
   - Fix nested `.settings-group` markup bugs in `templates/index.html` where memory and embedding groups were unclosed or nested inside the API Connection group.

## Why

Auditing the Settings modal revealed significant architectural debt:
- 52 direct `document.getElementById` calls inside the Model class (`config.ts`).
- Brittle inline `onchange` string scripts mutating global state directly from HTML attributes.
- Default connection values (`http://localhost:1234/v1`, `not-needed`, `lmstudio-community/lfm3-1.7b`) hardcoded and duplicated across 6 different files.
- Memory Worker lacked any diagnostic feedback, meaning connection failures or model misconfigurations were invisible until runtime character turns.
- Embedding settings sat in an isolated tab with only two text inputs.

## How

- `static/js/config.ts`:
  - Declare `CONFIG_SCHEMA` with typed field definitions and canonical defaults.
  - Refactor `_loadFromStorage()`, `getMemoryLLMClient()`, and `_getDefaultProfiles()` to read from `CONFIG_SCHEMA`.
  - Update `saveFromForm()` to delegate form reading to `SettingsView.readForm()`.
- `static/js/ui/settings-view.ts`:
  - Implement `readForm()` with type coercion and `turnOrder` normalization.
  - Implement `testMemoryConnection()` with timing measurement and error handling.
  - Add backwards-compatible alias for `switchTab('tab-embedding')` -> `'tab-connection'`.
- `templates/index.html`:
  - Add `data-config` attributes to inputs in `tab-connection`, `tab-agent`, and `tab-automation`.
  - Fix `.settings-group` nesting layout.
  - Add the Test Connection button and result span for the Memory Worker.
- `tools/unit/test_graph_toolbar.js` & `tools/unit/test_graph_tuning.js`:
  - Update DOM slice boundary from `tab-embedding` to `tab-engine-config` while preserving all 14 `GraphNetwork.applyGraphSettings()` call assertions.

## Verification

1. Run full JavaScript unit test suite:
   - `node tools/unit/run.cjs` (898 passed, 0 failed across 78 test files).
2. Run targeted graph toolbar and tuning tests:
   - `node tools/unit/run.cjs graph_toolbar graph_tuning` (23 passed, 10 passed).
3. Run targeted pytest suites:
   - `python -m pytest tests/test_trigger_migration.py tests/test_world_scopes.py` (42 passed).
4. Verify TypeScript compilation:
   - `npm run build:ts` (0 errors).
5. Verify em-dash absence:
   - Zero em-dashes introduced across all touched files.

## Acceptance

- [x] Model: `CONFIG_SCHEMA` defines all setting keys, types, and defaults in a single typed dictionary.
- [x] Model: `config.saveFromForm()` delegates to `SettingsView.readForm()`, eliminating direct DOM parsing from the model.
- [x] View: Form controls bind declaratively via `data-config="fieldName"`.
- [x] View: Embedding settings live within `tab-connection` as a clean sibling group.
- [x] View: Memory Worker has a live diagnostic Test Connection button reporting response time in milliseconds.
- [x] Tests: All existing unit tests and graph tuning test contracts remain 100% green.

## Files

- `static/js/config.ts`
- `static/js/config.js`
- `static/js/ui/settings-view.ts`
- `static/js/ui/settings-view.js`
- `templates/index.html`
- `tools/unit/test_graph_toolbar.js`
- `tools/unit/test_graph_tuning.js`
- `docs/virtualWorld/UI & Settings/Settings & Configuration.md`
