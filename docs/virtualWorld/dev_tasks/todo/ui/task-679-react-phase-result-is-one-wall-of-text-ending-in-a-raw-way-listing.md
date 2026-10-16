---
type: task
status: todo
area: ui
priority: medium
related: [task-333, task-334]
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
---

# task-679: React-phase result is one wall of text ending in a raw way listing

**Filed:** 2026-10-04
**Related:** [task-333], [task-334]

<!-- deps:start -->
**Related:** [[task-333-human-turn-panel-scene-first]], [[task-334-human-react-phase]]
<!-- deps:end -->

## What

The turn panel's react-phase result renders as a single prose blob that mixes the movement outcome, the room description, and a machine-formatted tail: 'You head through the grand_stairs. -- you're in upstairs hall. The light is dim... [grand_stairs_back] foyer is visible beyond (dimly lit, cool). [master_bedroom_door] a large oak door ... It is currently closed. [guest_room1_door] ...'. The trailing way enumeration duplicates data the scene view already renders as Ways out chips. Split the result into movement / prose / exits, clamp it, and drop or collapse the redundant tail.

**Scope note (2026-10-04, from a live mansion react phase):** the same blob also inlines
per-character look paragraphs verbatim (`kayla jenkins — a sixteen-year-old ... is
wearing black crop top on their torso. [wearing: ...] [holding: ...] at the rug`) and
`[!]` status-effect lines (`[!] The air is stale and making you tired.`). Those are in
scope too — the scene view's People/Things chips and hover cards already carry that
data. Root cause is `showResult()` in `static/js/agent/human-turn-composer.ts`: it
appends the entire raw result string as one text node.

## Acceptance

- [ ] The react-phase result block no longer renders the raw narration as one run-on
      paragraph: the movement line, the prose, and any structured tail are visually
      separated (paragraph breaks or sub-blocks).
- [ ] The trailing way enumeration (`[way] area is visible beyond (...)`) no longer
      appears verbatim in the result — dropped or collapsed behind a disclosure, since
      the scene view's Ways out chips already render it.
- [ ] Character look paragraphs (`[wearing: ...] [holding: ...]`) and `[!]` status lines
      are not inlined in full: summarized, clamped, or left to the People/Things chips
      and their hover cards.
- [ ] The result block is height-clamped with an expand affordance, so a crowded room
      cannot push the composer controls off-screen.
- [ ] No information is destroyed: the full unmodified text stays reachable (expand
      affordance, raw json toggle, or the event stream).
- [ ] The event stream's own result rendering is unchanged, and the `lastResult`
      plumbing into `react()` / auto-memory is untouched — this task is scoped to the
      HTC react-phase block only.
- [ ] Verified live in the browser on a real turn — compose → Act → react — including
      a room with ≥3 characters present (the case that produced the original wall).
      A code read alone does not close this.

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

Intended UI home: Human Turn Composer → compose an action → Act → react-phase result block. The event stream remains a separate output surface and is outside this rendering change.

Current availability: The card records a live mansion react phase with movement, room prose, way enumeration, character looks, and `[!]` status lines combined in one result string. The display fix is planned; task-698's replay affordance is the safe repeatable verification path.

Live steps when available:
1. In the e2e/dev preview, open react phase with a supplied result containing movement, room prose, three visible ways, another character's look paragraph, and an `[!]` status line.
   - expected: movement, prose, and status are separate readable blocks; the raw way enumeration and full look paragraph are collapsed or omitted from the visible summary.
2. Inspect the result height and activate its expand/raw-text affordance.
   - expected: the composer remains on-screen in a crowded room, and the complete unmodified result text remains reachable.
3. Compare the result block with the scene's Ways out and People/Things chips; inspect the event stream separately.
   - expected: the summary does not duplicate the way list or full character look; the event stream still renders its own full result as before.
4. Repeat on a real compose → Act → react turn in a room with at least three characters once safe replay is available.
   - expected: the visible result has the same separated/clamped layout without changing `lastResult`, auto-memory, or event-stream behavior.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
