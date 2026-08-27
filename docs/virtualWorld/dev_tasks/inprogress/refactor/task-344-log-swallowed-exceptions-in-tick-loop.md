# task-344 — Stop swallowing exceptions in the tick loop; log with context

**Status**: Todo — filed 2026-08-27 from code review of engine/tick_manager.py.

## Found

`engine/tick_manager.py::tick_turn()` contains 5+ bare
`except Exception: pass` blocks (:126 grapple-sync, :207, :295, :320, :482-487
delayed-event processing). The tick loop is where vitals decay, triggers fire,
items burn down and deaths resolve — failures there currently vanish as silent
no-ops. Several recurring mystery bugs plausibly live behind these walls:
bugs in review folder describe exactly this shape ("spawn drift", "state
doesn't change").

Also while there: `TickManager.__init__` comment at :13 admits
"player_manager is the VirtualWorldEngine instance" — the facade smuggled in
as a duck-typed dependency, reaching into privates (`gs._process_delayed_events`,
`gs._spawn_body_item`, `gs.name_matcher._set_player_area`). Not this task's
job to unwind the coupling; just don't make logging worse while touching it.

## Goal

Every except in tick_manager becomes `except Exception as e:` +
`self.gs.game_logger.log(f"[tick] {context}: {e}", ...)` (or module logger),
including enough context to locate it (character name / node id / event id).
Wrap-and-log is fine; silent pass is not.

## Verify

Inject a failing stub into each wrapped subsystem (monkeypatch raising) →
tick completes AND produces one identifiable log line per failure site;
full pytest suite green; manual turn with triggers running shows no error spam
in normal operation.
