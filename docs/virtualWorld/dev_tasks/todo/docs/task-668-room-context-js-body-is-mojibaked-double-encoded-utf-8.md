---
type: task
status: todo
area: docs
priority: medium
---

# task-668: room-context.js body is mojibaked (double-encoded UTF-8)

**Filed:** 2026-10-02
**Related:** 

## What

static/js/agent/prompt-builder/room-context.js is mojibaked throughout: 46 occurrences of the UTF-8-as-cp1252 marker (the em-dash renders as the three chars U+00E2 U+20AC U+201D) and damaged emoji in the blind/pitch-black warning strings. The whole file is not cleanly reversible (encode cp1252 fails at \\x8f and the emoji are lossy). Fix the file's encoding or rewrite the affected strings so comments and user-facing warnings read correctly. Discovered while fixing task-658; the contract header lines were corrected there, the body was not.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Human Turn scene/room context and the Agent Lens **Room context (observe / decide)** view; the room-context text and blind/dark warnings should render as normal Unicode in both the character-facing prompt context and visible panel.

Current availability: the card identifies mojibake in the body of `static/js/agent/prompt-builder/room-context.js`, including em-dash markers and damaged emoji in blind/pitch-black warnings. The file's current browser output has not been rechecked in this turn.

Live steps when available:
1. Load a scene containing a blind character in a dark area and open its Room context in the Agent Lens; also inspect the Human Turn scene context for that character.
   - expected: the warning text contains readable punctuation and symbols, not the literal `â€` sequence or replacement characters.
2. Compare the visible context and the captured prompt text for the same scene.
   - expected: both carry the same correctly decoded warning and room details; encoding repair does not alter masking or sensory facts.
3. Switch to a lit scene and to a sighted character, then reopen the same views.
   - expected: irrelevant blind/pitch-black warnings are absent and ordinary room context remains unchanged.

This section is not a claim that the corrected strings have been browser-verified today.
