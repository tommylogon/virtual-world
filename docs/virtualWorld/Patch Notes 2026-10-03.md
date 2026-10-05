---
type: doc
tags: [surface/docs]
---

**Written to be read cold by anyone who has never seen this project.** No code, no
file names, no jargon. If you know nothing about how VirtualWorld works, you can
still read all of this.

A companion technical version — the same work, described the way a programmer
would write it — is in `CHANGELOG.md` under *Things Stop Vanishing*. This one is
the same news told differently.

---

## The short version

The last update was about painting a world you could walk around in. This one is
about **things that were disappearing**.

Here is what that means concretely. You could spend an afternoon writing a
character's behaviour — "when someone is nearby, she is warm, she hides the knife
she is carrying" — and then open the behaviour in the picture editor to tidy up
the layout, press Save, and lose it. Not lose part of it. Lose **all of the
detail**, leaving only the bare instruction, with no error message and nothing on
screen to tell you it had happened.

That was not one bug. It was two, and between them they were quietly deleting
most of what you could write.

The other half of this update is that the world got **much better at knowing where
things are**, and the editor got a lot better at telling you the truth.

## The behaviour editor was throwing your work away

This is the one to read if you write characters' behaviour.

Characters do things because of **behaviours**: when something is true, do these
things. The game has a **graph editor** for these, where you draw boxes and join
them with lines, and a plain **form editor**, where you fill in boxes.

Those two disagreed, and the graph one was lossy. There are **121 kinds of thing**
a character can be told to do — pick up a knife, kiss someone, set an emotion,
hide something, wait. The graph editor's menu offered **11**.

So if you wrote a behaviour using "kiss", the graph editor showed the box, could
not find "kiss" in its menu, showed you "message" instead — and when you saved, it
wrote back the word **kiss** with every single detail gone. Who it was aimed at.
Where. How hard. All gone. No warning.

It is worse than that, because it was **110 of the 121**. Every action except the
eleven in the menu lost its details. I checked this by running the real game: I
wrote an instruction saying *kiss the player, on the mouth, gently*, opened it in
the graph editor, saved, and got back *kiss*.

**This is fixed at the root, not patched.** There is now **one list** of what
characters can do, with what each one needs, and it is read from the part of the
game that actually performs the actions — so the list cannot quietly drift out of
step with the engine, and both editors read the same one. Add a new kind of action
to the game and it appears in both editors, with the right boxes, without anyone
editing a list by hand.

Two honest caveats about that list. It is missing two actions the game can
perform — *listen* and *trade* — so those two are not yet editable in the picture
editor; they still save correctly, they just do not have boxes. And one action's
boxes are not quite right. Both were found by comparing the two lists against each
other rather than assuming they matched, and neither loses your work.

The same pass fixed the other disappearing thing. If you drew **one box feeding
two others**, only one of them was saved. That one turned out not to be a limit of
the game at all: the engine can run as many actions as you like in a row, so this
was purely the editor failing to look. It now follows every line you draw.

I also want to be straight about a mistake I made here. My first attempt at the fix
still lost details on 50 of the 121, because I wrote down the wrong set of names
to leave alone. **The test I wrote for this is what caught it** — a test that walks
all 121 kinds of action, gives each one everything it needs, and checks all of it
comes back. It now passes for all 121. Had I only tested by hand with the three
actions in the documentation, I would have shipped it still broken.

## You can now take wires out of a picture

If you used the graph editor for triggers or behaviours, you could not delete a
line. Not "it was fiddly" — you could not do it at all. If you drew a line
between the wrong two boxes, your options were to delete one of the boxes or start
over.

Now you can **click a line to select it and press Delete**, or just right-click
it. Lines also have **arrowheads** now, so you can tell which way information
flows without tracing it, and they still keep their colours — green for "yes this
is true", red for "no it isn't".

And two new refusals. If you draw a line that would make a **circle** — a box that
depends on itself — the game says so instead of quietly accepting it. If you draw
the **same line twice**, it says that too, instead of letting you believe you
have two paths when you have one.

## The editor now tells you when it cannot do something

Sometimes you can draw something the game genuinely cannot run. A character's
behaviour has no "otherwise" — there is no way to say "if this is true do A,
otherwise do B" for an action list the way you can for a single question. That is
a limit of the engine, not of the drawing.

Before, the game drew it happily and then quietly threw that part away when you
saved. Now there is a **badge in the toolbar** that tells you how many branches
will not be saved, and hovering it tells you exactly why.

I want to be clear that this one is a **warning, not a fix**, and it stays a
warning. The honest thing is to say the game cannot run it.

## The game now knows where everything is

A lot of work went into making the world **remember** things properly.

**Places, chunks and regions.** The world can now be split into regions that load
and unload as you travel, and it knows who owns what across that boundary — a
trigger in one region can fire an event that lands in another, correctly. There
is one index of the whole world, so the game knows a region exists **before** you
walk into it.

**One record of where a thing is.** Previously a location could be recorded in
more than one place, and which one won depended on load order. Now the link
between the things is the authority, so an item is in exactly the place its
connections say it is.

**Names that collide tell you.** If two places in your world end up with the same
name, the game says so, instead of quietly picking one.

**How many people fit.** A place's capacity is now computed from what is actually
in it, rather than being a number you set by hand and then had to keep updating.

**Saving is safer.** Every save now records which version of the game wrote it. If
you try to open a save from a newer version, the game **refuses and explains**,
instead of loading it, getting confused, and corrupting it.

## A character is a species, and can be properly hurt

**Species.** Characters can be told what kind of creature they are, and the part
of the game that decides what someone *needs* — food, warmth, rest — can now read
it. A wolf and a person no longer get the same needs by accident.

**One health model.** This is the one that mattered. The engine had no concept of
health at all; it had the number 100 written in several places. There is now a
single place that decides how much damage someone can take, how likely a hit is to
land, and what dying means. Before, writing a character's maximum health through the
editor would quietly squeeze the health back down — the thing that sets the ceiling
was clamping the thing it was supposed to bound.

**Defence in two directions, and you choose.** Protection is now armour *and*
skill, separately, and damage reduction is either a flat number or a percentage —
your choice, set once, and the log tells you which you picked.

**Arrows.** Ranged weapons and ammunition, including a quiver.

**Wetness is visible.** If a character is wet, that now reaches their
description, not just an internal number.

**Feelings steer behaviour.** One place decides what a named feeling means, so
declaring a feeling actually changes what a character does.

## An item has a history

- **Provenance.** Where an item came from and how you came by it.
- **Hiding things.** You can carry something concealed, and searching reveals it.
- **Stacks and piles.** Identical things stack; things that belong together can be
  related to each other.
- **Inscriptions** are now structured, and the AI character can read them.
- **Where things belong.** Items can prefer a kind of terrain, and a biome can say
  what grows in it — checked automatically from the biome definitions, so a new
  biome cannot ship with nothing in it.
- **The goblins have gear**, and starting kit, specified rather than improvised.

The library is now **1,999 items**, up from 1,915.

## Two small ones that you will notice

**The graph is calmer.** The map view no longer runs the physics solver by default,
which removes a visible stutter when the world shifts under your cursor.

**More of the world is painted.** Eldenford's town is finished, with a bathhouse.

---

## Three things you should know

**Your saved Kraktooth campaign is still modified in your working tree, and this
update deliberately does not include it.** The file
`data/scenarios/kraktooth_goblin_camp.json` was overwritten by the game's own
"Commit Scenario" button, so it now holds a played session rather than the authored
scenario — four simulated characters in place of the goblins, and a leftover player
name from testing. The good version is still in git history:

```
git checkout -- data/scenarios/kraktooth_goblin_camp.json
```

**The Python test suite reports 84 failures where you may have expected 12.** Most
of that is not us. **55** of them are the same thing: the MCP tests need a newer
version of a library than the one installed on this machine, and they were fixed
for the newer one. Nothing in the game's server code changed. The rest were
verified, by testing the same things on a clean copy, to be already failing before
this work started.

**Some editor text is still mojibake.** A handful of labels in the behaviour editor
read as `ðŸ’¬ Message` instead of `💬 Message`. This is an old encoding fault that
predates this work; the new shared list is clean, and repairing the rest of that
file is filed as its own task rather than folded in here.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Emotion & Mood — Whole-System Analysis]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]], [[Patch Notes 2026-09-28]], [[Patch Notes 2026-09-30]]

<!-- connected:end -->
