---
type: task
status: todo
area: docs
priority: medium
---

# task-668: room-context.js body is mojibaked (double-encoded UTF-8)

**Filed:** 2026-10-02
**Related:** 

## Goal

static/js/agent/prompt-builder/room-context.js is mojibaked throughout: 46 occurrences of the UTF-8-as-cp1252 marker (the em-dash renders as the three chars U+00E2 U+20AC U+201D) and damaged emoji in the blind/pitch-black warning strings. The whole file is not cleanly reversible (encode cp1252 fails at \\x8f and the emoji are lossy). Fix the file's encoding or rewrite the affected strings so comments and user-facing warnings read correctly. Discovered while fixing task-658; the contract header lines were corrected there, the body was not.

## Acceptance

- TODO
