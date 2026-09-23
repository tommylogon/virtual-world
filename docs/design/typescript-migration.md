# TypeScript in the front end

**Status:** adopted. Toolchain wired, two modules converted
(`static/js/agent/rate-limiter.ts`, `static/js/graph/graph-background.ts`).
Migration is **incremental** — `.js` and `.ts` coexist, and the app keeps working
at every step.

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

1. Copy `foo.js` → `foo.ts` (same directory, same name).
2. Add types; widen globals in `static/js/types/globals.d.ts` if needed.
3. Keep the `@module/@contributes/@powers/@relates/@docs` header **in the .ts** —
   it is emitted into the `.js`, so the module index keeps working.
4. `Delete foo.js` (the build regenerates it).
5. `npm run build:ts`, then `npm run typecheck`, `node --check <file>`, `npm run lint`.

The emitted `.js` carries a header note that it is generated. **Never hand-edit
a `.js` that has a sibling `.ts`.**

For symbols other code reaches through `window`, keep the assignment:

```ts
(window as unknown as { RateLimiter: typeof RateLimiter }).RateLimiter = RateLimiter;
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

## Suggested conversion order

Leaf → core → views (views are last: lit-html templates are the hardest to type):

1. Leaves with no globals or one: `shared/dom-utils.js`, `shared/json-utils.js`,
   `shared/vital-color.js`, `agent/rate-limiter.js` ✅ **done**
2. Logic modules: `agent/action-normalizer.js`, `agent/response-parser.js`,
   `agent/plan-tracker.js`, `agent/rate-limiter.js` peers
3. Services: `config.js`, `storage.js`, `world-state.js`, `api.js`, `llm-client.js`
4. Views/last: `inspector/*`, `ui/*` (they read `window.Lit`) —
   `graph/graph-background.js` ✅ **done** (converted early, see Status)

Add `// @ts-check` to a `.js` file once its ambient globals are typed enough —
that starts type-checking it without a rename.

## Guarding it

- `npm run typecheck` — add to CI alongside `npm run lint`.
- `python tools/js_module_index.py --check` — the module contract guard; it steps
  over a leading `"use strict";` so emitted scripts still count as documented.
