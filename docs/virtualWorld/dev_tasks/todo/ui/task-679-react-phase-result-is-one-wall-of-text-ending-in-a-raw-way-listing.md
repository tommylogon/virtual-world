---
type: task
status: todo
area: ui
priority: medium
related: [task-333, task-334]
---

# task-679: React-phase result is one wall of text ending in a raw way listing

**Filed:** 2026-10-04
**Related:** [task-333], [task-334]

## Goal

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
