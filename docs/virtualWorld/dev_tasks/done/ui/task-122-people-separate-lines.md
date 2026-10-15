---
area: ui
type: task
status: done
priority: medium
---

# Separate People Lines in Prompt Context

**Filed**: 2026-07-29  
**Priority**: Low  
**Status**: Done

---

## What

Character descriptions are currently concatenated into one comma-separated paragraph, making them hard to parse:

```
People here: Kayla Jenkins (awake): A sixteen-year-old Black girl..., Kyrie Johansen (awake): A sixteen-year-old white girl..., ...
```

Should be one line per person with clear separation:

```
People here:
- Kayla Jenkins (awake) — A sixteen-year-old Black girl...
- Kyrie Johansen (awake) — A sixteen-year-old white girl...
- John Smith (unknown to you) (awake) — Someone is here but you haven't met them yet.
```

**Note**: Unknown characters are shown with their actual name followed by "(unknown to you)" so the agent can still target them by name in actions (e.g., `attack John Smith`), while conveying the character hasn't met them yet.

### Scope
- `static/js/agent/prompt-builder.js` — `buildRoomContext()` people output format
- `static/js/agent-engine.js` — `_buildRoomContext()` people output format

## Why

TODO

## How

TODO

## Steps to verify

1. Select an agent in the graph and expand Agent Lens → `Room context
   (observe / decide)` for an area containing two known characters and one
   stranger.
   - expected: `People here:` is followed by one separate line per character;
     the stranger's line keeps the real name and marks “unknown to you”.
   - observed: the card records the formatter change in both prompt builders;
     no Agent Lens browser observation is recorded.
2. Switch the preview to another agent who does not know the stranger.
   - expected: the prompt context keeps the stranger distinguishable by name
     while preserving the unknown-to-this-character label.

## Browser UI and intended live verification

Intended UI home: Graph → select an agent → Agent Lens → live prompt context.

Current availability: Agent Lens is the existing prompt-context preview and
shows the context an agent receives without making an LLM call. The one-person-
per-line formatting change is recorded in both prompt builders; the card has
no browser observation for the preview.

Live steps when available:
1. Select an agent whose room contains two known people and one stranger, then
   expand `Room context (observe / decide)` in Agent Lens.
   - expected: each person occupies one line; the stranger's real name is
     followed by “unknown to you”, not merged into the previous description.
2. Select another agent in the same room who knows a different subset of the
   people and read the same section.
   - expected: names and unknown labels are resolved for that agent's
     relationships, and every person remains on a separate line.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Acceptance

- [ ] TODO

## Files

- TODO
