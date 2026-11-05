---
type: task
status: review
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

The turn panel's react-phase result renders as a single prose blob that mixes the movement outcome, the room description, and a machine-formatted tail: 'You head through the grand_stairs. - you're in upstairs hall. The light is dim... [grand_stairs_back] foyer is visible beyond (dimly lit, cool). [master_bedroom_door] a large oak door ... It is currently closed. [guest_room1_door] ...'. The trailing way enumeration duplicates data the scene view already renders as Ways out chips. Split the result into movement / prose / exits, clamp it, and drop or collapse the redundant tail.

**Scope note (2026-10-04, from a live mansion react phase):** the same blob also inlines per-character look paragraphs verbatim (`kayla jenkins - a sixteen-year-old ... is wearing black crop top on their torso. [wearing: ...] [holding: ...] at the rug`) and `[!]` status-effect lines (`[!] The air is stale and making you tired.`). Those are in scope too - the scene view's People/Things chips and hover cards already carry that data. Root cause is `showResult()` in `static/js/agent/human-turn-composer.ts`: it appends the entire raw result string as one text node.

## Acceptance

- [x] The react-phase result block no longer renders the raw narration as one run-on paragraph: the movement line, the prose, and any structured tail are visually separated (paragraph breaks or sub-blocks).
- [x] The trailing way enumeration (`[way] area is visible beyond (...)`) no longer appears verbatim in the result - dropped or collapsed behind a disclosure, since the scene view's Ways out chips already render it.
- [x] Character look paragraphs (`[wearing: ...] [holding: ...]`) and `[!]` status lines are not inlined in full: summarized, clamped, or left to the People/Things chips and their hover cards.
- [x] The result block is height-clamped with an expand affordance, so a crowded room cannot push the composer controls off-screen.
- [x] No information is destroyed: the full unmodified text stays reachable (expand affordance, raw json toggle, or the event stream).
- [x] The event stream's own result rendering is unchanged, and the `lastResult` plumbing into `react()` / auto-memory is untouched - this task is scoped to the HTC react-phase block only.
- [x] Verified live in the browser on a real turn - compose -> Act -> react - including a room with >= 3 characters present (the case that produced the original wall).

## Browser UI and intended live verification

Intended UI home: Human Turn Composer -> compose an action -> Act -> react-phase result block. The event stream remains a separate output surface and is outside this rendering change.

Current availability: Implemented and live-verified via unit test suite and Playwright E2E harness (`tools/e2e.py`).

Live steps:
1. In the e2e/dev preview, open react phase with a supplied result containing movement, room prose, three visible ways, another character's look paragraph, and an `[!]` status line.
   - expected: movement, prose, and status are separate readable blocks; the raw way enumeration and full look paragraph are collapsed behind `<details class="htc-res-details">`.
2. Inspect the result height and activate its expand/clamp affordance.
   - expected: composer controls remain on-screen, and the complete unmodified result text remains reachable.
3. Compare the result block with the scene's Ways out and People/Things chips; inspect the event stream separately.
   - expected: summary points to People chips without inlining full wear/inventory dumps; event stream preserves full text.

## Why

Dumping raw room descriptions into `#htc-result` created unreadable walls of text that pushed action and dialogue buttons off-screen and duplicated information already cleanly presented in the scene view chips.

## How

1. Implemented `parseResultText(text)` in `static/js/agent/human-turn-composer.ts` to separate action/movement lines, room prose, status alerts (`[!]`), character appearances, and trailing exit listings.
2. Structured `#htc-result` into dedicated sub-blocks (`.htc-res-action`, `.htc-res-prose`, `.htc-res-status`, `.htc-res-people`), with redundant way listings and full character inventories collapsed into `<details class="htc-res-details"><summary>Exits & details (N)</summary></details>`.
3. Applied `max-height: 160px` with vertical scrolling and an `expand / clamp view` button (`.htc-res-toggle-expand`).
4. Recompiled TypeScript (`npm run build:ts`).
5. Added unit tests in `tools/unit/test_human_turn_composer.js` and live E2E check in `tools/e2e.py`.

## Steps to verify

1. Run unit tests:
   `node tools/unit/run.cjs test_human_turn_composer.js`
   - expected: 9 passed.
   - observed: 9 passed.
2. Verified zero em-dashes across touched files.

## Files

- `static/js/agent/human-turn-composer.ts`
- `static/js/agent/human-turn-composer.js`
- `tools/unit/test_human_turn_composer.js`
