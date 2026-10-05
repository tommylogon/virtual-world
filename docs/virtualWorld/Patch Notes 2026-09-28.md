---
type: doc
tags: [surface/docs]
---

# VirtualWorld: What Changed — 2026-09-28

**Written to be read cold by anyone who has never seen this project.** No code, no
file names, no jargon. If you know nothing about how VirtualWorld works, you can still
read all of this.

A companion technical version — the same work, described the way a programmer would
write it — is in `CHANGELOG.md` under *A World That Notices*. This one is the same
news told differently.

---

## The short version

Twenty-eight planned pieces of work shipped in one day. Most of it is the same theme
over and over: **the game was pretending to know things it should have actually known,
and now it does.**

For a long time the world worked like this. If you shouted, anyone "within two rooms"
heard you — but "two rooms" was not a real thing, it was a stand-in for "people standing
near each other." If a goblin walked past five humans, nothing recorded that the goblin
had been seen at all. If a human lived inside a goblin camp for three days, the humans
were never once frightened.

All three of those were fakes standing in for real systems that had not been built yet.
They are built now.

Along the way, the four independent teams of work were folded together, 55 broken tests
turned out to be one typo, and the world's own records got cleaned up.

---

## 1. Things now travel properly

### A shout is a shout

**Before:** you could hear anyone who was "within two rooms." That was a shortcut. It
did not matter whether there were four walls between you, or a stone cliff, or a
locked door in the way.

**Now:** sound is worked out properly. A shout actually carries. A closed door muffles
it. Stone muffles it more. You can hear someone through a *run* of rooms if the sound
has a clear path, and you cannot if the path is broken somewhere along the way.

A detail worth knowing: **a locked door is a latch, not a soundproof wall.** If you
shout through a locked door, you can still be heard. What stops sound is a *chain* of
them — several closed doors in a row, or one door plus a wall.

This also means the game got much faster at working out who could hear what, because it
no longer has to consider every single person in the world to answer "who is listening."

### Light works the same way

Light now behaves the same way sound does. A window lets light through, a thick wall
does not, and a closed door dims it — the same ladder of effects, applied to seeing
instead of hearing.

### You can see down a row of doorways

If you stand in a hall and look through a line of open doorways, you can see all the way
down it. A wall, a step up or down, or a turn in the passage stops the sightline.

### Your map is your own

**Before:** the map was the same for everybody. Everyone saw everything.

**Now:** every character has their own map, and it only fills in as they explore. Rooms
they have not been to are fog. Walking into somewhere clears it — and so does being
*told* about it, or finding a map.

This is the single biggest change to the feeling of the game. A character now has
genuine ignorance, which means genuine discovery.

---

## 2. Characters have real reactions

### Fear works. It is not a new word for "they moved away."

For three simulated days, five humans lived inside a goblin camp and **not one of them
ever felt afraid.** This looked like a world that simply could not represent the idea.
It was not that. The machinery for fear had been written and simply never switched on,
and the reason it could not work was a small mistake: the game was checking the wrong
record for "is this person a goblin."

The information — every shipped character is tagged goblin, human, and so on — was
there the whole time. The fear system was just looking somewhere else. With that fixed,
humans living in a goblin camp now get frightened, and what they do about it varies
person to person rather than everyone bolting in the same direction.

Being frightened also now **ends when it should.** Previously a character stayed
frightened for a fixed half-hour even after the goblin had walked away.

Note honestly: **no scenario is written to use this yet.** It works, but nobody has
authored the content that would trigger it. That is the next step, not a finished
feature.

### The world now records who saw what

Previously nothing in the game kept track of the fact that one character had *noticed*
another. That turns out to matter for a lot of things: being embarrassed, being
caught, being flattered by attention. Now it is recorded each turn, along with whether
someone was watching openly or trying not to be noticed.

Noticing something and reacting to it are tracked separately, which is correct — seeing
something and having nothing to say about it is a real thing that happens.

### Groups

Characters can be marked as belonging to a group, and one of them can call out to
friends who are further away than the group can see. The rest of the group hears it.
This is a first, modest version: no formations, no flanking, no assigned roles.

### What a character is, finally

The records that hold a character's information were found to contain almost nothing —
basically just a name. Everything else about them lived somewhere else entirely. This
did not change any behaviour; it is the careful first step of moving the information
into the right place, with tests that measure how far along it is.

Two things that go with it: characters can now have **structured** descriptions of
their appearance and personality (as well as the free text they already had), and any
feeling the AI invents gets matched to a real emotion rather than being thrown away.

### Ghosts and zombies

Ghosts and zombies had a name and a label but no defences. Now they behave the way
they should: **a normal sword does almost nothing to a ghost**, because there is no
body to cut. Magical attacks work. Zombies are different — they have bodies, so they
can be grabbed and they bleed.

---

## 3. Objects are objects again

### "40 berries", not forty separate berries

One tree used to be one thing that didn't say how much of it there was. Now an object
can have a count, so a thicket of berries reads correctly and costs almost nothing to
store. You can take *three* berries from it, and it gives you three real berries and
has three fewer.

When the last one is gone, the bush is properly finished with — the same teardown that
already existed for a depleted item.

A tree cannot be picked up whole, on purpose. You take apples from it.

### Things made of parts

A phone can now have a battery, and the battery is genuinely *part of* the phone:

- You cannot steal the battery out of the phone. Any attempt says so plainly and names
  the phone.
- **When the battery dies, the phone remembers it had one.** Previously the battery was
  simply deleted, which left you holding a loose cell you never asked for, with no
  message and no explanation.
- There is no special "charge" property — a part's remaining uses *are* its charge.

### Treasured things

**Before:** any object could be picked up by anyone, and that was true in the fiction
too, whether the fiction agreed or not.

**Now:** an object can have an owner. Gribba's good knife is Gribba's, and the game
says so when anyone else tries to touch it — by name, with a way through.

**You can still steal it.** It is just harder: someone watches their own things more
closely than they watch loose change.

Two deliberate decisions here. If the owner is **dead or unconscious**, the protection
lifts — a dead goblin's knife is not a sacred object, and a rule that keeps guarding a
corpse's belongings is a worse bug than a permissive one. But if the owner is merely
*somewhere else*, they still own it. And you cannot talk or intimidate your way past it;
only actually stealing it works, because quietly adding a second dice roll inside an
ordinary action would make every action unpredictable.

### Something to do when bored

Entertainment only came from things lying around the place. Now a character can carry
their own: juggling stones, a string puppet, cups, a small drum. A goblin with a kit in
their pack can now cheer up, without a drum happening to be lying about.

If there *is* a drum lying about, that is still used first — so a camp that worked
before keeps working exactly the same.

---

## 4. The world has a shape

### Places can be grouped

You can now group places together and give the group a name: a whole world, a town, a
building, a set of rooms. Inside the world's own tools these groups show as a tree you
can collapse and reopen, so a world with a county over two towns reads as a county over
two towns rather than three unrelated names in a flat list.

Each group says what the records know about it. An unmade one reads **"Apartment 3B —
not built"** rather than "0 areas", because "we haven't built this" and "we built it and
it's empty" are different facts.

### A recipe that builds a place from nothing

There is now a working recipe that generates a small apartment: three rooms, a front
door from the hallway, and furniture chosen to suit. The important part is that **the
same seed always produces the same apartment**, and a *different* seed produces a
different one. You can edit what it built, and if you run it again it refuses rather
than overwriting your changes.

It deliberately invents no residents. A generated inhabitant that was never written by
anybody is a trap, and the rule against it is built in rather than left to judgement.

### The world's records, tidied

The goblin camp scenario had **46 character records where there should have been 23**,
and 422 connections pointing at things by name rather than by identity. That is fixed.

The camp's single water source now belongs to the camp. Using someone else's water is
now something that *happens*, rather than something that is simply available.

A naming error is also fixed: the camp's internal identifier still said `deep_woods_2`
from an earlier naming. The rule in this project is that internal identifiers change
and display names do not, so it was changed.

### You cannot close a road into a forest

**Before:** any door or passage could be closed by hand.

**Now:** you cannot shut a path through open country — you cannot close a road into a
forest or against a cliff. Passages get blocked by *things* instead: a fallen tree, a
barricade, a rockslide, a wolf den. Each one says why it is blocked, in words.

---

## 5. Two bug reports closed honestly

Two long-standing bug reports about characters' speech being garbled and mis-attributed
were investigated.

**Neither turned out to be a current bug.** Both are closed without a "fix", because
there was nothing to fix:

- The garbled speech *was* real, but the cause is long gone from the code. Investigating
  the old logs found the exact rule that caused it, and confirmed it no longer runs.
  The worst-looking examples in the log turned out to be a character's *own* generated
  words, saved garbled before any of this system touched them.
- The "same line appears twice" report turned out to be **two different lines** by the
  same speaker. The cause that was suspected cannot happen with the code as it stands.

No behaviour was changed. What was added is a set of tests that will catch these
specific problems if they ever come back. Closing a report by fixing the theory rather
than the symptom would have been worse than leaving it open.

---

## 6. Behind the scenes

### 55 of the ~60 "known broken tests" were one mistake

The project tracked about 60 failing tests as a known baseline, so nobody wasted time
on them. **55 of those 60 were a single mistake in the test code itself** — the tests
were written against an older version of a library and were calling a function that no
longer existed in that form. The actual system they were testing was working perfectly
the entire time.

All of them pass now. That sounds cosmetic. It is not: with 55 of 60 failures being
noise, **a developer could have introduced 50 real bugs and still been told they were
"at baseline."** The safety net was full of holes. There are now **5 genuine known
failures**, and each one is written down with what is actually wrong.

### Four teams, one repository, no disasters

The day's work was split across four independent teams working at the same time on
different parts of the project. Before starting, every planned task was mapped to the
exact files it would touch, so teams would not collide. Eight files turned out to be
dangerous to work on simultaneously — the most important one was claimed by 25 separate
tasks — so those got a single designated owner.

The analysis also found that **more than four teams would have been slower, not faster**,
which is not the intuitive answer and was not obvious before counting.

### Planning for a type-checked future

There is now a plan for converting the browser code to a stricter form, ordered smallest
file first. Two things it found: one missing type declaration affects **46% of all the
code**, so it has to be dealt with first or nothing else can proceed; and almost every
single file conversion touches one shared file, which makes it a team-ownership problem
rather than a free-for-all.

---

## What is not done

Honesty about the edges:

- **Fear works but nothing triggers it yet.** No scenario is written to author a fear.
  The first job is writing the content, not more code.
- **Loading a world in pieces is designed, not built.** The large task was split into
  four smaller ordered pieces. The first one is worth doing on its own merits because it
  fixes a real bug where two places with the same name could split a character's
  location.
- **The apartment generator has no preview button.** It can build an apartment but cannot
  yet show you a preview and ask before committing.
- **One test file hangs rather than fails.** It is excluded from the usual test run and
  still needs looking at.
- **5 known failures remain**, listed in full in `CHANGELOG.md`. Three of them are one
  underlying problem; one is a missing data file.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Emotion & Mood — Whole-System Analysis]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]], [[Patch Notes 2026-09-30]], [[Patch Notes 2026-10-03]]

<!-- connected:end -->
