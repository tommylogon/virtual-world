---
type: bug
status: review
area: ui
priority: medium
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [task-933]
---

# bug-582: Human Turn Composer modal vertical overflow pushes say, emote, memory, and Act button below the fold

**Filed:** 2026-11-09
**Related:** task-933

<!-- deps:start -->
**Related:** [[task-933-character-controller-selector-and-director-turn-composer]]
<!-- deps:end -->

## What

In the Human Turn Composer (`#htc-modal` in `static/js/agent/human-turn-composer.ts`), adding the `#htc-director-bar` and `#htc-thought-row` increased the modal content height to `791px`, causing `#htc-modal` (`overflow: auto`) to push the `say`, `emote`, `memory`, and `Act` / `end turn` controls `152px` below the fold on standard desktop viewports.

## Why

`#htc-modal` used a single scrolling container (`max-height: 94vh; overflow: auto`) instead of a flex-column layout where the upper `.htc-grid` (scene + feed) scrolls internally while `#htc-composer` stays pinned at the bottom with compact row spacing.

## How

1. In `static/js/agent/human-turn-composer.ts` (`ensureStyles()`):
   - Set `#htc-modal` to `display: flex; flex-direction: column; max-height: 94vh; overflow: hidden;`.
   - Set `.htc-grid` to `flex: 1 1 auto; min-height: 0; overflow: hidden;` with `.htc-scene` (`overflow-y: auto; max-height: 36vh;`) and `.htc-feed` (`overflow-y: auto; max-height: 36vh;`).
   - Tighten padding and row margins inside `#htc-you` and `.htc-composer` (`flex-shrink: 0`) so all composer rows (`Ask Director`, `thought`, `do`, `say`, `emote`, `memory`, and `Act`) fit comfortably above the fold without scrolling the modal.

## Browser UI and intended live verification

Intended UI home: Human Turn Composer modal (`#htc-modal`).

Live steps:
1. Open the Human Turn Composer on `http://localhost:4444` at a standard `1280x720` / `1366x768` viewport.
2. Measure `#htc-modal` `scrollHeight` vs `clientHeight` and check visibility of `#htc-act` (`Act` button).
   - expected: `#htc-act` is 100% visible inside the viewport (`getBoundingClientRect().bottom <= window.innerHeight`) with zero modal scrolling required.

## Steps to verify

1. Open Human Turn Composer in Playwright on `http://localhost:4444` and inspect bounding rects of `#htc-modal` and `#htc-act`.
   - expected: All composer rows and `#htc-act` are visible without scrolling `#htc-modal`.

## Acceptance

- [x] `#htc-modal` uses a flex-column layout with internal scene/feed scroll and a pinned `#htc-composer` footer.
- [x] `#htc-act` (`Act` button) and all composer rows are visible without scrolling on standard viewports.
- [x] Zero em-dashes in code or task files.

## Files

- `static/js/agent/human-turn-composer.ts`
