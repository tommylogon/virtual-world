---
group: Characters
status: done
---
# Pack Logic for Simple NPCs

**Filed**: 2026-08-19
**Priority**: Low
**Status**: Idea

---

## Idea

Pack logic for simple NPCs so multiple of the same type can coordinate together via code. Examples: rats, wolves, and other such animals. the idea is that they can hear or smell others of their kind over larger areas to call or warn each other to go away or approach. pack creatures might move or follow each other to areas, attack in groups etc.

## Notes

- Exploratory — flagged "maybe not, we'll see". The idea is recorded for later evaluation. 
- MVP if it ever gets picked up: a shared `pack` tag/property on group members, packmate awareness (detect nearby packmates in the same area), and a coordinated-target behavior rule ("attack the same target as the nearest packmate").
- Full pack AI (formation, flanking, role assignment) is intentionally out of scope for the MVP.

## Related

- `developer ideas.md` line 1
- NPC behavior system (`engine/npc_behaviors.py`)

## MVP implemented — 2026-09-28 (WT-C)

The three pieces the Notes section specifies, and none of the part it puts out
of scope.

### Pack identity is a tag, not a field

`pack:<name>` in the character's existing `tags`. No `Player.pack` attribute —
that is `player.py`, a hub file — and `tags` is already where the shipped data
puts what a character *is* (`"goblin"`, `"rat"`). Pack names are lowercased, so
`pack:Sewer` and `pack:sewer` are one pack, for the same reason
`player_manager.relationship_key` lowercases.

A tag also means a pack is visible to everything else that already reads tags,
which task-552 proved was the load-bearing detail for `fear_tags`.

### Files

- `engine/pack.py` — **new**. `pack_of`, `packmates_in`, `coordinated_target`,
  `call_for_help`, `on_call_cooldown`, `pack_summary`.
- `engine/npc_behaviors.py` — `_apply_pack_signal` / `_nearest_threat`, called
  at the top of the `process_simple_npcs` loop.
- `tests/test_pack_logic.py` — **new**, 32 tests.

### The three pieces

- **Awareness** — `packmates_in(gs, player, areas=0)`: same-area by default,
  and `areas` widens it by walking the **area graph** through
  `_build_exits_for_area`, not by a flat distance. A packmate in the next room
  is one exit away, not "within N" of anything.
- **The coordinated target** — the *nearest* packmate's `pack_target`, not a
  majority vote. A pack that has to agree before it acts is not a pack, it is a
  committee.
- **The call** — `call_for_help` reaches `PACK_CALL_RANGE` (one room) further
  than sight and **stamps `pack_target` on every listener**. That stamp is the
  point: without it a "pack" is a crowd standing near each other, and the
  coordinated-target rule has nothing to converge on. Throttled per pack so a
  cornered rat does not have the whole sewer howling every tick.

### What it does not do, deliberately

- **It does not move anyone.** "Attack the same target" is something a behaviour
  definition can already say; "walk over there" is not this task's business, and
  the legacy wander/flee fallback already owns simple-NPC movement. The hook sets
  state and the existing behaviour system acts on it.
- **No formation, flanking or role assignment.** The task file puts those out of
  scope, and they are the part that turns a mechanic into a project. A test
  asserts the module exports no such names, so a later well-meaning addition has
  to update the test on purpose.

### The important negative case

**A mechanic nobody has authored must be inert.** That is the lesson from
task-552, where a fear system existed, worked, and had never been asked a
question. Nothing in `data/library` or a scenario carries a `pack:` tag yet, so
no pack exists in any shipped content and the whole surface is dormant — which
is the correct answer, and a test pins that a character with no pack tag sees
nobody, calls nobody, and is on no cooldown.

Authoring a pack is one tag per rat:

```json
"tags": ["rat", "pack:sewer"]
```

and a `pack_target` needs setting by whatever is doing the attacking, which today
is a behaviour definition.

### Handed to WT-0

Nothing. No hub file was touched.

### Verify

`python -m pytest tests/test_pack_logic.py -q` — 32 tests. And
`tests/ -q -k "npc or pack or simple or background"` — 221 pass, no failures.

Covering: a pack tag names the pack and a bare `pack:` does not; names are
case-insensitive; another pack is not a packmate; a dead packmate does not call;
sight is same-room and hearing is one graph-hop further, with a test that builds
the exit graph explicitly and checks an unreachable area stays unreachable; a
lone pack has no coordinated target; a pack does not inherit a grudge against
its own kind when threats are restricted; a character never adopts its own name
as a target; a call stamps the target on every listener and returns them in a
stable order; a herd does not howl every tick; the hook sets a pack target,
ignores non-packs, and survives a packmate with `tags = None`; and
formation/flanking/role-assignment names are absent from the module.
