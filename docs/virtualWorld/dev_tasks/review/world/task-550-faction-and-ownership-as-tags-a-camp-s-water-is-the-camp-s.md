---
type: task
status: review
area: world
priority: high
---

# task-550: Faction and ownership as tags: a camp's water is the camp's

**Filed:** 2026-09-27
**Related:** task-549

## Goal

Areas carry tags but no owner, so the goblin camp's single water source and waste disposal are a shared resource with no claimant. Make faction and ownership tag-based so using someone else's resource is an event.

## Measured (2026-09-27) — nobody owns anything

Areas carry `tags`, `cell`, `x`/`y`, `description`, `world_scope_id` and
per-faction description keys, but **no owner and no faction**. `goblin_camp` is a
*tag on a node*, not a claim on it.

That has a measured consequence. In the Kraktooth goblin camp:

- 84 areas, of which **one** carries a `RELIEF_TAGS` tag (`Waste Disposal`) and
  four carry a `DRINK_TAGS` tag (`Murk Lake`, `Raven River`, `Water Source`,
  `item_water_skin`).
- 23 goblins and 5 humans share that one `Water Source` and that one
  `Waste Disposal`.
- **4 of the 5 humans start in Eldenford** (the farmer starts at the neighbouring
  Abandoned Farm, the road guard on the Human Road) and **all 5 end up living in
  the goblin camp** after a 3-day run. That is emergent, not authored — and it is
  the clearest available evidence that resources have no claimant, because the
  only place that satisfies survival wins outright regardless of who is there.
- When a human drinks from the camp's water, **nothing is recorded at all**. There
  is no state for "someone took mine" and no event, so the situation is silent.

## Tag-based, as the author intends

Faction and ownership are both expressible as tags, which needs no new field and
no migration: a character carries its faction, an area carries the faction that
holds it, and "mine" is a comparison. A `civilization` tag already exists on
Eldenford and is currently doing nothing.

## Open decisions

1. Is ownership a tag on the area, or derived from the area's *scope*? The goblin
   camp is a WorldPainter scope (`deep_woods_2`, 21 `area_placements`), so
   ownership may be free — the scope already is a claim.
2. Is a road or a border area owned by nobody, or by both?
3. What happens on a contested use — an event, a vital, a relationship delta, or
   all three?

## Acceptance

- An area can name who holds it, and a character can tell whether a place is
  theirs.
- A non-owner using a held need-resource produces a recorded event, not silence.
- A test asserts the whole-cast ownership map, so an unowned shared resource is
  visible in a test failure rather than only in a dashboard.

## Related

- task-549 — the same tag idea applied to characters
- task-552 — fear, which is the reaction this is supposed to produce

## Progress — 2026-09-28 (vocabulary, decisions, camp data)

`engine/ownership.py` (new) plus `tools/claim_areas.py` (new, idempotent,
dry-run by default) and `tests/test_ownership.py` (28). The three open decisions
are answered, and each answer is pinned by a test that can actually fail.

### The vocabulary

Two symmetric, explicit tags. No new field, no migration, no schema change.

| side | tag | meaning |
|---|---|---|
| a character | `faction:<name>` | what it belongs to |
| an area | `held_by:<name>` | who holds it (one per holding faction) |

**The prefix is load-bearing, not decoration.** `goblin` on an area is already a
domain tag meaning "a goblin place", and `human` already means "a human place",
so an unprefixed faction vocabulary would make every claim ambiguous. Only
`held_by:goblin` is a claim; `tests/test_ownership.py::test_a_bare_tag_is_not_a_claim`
holds that line.

### Decision 1 — ownership is a tag, **not** derived from the scope

A scope is a containment construct (the task-397 / WorldPainter hierarchy) and
does not track who lives where. Decided, and the data supports it: the camp's own
scope `deep_woods_2` holds exactly the 21 `goblin_camp`-tagged areas, so on
today's data the two rules agree — and that is precisely why the test cannot
simply assert they agree. It forces them **apart** instead:

- Eldenford carries `held_by:human` and is **not** in the goblin scope. A
  scope-based derivation would have to place it somewhere; the tag says who holds
  it without asking where it is.
- Un-tagging `Water Source` (a scoped area) turns it into a commons, and
  `unowned_need_areas` reports it. Nothing about the scope puts it back.

### Decision 2 — an unheld area is a **commons**, not an error

The Murk Lake and the Raven River stay unclaimed on purpose: wild water nobody
would fence, and a commons is a real state a river should be in. A second
concept would be needed to say "held by both", and the tag is a *set* — so
`held_by:goblin` + `held_by:human` on one area is a shared, visibly contested
holding with no extra machinery.

This is why the acceptance invariant is **not** "every need-resource is owned"
(which would be wrong) but **"every need-resource is accounted for"**:

| need | claimed | declared commons |
|---|---|---|
| water | `Water Source` | `Murk Lake`, `Raven River` |
| food | `Cooking Area`, `Food Storage` | — |
| relief | `Waste Disposal` | — |

`KNOWN_COMMONS` in the test names the commons explicitly, so a **new** unclaimed
water area fails the test. That is the "visible in a test failure rather than
only in a dashboard" acceptance, applied to resources; the same discipline is
applied to the cast (`FACTION_ROSTER` / `UNAFFILIATED`).

### Decision 3 — a contested use records an event; it does not refuse and does not punish

`note_contested_use(player, area_node, need, gs)` writes the fact to the player's
`lived_log` (`why="ownership:use:<need>"`, `salient=True`) and to the game log.
Same reasoning as `engine/relief.py` (task-551), which measured that turning a
preference into a permission gate makes characters stop going and concentrates
them instead. Drinking the camp's water is **observed, not punished**: the
character still gets their Thirst, and "someone took mine" stops being silence.

Deliberately **not** in this task: a vital cost, and a relationship delta. The
former is the mistake task-551 already made once; the latter is task-552's fear
model and `engine/background_social.py`'s. Both are named here so they are
decisions rather than oversights.

**A bug this task found in its own first draft:** the rule "no matching holder
⇒ contested" also matches a character that declares **no** faction at all. Six
characters in the camp are exactly that case — the five wild animals and
`Croak-Mother`, the frog in Murk Lake — so the first version would have accused
all six of taking goblin water every time they drank. **Unknown is not the same
as foreign**: a character with no `faction:` returns `None`. That is why they
are listed as `UNAFFILIATED` rather than being given a token faction, and
`test_the_animals_were_never_accused_of_taking_the_camps_water` holds it.

### The camp data

`tools/claim_areas.py --write` stamped **39 tags**: `held_by:goblin` on the 21
`goblin_camp` areas (including `Water Source` and `Waste Disposal` — the two the
task names), `held_by:human` on Eldenford, `faction:goblin` on 10 goblins and
`faction:human` on 7 humans (5 Eldenford residents, `Leslie` the captive, and the
player character). Both halves come from one table, because a claim whose
membership nobody carries is half a claim, and the two drifting apart is the
failure this task is about. Re-running reports 0.

### Still open — and it is not a data task

**`engine/background_simulation.py` is WT-C's file, so the call site is not
wired here.** `note_contested_use` is implemented and tested, but nothing calls
it yet, so a human drinking the camp's water is still silent at run time. The
hook is three lines, at the two places a background character satisfies a need
from the area it stands in — `_in_water_area(p)` (line 342) and
`_consume_here(p, FOOD_TAGS, "eat")` (line 390):

```python
from engine.ownership import note_contested_use

# after the vital is restored, before the log line
note_contested_use(
    p,
    self.gs.graph.get_node(self._resolve_area_id(p.current_area)),
    "drink",           # or "eat" / "relief" / "hygiene"
    self.gs,
)
```

Nothing about the call is conditional: `note_contested_use` returns `None` for an
owner, for a commons, and for a factionless character, so it can be made
unconditional at every site without gating anything. **Posted to the board for
WT-C.**
