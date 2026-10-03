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

## 🐞 Report a bug (the 🐞 Report dialog)

**What it does.** Turns whatever you are looking at *right now* into a real dev-task file —
`docs/virtualWorld/dev_tasks/todo/<area>/bug-N-<slug>.md` — with the evidence attached, so the
next reader does not have to go and reproduce it. It writes a file; it does not send anything
off-machine.

**How to use it.** Click **🐞 Report** in the graph toolbar's *Look* zone, next to **📷 PNG**
(`templates/index.html`, `btn-report-bug`). Then:

1. **Area** — which dev-task folder the report lands in (`bugs` by default; the 13 areas are the
   same list `tools/tasks.py` uses).
2. **Short title** — optional. Left blank, the first line of the message becomes the title, which
   is also what the filename slug is made from.
3. **What went wrong, and what did you expect instead?** — the only required field. It becomes the
   task's **Goal** verbatim.
4. **Screenshot** — any of three ways, all ending up as the same single `screenshot` field:
   - **📷 Capture view** composites the graph `<canvas>` with the map background, exactly as the
     PNG export does. Good for "the layout is wrong". It does **not** capture the DOM chrome
     around it, and it cannot capture a graph node — those are drawn, not DOM.
   - **📎 Attach image**, or just **paste with `Ctrl+V` while the dialog is open**. This is the only
     way to get the whole window, panels and modals included, because no DOM rasteriser is vendored
     anywhere in this repo (no html2canvas, no `toDataURL` outside tests).
   - **Clear** removes the current image. Limit: 8 MB; `png`, `jpg`, `jpeg`, `webp`, `gif`.
5. **🎯 Pick an element** — for "the inspector looked wrong", which on its own is not a report. The
   dialog hides itself so it cannot swallow the click you are trying to make; a dashed cyan box
   follows the cursor; click to record that element, or **Esc** to cancel. Each pick stores the CSS
   selector path, box geometry, ancestor chain, ~17 computed properties, visible text and truncated
   `outerHTML`. Up to 12 per report; picking the same element twice is rejected, and each row has a
   **✕**. **The picker is DOM-only** — `document.elementFromPoint` over the graph container resolves
   to the container, never a node, because vis.js draws to a canvas. For a graph node, select it
   first: the capture already records the selected node ids.
6. **📝 File bug** — the dialog closes and a toast names the file it wrote.

**Context is captured for you.** You do not have to write down what mode you were in: the report
records the timestamp, URL, viewport, device pixel ratio, user agent, layout mode, physics state,
view mode, camera scale and position, selected nodes, and map spacing.

**What lands where.** The task file's frontmatter matches `tools/tasks.py new` (`type: bug`,
`status: todo`, chosen `area`, `priority: medium`), the message is the **Goal**, **Acceptance** is
`- TODO` for the fixer to fill in, and an **Evidence** section holds the screenshot, the context
JSON and one block per picked element. The screenshot PNG is saved under
`static/images/bug-reports/` — *not* beside the task file, because `routes/docs_ops.py` refuses to
serve anything under `dev_tasks`, so an image next to the task could not be rendered by the docs
reader. Ids come from `tools/tasks.py`, and the file is created with an exclusive `open('x')` so two
reports filed in the same instant retry instead of overwriting each other.

**Where it is wired:** `static/js/bug-report.ts` (dialog, picker, multipart POST),
`routes/bug_reports.py` + `routes/bug_reports_ops.py` (the handler), `templates/index.html`
(modal markup and the toolbar button). Covered by `tests/test_bug_reports.py` (11 tests, passing).

## File-size rule

`AGENTS.md` enforces production files < 600 lines and prioritizes extracting concerns into
modules over appending to a monolith. Follow the "move, don't copy" extraction pattern: keep the
old public symbol as a thin `@deprecated` delegate, add the new module's script tag, and verify
with `node --check` (JS) / `pytest` (Python) after each move.

## Related

- [[Settings & Configuration]] — settings modal + browser-side config
- [[Inspector Panels]] — inspector views (lit-html consumers)
- [[Engine Config]] — schema-driven lit-html editor (backend constants)