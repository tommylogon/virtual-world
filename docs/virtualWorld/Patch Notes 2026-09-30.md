---
type: doc
tags: [surface/docs]
---

**Written to be read cold by anyone who has never seen this project.** No code, no
file names, no jargon. If you know nothing about how VirtualWorld works, you can
still read all of this.

A companion technical version — the same work, described the way a programmer
would write it — is in `CHANGELOG.md` under *A Painted World You Can Walk Around
In*. This one is the same news told differently.

---

## The short version

The last update was about the game learning to notice things. This one is about
the **map** — about painting a place in and then being able to live in it.

Before this, if you painted a tavern on your map, what you got was a box with a
picture in it. You could not say what was *inside* the tavern, because there was no
way to say. There was no word for a corridor, no word for a cellar, no word for
the stairs between two floors. If you drew a whole town, you got a hundred boxes
and no inn to sleep in, no kitchen to cook in, and no garden.

You also could not say how warm or how cold a place was, because nothing outside
read the weather at all — it was a pretty sky and a colour on the horizon. A
character who was tired lay down in the road, because the idea of "there is a bed
in that building over there" simply did not exist in the game.

All of that is now here.

## You can draw a floor plan

The big one. There are **fifty-three named rooms** you can paint, from a
corridor to a parlour to a buttery, a crypt, a hayloft, an animal pen, a counting
house, a bath, a dungeon, a dovecote's neighbour and everything between. They are
grouped in the dropdown by what they are *for*, because the question you are
asking when you draw a plan is not "which of a hundred words" but "where does
somebody sleep, where do they cook, where do they go to the privy".

Draw a corridor that runs the length of your inn, with a tap room off it, a
kitchen, two bedrooms and a latrine, and stairs between floors. All of it
compiles. If you spell something wrong, the game tells you which cell and what it
expected — it does not quietly turn your ballroom into a barn.

**Stairs work however you draw them.** If you paint the floor layer going up, the
stairs are stairs. If you would rather say "this cell is a stair" in a house where
the floors are all the same number — a loft stair, a step down to a cellar — there
is a stairway you can paint, and it makes the same kind of way. Either way a
character can say "go up the stairs" and it works.

## A painted building can bring its own inside

Thirty different building types now have a floor plan drawn for them, and one more
for anything that does not — so **every** building you can paint has an interior.
Paint a tavern and it gets a tap room, a kitchen, a cellar and a dormitory. Paint a
mill and it gets a mill room and a grain store. Paint an apartment block and the
same plan is stacked three storeys high.

And then you change it, because it is a **starting point, not a rule**. Paint a
room where you want one, delete a room you do not, and the compiler works from
what you painted. The game remembers which cells you touched, so re-running the
generator fills in the cells you never looked at and leaves your changes alone.

## You can put a road out of your own place

This is the one that changed the most, if you are the person who was fighting it.

You could already place one of your own hand-written areas onto the painted map.
It just sat there. You could walk up to it and nothing happened, because the
compiler never saw it — the cell it was standing on was reserved, so the compiler
did not treat it as part of the map, and there was no way out of it and no way in.
You could not even put a feature on the same cell; the game would accept it and
then quietly do nothing.

Now a placed area gets a **way out to every painted cell that touches it** — a
road above, a road below, a wood to the east, each with a proper name and a
direction a character can say. And the ways it mints are a **first draft**. Open
the cell and you see each one listed with a ✕. Delete the one you do not want, and
it stays deleted: re-running the generator will not bring it back, because the
game records that you did that on purpose, and offers a ↺ beside it to change
your mind.

If a building and a feature really do need to share a cell, you can now say so
explicitly, and the building's own area becomes the **doorstep** the gateway opens
from — which is the shape most real inns and gatehouses have anyway.

## Weather that touches the ground

There is a new layer you can paint: **climate**. Five kinds — arctic, alpine,
temperate, arid, tropical — each drawn in its own colour with its average
temperature written on it, so you paint a cold blue across the north of your map
and a hot one in the south. When the world is generated, each place takes the
climate most of its cells were painted, and a cliff face six storeys high is no
longer a step you can stroll up — it is refused, in words, unless someone has cut
a **road** across it. Paint the road and it opens.

And the sky now knows what time of year it is. It always did, in a sense — the
month was right there — but the game engine never asked, and the weather widget
kept its own private copy of the calendar. There is one calendar now, in one
place. When the season turns, the world says so: *Winter arrives.*

The deliberate part: **if you have not painted a climate, nothing changes.** Every
existing world still reads the same temperature it always did, in every season.
A world that has never chosen a climate is a world that has not got one, and the
game will not invent it.

## The painter grew a proper tool rail

Eight tools down the left-hand side now, each with a key, with the active one
showing. The two that are new:

- **Select** — click cells, shift-click for more, drag a rubber band over a block
  of them, or select the lot. And the useful part: **with cells selected, painting
  or erasing hits all of them at once**, in one go you can undo in one step.
- **Move** — arrow keys shift whatever is in the selected cells one square
  sideways, and the cell it came from is properly emptied. A road that moves is a
  road that moved, not a road that was copied.

## The world is one list, in one place

The scope tree used to be at the bottom of the graph view, the outline of the
world was down the left side, and you could pick a region of the world from two
different dropdowns. It is now **one list, in the left panel**: the whole world,
then each region under it, then the rooms in each region. Click a region and the
graph loads it.

An unbuilt region says **"🖌 Paint"** next to it, which opens that region in the
painter — because the previous version of this problem was that the game would
tell you a region was empty in one window and expect you to know which button in a
different window fixed it.

## The map tells you where places are

The map view was drawing every place as an anonymous dot. Now it draws **names**,
because the pitch the auto-layout aims for roughly doubled. A small map gets big
comfortable boxes; a very large map still gets dots, because at that size names
would be a wall of text — but the middle, which is where most worlds live, gets
readable labels.

Long labels on connections wrap instead of running off into the next county, and
the "this key unlocks that door" arrows now show three lines of their text rather
than a whole paragraph stretched across your map.

## And 1,383 new things to find

The item library has more than tripled, from 532 to **1,915**.

Mostly the things a medieval person would actually have handled: fifty-one
vegetables, sixty-four herbs including nine that will quietly damage you if you
misread them, dried beans and lentils and chickpeas, a shelf of seeds, nineteen
edible mushrooms **and two that will kill you**, a larder of preserves and jams and
cheeses, thirty-odd kinds of fish, and the tools of twenty-one trades — a scythe, a
billhook, a cooper's sun for bending barrel staves, a millstone, a fulling rock
for shrinking cloth, a bow drill, a bee smoker.

Then the household: bowls and plates and jars, a mortar and pestle, a churn, a
cheese press, rushlights, a warming pan, bed curtains, a linen press, a clothes
chest, a settle by the fire. And the town: milestones, a toll gate, a stile, a
water butt, a market cross worn hollow by three hundred years of standing, a
dovecote, a guildhall.

They are not filler. The one about a hay bale had a bug in it — it was set to
weigh a stone because a helper rounded its weight off — and the test that holds
the library against the generator found it. **A thing you can find in the world
should be the thing somebody decided it was**, and now there is a check that says
so every time the tests run.

---

## Two things you should know

**Your saved Kraktooth campaign was overwritten by the app at 20:28 on 29
September.** The file `data/scenarios/kraktooth_goblin_camp.json` lost its `name`
and the twenty-three character entries that let a character load as one node
instead of two. The good version is still in git history, and this update
deliberately does **not** include the damaged one. If you want it back:

```
git checkout -- data/scenarios/kraktooth_goblin_camp.json
```

**Your own uncommitted change to `vital_rates.py` fails a test.** The file now sets
`SOCIAL_COMPANY_GAIN` to 0.030 while `test_decay_rate_bake.py` still insists it
must not exceed the 0.020 baseline. The history comment above that line argues
for 0.030 with a measurement, and it mentions "need-travel herding toward shared
service areas" — which is the change in this update, so the measurement and the
assertion are now on opposite sides. That is your call to settle, not ours.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Emotion & Mood — Whole-System Analysis]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]], [[Patch Notes 2026-09-28]], [[Patch Notes 2026-10-03]]

<!-- connected:end -->
