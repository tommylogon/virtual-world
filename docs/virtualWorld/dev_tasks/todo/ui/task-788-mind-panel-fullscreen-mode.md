---
type: task
status: todo
area: ui
priority: medium
related: ["'task-691'", "'task-787'", "'task-820'", 'task-785', 'task-787', 'task-820']
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-788: Mind panel: fullscreen mode

**Filed:** 2026-10-12
**Related:** 

<!-- deps:start -->
**Related:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-787-mind-panel-migrate-the-remaining-mind-surfaces-out-of-the-bio-and-advanced-tabs]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]], [[task-785-mind-panel-click-a-memory-to-inspect-its-underlying-record-and-evidence]]
<!-- deps:end -->

## What

Let the Mind panel expand to fullscreen so a long memory list and its detail pane are readable.

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

Intended UI home: Character Inspector → 🧠 Mind panel header → Fullscreen control; return with the same control or Escape.

Current availability: The Mind panel is a tabbed modal and the full-screen mode is planned; the card records no current full-screen control.

Live steps when available:
1. Open Mind → Memories for a character with a long memory list and select a memory; activate Fullscreen.
   - expected: the panel fills the viewport, the memory list and detail have usable space, and the selected character/title remain unchanged.
2. Switch to Mind, Perception, and People while fullscreen; scroll to the bottom of each tab.
   - expected: every tab remains reachable, no body content is cut off, and the panel—not the page behind it—owns scrolling.
3. Exit fullscreen with the control and with Escape, then reopen Mind from the inspector.
   - expected: the panel returns to its original modal size, the opener receives focus, and reopening does not create a second Mind instance.
4. Resize the browser while fullscreen and after exit.
   - expected: the tab content reflows without horizontal clipping and the original inspector remains intact behind the modal.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
