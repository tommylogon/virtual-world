---
type: task
status: cancelled
area: ui
priority: high
---

# task-626: Item inspector renders equip_slots as an unstyled empty multi-select

**Filed:** 2026-09-30
**Related:** [task-292]

## Goal

equip_slots shows as a blank unstyled multi-select holding ten slots, so authored slots are invisible. Note 'apron' declares equip_slots ['torso'] but its actions lack 'equip'.

## Acceptance

- TODO

## Cancellation

Cancelled 2026-09-30. The finding does not reproduce; the field works.

The claim was that `equip_slots` renders as "an unstyled empty multi-select
holding ten slots, so authored slots are invisible". Driving it in the browser --
Build > Library > Items > search "apron" > click the row > scroll to the field >
click the chip to open the dropdown -- shows the opposite on all three counts:

- **Not unstyled.** It is Choices.js-enhanced (`el._choices` is set, and the
  widget renders as a `choices__list--multiple` chip input).
- **Not empty.** The apron's slot shows as a selected chip, `torso`, with a
  working remove control.
- **Not invisible.** `DEFENSE (DR) 4` sits directly below it, and the row is
  labelled "EQUIP SLOTS (SELECT ONE OR MORE)".

Screenshot: `audit/75-equip-slots-open.png` -- dropdown open listing `neck`,
`arms`, `hands`, `legs`, `feet`, `back`, `waist`; the selected `torso` chip
rendered in blue with an `x`.

One real sub-detail found while checking, recorded because it looks alarming and
is not: the underlying `<select>` reports `optionCount: 1` while the dropdown
shows 11. That is Choices.js managing its own list and pruning the original
element, which is the library behaving as designed.

This is the sixth finding in the live audit retracted for judging a surface
without interacting with it. The underlying observation that prompted it --
`apron` declares `equip_slots: ["torso"]` but its `actions` lack `equip`, so the
slot is authored and unreachable -- is real and is already filed under task-292
and task-610.