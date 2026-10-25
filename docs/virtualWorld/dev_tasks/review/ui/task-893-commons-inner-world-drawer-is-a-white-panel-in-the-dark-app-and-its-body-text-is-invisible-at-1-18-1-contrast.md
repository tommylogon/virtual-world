---
type: task
status: todo
area: ui
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-888, task-824, task-827]
---

# task-893: Commons inner-world drawer is a white panel in the dark app and its body text is invisible at 1.18:1 contrast

**Filed:** 2026-10-21
**Related:** task-888 (the card that built the drawer and marked it live and verified), task-824 (The Commons itself), task-827 (the Commons theme work, which is where the dark override block came from)

<!-- deps:start -->
**Related:** [[task-888-the-commons-active-character-indicator-and-character-inner-stream-sidebar]], [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]], [[task-827-setting-aware-communication-themes-for-the-commons]]
<!-- deps:end -->

## What

The Commons inner-world drawer renders as a **white panel inside a dark application**, and the body text inside it is effectively invisible.

The page around it is dark: the body is `rgb(13, 17, 23)`, the top bar `rgb(22, 27, 34)`, the sidebar `rgb(17, 22, 29)`. The drawer is `rgb(255, 255, 255)` - pure white - with a near-white header `rgb(251, 250, 249)`.

The cause is a plain cascade-order mistake, and it is worth stating precisely because the fix is a fix to the file's structure rather than a colour tweak:

- `static/css/commons.css` has a **dark-theme override block** starting at line 213 (`.commons-topbar, .commons-main, .commons-input-row { background: #161b22; ... }`) which re-themes the whole page. It runs to roughly line 380.
- The drawer's rules were added **later**, starting at line 478 (`.commons-drawer-scrim`) and running to the end of the file at line 691. There are **zero** `.commons-drawer-*` rules inside the dark block - a text search for `drawer` between lines 213 and 400 returns nothing.
- So the drawer's own light-theme rules win by source order, and nothing overrides them.

Git history confirms the sequence: the dark block landed in `a0b06866` ('expand Commons communication modes'), and the drawer landed afterwards in `524a63c7` ('merge plan templates, action verb registry, commons UI and task status reconciliation') - which is also the commit that added task-888's Inner World drawer. The drawer was never added to the dark block, because the dark block was already written and nothing says 'new UI goes here'.

**The invisible text is the real bug.** The drawer body text inherits the page's light foreground (`rgb(230, 237, 243)`) while sitting on the drawer's white background. Measured contrast ratios against `#ffffff`:

| Element | Colour | Ratio | WCAG AA needs 4.5 |
|---|---|---|---|
| `.commons-drawer-traits` | `rgb(230, 237, 243)` | **1.18** | fail |
| `.commons-drawer-monologue` | `rgb(230, 237, 243)` | **1.18** | fail |
| `.commons-drawer-decision` | `rgb(230, 237, 243)` | **1.18** | fail |
| `.commons-drawer-history` | `rgb(230, 237, 243)` | **1.18** | fail |
| `.commons-drawer-section-title` | `rgb(147, 143, 156)` | **3.16** | fail |
| `.commons-drawer-presence` | `rgb(119, 115, 125)` | 4.63 | pass |
| `.commons-drawer-personality` | `rgb(85, 81, 94)` | 7.71 | pass |
| `.commons-drawer-name` | `rgb(43, 40, 51)` | 14.44 | pass |

So the drawer's *identity* block (name, presence, personality) is readable, because those rules are light-theme coloured. Everything below it - the three section bodies that are the entire point of the drawer (Current Inner Stream, Latest Decision & Action, Recent Turn Thoughts) - is white-on-white at 1.18:1 and cannot be read at all. The trait badge has a light background too.

## Why

The drawer's entire purpose is to show a character their inner cognition: the monologue they just had, the action they chose, the thoughts from earlier turns. Four of its six content areas are unreadable. The feature ships, the button works, the panel opens, and it shows a name and a personality and then a blank white space where the content should be. This is the failure mode where a UI looks wired and produces nothing - the same class of bug as the Cardinal overlay reading the wrong object, and it is why the fix is measured in contrast ratios rather than in 'it looked wrong to me'.

It is also a structural problem, not a colour problem. The dark theme is a *block* in the middle of the file, and every new component added after it is silently light. The Commons already has a `commons-icon-btn`, a `commons-select`, a `commons-btn` and a `commons-dialog` that all had to be re-listed in the dark block by hand - and the drawer, the newest surface, was not. The next component will have the same bug unless the structure changes.

The drawer's own card (task-888) is marked 'live and verified', with acceptance boxes ticked. The verification was of *behaviour* - the chip updates, the drawer opens, the content renders into the DOM - and that was true. Nothing checked whether the content was legible. A behaviour check and a legibility check are different checks, and only the second one catches this.

## How

1. **Add the drawer to the dark block.** The minimal fix is to extend the existing dark-theme override block in `static/css/commons.css` (from line 213) with the drawer's rules: the panel background, the header, the section titles, the body text colour, the monologue/decision/history text, the trait badge, the empty-state text, and the history-row text. The dark block already defines the palette to reuse - `#161b22` for panels, `#11161d` for the raised surface, `#e6edf3` for primary text, `#a1aab5` for secondary, `#30363d` for borders.
2. **Then remove the drawer's light rules.** The drawer's own light-theme declarations at lines 478-691 should go, so there is exactly one source of truth for the drawer's colours. Leaving them and overriding them later is how this bug happened twice.
3. **Make the structure prevent a recurrence.** The dark block is a hand-maintained list of selectors, and the cost of adding a component is remembering to add it. Two options:
   - a CSS custom-property block at the top of `commons.css` (the app's `style.css` already uses `--bg-*`, `--border`, `--text-*` tokens - the main app's own stylesheet does this) and have every Commons rule reference the tokens, so there is one dark palette and no override block at all;
   - or, smaller: keep the override block but add a check that fails when a `commons-*` class has a hardcoded light colour and is absent from the dark block.
   The first is the real fix and the second is a cheap guard. Doing the first is a whole-file change to `commons.css` and should be its own card, not a rider on this fix - so this card should do the token migration *for the drawer only* and file the rest.
4. **Add a contrast check.** The measurable part of 'this is fixed' is a ratio, not an opinion. A unit-style check that reads the computed styles of the drawer's text elements against the drawer background and asserts at least 4.5:1 would have caught this and would catch the next one.
5. **Re-check the other surfaces.** The same override block may have missed other post-dark-block additions. Compare the set of `commons-*` classes used in `templates/commons.html` against the set named in the dark block, and list anything that is styled with a hardcoded light colour and never overridden.

Not in scope: re-theming the whole Commons to a light theme, or changing the app's dark palette.

## Browser UI and intended live verification

Intended UI home: /commons -> click any character name or avatar in the message feed, the member list or the participants list -> the right-hand 'Inner World' drawer.

Current availability: Implemented but visually broken. Verified 2026-10-21 in the browser on the Kraktooth goblin camp: the drawer opens and the identity block renders, but the panel is white (#ffffff) against a dark page, and the monologue, decision, history and traits text all measure 1.18:1 contrast - unreadable.

Live steps when available:
1. Open /commons and click a character name in the message feed or the participants list.
2. expected: the drawer opens on the right, dark like the rest of the page, with no white panel.
3. Read the Current Inner Stream, Latest Decision & Action, and Recent Turn Thoughts sections.
4. expected: all three sections' text is legible against the panel background; the empty-state text is legible too.
5. Measure the contrast of each text element against the drawer background.
6. expected: at least 4.5:1 for every text element, including the trait badge and the history rows.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] The inner-world drawer's panel background matches the surrounding dark application rather than being white.
- [ ] Every text element inside the drawer measures at least 4.5:1 contrast against its own background.
- [ ] The three drawer sections (Current Inner Stream, Latest Decision & Action, Recent Turn Thoughts) are readable, including their empty-state text.
- [ ] The trait badge and the history rows are themed to match.
- [ ] The drawer's light-theme declarations are removed rather than overridden, so the drawer has one source of truth for its colours.
- [ ] A contrast check runs as part of the test suite and fails on a drawer element below 4.5:1.
- [ ] Every `commons-*` class in `templates/commons.html` that carries a hardcoded light colour is either themed in the dark block or listed in a follow-up card.

## Files

- `static/css/commons.css`
- `templates/commons.html`
- `static/js/commons/commons-ui.ts`
- `tools/unit/test_commons_agent.js`
