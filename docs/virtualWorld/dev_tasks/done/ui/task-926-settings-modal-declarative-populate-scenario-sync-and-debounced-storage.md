---
type: task
status: done
area: ui
priority: medium
wiki: "[[Settings & Configuration]]"
related: ["task-925", "task-845", "task-894"]
---

# task-926: Settings modal declarative populate, scenario state sync, and debounced storage

**Filed:** 2026-10-31
**Closed:** 2026-10-31
**Status:** done
**Related:** task-925, task-845, task-894

## What

Complete the Settings modal MVC refactor started in task-925:

1. **Declarative Bi-directional Binding in `SettingsView.populateForm()`**:
   - Modernize `populateForm()` to read declaratively from `CONFIG_SCHEMA` and `[data-config]` attributes across all tabs.
   - Eliminate ~100 lines of manual `document.getElementById` and fallback defaults that drift from the model schema.
   - Automatically format and update companion `-val` display spans for range sliders in a single helper.
   - Add `data-config` attributes to all controls in `tab-graph` in `templates/index.html` while preserving existing `GraphNetwork.applyGraphSettings()` call assertions.

2. **Scenario Flag Synchronization on Save**:
   - Toggling scenario-scoped flags in the modal (`mature_content`, `ghost_mode`, `auto_generate_descriptions`) must synchronize to their corresponding server endpoints (`/api/settings/mature_content`, `/api/settings/ghost_mode`, `/api/settings/auto_generate_descriptions`).
   - Prevents desync where client IndexedDB reflects a toggled state while the backend simulation and the Benchmark Lab (`templates/benchmark.html`) continue running with stale scenario values.

3. **Debounced `config.save()` for Range Sliders**:
   - Add a 150ms debounce window to `config.save()` when slider values change.
   - Retain instant 60fps canvas updates via `GraphNetwork.applyGraphSettings()` during mouse drags while eliminating IndexedDB transaction flooding.

4. **Benchmark Lab Access & Shared State**:
   - Verify that `(window as any).CONFIG_SCHEMA` and `config` profiles remain fully accessible and functional in `templates/benchmark.html` and `static/js/benchmark/benchmark.js`.

## Why

1. `task-925` introduced `CONFIG_SCHEMA` and made `readForm()` declarative, but `populateForm()` was left with 120 lines of manual DOM lookups and hardcoded fallback defaults that drift when schema values change.
2. Scenario flags like `matureContent` were saved only to client IndexedDB, leaving `app.world.mature_content` desynchronized on the server.
3. Continuous dragging on physics range sliders generates 60-100 async IndexedDB transactions per second, introducing unnecessary I/O friction.

## Acceptance

- [x] `SettingsView.populateForm()` populates all `[data-config]` inputs declaratively from `config` / `CONFIG_SCHEMA`.
- [x] Companion `-val` display spans update automatically for all range sliders without manual boilerplate.
- [x] Saving settings synchronizes scenario flags (`mature_content`, `ghost_mode`, `auto_generate_descriptions`) to server endpoints.
- [x] `config.save()` is debounced during slider input to prevent transaction spamming.
- [x] All 14 `GraphNetwork.applyGraphSettings()` in-place calls in `templates/index.html` remain intact, passing `test_graph_tuning.js`.
- [x] `templates/benchmark.html` and `static/js/benchmark/benchmark.js` boot cleanly with shared config and world state.
- [x] Full unit test gate (`python tools/ts_convert.py check --lenient-guards`) is green.

## Files

- `static/js/config.ts`
- `static/js/ui/settings-view.ts`
- `templates/index.html`
- `tools/unit/test_settings_view.js`
