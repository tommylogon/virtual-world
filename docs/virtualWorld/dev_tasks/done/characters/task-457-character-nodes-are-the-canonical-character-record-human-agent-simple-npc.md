---
type: task
status: done
area: characters
priority: high
---

# task-457: Character nodes are the canonical character record (human, agent, simple NPC)

**Filed:** 2026-09-22
**Related:** task-446, task-316

## Goal

Make the character graph node the single source of truth for a character's full definition (stats, skills, vitals, traits, tags, interest_tags, personality, descriptions, emotion, conditions, simple_npc/autonomy/behaviour fields; inventory/equipped via edges). The Player object becomes a runtime view derived from and synced with the node: load seeds node properties from the players section (additive migration), node writes are authoritative, and no defining field lives only on the Player. Uniform for human, agent, soak and simple NPCs.

## Acceptance

- TODO

## The non-hub half — 2026-09-28 (WT-C)

### What the audit found

**A character graph node carries no definition at all.** It is created with a
name and a type and nothing else:

- `engine/player_manager.py:202` — `add_player`:
  `Node(id=player_node_id, type="character", name=player_obj.name)`
- `engine/serialization.py:552` — the load path: the same bare `Node(...)`

Nothing anywhere writes definition properties onto it. So *every* field in the
task's scope — stats, skills, vitals, traits, tags, interest_tags, personality,
descriptions, emotion, conditions, the simple_npc/autonomy/behaviour fields —
lives only on the `Player`, and the node is currently canonical for exactly one
thing: its own name. The task reads like a migration about moving fields onto
the node; it is actually the first step of one.

The clearest evidence is task-552's: every shipped character carries
`"goblin"`, `"teen"`, `"female"` in `player.tags`, and nothing on the node could
ever see them, so `fear_sources` matched nothing.

Two tests in `tests/test_character_identity.py` are already failing on master —
`test_collapse_is_idempotent` and `test_kraktooth_loads_as_one_node_per_character`
— and they fail on exactly this: `character_arix` alias nodes and one node per
character. **Those two tests are the closest thing to an acceptance criterion
this task already has**, and they are red before any of this work. Verified
against a clean master worktree, so they are part of the 61-failure baseline, not
something introduced here.

### What I built, and why it is read-only

`engine/character_record.py` — the two halves of the task that do not need a hub:

- **`DEFINITION_FIELDS`** — every defining field, grouped (identity, capability,
  state, social, tier, knowledge, inventory, spatial, runtime), each tagged with
  where it lives today (`player` / `node` / `edges` / `derived`) and whether the
  node must carry it. `PLAYER_ONLY_FIELDS` is the migration's work list, derived
  from that table rather than hand-maintained so the two cannot disagree.
- **`definition_drift(player, node)`** — read-only. Reports which fields the
  Player holds alone, split into `missing` (the node has never heard of it) and
  `differs` (two records, two answers, no way to tell which is right — the
  dangerous case).
- **`audit(world)`** — drift for every character, so "how far along is 457?"
  has an answer against a running world instead of against a plan.

**No projector.** A function that writes a definition onto a node, called from
nowhere, does not make the node canonical — it makes a **second** source of
truth and invites exactly the drift the task exists to remove. The write belongs
in the hubs; the drift reader is how whoever does it verifies the result.

### Two fields the task's scope argues about, recorded rather than decided

- **`vitals`, `emotion`, `conditions` are runtime state, not definition.** They
  change every tick; a "canonical" copy on the node is a cache of something that
  is already moving. The task's goal paragraph lists them in scope, so the list
  follows the task — with a `note` saying so, which is the honest place for the
  argument to live.
- **`memories` is canonical but `memory_index` is not.** The index is a lookup
  into the memories; storing it separately means two records of the same thing
  that can disagree.

### Handed to WT-0 — the write path, which is two call sites

Both are hub files, so neither is mine:

1. **`engine/player_manager.py:202`** (`add_player`) — after the bare `Node(...)`,
   project the definition onto it. This is the seam for new characters.
2. **`engine/serialization.py:552`** (the load path) — the task's "additive
   migration": seed the node from the players section on load, so an old save
   does not lose its definition, and a new one is already canonical.

`engine/character_record.py` gives both a field list to walk, and
`definition_drift` to check the result. **The two red `test_character_identity.py`
tests are the natural acceptance for this** — they already assert one node per
character and would go green when the seam is closed.

Also worth deciding there, not here: whether the Player becomes a pure view, or
stays writable and the node is kept in sync. The task says "node writes are
authoritative", but every current writer is on the Player, so that decision
determines whether this is a sync layer or a refactor of all of them.

### Verify

`python -m pytest tests/test_character_record.py -q` — 30 tests. `tests/ -q -k
"character or player or serial or node"` — 445 pass; the 21 failures there are
the pre-existing `test_mcp_*` FastMCP wrapper mismatches plus the two
`test_character_identity.py` failures described above, all confirmed on a clean
master worktree.
