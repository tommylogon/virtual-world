---
type: doc
tags: [system/world, surface/in-game, topic/authoring]
---

# Ways

A **way** is everything you can move through to get from one area to another: a
door, an arch, a portal, an elevator, a ladder, a stairway, a forest path, a
crack in a cliff face. If you want to go from A to B, you use a way. All
traversal in VirtualWorld is a way — there are no direct area-to-area links.

On the graph a way is a node joined to the two areas it connects. Its node type
is `way`.

For the exact property keys and which code reads each one, see
[[Way Properties]]. This page is the *why* behind them.

## Name and appearance

A way carries two descriptive fields, and they do different jobs.

- **`name`** is what *you*, the author, call it — "stairway", "ladder", "crack
  in the rock face". It exists so you can find it in the editor and the graph.
  It is also a label commands can match against (the matcher resolves names and
  aliases to the node's id), but it is not the way's identity: identity is the
  id, and renaming a way never changes what it connects.
- **`description`** is what the way *looks like*: what a character reads when
  they look at it, and what the room lists as the exit while the way is solid.
  A closed way reads as `[direction] <description> It is currently closed.` The
  glance text never leaks whether the shut door is merely shut, locked or
  blocked — that is what examining it is for.

The view *through* an open way is a separate field per side; see
[Seeing to the other side](#seeing-to-the-other-side).

## States

A way's `current_state` decides whether it lets you through. The inspector
offers six states:

| state | you can pass? | what it means |
|---|---|---|
| `open` | yes | passable |
| `closed` | no, until opened | shut but not secured; walking through auto-opens it |
| `locked` | no | secured; must be unlocked first |
| `blocked` | no | something is in the way |
| `broken` | see note | the way is ruined |
| `hidden` | depends | not shown in the exit list until found |

A state the engine does not recognise — or a missing one — is treated as
**`open`**. That default is deliberate (a typo should not wall off a room), but
it means a typo in `current_state` fails *open*, not closed.

> **`broken` is half-implemented.** It is a real state, and `open` / `close`
> correctly refuse it (`You can't — it's broken`). But the *passage* check does
> not test for `broken`, and the light/sound tables fold it to `open`, so a
> broken way can still be walked through and passes light and sound as if it were
> open. Until that is reconciled, use `blocked` for a way nobody should pass, and
> describe the damage in `description`.

### `see_through` is a property

`see_through` is a boolean on the way. It answers "does this let sight and light through",
while `current_state` answers "does this let you through". A window is

```
current_state: closed
see_through: true
```

Open that window and it is `open` + `see_through: true`; close it and it is back
to `closed` + `see_through: true`. Under the hood the two combine into
one value for the light and sound tables (a `see_through` way is indexed as
`see_through`), and that is the only sense in which the word appears in the state ladder.

### Blocked and locked are the author's distinction

The engine gives you both states and the same result — no passage — but they
mean different things, and your players and agents will read the difference.

- **`blocked`** is an *obstacle at the way*. A fallen tree, a thorn bush wedged
  in the cave mouth, rubble. It clears when someone moves or destroys the thing
  in the way. Tag the obstacle and put the clearing action on it.
- **`locked`** is a *lock*. A key, a code, a lever elsewhere, a spell. It opens
  when the right thing is applied to it.

Neither is built into the engine as a rule — both are states you change with
triggers. `unlock_way` changes a way from `locked` to `closed` (it does not open
it; the door then auto-opens when walked through). To clear a block, put the
removal action on the item that is the obstacle and have it set the state to
`closed` or `open`. The `lock` / `unlock` verbs exist so a character can attempt
the obvious action; whether it succeeds is your trigger's business.

## What a character sees

The room lists every way a character can perceive, with its direction-as-written,
what is visible through it, and the verbs that currently apply. A sample from a
wintry exterior:

```
From where you stand, you can see the following paths:
  To the ice bridge, the Frozen Stream Crossing is visible beyond (trickling
    water and wind audible, cool). (you can go through it, approach it, dash,
    examine or close it)
  [icy arch] is clear — ahead the Snowbound Hollow appears as a dim, sheltered
    hollow beneath a lattice of icy branches. (you can go through it, approach
    it, dash, examine or close it)
  [rocky slope] is open — Glancing back through the gap, you glimpse the
    bowl-shaped clearing, the old stone well silent in the center. (you can go
    through it, approach it, dash, examine or close it)
```

Two details worth knowing:

- **`is clear` versus `is open`.** An open way under open sky reads *is clear*;
  one with a roof or a frame over it reads *is open*. Same state, different word.
  What decides it is the **way's own** `tags`: if they include `outdoor` or
  `exterior` (`engine/area_tags.py:OPEN_SKY_TAGS`), the word is *is clear*,
  otherwise *is open*.
- **The verb list changes with the state.** An open or see-through way offers
  `go through it, approach it, dash, examine or close it`; a closed one offers
  `... dash, or open it` instead, because closing what is already shut is not a
  thing you can do.

A hidden way simply is not in this list until it is found. Finding one is the
`fumble_around` action: a Perception check (DC 12) rolled **with disadvantage**,
and on success the way joins that character's `discovered_exits` and its state
is set to `locked` — you find it shut, not open. A guiding cane (an item tagged
`sensory_aid`, e.g. a white cane) adds its `sensory_bonus`, default 2, to the
roll: this is a *tactile* search, so the tool for feeling your way helps, and
carrying two aids stacks. A character with the slasher trait sees hidden ways
without searching.

**A fumble costs 1 HP.** Disadvantage means the *lower* of two d20 comes up 1 —
at least one die showing a 1, roughly a one-in-ten chance — and the character
bangs their shin on something in the dark for 1 non-lethal damage. It fires
whether or not anything was hidden, and the action has already cost 2 time and 3
energy. The whole search is skipped when the character can see in the dark or the
area is lit (ambient light above 40); a blind character must always fumble.

## What a character knows — and what they only think they know

The room never tells a character the raw state of a solid way. It tells them what
they have *discovered*. Learning happens by running into the thing: a refused
move or a failed open calls `movement._learn_way_aspect(...)`, which records the
aspect on the **Player**, not on the way:

```
Player.known_way_aspects[(area, direction)] = {"locked", "blocked", "needs_force", ...}
```

The three aspects that drive the display are `locked`, `blocked` and
`needs_force`. On the next look, `scene_snapshot` resolves them per character and
the exit carries `known_locked` / `known_blocked` / `needs_force_known`; the agent
prompt renders those as `(it's locked — you'd need to unlock it first)` or
`(you can force it open)`. Until a character has tried, none of it is shown — a
shut door reads as a shut door to everyone. Knowledge is per-character, and the
way's true state is never leaked.

## Passing through

By default, walking through a way says one line and then gives you the new
area's description. The line depends on how you crossed:

| verb | default line |
|---|---|
| `go` | `You head through the {direction}.` |
| `crawl` | `You drop to your hands and knees and crawl through the {direction}.` |
| `climb` | `You climb through the {direction}.` |
| `jump` | `You leap across the {direction}.` |

The destination is then appended (` — you're in {Area}.`), so the character
always knows where they landed.

To write your own, set **`pass_message`** on the way. It replaces the first part
only, so `"You slip between the sharp, jagged rocks of the cave opening and
enter"` reads as `You slip between the sharp, jagged rocks of the cave opening
and enter — you're in Frozen Stream Crossing.`

The WorldPainter sets a `pass_message` per painted **kind**, so a path does not
read like a door:

| painted cell | the compiled line |
|---|---|
| road / path | `You follow the path {direction} toward {to_name}.` |
| door | `You go through the door into {to_name}.` |
| stairs | `You climb {n} storeys to {to_name}.` (or `You take the stairs to {to_name}.`) |
| a scope gateway | `You pass between {parent} and {entry}.` |
| a building entrance | `You step inside the {subject}.` |

Only a cell the author painted as a `door` says "door".

## Behaviours that change how a way works

These are the options in the way's inspector, mostly under Behaviour. Each is
independent — any combination is valid.

- **`one_way`** — a character can cross but not come back. The reverse traverse
  is refused. Use it for an opening that crumbles behind you, a chute, a
  one-way portal.
- **`see_through`** — the way does not let you through, but it does not stop
  sight or light either. A window, a glass door, a portcullis, a fence. It is
  independent of `current_state`, so `closed` + `see_through` is a shut window
  and `open` + `see_through` is a glass door held open.
- **`auto_close`** — the way closes behind whoever passes through (and fires its
  `on_close` triggers). An automatic door, a trap that seals, a sci-fi iris.
- **`needs_open`** — the way is shut and opening it takes a roll:
  `{ enabled, skill, dc }` (skill defaults to Athletics; the engine's DC fallback
  is 10, but the inspector's checkbox saves 15 by default — see below). On
  success it opens itself and fires `on_open`. This is the inspector's
  **"🔒 Needs skill check to open"** checkbox, and the jammed door you *can*
  force, dice permitting.

  Two different skill checks exist and they are not the same:
  `needs_open` gates **getting a closed way open** (Athletics, DC 10 by default);
  `requires: climb` / `requires: jump` roll against `{requires}_dc`
  (**default 12**) to get *across* a way. A way can have either, both, or neither.
- **`prevent_close`** — nobody can close it. A road, a cave mouth, an archway,
  a trail. Use it so characters and agents stop attempting an impossible action.
  A way authored with `requires: crawl` / `climb` / `jump` is uncloseable anyway,
  without needing this.
- **`requires: jump`** — the way can only be crossed with the **`jump`**
  command; `go` is refused (`You need to jump through the {direction}.`). The
  character rolls Athletics against `jump_dc` (default 12). On failure the way's
  **`on_fail_jump`** trigger fires — fall damage, a teleport into a spike pit,
  whatever you author. Nothing is hardcoded: no trigger, no consequence.
- **`requires: climb`** — as above with the **`climb`** command and
  **`on_fail_climb`**, against `climb_dc` (default 12). For cliffs, ladders,
  shafts.

`go`, `crawl`, `climb` and `jump` are all movement commands. A way with
`requires: jump` *demands* `jump`; a way with no requirement still accepts
`jump` or `climb` as flavour — `jump across the gap` works either way, and reads
as `You leap across the gap.`
- **`max_size`** — the largest body that passes. Tiers are `tiny`, `small`,
  `normal`, `huge`, `giant`, `titanic`; empty or `none` means no limit. One tier
  over and the character **crawls** through; two or more tiers over and they do
  not fit. So a `tiny` mouse hole stops the frost giant but a normal person
  drops to hands and knees and follows — and a character carrying half their
  capacity or more counts as one tier larger (task-202), which is how a loaded
  character gets locked out of a gap they walked through empty.
- **`sound_barrier`** — a per-way multiplier on how much sound crosses, applied
  while the way is solid. Blank means the engine default for its state.
- **`insulation`** — a multiplier on heat transfer across the way, default 1.0.
  A thick curtain or a shut door is how a cold room stays cold.
- **`cost`** — the traversal drain, authored as `{"energy": N}`. It is passed to
  the action system on every crossing, and ghosts and the dead are exempt. `time`
  is a legacy key with no effect (the clock advances once per turn for everyone,
  never per action), and the energy drain itself belongs to the still-planned
  stateful-action cost system. Encumbrance and deep snow add energy on top.
- **`requires_item`** — the way needs gear to cross: a name or id (`bike`), or a
  tag gate (`tag:rope`). Comma-separate several. The agent is told the
  requirement rather than left to fail silently (` (needs: the rope)`).
  **Engine-only** — it is not on the way inspector, so it is authored in JSON,
  in the library, or by the compiler.
- **`refusal_message`** — a themed line shown *instead of* letting you through,
  and it holds until the way is actually `open`. It is checked before the state
  machine, so a themed refusal replaces the generic `the door is locked` without
  every closed way in the game needing to be re-authored. `blocked_description`
  falls back to it. **Engine-only** — not on the inspector.

## Putting a way into the world

Three routes, all equivalent in the end:

1. **Build → Way**, and fill the form.
2. **Build → Library → Ways**, and import one that fits. (A library way is a
   saved way node; importing copies its properties.)
3. **Ask the NL editor.** "Can you make a wooden door that screeches when you
   enter the dungeon cells from the dungeon hallway" gives you a first draft to
   work from.

Once it exists, the inspector's **Reconnect Ways** tool re-wires a way to
different areas — pick the two areas and reconnect — which is the fix when a
way points at the wrong place. The **library sync** tools at the bottom of the
inspector (common to every node type) push the way back to the library or pull
the library version down.

## Finding your way: directions and cardinals

A way's **direction** is what a character types and what the room lists. It can
be anything: `north`, `up the ladder`, `enter the house`, `kitchen door`. The
command is `go` — `go north`, `go up the ladder`, `go kitchen door`. The same
direction string works from either side, so a door named "kitchen door" can be
crossed by that name from the dining room *or* from the kitchen.

You do not have to match the direction exactly. `resolve_exit` tries, in order:

1. exact handle;
2. relative facing — `left` / `right` / `forward` / `back`, resolved against the
   character's heading into a cardinal (these *alias* this area's directions,
   they do not replace them, so the room keeps the name of the way you can see);
3. a cardinal;
4. word-boundary substring;
5. the way's node name, or the target area's name;
6. words in the way's description;
7. the way's state word;
8. fuzzy (edit-distance) match.

So `north`, `n`, `front door`, `front`, `door`, `the circular door with the
keycard slot`, or the name of the area it leads to all land. Where several ways
match, the first wins.

If a direction is a **cardinal** (`north`, `northeast` …), it also drives the
compass layout and relative facing (left / right / forward / back). The
inspector shows a cardinal button pad; clicking one sets that side's cardinal
and the UI offers the opposite cardinal for the other side, so a two-way door is
laid out once rather than twice. You can have both a narrative direction *and* a
cardinal — the compass works even when the typed direction is prose.

A way that reads better as an instruction than as a bearing can carry an
**`entry_phrase`**: the room then lists it as `You could go down the tunnel.`
rather than as another compass exit. It is a **display phrasing only** — the
way's `direction` and `aliases` still do the matching, so `go in` and `enter the
tavern` both resolve. A scope gateway sets it (`You enter the tavern.`) while
keeping its `direction` (`enter`), which is why the phrase exists rather than
being folded into the direction.

### Seeing to the other side

What a character sees *through* a way is authored per side, on the connection
from the area to the way — not once on the way itself. From the hall you might
write *"from the dungeon hall you can see rows of cells on the other side of the
wooden door"*; from the cells, *"you see the hallway lit by torches until it
reaches the stairs on the far end"*. That text is shown when the way is open, or
at any time if it is `see_through` — which is how a closed window still shows
you the garden. If you leave it blank, the engine may still generate a
peek-through from the far room's light, noise and temperature; a `see_through`
way suppresses that auto-text so your own line is what shows.

## Tags and aliases

- **`tags`** are objective facts about the way — `tight space`, `natural`,
  `stinky`, `secret`. They are how conditions, triggers and wandering NPCs query
  it (e.g. a `tight_space` tag feeding a claustrophobia condition). They do not
  affect traversal by themselves.
- **`aliases`** are other names a command can match. When old Crankerson tells
  you to find "that stinking sinkhole" and the way is officially `sinkhole 1`,
  the alias is what makes `go stinking sinkhole` work.

## Way triggers

Ways fire triggers that items and areas do not. The trigger names are:

| trigger | fired when | typical use |
|---|---|---|
| `on_open` | the way becomes open | reveal text, ambient effect, logging |
| `on_close` | the way becomes closed | a trap sealing the room |
| `on_enter` | someone passes through | auto-close, damage, teleport |
| `on_fail_climb` | a `climb` roll fails | falling, losing grip |
| `on_fail_jump` | a `jump` roll fails | slipping into the gap |
| `requires_open` | a shut way is attempted | a condition that *blocks* opening it |

Triggers are `logic_trigger` nodes linked to the way. `requires_open` is the
special one: it gates *whether a shut way can open at all*, which is how you get
a barricade, a magical seal, or a door that a character must do something else to
unlock.

## Light, heat and sound

An open way spills what is on the other side; the state decides how much. Two
ladders, both running from least to most obstructive. The row the engine uses is
`see_through` whenever the way's `see_through` property is set, *whatever* its
state:

| state | sound cost | light passed |
|---|---|---|
| `open` | 0.5 | 100% |
| `see_through` (the property) | 0.75 | 75% |
| `closed` | 1.0 | 25% |
| `locked` | 1.0 | 10% |
| `blocked` | 1.0 | 0% |
| `hidden` | 2.0 | 0% |
| (`broken`) | 0.5 | 100% — it folds to `open` |

So an open door passes light fully and most sound; a shut door leaks a little
light around the frame and muffles sound; a window (`see_through`) passes three
quarters of the light even though you cannot walk through it. Heat uses the same
idea, scaled by `insulation`. Both tables are overridable live in Engine Config
(`sound.way_*`, `light.way_*`).

A window (or any `see_through` way) lights the far room to
`max(own_light, neighbour_light × 0.5 × transmission)` — the spill is the
neighbour's light, halved (`light.spill_factor`, default 0.5) and scaled by the
way's light transmission for its state or property (`open` 1.0, `see_through`
0.75, `closed` 0.25, …). So a bright room behind a window makes a dark one at
least three-eighths as bright.

## Design patterns and edge cases

- **Distance is chained areas, not way length.** Every `go` through a way costs
  one action, so a passage made of N segments takes N turns with no extra engine
  logic: `Tunnel Entrance → Inside Tunnel → Tunnel Exit`. Each midpoint is a real
  area — its own description, environment, size tags, light spill and map
  position — so keep them meaningful (landings, bends, rooms-within-tunnels)
  rather than every few metres.
- **A way is one node shared by both sides.** `room1 → way` and `room2 → way`
  reach the same way with different direction labels, and its state is shared;
  opening it from one side opens it for both.
- **One way per direction per room.** Direction matching finds the first match,
  so a second way on the same direction is not addressable by that direction.
- **A way that points nowhere** raises `The {direction} leads nowhere.` when
  crossed.
- **Node ids** are `way_<area>_<direction>`, lowercased
  (`NodeIDHelper.way_node_id("Kitchen", "west")` → `way_kitchen_west`). Older
  saves and some prose still say `door_…`; the `door_` prefix is legacy.

## See also

- [[Way Properties]] — every key a way can carry, its values, and which code
  reads it.
- [[Connections]] — the graph architecture (`area → way → area`), node
  ids, unlocking via triggers, the inspector, and graph colours. **Partly
  stale:** it still calls the node type `door` and lists the older state set
  (with `see_through` as a state and `broken` in a colour table). Read it for the
  architecture, not for the state model.
- [[Grid to Graph]] — how the WorldPainter compiles painted cells into ways, and
  why a painted door arrives with a `pass_message` and `see_through` set.
- [[Rooms & Areas]] — what is on the far side of a way.
- [[Gameplay/Character Spatial Position]] — walking *at* a way versus through it,
  and how witnesses see it.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[way-authoring|Way authoring]] (#51)

**Dev tasks** — [[dev_tasks/inprogress/refactor/task-446-id-first-node-identity|task]], [[dev_tasks/todo/docs/task-781-way-properties-py-omits-entry-phrase-and-requires-item-and-check-does-not-validate-values|task]], [[dev_tasks/todo/ui/task-780-expose-requires-item-refusal-message-and-entry-phrase-in-the-way-inspector|task]], [[dev_tasks/todo/world/bug-547-broken-way-state-is-half-implemented|bug]]

**Neighbouring notes** — [[Connections]], [[Generated Scenario Review (2026-08)]], [[Graph System]], [[Grid to Graph]], [[Millbrook Falls Town Map]], [[Movement]]

<!-- connected:end -->
