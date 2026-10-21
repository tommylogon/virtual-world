---
type: bug
status: todo
area: library
priority: medium
related: [task-751]
blocked_by: [task-751]
wiki: "[[Library System/Library System Overview]]"
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

**Overlap with task-751 - read this first.** The *native-popup* half is already ticketed: **task-751** (`review/ui`) replaces every native `alert`/`confirm`/`prompt` with the in-app `dialog.*` module (`static/js/shared/dialog.ts`, already built), and this site - `library-browser.ts`'s way import (`Connect FROM area name:` / `Connect TO area name:` prompts) - is one of its ~20 `prompt()` call sites. But task-751 only swaps the widget; it would still ask for a **typed name/id**. The distinct fault here is that a placement target needs a **picker**, not free text: the author cannot know the id. So this card survives task-751 as *"the way placement needs a target picker (a searchable list, or click-the-graph)"*, and its native-popup half is discharged by task-751.

## How

The fix is to reuse the flow items already use, not to invent a second one.

1. **Reuse the existing placement target picker.** Items are placed through
   `openForRoom` in `static/js/item-library.ts` (and the Library Browser's
   equivalent), which already presents a list of candidate areas in the current
   scope and lets the author choose one. The way placement path should open the
   same picker for its source and destination, rather than a free-text field.
   The two endpoints are chosen the same way, so the author picks "the hall" and
   "the yard" by what they are called.

2. **Search on display name, resolve to node id at the point of use.** The
   author's input is a name they can see; the id is an internal fact the picker
   resolves. `engine/matching.py` already resolves names to ids for the
   existing verbs, and the placement call should use the same resolution rather
   than asking the author for the raw id.

3. **Offer the graph as a second route.** Picking by clicking a node in the
   graph view is the same action seen from a different surface. If the picker
   is a modal, "pick from the graph" is a mode of that modal, not a separate
   flow.

4. **Keep the id path working for machine callers.** The typed-id form may
   still be reachable programmatically (a script placing a way by id), but the
   human-facing surface must not require it. That distinction matters because
   an MCP edit or a test may legitimately have the id.

5. **Cancel cleanly.** Closing the picker creates no edge and leaves the
   library unchanged - the current prompt's cancel path already does this, and
   the picker must match it.

The `window.prompt()` widget itself is task-751's job, not this card's. This
card's job is that the thing the widget asks for stops being free text.

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

- [ ] The way placement flow in the Library Browser offers a target picker
      instead of a free-text prompt, for both the source and the destination
      endpoint.
- [ ] The picker lists areas in the current scope by their displayed names,
      is searchable, and resolves the author's selection to a node id
      internally.
- [ ] The author can complete a way placement without knowing, discovering or
      typing a single node id.
- [ ] Cancelling the picker at either step creates no edge and leaves the
      graph unchanged.
- [ ] A placed way connects exactly the two selected areas, and the
      connection survives a scenario reload.
- [ ] The typed-id path still works for programmatic callers, but no human
      surface requires it.

## Files

- `static/js/library-browser.ts` - the way placement path whose
  `Connect FROM area name:` / `Connect TO area name:` prompts are the reported
  fault
- `static/js/item-library.ts` - `openForRoom` and the item placement flow the
  picker should reuse rather than duplicate
- `static/js/shared/dialog.ts` - the in-app dialog module task-751 uses; it
  replaces the widget but does not supply a picker, so this card's work sits
  on top of it
- `engine/matching.py` - the name-to-id resolution the picker should use

## Reconciliation (2026-10-20)

Verified current behavior:
- static/js/library-browser.ts: way placement uses native prompts for targets; task-751 replaces native alert/confirm/prompt with in-app dialogs but does not add a target picker.
- No picker implementation found for way placement in library flow; still requires typed node ids via prompt.
- No newer done task addresses the picker requirement specifically.

Verdict: **STILL_VALID**. Native prompts remain and no target picker exists. The popup replacement alone (task-751) does not satisfy the need to find/select targets without knowing node ids.
