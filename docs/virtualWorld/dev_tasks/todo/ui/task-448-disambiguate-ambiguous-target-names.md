---
type: task
status: todo
area: ui
priority: medium
---

# task-448: Disambiguate an ambiguous target name/nickname

**Filed:** 2026-09-22
**Related:** task-446 (id-first node identity), task-447 (character nicknames),
`engine/matching.py` (`_match_character_name` returns `(None, candidates)`),
`routes/action_handlers.py`, `static/js/agent/human-turn-composer.js`

## Why

When a spoken name matches more than one character — two people called "Violet",
or two sharing the nickname "Vi" — the engine must **ask**, not guess. The matcher
already detects this and returns candidates (`name is None, candidates=[...]`),
but the prompt lists bare names (or internal keys), so "Violet or Violet?" is
unanswerable.

This is normal authoring, not an edge case: families share surnames and nicknames,
and populated worlds reuse generic names (task-357, task-446).

## Scope

- When `_match_character_name` (and item/exit equivalents) reports ambiguity,
  render a **chooser** that shows, per candidate: display name **plus a
  distinguishing detail** — description / `unknown_display_name()` / current
  area / a visible item — using the identity key as the value.
- Accept the choice and resolve it to the identity key so the action targets the
  chosen character (relationships, grapple, give/take, attack all use the key).
- Works in both the text command path and the human turn composer / inspector.
- Never auto-pick when the candidate set is ambiguous.

## Acceptance

- Two "Violet"s in one room: `talk to violet` lists both with a distinguishing
  detail; picking one targets the right identity (verified via a relationship or
  a grapple hitting only the chosen character).
- Two characters sharing an alias behave the same.
- An unambiguous name still resolves directly (no chooser).

## Non-goals

- Authoring the nicknames themselves (task-447).
- Duplicate-name storage (done, task-446).
