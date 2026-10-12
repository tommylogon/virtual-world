---
type: doc
tags: [surface/docs]
---

**Written to be read cold by anyone who has never seen this project.** No code, no file
names, no jargon. If you know nothing about how VirtualWorld works, you can still read
all of this.

A companion technical version — the same work, described the way a programmer would
write it — is in `CHANGELOG.md` under *Ways and Wires*. This one is the same news told
differently.

---

## The short version

This project keeps its own notes about how everything works: what a door is and what you
can do with it, how a character remembers things, how the world is drawn. Two things were
wrong with those notes.

First, they didn't connect to anything. Every piece of work in this project is written
down as a *task* — a small card describing a job — but a card rarely said which other
cards it depended on, or which part of the world it was about. So the notes were real,
and almost none of them pointed at each other. Reading them was like a library where no
book mentions another book.

Second, the page about **ways** — the doors, arches, ladders, paths and gaps that let you
move from one place to another — was written for a machine, not a person. It was a list
of settings and which part of the code reads each one. It never told you what a way *is*.

This update fixes both. Tasks now name the tasks they depend on, as real links. The ways
page is rewritten as an actual guide, and — the part that matters — it was **checked
against the way the world really behaves**, which turned up four things the old page got
wrong.

---

## The ways page, and why it was wrong

A way is anything you move through: a door, a portal, an elevator, a forest trail, a
crack in a cliff. If you want to get from one area to another, you use a way.

The old page described the settings. The new one describes the decision. It tells you
that a way can be open, shut, locked, blocked, broken or hidden; that "locked" and
"blocked" behave the same to the world but mean different things to a storyteller (a
blocked door has something *in* it — a fallen tree, a thorn bush wedged in the cave
mouth — where a locked one wants a key); that a way can be a window you can see through
but not walk through; that a giant's doorway can stop a normal person from following
someone who squeezed through a mouse-sized hole. It shows you, word for word, what a
character actually reads when they look around.

Checking that page against the real behaviour found four old claims that were simply not
true — the kind of quiet wrongness that sends a builder down the wrong path for an hour.
One of them: the notes called "see-through" a *state* a way could be in, when it is
really a separate switch (a window is a window whether it is open or shut). Another: a
"broken" way was listed as though it worked, but the world only half-believes in it — you
can't open or close something broken, yet you can still walk straight through it. That
is now written down, and handed to someone to fix properly.

---

## Tasks that point at each other

Every task card now lists the other tasks it depends on, as links you can click. On this
project, "this needs doing before that" is recorded in the card's own header, and nothing
was showing it — so a card you were looking at gave no hint that something else had to
happen first. Now it does. Before this, **746 of 885** task cards linked to nothing at
all. After it, that number is **681**, and every link that was added resolves to a real
card. A link that would point at a card that doesn't exist is left out rather than added
broken.

If you file a new task, or change one, the links keep up with it automatically. And if
someone hand-edits a card and lets the links go stale, the project's own checker says so.

---

## One quiet bug worth naming

A scenario can say up front: *this character already knows the cellar door is locked.*
That knowledge is how the game avoids showing every character every locked door — you
learn a door is locked by walking into it. But the part of the code that records this
"already knows" fact was writing it down in a place nothing else looked. So the authored
knowledge was silently thrown away: the character knew nothing, and no one could tell.

It's fixed, and so is the test that was happily agreeing with the mistake. This is worth
naming because it is the exact kind of bug that hides: the feature existed, it saved, it
loaded, a test passed — and it had never once worked.

---

## A standard for the notes

So that this doesn't drift back, the project now has a written standard for how its notes
are made — eight rules, in the file that guides everyone working on the project. The
short of it: write for the person building or playing the world, not for the code; put a
concrete example on every abstract rule; show what a player actually sees; say *why*
where the world itself doesn't care; and verify every claim against the real behaviour
before shipping it. A confident lie is worse than a gap.

---

## The game keeps a diary, and now you can ask it questions

While you play, the world writes a running diary: every line of what a character says,
thinks, tries and gets. You could already save that diary as a readable text file. Now you
can also save it as **data** — the kind a computer can search, count and sort, line by
line — as well as the readable version.

One panel does it. You choose *which* slice: a range of the run's sequence numbers (or of
in-game turns), a single character, a single place, and the file format. Before you commit,
the panel tells you exactly what it is about to include and which of your on-screen filters
it is honouring — so a version that quietly drops the "thinking" rows, or a character, is
something you choose rather than something that happens to you. There is an explicit switch
to *ignore* your filters and take everything.

Two long-standing annoyances went with it. The saved text used to end every turn heading
with a stray square bracket, and the little "scoped to" reminder at the top of the log used
to carry the × button that clears it, pasted onto the end. Both are gone — and both were
checked against a real run of the game, not just the code.

---

## Housekeeping

Four stale copies of the task list — snapshots of the same information that already lives
inside the notes — were deleted, along with two abandoned planning documents. The page
titled "Doors & Connections" was renamed to "Connections", because "door" stopped being a
separate concept a while ago and the old name was the last place still pretending
otherwise.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Commands]], [[Emotion & Mood — Whole-System Analysis]], [[Feature Ledger]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]]

<!-- connected:end -->
