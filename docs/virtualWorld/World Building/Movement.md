---
type: doc
tags: [system/world, surface/in-game]
---

# Movement

Movement is the *act* of getting from one area to another. Everything you pass
through is a [[Ways|way]] — a door, an arch, a ladder, a forest path; there are
no direct area-to-area links. This page is about crossing one: the verbs that do
it, what can stop you, and what you bring to the crossing. For the way *itself*
— its states, its properties, its light and sound — read [[Ways]].

## The verbs

Every crossing is one action. Which verb you use is a choice about *how* you
cross, not *whether*.

| verb | aliases | what it does |
|---|---|---|
| `go` | `move`, `walk` | cross a way into the next area |
| `dash` | — | sprint: one `go` now, plus a free second `go` in the same turn |
| `crawl` | — | cross a way that requires crawling (crawl-only ways auto-crawl on a plain `go`) |
| `climb` | — | cross a climbable way; risks an Athletics check |
| `jump` | — | leap a gap; risks an Athletics check |
| `approach` | `approach to` | walk up to a way, item or person and **stop** — never crosses |

`go`, `dash`, `crawl`, `climb` and `jump` are **major** actions — one per turn.
`approach` is **minor** (`engine/action_tiers.py`), because positioning is not
the action; it is what you do just before one.

## What you see

A plain crossing reads as a movement line, the way you went, and where you
landed:

```
You head through the north. — you're in the Kitchen.
```

That is the literal output, period and dash and all (`You head through the
north. — you're in …`). The verb sets the first half: `You climb through the …`,
`You leap across the …`, `You drop to your hands and knees and crawl through the
…`. An authored `pass_message` on the way replaces the whole line with a bespoke
one. A door with `auto_close` adds `The north door swings shut behind you.`

`approach` never crosses, and says so (one line in the game; wrapped here to
read):

```
You walk over to the north door and stop, right at it. (use "go north" or "go Kitchen" to walk through the way to the other side.)
```

A character who is blind gets a stumble line instead of a clean crossing:

```
You stumble blindly in the dark and fall — you're now prone. Get back up with
'stand' before moving on. A cane or a guide would help.
```

## Crossing a way

Whether a way lets you through is its `current_state` — see [[Ways]] for the
full model. The movement-side lines are:

- **`locked`** — `The north is locked. You need to unlock it first.`
- **`blocked`** — `The north is blocked. There's no way through.`
- **`closed`** — walking through normally auto-opens it and you pass. Two things
  override that:
  - `needs_open` — the door takes an effort check (`Athletics DC 10` by default;
    the inspector calls it "Needs skill check to open"). Fail and you get
    `The north requires effort to open. (Athletics DC 10: roll 7)`.
  - a `requires_open` trigger — conditions on the door that bar it until met,
    failing with its own message or `The north is barred. Something prevents it
    from opening.`
- **`refusal_message`** — if an author has set this, it is what the way says
  instead of letting you through, *whatever* the state, until the way is truly
  `open`. It is how a themed door replaces the generic "the door is locked".
- **one-way** — `The north is one-way — you can't go back that way.`

Ways also carry requirements on the *crossing*:

- **`requires: crawl | climb | jump`** — a plain `go` auto-converts to a crawl
  on a crawl-only way, but a climb or jump way demands the matching verb:
  `You need to climb through the north.` A climb/jump failure fires the way's
  `on_fail_climb` / `on_fail_jump` triggers and stops you.
- **`max_size`** — a way too small for you refuses: `You don't fit through the
  north.` A tight fit forces a crawl (`You can't climb through the north — it's
  too tight.`).
- **`requires_item`** — an item name or a `tag:fly`-style tag gate; without it,
  the way refuses with its own message. A parked bike in the room counts.
- **incorporeal** characters (ghosts, task-309) ignore all of it — locked,
  blocked, closed, one-way, item-gated, skill-gated passage is meaningless to
  them.

## What you bring to the crossing

The way decides if it *can* open; you decide if *you* can get through.

- **Size.** Greater than the way's `max_size` and you do not fit; one tier over
  and the only way through is a crawl.
- **Load.** Carry over half your capacity and you count as one size larger — a
  heavy pack is bulk through a narrow gap. At **80%** you cannot `dash` at all
  (`You're too heavily encumbered to sprint.`); at **100%** you cannot move.
- **Conditions.** `prone` allows only a crawl; `grappled` and `restrained` stop
  you entirely (`Try to escape first.`); `suffocating` and `petrified` are hard
  gates; an exhausted character (effective speed ≤ 0) cannot move.
- **Fear.** A `frightened` character will not re-use a feared passage, will not
  re-enter a feared area, and will not walk into an area where a feared
  character is standing.
- **Blindness.** A blind character's plain `go` is a gamble: `1d20 + Perception`
  against **DC 12**, and a failure drops them **prone**. A `sensory_aid` item —
  a cane — adds its bonus (default 2) and steadies the step; climb and jump get
  a **+4** DC instead, reduced by the same cane. Led characters do not
  self-move; the cooperative grab-and-drag is their path.

## Dash: two `go`s in one turn

`dash` is the interesting one. It performs one sprint hop, and the turn then
offers a single follow-up `go` — a second destination — so a dash crosses **two
areas before the turn ends**. An agent takes that follow-up as a chained action
for free; a human composing their turn simply takes the next step in the same
panel. Either way it is the move you run with: through the way and into the next
area while everyone else is still deciding.

It is not free movement. You cannot dash while winded (effective speed below
0.5), and heavy encumbrance (80–100%) blocks it outright. It carries a **+4
energy** sprint surcharge over the normal crossing.

> **The chain is general, not dash-only.** `grab` offers an
> `approach`/`release` follow-up, and `lead` offers `go`/`approach`/`release`.
> A follow-up is exactly **one** action — the old `movement.py` comment that a
> dash "can cross several rooms in one turn" overstated it (now fixed); it is
> two areas, because dash's allowed follow-ups are `go` and `wait` only.

## Moving as a group

When a character who is **grappling** someone moves, the grappled target is
**dragged along** unless they resist with a save — they do not get to stand
still while you walk off with them. A character who is *themselves* grappled
cannot move at all until they escape. `lead` is the cooperative version: you
guide a willing target, and the lead hands you a follow-up to keep walking.

All of this happens inside one `go`; the drag line is appended to the crossing.

## Cost

A crossing costs:

- the way's authored **`cost`**, applied as-is;
- plus an **encumbrance** tier: `+1` energy at 50–80% capacity, `+2` at 80–100%;
- plus **settled snow** depth at the destination (task-556);
- plus the **`+4`** sprint surcharge on a `dash`.

Ghosts pay none of it.

> **Traversal has no time cost.** Crossing a way costs energy, never game time
> — the clock advances on turn boundaries, not per action, so `crawl`, `climb`
> and `jump` do **not** scale the cost. The verbs differ by the *check*, not the
> energy. (`crawl_to_area`'s old "(2× time)" docstring was wrong and is gone.)

## Facing

Crossing a way is the **only** thing that changes which way a character faces —
there is no turn-in-place verb, so standing still, examining and talking all
leave facing alone. The cardinal comes off the connection edge (the authored
heading), not the word you typed, because the word may be narrative ("through
the swinging door"). An off-ring heading — a diagonal, a vertical way — leaves
facing untouched rather than inventing a direction nobody travelled.

## See also

- [[Ways]] — the passage objects: states, properties, light and sound.
- [[Way Properties]] — every key a way can carry and which code reads it.
- [[Connections]] — the graph architecture (`area → way → area`). **Partly
  stale** — read it for the architecture, not the state model.
- [[Gameplay/Character Spatial Position]] — being *at* a thing versus crossing
  past it, and how witnesses see a crossing.
- [[Rooms & Areas]] — what is on the far side.
- [[Per-Agent Knowledge (Fog of War)]] - what a character learns by walking,
  looking down a corridor, or being told a direction.
- [[Commands]] — the verb index: every command and its aliases, and where each one is documented.

## Where it lives

- `engine/action_tiers.py` (major/minor action classification: `go`, `dash`, `crawl`, `climb`, `jump` = major; `approach` = minor)
- `engine/movement.py` (movement logic, `crawl_to_area`, follow-up chaining)
- `engine/character_spatial.py` (`approach_character`)
- `engine/fear.py` (fear-gated movement: feared passages/areas/characters)
- `engine/combat.py` (grapple drag-along on movement)
- `engine/equipment.py` (encumbrance tiers: 50%, 80%, 100% capacity effects on movement/dash)
- `data/library/` (way properties: `requires`, `max_size`, `requires_item`, `cost`, `auto_close`, `pass_message`, `refusal_message`, `needs_open`, `one_way`)
- `templates/index.html` (movement verb handling in command system)

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[move|Move]] (#3), [[open-close|Open / close]] (#4), [[traversal-abilities|Traversal abilities]] (#38)

**Neighbouring notes** — [[Connections]], [[Generated Scenario Review (2026-08)]], [[Graph System]], [[Grid to Graph]], [[Millbrook Falls Town Map]], [[Rooms & Areas]]

<!-- connected:end -->
