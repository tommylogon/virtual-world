---
type: bug
status: review
area: bugs
priority: high
---

# bug-40: Save list renders AUTO and version badges as literal HTML

**Filed:** 2026-09-22
**Related:** task-365

## Symptom

Reported from a screenshot of the Save / Load Game modal. The autosave row's title
rendered as raw markup instead of a badge:

```
<span style="background:var(--accent,#4a9eff);color:#fff;border-radius:3px;padding:1px 5px;font-size:9px;margin-right:5px;"> AUTO </span>Autosave<span style="font-size:9px;color:var(--text-muted);margin-left:4px;">v1.3.0</span>
```

Every row also showed its version tag as the same literal `<span style="font-size:9px;...">v1.3.0</span>`
text. The storage is fine — `save.name` is `Autosave` and the metadata is correct; only
the rendering is wrong.

## Root cause

`static/js/ui/saveload-view.js:462-471` builds `badge` and `versionBadge` as **HTML
strings**, then interpolates them into a Lit template:

```js
var badge = isAuto
    ? '<span style="...">AUTO</span>'
    : '';
...
<strong>${badge}${save.name || save.filename}</strong>${versionBadge}
```

Those interpolations are Lit **text** bindings, so Lit escapes the markup and the user
sees it verbatim. `save.name` and `save.filename` are also text-bound, which is correct
and should stay escaped.

## Fix

Preferred: stop pre-building markup as strings. Emit the badges as real elements in the
template (e.g. a conditional badged span before the name, a small muted span after it),
so the row no longer depends on an escaping opt-in.

If the minimal change is wanted first, wrap the two values in the escaping escape hatch
already used elsewhere in the repo — `window.Lit.unsafeHTML(badge)` /
`window.Lit.unsafeHTML(versionBadge)` (precedent: `static/js/event-stream.js:493`).
Do not route `save.name`/`save.filename` through `unsafeHTML`; those are user text.

Whichever path is taken, the extracted row template from task-456 is the natural home
for it.

## Acceptance

- [ ] The autosave row shows a styled `AUTO` badge, not raw `<span ...>` text.
- [ ] Every row shows `v<version>` as a muted badge, not raw markup.
- [ ] A save whose display name contains `<`, `>`, `&`, or a quote renders those
      characters literally (name stays escaped).
- [ ] No badge markup is visible in the rendered list for any row.

## Files

- `static/js/ui/saveload-view.js` — list template, badge construction (lines ~462-471)

## Fix — 2026-09-24

`badge` and `versionBadge` are now Lit templates (`saveLoadViewTag\`<span …>\``)
instead of HTML strings, so Lit renders the elements rather than escaping them
as literal text. `save.name` / `save.filename` remain ordinary text bindings, so
a name containing `<`, `>`, `&` or a quote still renders literally. No engine or
route change; `node --check` / lint / typecheck clean. The badge markup is now
built by the same `saveLoadViewTag` used for the row.

Acceptance met by construction; the row markup cannot contain a raw `<span …>`
string any more (only the two element templates, which Lit owns).
