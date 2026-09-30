---
type: task
status: cancelled
area: ui
priority: high
---

# task-608: Derived values render indistinguishably from authoritative ones

**Filed:** 2026-09-30
**Related:** 

## Goal

A derived display must declare itself. The human-turn modal renders strangers as 'the woman'/'the man' with no signal that they are unknown, that names exist, or that talking reveals them -- a competent first-time reader takes it for a broken name lookup. Same class as way labels showing raw node names. Every surface this audit misread was one that showed a fact without showing where the fact came from.

## Acceptance

- TODO

## Cancellation — rests on a retracted premise

Cancelled 2026-09-30. This task's stated basis is the finding that "the
human-turn modal renders strangers as 'the woman'/'the man' with no signal that
they are unknown, that names exist, or that talking reveals them".

**That finding was retracted.** Hovering a person in the turn modal reveals:

    the woman
    A nervous goblin squire in worn leathers, clutching a simple staff.
    (female)
    recognized — but you don't know their name yet

so the surface *does* declare the knowledge state, in words, on hover. The
audit's Â§61 ("derived values render indistinguishably from authoritative ones")
was withdrawn for the same reason, and this task was written from that
withdrawn claim.

Keeping a task whose entire goal statement is a disproof of a retracted finding
leaves the backlog asserting something the audit has already taken back.

### The residual that is real, and where it lives

Â§61 kept a narrower observation after the retraction, and it is not a defect
worth a ticket on its own:

> The modal's **hover layer** declares itself well — direction, cost, knowledge
> state, free-look status, resolved names. Its **at-rest labels** do not:
> `the woman` Ã—2 for two different people, and the raw way-node name on the
> movement chip.

Of those two, the coordinate half is **already fixed** under task-624
(`display_area_name` strips the `(world N,M)` suffix, verified live: "You follow
the path north toward Road — you're in Road"). What remains is that two
different people share the label `the woman`, which is the *intended* anonymity
mechanic rather than a defect — the hover disambiguates by description and
gender, and the name arrives through interaction.

If someone later wants that tightened, the right change is in the hover copy
(disambiguate the two), not in a claim that the modal fails to declare itself.