# Task-245: Multiplayer Humans — Online or Local

**Status:** In Review — local multi-human MVP implemented 2026-08-16.
**Source:** `dev_tasks/developer ideas.md` (multiplayer humans online or local)

## Local MVP implementation (2026-08-16)

Every non-dead player is in the turn queue regardless of control type. When the queue
lands on a human character, `agent-engine._humanTurn()` calls `ApiClient.setActivePlayer(
thatHuman)` before prompting, so each human is targeted in queue order and gets a clean
turn handoff via the existing `active_player` mechanism. No online/concurrent-writer
support (Flask is single-process) — that remains out of scope.

## Goal

Support more than one human-controlled player in the world, either locally (multiple
humans taking turns on the same machine) or online (humans in different sessions sharing
the same world state).

## Notes / open questions

- Local: allow multiple players marked human/active and a clean turn handoff (who acts
  each turn), reusing the existing `active_player` mechanism.
- Online: feasibility of concurrent writers to the same `app.world.graph` (Flask is
  single-process/single-threaded here) — locking, session identity, and tick scheduling
  for multiple humans must be designed before building.
- Recommend scoping MVP to local multi-human first; online is a large architectural lift.