---
type: bug
status: todo
area: ui
priority: medium
horizon: now
effort: S
wiki: "[[where-you-ve-been|Where you've been]]"
related: [task-694]
---

# bug-553: Minimap opens on the alphabetically-first scope, hiding freshly explored cells

**Filed:** 2026-10-17
**Related:** task-694

<!-- deps:start -->
**Related:** [[task-694-htc-fixture-world-a-tiny-scenario-authored-to-exercise-every-turn-panel-surface]]
<!-- deps:end -->

## What

`render()` in `static/js/agent/turn-minimap.ts` builds the scope `<select>` from `payload.scopes` in server order and never assigns an initial `sel.value`, so the panel opens on the first `<option>`. The server sorts scopes by scope id (`routes/player_ops.py:1607`, `sorted(scope_counts.items())`), so the default is the alphabetically-first scope id, not the scope that holds `payload.current_area`. `paint()` then filters the visited areas to the selected scope, so any cell explored in another scope is not drawn.

## Why

Measured live 2026-10-17 against scenario `kraktooth_goblin_camp`. Cullen Rutherford stands in `Road (world 13,7)` (scope `world`), with 3 visited cells in `world` and 1 in `goblin_camp`. The panel opens on `goblin camp (1)` and draws one cell. To the player this reads as the minimap having lost where they went: they moved N/W/S, saw the cells (they had switched the dropdown), ran a timeskip, reopened the human turn composer, and only the cells in the default scope were left. Every open re-renders a fresh select with no persisted choice, so the selection silently resets to the first scope. The map payload itself is byte-stable across the timeskip (same areas, same scopes), so no observation is lost - the panel is simply looking at the wrong scope. Caveat: this explanation only covers cells the character gained in a scope other than the first. If the cells that disappeared were all inside the first scope, then the panel is telling the truth and the loss is real; that case points at observation or serialization loss instead, and needs its own repro (capture `/api/players/<name>/map` before and after the timeskip and diff the `areas` and `scopes`).

## How

In `turn-minimap.ts render()`, after the options are appended, set `sel.value` to the scope id of the current area: find the entry in `payload.areas` whose `name === payload.current_area`, read its `scope_id`, and select it when it matches an option; otherwise keep the fallback to the first option. Apply the same default in `openFullscreen()`. Both `current_area` and `areas[].scope_id` are already in the `/api/players/<name>/map` payload (`routes/player_ops.py handle_get_player_map`), so no server change is needed. Edit the `.ts` and rebuild; do not hand-edit the emitted `.js`.

## Browser UI and intended live verification

Intended UI home: the human turn composer (HTC) scene column, the `Where you've been` panel and its fullscreen map. Current availability: the panel works and draws, but opens on the wrong scope. Live path: load a scenario where the active character has visited cells in two scopes, open their turn, and confirm the scope dropdown opens on the scope of the current area and draws every cell visited there. Switch scope and confirm the other cells draw; close and reopen the panel and confirm it opens on the current scope again.

## Steps to verify

1. Start the app (`python app.py`, port 4444), load `kraktooth_goblin_camp`, and give a human character cells in two scopes.
   - expected: the map scope dropdown shows the current area's scope selected and draws that scope's cells.
   - observed: TODO
2. Switch the dropdown, then close and reopen the panel.
   - expected: it opens on the current area's scope again, showing all cells there.
   - observed: TODO
3. `python tools/ts_convert.py check` after the `.ts` edit.
   - expected: pass
   - observed: TODO

## Acceptance

- [ ] The minimap panel opens on the scope of `payload.current_area` when that scope is present, and falls back to the first scope only when it is not.
- [ ] Switching scope still redraws; the fullscreen map uses the same default.
- [ ] No `.js` under `static/js/` is hand-edited; `python tools/ts_convert.py check` passes.

## Files

- `static/js/agent/turn-minimap.ts` (`render`, `openFullscreen`)
- `routes/player_ops.py` (`handle_get_player_map`, scope ordering - reference only)
