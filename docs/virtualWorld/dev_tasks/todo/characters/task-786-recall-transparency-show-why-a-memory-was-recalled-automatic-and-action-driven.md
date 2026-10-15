---
type: task
status: todo
area: characters
priority: high
---

# task-786: Recall transparency: show why a memory was recalled, automatic and action-driven

**Filed:** 2026-10-12
**Related:** task-685, task-686, task-690, task-714

## What

Surface why a memory fired: what matched (speech, sight, emotion, tags, keyword/entity), what was reinforced, and how context (speaker, who is present, area and item tags) shaped recall.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: select a character → Mind panel → Memories → expand a recalled memory's **Why this memory** detail. Show the recall evidence beside the memory it explains, so the author/player can see what matched and how the current scene shaped retrieval.

Current availability: this card asks for recall transparency across automatic and action-driven recall. The explanatory detail is planned; no existing memory UI is claimed to expose all match signals.

Live steps when available:
1. In a scratch scene, give one character two memories with distinct tags and actors. Cause the first memory to be recalled by matching a keyword, then expand that memory in Mind.
   - expected: the detail names the matched keyword/tag and identifies the memory that was reinforced; the other memory is not shown as the source.
2. Cause a second recall through a different route, such as an action-driven `recall` request, with a different speaker or present character.
   - expected: the detail labels the route and the matching signals separately; speaker, area, presence, or item tags appear only when they affected this retrieval.
3. Repeat the automatic recall with a different current speaker/area while keeping the remembered event fixed.
   - expected: the explanation changes only for context that actually changed the score or selected memory; it does not claim a signal that the resolver did not read.
4. Compare the panel's explanation with the recalled memory and the corresponding `/api/state` record.
   - expected: the memory ID, reinforcement, and recorded match evidence agree; the explanation is not a second memory store.

This section is not a claim that planned UI exists or works today.
