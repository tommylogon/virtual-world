---
type: task
status: inprogress
area: characters
priority: medium
---

# task-447: Character nicknames / aliases (authoring + resolution)

**Filed:** 2026-09-22
**Related:** task-446 (id-first node identity), task-448 (ambiguous target prompt),
`engine/matching.py` (character alias tier), `engine/serialization.py`

## Why

A character can go by a short name the game must resolve: "Vi" for *Violet
Halloway*. Nicknames are a **resolution-layer** concern — they map spoken input
to an identity; the data stays id-keyed. The engine already has a character
**alias tier** (`matching.py` `_match_character_name` step 2b, reading the node's
`aliases` property via `node_aliases`), but there is no way to author it and it
does not persist.

Note: "Vi" is *not* a substring of "Violet" (matching is word-boundary aware), so
a nickname cannot be inferred — it must be declared.

## Problem

1. **No authoring surface.** Character nodes in scenarios carry only
   `personality`; the inspector/library has no nicknames field.
2. **Aliases do not survive save/load.** On load a character's graph node is
   recreated bare — `Node(id, type="character", name=pname)` with no properties
   (`serialization.py`) — so an authored alias on the node would be lost. The
   alias must live where player state round-trips (the player payload) or be
   re-applied on load.

## Scope

- Add a **nicknames/aliases** field for characters in the inspector and library
  editor (list, or comma/`|`-separated like other alias fields).
- Persist it: store on the player payload (or a node-properties map that
  serialization restores) so it survives save/load and library import/export.
- Resolve it: the existing character alias tier already returns **candidates**
  when several characters share an alias — keep that (it feeds task-448).
- Consider surfacing aliases in autocomplete and in the target prompt.
- **Add `name` to the agent verb vocabulary** so an agent can declare an alias,
  since the backend already accepts the command from any actor.
- **Show a character's known aliases** where they matter — the HTC person view
  and the agent's people block — instead of resolving them silently.

## Acceptance

- Author can add "Vi" to Violet Halloway; `look`, `approach`, `talk to vi`
  resolve to that character.
- Alias survives a save → load and a library round-trip.
- Two characters sharing an alias return an ambiguous candidate set (not a silent
  pick).
- An agent can set an alias (the `name` verb is offered to it), not only a human.
- A known alias is visible in the HTC and in the agent's people listing, not only
  resolvable.

## Non-goals

- Duplicate **display** names (task-446).
- The disambiguation prompt UX (task-448).

## Status (2026-10-07) — in place; moved to review for live test

The two problems stated at filing are stale. Verified:

- **Authoring:** the inspector has a **🔖 Aliases** field — `renderAliasesSection`
  (`static/js/inspector/helpers.ts:973`), rendered for characters
  (`agent-view.ts:861`) and areas (`area-view.ts:143`); `saveAliases` →
  `api.updateNode(nodeId, { properties: { aliases } })`. Comma/`|` separated.
- **Persistence:** round-trip proven by the agent — set `aliases` on
  `player_elena_vance`, `to_dict()`, `load_from_dict()` into a fresh world; the
  aliases came back and `node_aliases()` read them. `load_from_dict` restores the
  graph node properties (`serialization.py:648`); the bare `Node()` at `:722`
  only fires when a node is absent. `data/library/characters/miki doki.json`
  already carries an `aliases` key, so the library round-trip holds too.
- **Resolution:** `matching.node_aliases` + the character alias tier
  (`matching.py:670`); ambiguity pinned by `tests/test_ambiguous_target.py`.

**Two real gaps found while checking — added to this task's scope (2026-10-07):**

1. **Agents cannot set an alias in practice.** The in-game `name <target> as
   <alias>` command (`routes/action_handlers.py:1180`) works for any actor and
   writes the node property, but `name` is **not** in the agent's verb
   vocabulary (`system-prompt.ts:69`), so an LLM agent never emits it. A human
   can type it; an agent cannot choose to.
2. **Aliases are never displayed.** The HTC person menu deliberately omits
   `name` and shows no alias (`turn-scene-view.ts:215-220`, task-610); the agent
   prompt lists people by name/description only (`system-prompt.ts:72` tells the
   agent matching *accepts* aliases, and `conversation-context.ts:71` uses a
   listener's aliases for address-detection — but the alias set is not shown).
   So a known alias is resolved silently, not surfaced, in both the HTC and the
   prompt.

The original acceptance (author / resolve / persist / ambiguous) is already met;
the two gaps above are the remaining work. Moved to `inprogress` (2026-10-07).
