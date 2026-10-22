---
type: doc
tags: [surface/docs]
---

# Charted Ground - 22 October 2026

A week of work, written for someone who has never opened the project. Three
changes are the kind you notice by playing: a practice run now leaves the world
exactly as it found it, you only know the parts of the map you have actually
looked at, and worn gear counts as gear you are carrying. The rest is quieter:
characters can be known by more than one name, roads describe the view through
them, the weather is no longer stuck, and the event log finally says who did
what.

## A practice run leaves no footprints

**Play Mode** is a sandbox. Turn it on, take a few turns, and the authored world
is untouched: characters go back to where they were, items go back to their
shelves, and the clock goes back. Stopping the run keeps your ordinary log and
throws the run's rows away, so a play session cannot be mistaken for the real
history of the scenario. Loading a different world while Play Mode is still on
now discards the checkpoint instead of quietly restoring the wrong world later.

The log is deliberately a boundary, not a filter. Everything written before you
pressed the button comes back when you stop, including rows restored after a
reload. Everything written during the run is discarded, including the "Play Mode
active" marker. The one thing that does not survive is a browser reload during
the run itself: that checkpoint lives in the open page, not on disk.

## You know only what you have seen

Sight is now traced along a ray through the world instead of inferred from
distance. Height and obscurity matter, so a rise can reveal something a hedge
hides. What you have looked at is **charted**, and charted cells stay on your
map after you walk away. The minimap only shows what the character can see, and
distant landmarks on the horizon are drawn as remembered shapes rather than
current facts.

The practical effect: exploring is a decision. Walking into the open teaches you
the ground; walking past it does not.

## Worn is carried

Gear you are wearing now counts toward what you are carrying, and the equipped
map is published in the state payload instead of being implied by inventory
lists. A character who picks up a coat and puts it on is heavier, slower, and
more likely to be refused at a gap they used to fit through. That is the
intended reading of the rule, not a regression.

Unlit items also stop pretending to glow. Anything that is not a light source
defaults to no light at all, rather than the dim value it used to report.

## Your character has a face, and more than one name

Characters carry structured persona fields for appearance and bearing, and a
button compiles them into the prose the simulation actually uses. The inspector
shows the same fields, including a gender row and the paper doll, so what you
edit is what the prompt sees.

Characters can also be referred to by an alias. The scenario knows the nickname;
the room still resolves it to the person. An ambiguous alias asks instead of
guessing.

## Roads that describe themselves

Generated ways now carry a description and a separate "what you see looking
through it" line, so a path reads as a view rather than a label. Compiled ways
also carry tags, which means a generated road no longer reports "Tags: none" to
every inspection.

Open outdoor ways are marked as things you cannot simply close. A road into the
forest is not a door; the close verb refuses it instead of pretending a field
gate can be shut.

## Weather that changes

Deterministic forecast mode used to pick the first non-zero weight in its
transition table, and every row lists "clear" first. The result was a sky that
stayed clear forever. It now picks from the weighted table using a seeded
generator: reproducible, but a real sequence.

## The log says who acted

Raw model output arrives as a labelled chip carrying the actor, the area, and a
real tick number instead of a line sequence pretending to be one. The event log
exports to Markdown, plain text, JSON, and JSONL from one modal, with a tick
range and actor or area scope, and the modal says which rows the filter actually
covers.

## For builders

Trigger graph editing handles every trigger on an item, not just the first one,
and each trigger keeps its identity while you edit it. Triggers live as arrays
on the node, so the graph editor and the engine read the same thing.

The world library grew 411 feature biome records and a river family with height,
hazards, and flow checks. WorldPainter gained a vision raycast debugger, a
current paint layer indicator, and a palette that docks beside the canvas. The
validator exports its issues as JSON or Markdown. An open editor tab now notices
when the served frontend has changed underneath it.

## Under the hood

Saving the item library used to rewrite every entry it was handed, and the JSON
writer did not end files with a newline. A single item action therefore produced
hundreds of one-byte diffs in the working tree. The writer now only touches
entries whose content changed, and a guard fails the pre-commit checks if a
changed JSON file loses a trailing newline it used to have.

## Not in this one

Two pieces are still in flight. The natural-language editor cannot yet author a
character's schedule, goals, and obligations; the validation and route work is
landed, the editor surface is not. And NPC action results in the turn feed still
read "You" instead of the character's name, because result rows do not yet carry
their actor.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` - relations the repo already asserts, not invented.*

**Neighbouring notes** - [[Patch Notes 2026-10-15]], [[Event Log Export]], [[Commands]], [[Feature Ledger]], [[History]]

<!-- connected:end -->
