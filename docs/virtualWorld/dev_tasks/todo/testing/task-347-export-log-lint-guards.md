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
