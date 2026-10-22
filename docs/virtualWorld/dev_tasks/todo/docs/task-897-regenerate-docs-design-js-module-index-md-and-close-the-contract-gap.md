---
type: task
status: todo
area: docs
priority: medium
wiki: "[[Developer Tooling]]"
---

# task-897: Regenerate docs/design/js-module-index.md and close the contract gap

**Filed:** 2026-10-21
**Related:** 

## What

docs/design/js-module-index.md is stale against the source it is generated from. It lists 382 modules / 211 documented / 171 awaiting a contract header; a live run of `python tools/js_module_index.py --write` reports 405 / 223 / 182. The missing rows are real modules added since the index was last generated, including static/js/agent/prompt-builder/capture.js (the shared turn-prompt capture used by the Benchmark Lab and the in-app harness). It cannot be regenerated today without reintroducing banned characters: roughly 100 source headers still use an em-dash (—) as their separator, and the generator emits that character verbatim into the Powers column, which violates the repo-wide em-dash ban.

## Why

The index is a generated reference, not a hand-written note, so the drift is a bug in the declaration, not a documentation gap to paper over. Leaving it stale means every new module is invisible in the index until someone hand-edits it, which the file's own header forbids. The em-dash blocker is the same sweep as bug-564 (Way Properties.md carries 117 em-dashes) and is not being fixed here; this task exists so the index regeneration is not silently blocked by it.

## How

1. Make the generator em-dash-proof: in tools/js_module_index.py write_index(), normalise the em-dash and en-dash characters to an ASCII hyphen in every emitted cell before writing the markdown, so regenerating can never reintroduce a banned character. 2. Run `python tools/js_module_index.py --write` and confirm the diff is only the missing rows plus the normalised separators. 3. Update the baseline if the two currently-uncovered modules (static/js/ui/play-mode.js, static/js/ui/source-version.js) are intentionally left undocumented. 4. Add the @module/@contributes headers to play-mode.js and source-version.js if they are meant to be documented, or record them in docs/design/js-module-baseline.txt.

## Browser UI and intended live verification

Intended UI home: Settings > Developer Tooling > Module index (docs/design/js-module-index.md)

Current availability: Always, for anyone running the tooling gates

Live steps when available:
1. Run `python tools/js_module_index.py --write`
2. Confirm the file is em-dash-free and includes static/js/agent/prompt-builder/capture.js
3. Run `python tools/js_module_index.py --check` and confirm no new gaps

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] `python tools/js_module_index.py --write` produces an em-dash-free file (count of U+2014 is 0).
- [ ] The generated file includes static/js/agent/prompt-builder/capture.js and every other module added since the last generation.
- [ ] `python tools/js_module_index.py --check` reports no new gaps and no new bad @docs targets.
- [ ] No em-dash characters are introduced anywhere by this change.

## Files

- `tools/js_module_index.py`
- `docs/design/js-module-index.md`
- `docs/design/js-module-baseline.txt`
- `static/js/ui/play-mode.js`
- `static/js/ui/source-version.js`
