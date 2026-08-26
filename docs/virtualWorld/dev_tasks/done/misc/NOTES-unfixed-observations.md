# Unfixed Observations & Remaining Notes

## WebSocket error `ws://localhost:8081/`
Appears in console as `WebSocket connection to 'ws://localhost:8081/' failed`. This is from a browser live-reload / auto-refresh extension (e.g. LiveReload, BrowserSync, etc.) scanning for file changes. It has nothing to do with the app code — the server process isn't running a websocket on 8081. **No fix needed.**

## Bug 3: Server-side caching not implemented
The frontend was fixed (parallel fetches + no duplicate), but the server still reads each library file individually via `load_registry()` — 231+ file I/O ops per request. A server-side LRU cache with ~60s TTL in `routes/helpers.py:load_registry()` would eliminate redundant disk reads entirely. Not done yet because it's a larger change and the frontend fixes should provide noticeable improvement on their own.

## Bug 5: Rat Max_HP may not be set
The fix adds the `Max_HP` clamp to `adjust_vital` effects targeting NPCs, but it assumes `Max_HP` exists in the target's vitals dict. If the rat was created/imported without `Max_HP` ever being set, `vitals.get("Max_HP", 100)` would default to 100, and the HP display would show e.g. `11/100` rather than `11/10`. The `11/10` display suggests `Max_HP` was explicitly set to 10 somewhere — possibly in the scenario save file or via a backend API call. Check the scenario JSON if this persists.

## Bug 9: Tab was always visible, just poorly labeled
The "Automation & Advanced" tab was always there and functional. The issue was (a) the unescaped `&` in the HTML entity, and (b) the label "Automation & Advanced" didn't match what the user was looking for ("provider settings"). Renamed to "Behavior & Automation" and the `&` is now properly escaped as `&amp;`.
