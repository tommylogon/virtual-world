---
type: bug
status: todo
area: library
priority: medium
related: [task-751]
blocked_by: [task-751]
---

# bug-538: Placing a way from the Library asks for the target in a window.prompt, with no picker and no way to find the node id

**Filed:** 2026-10-10
**Related:** 

<!-- deps:start -->
**Blocked by:** [[task-751-replace-native-alert-confirm-prompt-popups-with-a-promise-based-in-app-dialog]]
**Related:** [[task-751-replace-native-alert-confirm-prompt-popups-with-a-promise-based-in-app-dialog]]
<!-- deps:end -->

## What

Placing a way from the library opens a browser window.prompt asking the author to type a target node id. There is no picker, no search and no way to discover the id, so the placement is effectively unusable by hand. Replace the prompt with the same placement flow items use (a target picker / openForRoom over the graph), so an author picks the destination area or way from a searchable list or by clicking the graph. Surfaced 2026-10-10 while trying to verify task-659 (library way spawn carries insulation/sound_barrier) - the spawn could not be reached by hand.

## Why

**Overlap with task-751 — read this first.** The *native-popup* half is already ticketed: **task-751** (`review/ui`) replaces every native `alert`/`confirm`/`prompt` with the in-app `dialog.*` module (`static/js/shared/dialog.ts`, already built), and this site — `library-browser.ts`'s way import (`Connect FROM area name:` / `Connect TO area name:` prompts) — is one of its ~20 `prompt()` call sites. But task-751 only swaps the widget; it would still ask for a **typed name/id**. The distinct fault here is that a placement target needs a **picker**, not free text: the author cannot know the id. So this card survives task-751 as *"the way placement needs a target picker (a searchable list, or click-the-graph)"*, and its native-popup half is discharged by task-751.

## How

TODO

## Steps to verify

1. Open the Library Browser, choose a way template, and invoke its action to
   place/connect it in the current world. Record the current native prompt and
   the selected source and destination areas.
   - expected today: the reported path asks for typed target IDs; capture the
     exact prompt and whether the way is added after valid IDs are entered.
2. After the picker is implemented, repeat from the same template using the
   source and destination areas by their displayed names, without looking up
   node IDs.
   - expected: a searchable target picker lists current graph areas and allows
     selecting one by name or clicking it in the graph; no browser
     `window.prompt()` is shown.
3. Place the way, inspect the graph and the new way's properties, then reload
   the scenario.
   - expected: the selected endpoints are connected by the placed way and the
     connection remains after reload; cancelling the picker creates no edge.

## Browser UI and intended live verification

Intended UI home: Library Browser → select a way template → **Place in world**
→ choose the source and destination from a searchable graph-node picker or by
clicking the graph. This extends the existing item-placement flow; it does not
send the author to a raw node-ID prompt.

Current availability: the card reports that way placement asks for typed
target names/IDs through native prompts. Task-751 replaces native popups but
does not provide the target-selection affordance required here. The current
browser reproduction has not been repeated in this turn.

Live steps when available:
1. Open Library Browser, choose an existing way template, and invoke **Place in
   world**. Inspect the complete visible dialog and count its controls before
   choosing a target.
   - expected after this task: a searchable list of existing areas and/or a
     graph-selection mode is visible; there is no free-text node-ID prompt.
2. Search for and select two existing areas by their displayed names, finish
   placement, and inspect the graph endpoints.
   - expected: the new way connects exactly the two selected area node IDs;
     the author never had to discover or type those IDs.
3. Repeat and cancel before selecting the second endpoint.
   - expected: cancellation leaves the graph unchanged and creates no partial
     way.

These steps define the intended authoring path and result; they do not claim
the picker exists today.

This section is not a claim that planned UI exists or works today.

## Acceptance

- [ ] TODO

## Files

- TODO
