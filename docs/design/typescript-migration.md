# TypeScript in the front end

**Status:** complete. All **158** classic-script modules under `static/js` are
TypeScript sources that emit back to `.js`; **0** hand-written `.js` remain
(the only `.js` files left are the 26 vendored `lit-html` files, which are not
ours to convert). `templates/index.html` is unchanged and still loads plain
`<script>` tags.

The single gate is `python tools/ts_convert.py check`, which runs
`build:ts`, `typecheck`, `lint`, `module:check` and the unit runner, checks that
every emitted `.js` kept its `@module` header, and fails on an unreviewed
`window.` prefix drop. **It is green.**

To convert one more file (or re-verify after an edit) see
[Converting a file](#converting-a-file) and [Guarding it](#guarding-it).

**Size-ordered plan:** see `docs/design/typescript-migration-plan.md` for the
measured 151-file inventory, the six waves, and the `window.Lit` prerequisite
that gates 46% of the corpus.

`graph-background` was converted out of the recommended order on purpose: it is
views-adjacent, but it had just been rewritten (task-451) and its geometry,
migration and hit-testing logic is exactly the kind that benefits from types. It
also proved the ambient-globals route: `ApiClient` and `appEvents` were typed into
`globals.d.ts` for the first time, and the unit runner keeps working because it
loads the **emitted** `.js`.

## Why it can be incremental

The front end loads **classic `<script>` tags** and shares state through globals
(`config`, `worldState`, `VW.PromptBuilder`, …). TypeScript supports that
directly: a `.ts` file with **no `import`/`export`** compiles to a plain script
with the same top-level declarations. So one file can become TypeScript without
touching its neighbours or the HTML.

This property is why the migration was parallelisable at all: six lanes could
convert files concurrently because no file imports another.

### The classic-script hazards that actually bit

These are not stylistic. Each one broke the page, and each is now a rule.

1. **A top-level `const`/`let`/`class` is a global *lexical* binding, and two
   files declaring the same name is a parse-time `SyntaxError` that kills the
   whole file.** The original `window.X = …` had no binding, so this collision
   was impossible before the migration. Do not "fix" a typing error by writing
   `const X = (() => {…})()` — cast the assignment instead:

   ```ts
   (window as unknown as { Thing: unknown }).Thing = (() => { /* … */ })();
   ```

2. **Never silence `Property 'X' does not exist on type 'Window'` by deleting
   the `window.` prefix.** `window.X` is undefined-safe; bare `X` throws
   `ReferenceError` when the module has not loaded. This is how
   `test_fear_verbs` broke. The correct spelling now compiles anyway, because
   `interface Window` is generated from real `window.X =` assignments
   (`tools/window_members.py`); if a name is missing, add it there rather than
   dropping the prefix.

3. **Capture a cross-module global at call time, not at load time.**
   `const worldSync = window.worldSync` at the top of a file makes the file
   depend on a script that loads later. `const getWorldSync = () => window.worldSync`
   does not.

4. **Declare class fields with `declare`.** `useDefineForClassFields` defaults on
   for target ES2022, so a bare `cache: Record<…>;` emits `cache;` into the
   class body — an extra property definition at construction that the original
   never had.

5. **Never bulk-rewrite these files with PowerShell `Get-Content`/`Set-Content`.**
   PS 5.1 reads them as the ANSI codepage and re-writes as UTF-8-with-BOM, which
   double-encodes every non-ASCII character and is **unrecoverable from the
   file**. Use the `edit` tool for in-file changes; the shell is only for
   running the tools.

## The two configs

| Command | Config | Purpose |
|---|---|---|
| `npm run build:ts` | `tsconfig.json` | Compiles `static/js/**/*.ts` → `.js` **next to the source** (same path the HTML already loads). `strict`, `noEmitOnError`, comments preserved. |
| `npm run typecheck` | `tsconfig.check.json` | Parses **all** JS + TS with `noEmit`. JavaScript is *not* type-checked unless a file opts in with `// @ts-check`, so the codebase can be tightened file by file. |

`typecheck` passing today means every file is at least parseable and
self-consistent; it will start reporting as files opt into `@ts-check`.

## The load-order constraint (do not break it)

Converted files must **not** use `import`/`export`. Cross-file symbols come from
ambient declarations in `static/js/types/*.d.ts` (currently `globals.d.ts`).

Two options land in `tsconfig.json` because TypeScript 7 removed them:
- `module: "esnext"` — `"none"` no longer exists. A file with no imports/exports
  still emits as a classic script, so this is a non-issue in practice.
- `alwaysStrict` was removed entirely. **Emitted files therefore start with
  `"use strict";`** — converted files get strict semantics automatically. That is
  a benefit, but it is a real behaviour change for the file, so convert
  deliberately (no sloppy-mode-only constructs).

## Converting a file

Prefer the tool — it renames header-preservingly, emits, and records the
`window.` usage baseline before the original `.js` disappears from HEAD:

```powershell
python tools/ts_convert.py plan static/js/example.js   # what one file needs
python tools/ts_convert.py convert static/js/example.js --apply
python tools/ts_convert.py check                      # the gate
```

By hand, the steps are:

1. Copy `foo.js` → `foo.ts` (same directory, same name).
2. Add types; widen globals in `static/js/types/globals.d.ts` if needed. File-local
   `interface`/`type` names must be unique across the corpus, since every file
   shares one global scope.
3. Keep the `@module/@contributes/@powers/@relates/@docs` header **in the .ts** —
   it is emitted into the `.js`, so the module index keeps working. A leading
   type-only statement can make `tsc` drop the header; `check` verifies this.
4. Delete `foo.js` (the build regenerates it).
5. `npm run build:ts`, then `npm run typecheck`, `node --check <file>`, `npm run lint`.

`python tools/ts_convert.py build-one <file.ts>` type-checks and emits **one**
file without the project-wide build, which is what made parallel lanes safe.

The emitted `.js` carries a header note that it is generated. **Never hand-edit
a `.js` that has a sibling `.ts`.**

For symbols other code reaches through `window`, keep the assignment — and
prefer the no-binding form, see hazard 1 above:

```ts
(window as unknown as { Thing: unknown }).Thing = (() => { /* … */ })();
```

## Naming convention (enforced by review)

Cryptic single-letter names are not acceptable for domain values. Prefer the
thing's name:

| Don't | Do |
|---|---|
| `const v = Number(vitals[key])` | `const value = Number(vitals[key])` |
| `const T = window.VitalThresholds` | `const thresholds = window.VitalThresholds` |
| `v < T.WARNING` | `value < thresholds.WARNING` |
| `const n = Number(...)` | `const value = Number(...)` |

A sweep renamed **163** such locals across 11 files (e.g. the prompt builder's
`describeVital`, which is now readable). Short names are fine only where they are
idiomatic and local — loop indices (`i`, `j`), coordinates (`x`, `y`).

## Conversion order (historical)

The migration is finished, so this is a record of how it was sequenced rather
than a plan. Leaf → core → views, views last because lit-html templates are the
hardest to type:

1. Leaves with no globals or one — `shared/dom-utils`, `shared/json-utils`,
   `shared/vital-color`, `agent/rate-limiter`.
2. Logic modules — `agent/action-normalizer`, `agent/response-parser`,
   `agent/plan-tracker`.
3. Services — `config`, `storage`, `world-state`, `api`, `llm-client`.
4. Views — `inspector/*`, `ui/*`, `worldpainter/editor`, `graph-manager`.

`graph/graph-background` was converted out of order on purpose: views-adjacent,
but freshly rewritten (task-451) and full of geometry and hit-testing, which is
exactly what benefits from types. It also proved the ambient-globals route.

## Guarding it

- **`python tools/ts_convert.py check`** — the migration gate. Runs `build:ts`,
  `typecheck`, `lint`, `module:check` and `node tools/unit/run.cjs`; verifies
  every emitted `.js` kept its `@module` header; and fails on an **unreviewed**
  `window.` prefix drop. Run this before committing any front-end change.
- **`python tools/ts_convert.py audit-window`** — the dropped-prefix report on
  its own, with the reason for each already-signed-off drop.
- **`python tools/ts_convert.py report` / `list` / `plan`** — error distribution
  and per-file readiness, read out of `tsc` rather than a hand-kept list.
- **`python tools/ts_convert.py verify-emit`** — proves each per-file emit
  matches the project emit.
- `npm run typecheck`, `npm run lint`, `python tools/js_module_index.py --check`.

### `window-usage-baseline.json` and `window-usage-reviewed.json`

Two records that the dropped-prefix check depends on, and both have a trap:

- The **baseline** is `window.NAME` counts captured *before* each conversion. It
  has to be stored rather than re-derived, because once the conversion is
  committed the original `.js` is gone from HEAD.
- The **reviewed** file maps `"<rel>::<name>"` → why that drop is safe. All 8
  remaining drops are signed off there. Adding a key is a claim that the bare
  read resolves — check it, do not assume it.

### Refreshing the baseline

`python tools/ts_convert.py baseline` **only adds files that are not already in
the baseline** (`if rel in data: continue`); it cannot refresh a stale entry.
That matters because a baseline seeded before a large conversion wave records
counts that later commits had already reduced, and the gate then fails on drops
nobody made.

To regenerate wholesale, call the tool's own `window_usage` so the regex stays
in one place — but **only while HEAD still predates the conversions you want
recorded.** The baseline is a point-in-time record: once a conversion is
committed, HEAD holds the *converted* `.js`, and regenerating against it silently
overwrites the "before" counts for exactly the files you just converted, which
is how a real drop gets erased from the report.

```powershell
# Only valid while the conversions are still uncommitted.
python -c "import sys; sys.path.insert(0,'tools'); import ts_convert as t, pathlib, subprocess; t.save_baseline({r.with_suffix('.js').as_posix(): t.window_usage(subprocess.run(['git','show','HEAD:'+r.with_suffix('.js').as_posix()],capture_output=True).stdout.decode('utf-8','replace')) for r in sorted(pathlib.Path('static/js').rglob('*.ts')) if r.name != 'globals.d.ts'}); print('ok')"
```

Verify with `python tools/ts_convert.py audit-window`. The number it prints
should match what the **current worktree** changed, not what an earlier commit
changed — if it is much larger, the baseline is stale, not the code.

### A note on `interface Window`

`tools/window_members.py` generates `interface Window` from the names modules
actually assign via `window.X =`, so the correct spelling compiles and hazard 2
does not arise. When a converted file wants a global that is not declared, the
fix is to widen `globals.d.ts` — not to drop the prefix.
