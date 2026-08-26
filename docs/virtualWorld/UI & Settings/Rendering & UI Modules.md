# Frontend Rendering & Module Layout

How the browser-side UI is structured: the lit-html rendering system, the classic-script vs
deferred-module bootstrap, and the graph module split. This page exists because the wiring is
non-obvious — especially the ordering rule that keeps `window.Lit` from racing `main.js` init.

## Rendering: lit-html via `window.Lit`

All UI rendering goes through **lit-html** (vendored in `static/js/vendor/lit-html/`, no CDN).
The one entrypoint is `static/js/shared/lit-bootstrap.js`, a deferred ES **module** that imports
lit-html and stamps the API onto `window.Lit`:

```js
window.Lit = { html, svg, render, renderInto, renderPanel, nothing, noChange,
               classMap, styleMap, repeat, ifDefined, guard, live, unsafeHTML };
```

Every view file is a **classic (non-module) script** that captures the tag lazily:

```js
const viewHtml = (strings, ...values) => window.Lit.html(strings, ...values);
```

Classic scripts can't `import`, and module scripts are deferred — which is exactly why the tag is
captured lazily *inside functions*, never at parse time. Referencing `window.Lit.html` at module
load would crash because the module hasn't run yet.

### Why event handlers work in templates

`@click=${fn}`, `?selected=${bool}`, `.property=${value}` bindings are part of `lit-html`'s tag
itself — no extra directive needed. The `live`, `guard`, `classMap` etc. **directives** are
separate and only needed when you want reactive re-render behavior.

### XSS stance

lit-html escapes interpolations by default. Markup-injective content (LLM output, stored
descriptions) must go through `window.Lit.unsafeHTML(...)` **explicitly** — search for it when
checking new UI code. String-concat `innerHTML` builds are legacy; prefer lit-html templates.

## The classic/module race (and the fix)

`lit-bootstrap.js` is `<script type="module">`, so it executes **after** all classic scripts on
the page. `main.js` is classic and its async `init()` ran immediately — the first init path that
touched `window.Lit` (`events.restoreLog()`, restoring the event stream from IndexedDB) crashed
when the module hadn't stamped `window.Lit` yet:

```
event-stream.js:206 Uncaught TypeError: Cannot read properties of undefined (reading 'render')
```

Fix (2026-08-20):
- `static/js/main.js` — `init()` now **polls for `window.Lit`** (up to 5 s) before restoring the
  event log:
  ```js
  while (!window.Lit && Date.now() < deadline) await sleep(20);
  ```
- `static/js/event-stream.js` — `restoreLog()` returns early if `window.Lit` is still missing, so
  a module-load failure degrades gracefully instead of killing startup.

**Rule for future init paths:** anything that renders via `window.Lit` during startup must either
wait for the bootstrap or be deferred to a user action (like Engine Config's lazy load on tab
click). Do not call `window.Lit.*` from top-level classic-script code.

## Graph module layout

The graph editor used to be one `network-manager.js` monolith (1 496 lines). It was split into
focused modules (task-314); `network-manager.js` keeps the shell + thin `@deprecated` delegates
so existing call sites keep working:

| Module | Owns |
|--------|------|
| `graph/projector.js` | Pure visibility projection (node/edge visibility, no vis.js) |
| `graph/overlays.js` | The 5 ambient overlays (light/heat/sound/trigger/cardinal) + change-cached lighting |
| `graph/tooltips.js` | Node/edge tippy tooltips |
| `graph/focus.js` | Search reveal + camera fit + bounded physics kick (debounced) |
| `graph/layout-engine.js`, `graph/node-badges.js`, et al. | Layout, badges |

Load order in `templates/index.html` matters: modules that only reference globals at call time
can load before the objects they use, but keep dependencies load-order-stable or lazily global.

## File-size rule

`AGENTS.md` enforces production files < 600 lines and prioritizes extracting concerns into
modules over appending to a monolith. Follow the "move, don't copy" extraction pattern: keep the
old public symbol as a thin `@deprecated` delegate, add the new module's script tag, and verify
with `node --check` (JS) / `pytest` (Python) after each move.

## Related

- [[Settings & Configuration]] — settings modal + browser-side config
- [[Inspector Panels]] — inspector views (lit-html consumers)
- [[Engine Config]] — schema-driven lit-html editor (backend constants)