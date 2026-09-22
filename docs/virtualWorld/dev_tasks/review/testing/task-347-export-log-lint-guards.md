# task-347 — Export-log lint guards: grep-able regression checks over play sessions

**Status**: Todo — filed 2026-08-27 from export-log review.

## Found

Export logs turned out to be the cheapest observable surface for engine +
prompt regressions (two 2026-08-23 logs surfaced five defects between them:
bug-27 outcome strings, bug-28 conversation echo mangling, bug-29 double
attribution, memory dup writes → task-346, appearance grammar → task-345).
Today these are found by hand months later.

Sibling to task-11 (live-agent regression harness): task-11 replays full
sessions with an actual model; THIS task needs no model — just lint existing/
new exports for known-bad signatures.

## Goal

`tools/log_lint.cjs <export.txt ...>` (+ optional pytest twin reading new
exports) checking patterns like:

| Pattern | Catches |
|---|---|
| `\bthe the\b` | article doubling (bug-27) |
| `[a-z](from|on|in|under)the\b` / `[a-z](from under the)` joined-no-space | missing-space joins (bug-27) |
| `\bthat s\b|\bi m\b|\bdon t\b` in CONVERSATION blocks | apostrophe stripping (bug-28) |
| same quoted speech attributed 2× within one WITNESSED block | double attribution (bug-29) |
| identical sentence twice in one I REMEMBER | memory dup writes (task-346) |
| `<name> hugs your(self| knees)|\bhugs you\b` | pronoun stitching G1 |
| `\byou is\b|\byou was\b` in Your appearance | appearance grammar (task-345) |

Exit non-zero on any hit; summary table of file → findings. Wire into the
manual release checklist ("run log_lint on latest export before tagging"),
keep out of test_all.cjs (needs no server).

## Verify

Run against `event_log_2026-08-10T21-45-19.txt` and the two 2026-08-23 logs →
flags their KNOWN issues, and reports zero false positives on clean sections.
After fixing bugs 27/28, re-lint the same files → those classes go dark while
historical logs stay annotated (lint runs per-file, not per-build).

## Implemented (2026-09-22)

`tools/log_lint.cjs` (Node, no deps) + `tests/test_log_lint.py`.

- CLI: `node tools/log_lint.cjs <file|dir> [...] [--json] [--quiet]
  [--only rule,rule]`. Directories are walked (`.txt/.md/.log`, skipping
  node_modules/.git/.kilo). Exit 0 clean, 1 findings, 2 usage/IO error.
  Wired as `npm run loglint` and documented in `AGENTS.md`.
- Rules: `article-double` (bug-27), `missing-space` (bug-27; glued relation word,
  with an allowlist for real words like *thunder*), `apostrophe-strip` (bug-28,
  scoped to CONVERSATION), `double-attribution` (bug-29, scoped to WITNESSED —
  same quote twice in one block), `memory-dup` (task-346, scoped to I REMEMBER),
  `pronoun-stitch` (G1 verb + "your"), `appearance-grammar` (task-345
  "you is/was").
- Tests (`tests/test_log_lint.py`, 5): every rule fires on a synthetic dirty log;
  clean text passes; `--only` restricts; no args is a usage error; the real
  taco_bell export is a smoke test asserting the bug-28 class is observable.

### Findings on the real logs

- **bug-28 confirmed observable**: the taco_bell log shows the
  `that s— … i m` apostrophe-stripped CONVERSATION echo (16 hits) — so the
  mangling is in what was recorded/broadcast, even though the current code path
  stores speech verbatim (see bug-28 notes).
- **bug-29 stays a false alarm**: `double-attribution` = 0 on the same log,
  matching the earlier finding that the two quoted lines were different
  utterances.

