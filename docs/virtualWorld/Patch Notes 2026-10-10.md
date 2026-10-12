---
type: doc
tags: [surface/docs]
---

**Written to be read cold by anyone who has never seen this project.** No code, no file
names, no jargon. If you know nothing about how VirtualWorld works, you can still read
all of this.

A companion technical version — the same work, described the way a programmer would
write it — is in `CHANGELOG.md` under *Update in Place*. This one is the same news told
differently.

---

## The short version

The world map is the heart of this editor: a living picture of every room, road,
character and object, drawn as a graph you can pan, zoom and reshape. The last few
updates quietly made that picture expensive — every small change rebuilt the whole
thing. This update makes it **stop rebuilding**.

Concretely: a place opens in about a quarter of a second instead of several, the map no
longer freezes for a minute and a half on first load, a narrowed view stays narrowed,
pausing the simulation now freezes things exactly where they are, and the pause button
finally shows the right icon. Nothing about the world itself changed — only the
machinery that draws it.

---

## Opening a place is instant now

Before, if you picked a small region — a camp, a district — the editor would first build
the *entire* world, then throw it away and build the region you actually asked for. Twice
the work for one screen.

Now it builds only what you asked for, first time. A camp that is a fraction of the world
opens in about a quarter of a second.

---

## The freeze is gone

The worst of it was a minute and a half of locked-up browser on first load. The cause was
almost embarrassing: the code asked the drawing engine to redraw the *whole* map once per
object — thousands of times — instead of once for all of them. It now asks once. The
minute-and-a-half became milliseconds.

---

## Nothing is thrown away when two things happen at once

The editor is a small web server and it serves several requests at the same time. One
request could be redrawing the map while another was adding something to the world, and
the moment the two overlapped the server fell over with an internal error. The specific
crash you could hit — checking a map that has unfinished routes — is fixed. The general
pattern, several requests touching the same world at once, is written up as its own job to
solve properly, because hiding a symptom is not the same as fixing it.

---

## A narrowed view stays narrowed

If you zoom the map down to one region and then the editor refreshes, it used to quietly
fill back up with the *entire* world — rooms and objects from everywhere, floating loose
with no connections to anything. Your chosen view is now respected: a camp shows the camp,
its own 142 things, not the world's 2,763.

---

## Pausing freezes, it does not rewind

Pausing the simulation used to teleport everything back to where it started, as if nothing
had ever run. There were two causes, and both are fixed. Pausing no longer nudges the
simulation with a fresh instruction, which had the side effect of restarting it; and the
"arrange everything neatly in a ring" step now runs once when a layout is first built, not
again every time the simulation comes to rest — which is what had been dragging every
settled object back onto its original ring.

---

## The buttons tell the truth

The physics button always showed the same "pause" icon, even when the simulation was
already paused. It now shows a pause symbol while things are moving and a play symbol
while they are held, so one glance tells you which state you are in.

---

## Small things

- The map no longer waits on outside websites to fetch its drawing libraries; they now
  ship with the editor, so a first load does not depend on the network.
- The code that decides "should things be moving right now" has a single owner, instead of
  three places each deciding for themselves and disagreeing.
- A stale, unused "refresh the graph" command with no button anywhere was removed rather
  than left to mislead the next reader.

---

## Follow-up: the pause button, and the map that drifted

Two things the same day's work left behind, found while checking a long list of older fixes.

**The pause button did not believe the lock.** If you had frozen the map's layout — the little lock that pins every room and object where you put it — the pause button still lit up as though things were moving, and clicking it changed nothing at all. The button was asking a question nobody was answering: it looked for a setting that was never actually written. It now checks the same thing the simulation checks, so when the layout is locked the button greys out and tells you why.

**The map jumped a few seconds after you resized it.** Nudging the map's spacing puts every room and road neatly on the painted map for a moment — and then, seconds later, they slid off somewhere else. The editor was remembering an old snapshot of where everything sat (from a *previous* spacing) and quietly re-applying it over the new, correct arrangement. It now leaves painted rooms and roads where the map put them, the same way it already refuses to store a canvas position for a painted room in the first place.

Neither changed the world itself. One stopped a button from lying; the other stopped a saved memory from overwriting a fresh decision.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Commands]], [[Emotion & Mood — Whole-System Analysis]], [[Feature Ledger]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]]

<!-- connected:end -->
