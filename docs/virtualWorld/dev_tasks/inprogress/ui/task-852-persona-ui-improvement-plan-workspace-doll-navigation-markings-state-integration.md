---
type: task
status: inprogress
area: ui
priority: medium
wiki: "[[Characters/Persona]]"
---

# task-852: Persona UI improvement plan: workspace, doll navigation, markings, state integration

**Filed:** 2026-10-16
**Related:** 

## What

Deliver the Persona improvement plan P1-P5: workspace redesign, paperdoll navigation with front/back views, region-linked markings, body-state integration, personality/narrative polish — no duplicate truth, no readerless fields.

## Why

The Persona tab read as a database form: a 720px max-width column of
bordered inputs. The user's review (2026-10-16) asked for a polished,
cohesive authoring workspace where the doll is central and the body is
super useful AND stunning — real hierarchy, state clarity, region
navigation, and markings — without duplicating systems or inventing
readerless fields.

## How

Blueprint: user-provided Persona UI Improvement Plan (P1-P5). Order:
workspace layout → doll navigation (front/back, keyboard, no artwork
required) → region-linked markings (multiple per region, canonical
store) → body-state integration (sensitivity verified end-to-end,
injuries/bleeding/coverage read-only, task-851 seeded wounds wired) →
personality/narrative polish → regression.

Non-goals (hard): no second doll/region catalog, no duplicate editors
in the region panel, no fields without consumers, sensitivity never
compiles to prose, no pregnancy/identity work (846/850 stay out).

## Browser UI and intended live verification

Intended UI home: Mind dashboard → Persona tab.

Current availability: P1 (workspace layout) is implemented and passes the
static gates; it has NOT been verified in a browser. Full-width pane, header
(name, base_description one-liner, badges) and the saved / unsaved /
uncompiled chips are in the code. P2-P5 are not part of this pass.


Live steps when available:
1. Mind > Persona on a character whose prose is stale.
   - expected: wide workspace, character header (name, one-liner from
     base_description, badges); chips read ✓ saved + ⚠ uncompiled;
     actions on the right.
   - observed: not verified live in this pass (see Steps to verify).
2. Type in any sheet field (text input or chip pill add/remove).
   - expected: chip flips to ● unsaved and ⚠ uncompiled. Typing in the
     chip draft box, the marking draft box, or moving a sensitivity slider does
     NOT mark the sheet unsaved (those do not write the record).
   - observed: not verified live.
3. With unsaved edits, switch to the Mind tab and back, or wait for a state push.
   - expected: the edits are still in the form and the chip still says unsaved.
   - observed: not verified live.
4. With unsaved edits, press compile.
   - expected: message says to save first; nothing is compiled (compile reads
     the saved block).
   - observed: not verified live.
5. Press save block, then compile.
   - expected: after save the chip reads ✓ saved and stays ⚠ uncompiled
     (the server flags the prose stale on every save); after compile it clears.
   - observed: not verified live.
6. Narrow the window below 920px, then below 640px.
   - expected: doll column stacks above the sheet and stops being sticky; below
     640px the header stacks and chips and actions left-align.
   - observed: not verified live.


7. Identity fields: click into pronouns, gender, sexuality, species (restart the
   server first: the vocabulary comes from GET /record).
   - expected: each shows a native pick-list; picking an entry fills the field
     and flips the chips to unsaved; typing a value not in the list is accepted;
     after save and reload an existing custom value (e.g. xe/xem) still displays.
     Note: the browser filters a datalist by the current text, so clear the field
     to see every option. occupation and age have no list.
   - observed: not verified live.

Why no browser UI: (only when Intended UI home is Not applicable) TODO — explain why browser interaction is not appropriate.

Alternative verification steps: (only when Intended UI home is Not applicable)
1. TODO — describe an observable alternative.
   - expected: TODO — describe the result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Live path above (Mind > Persona), steps 1-6.
   - expected: wide workspace + header + chips that follow the real state.
   - observed: NOT verified live. On :4444 over HTTP only: the served
     static/js/inspector/mind-view.js contains the new code, and
     GET /api/players/Arix/record answers (prose_stale true, structured false).
     Earlier pass (pre-chip-wiring): full-width pane and header seen live.
2. `python tools/ts_convert.py check`.
   - expected: green.
   - observed: green 2026-10-16 after the chip/dirty/stale and layout edits
     (build:ts, typecheck, lint, module:check, unit all ok).
3. `python -m pytest tests/test_character_appearance.py tests/test_character_record.py`.
   - expected: green.
   - observed: 110 passed 2026-10-16. Two premise errors in the uncommitted
     test_compile_region_linked_markings were fixed first (it passed a Player
     where a node was needed, and asserted lower-case prose that is capitalised).
4. Identity pick-lists: `python -m pytest tests/test_character_appearance.py tests/test_character_record.py tests/test_emote.py`.
   - expected: green, including TestIdentitySuggestions (every pronouns option
     resolves in engine.pronouns; species list = SPECIES_PROFILES; GET /record
     serves the lists; custom values round-trip unchanged).
   - observed: 127 passed 2026-10-16; ts_convert.py check green after the edit.
     Not verified in a browser. The server on :4444 predates the route change
     (GET /record has no `suggestions` yet), so it needs a restart.
5. Live region/navigation acceptance (pending figure asset, P2).

6. P2 paperdoll navigation (front/back, keyboard, region selection polish).
   - expected: navigate-mode doll swaps front/back faces over the same slot grid, arrow keys move selection, selected area drives the region panel.
   - observed (start): P2 started 2026-10-16. Already in the tree (uncommitted): paperdoll-view.ts takes opts.facing and hides the back slot on the front face / held-item slots on the back face; style.css has data-facing grid templates; mind-view.ts has front/back buttons, arrow-key handler and _navAreas(). Verifying and polishing these now; nothing here is live-verified yet.
   - observed (trace): the face filter was declared twice (paperdoll-view hid slots, mind-view _navAreas had its own order list). On the back face the waist slot was still rendered although the back grid template has no waist cell, so it would auto-place outside the figure. Arrow keys cycled a flat list, not the grid; a state push rebuilds the modal and dropped doll focus, which would break keyboard use.
   - observed (change): AREA_FACE + areasForFacing() now live once in paperdoll-view.ts (back: back; front only: waist, lhand, rhand, hand_l, hand_r) and feed both the renderer and the Persona tab. Arrows move to the nearest visible slot in that direction (read from the rendered grid), F/B flip, Esc clears. Selection is aria-pressed, the doll has a focus ring and survives a modal re-render. New tools/unit/test_paperdoll_facing.js (6 tests) is wired in tools/unit/run.cjs.
   - observed (gates): ts_convert.py check green; node tools/unit/run.cjs 727 passed, 0 failed (the 6 paperdoll facing tests ran). NOT verified in a browser (spatial arrows, focus ring, face flip need eyes); server restart not needed for P2 (static files only).
   - open decision: appearance.body.butt/hips are linked to the waist area (front only), so they are reachable from the doll on the front face only. Showing waist on the back too would need a 7th row in the back template and would show genitals/balls on the back view, so it was left as is.
<!-- p2-log -->

## Acceptance

- [ ] (implemented, gate green, live not verified) Full-width pane.
- [ ] (implemented, gate green, live not verified) Character header: name, one-liner, badges; source = base_description.
- [ ] (implemented, gate green, live not verified) State chips: unsaved when a sheet field is edited, saved after save/re-read, uncompiled from the server prose_stale flag or unsaved edits; edits survive re-render; compile refuses while unsaved.
- [ ] (implemented, gate + pytest green, live not verified) Identity fields stay free text and offer a pick-list (pronouns, gender, sexuality, species). Known gaps, not fixed here: the live emote path calls pronouns_for(player) without the record, so identity.pronouns does not reach narration; nothing reads identity.gender.
- [ ] Responsive pass for the P1 layout (breakpoints added at 920px and 640px; not viewed in a browser).
- [ ] Paperdoll navigation front/back + region selection polish (P2). Implemented; ts_convert check + unit runner green (6 new facing tests); keyboard/face flip/focus ring NOT verified in a browser.
- [ ] Region-linked markings, multiple per region (P3).
- [ ] Body-state integration incl. task-851 wiring (P4).
- [ ] Personality/narrative polish (P5).
- [ ] Regression + responsive pass.

## Files

- static/js/inspector/mind-view.ts (generated mind-view.js): header, state chips, dirty/stale logic, form-sync on re-render, compile guard, persona styles in _personaCss()
- static/css/style.css (uncommitted paperdoll back-face rules from P2; no P1 rules live here)
- static/js/inspector/paperdoll-view.ts (AREA_FACE, areasForFacing, navigate aria) and mind-view.ts (facing/keyboard wiring, focus kept across re-render)
- tools/unit/test_paperdoll_facing.js, tools/unit/run.cjs (loads paperdoll-view.js)
- tests/test_character_appearance.py (fixed the P3 markings test; TestIdentitySuggestions)
- engine/character_appearance.py (IDENTITY_SUGGESTIONS + identity_suggestions(): the one place for the pick-list options)
- routes/player_ops.py (GET /record serves `suggestions`)

