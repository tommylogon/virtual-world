---
type: task
status: done
area: refactor
priority: medium
wiki: "[[Library System/Library System Overview]]"
---

# task-696: Server log file option, and mutating routes log the identity they actually resolved

**Filed:** 2026-10-04
**Related:** bug-521

## What

Name-resolution drift is this repo's most common bug class, and today's import bug (bug-521) produced exactly one server-side trace — a generic warning — while the updateCharacter response echoed `"player":"zombie"` for a call targeting `zombie__c4d808`. So a resolver that silently rewrites its target is invisible at the moment it happens. The fix is logging only, and the file option is off by default, so nothing about behaviour changes: `VW_LOG=<path>` (or `--log-file`) routes the root logger to a file so an agent without the launching terminal can read server evidence; every mutating route logs the resolved identity at INFO when input name and stored key differ (`set_player_area('zombie__c4d808' -> key 'zombie', area 'Old Dwarven Ruins')`); responses that echo an identity echo the RESOLVED one, not the input; and the import/refresh paths in `routes/library_ops.py` log the pre/post key when `_unique_key` suffixes a duplicate. Reuse the existing resolver rather than adding a second one — the log records what the resolver actually returned, so a future drift guard has a source of truth to check against.

## Acceptance

Today's import bug (bug-521) produced exactly one server-side trace — a generic
warning — and the updateCharacter response echoed `"player":"zombie"` for a call
targeting `zombie__c4d808`. Name-resolution drift is this repo's most common bug
class; the logs should show it at the moment it happens.

- [ ] `VW_LOG=<path>` (or `--log-file`) routes the root logger to a file, so an
      agent without the launching terminal can read server evidence.
- [ ] Every mutating route logs the resolved identity when input name and stored
      key differ, at INFO: `set_player_area('zombie__c4d808' -> key 'zombie',
      area 'Old Dwarven Ruins')` — a resolver that silently rewrites its target
      must be visible.
- [ ] Responses that echo an identity echo the RESOLVED one, not the input.
- [ ] The import/refresh paths (routes/library_ops.py) log the pre/post key when
      `_unique_key` suffixes a duplicate.
- [ ] Does not change any behavior — logging only, and the file option is
      off by default.

## Why

Name-resolution drift is this repo's most common bug class. The resolver rewrites
its target silently (`zombie` -> `zombie__c4d808`), so the only evidence was a
generic warning and a response echoing the wrong name. Logging is the smallest
coherent change that makes the rewrite visible without changing behaviour; the
file option is off by default so nothing about the simulation moves.

## How

- `app.py`: `_LogFileHandler` marker subclass + `_attach_log_file(path)`, which
  finds and replaces any prior instance on the root logger so re-attaching is
  idempotent. Wired into `__main__` via `--log-file` and the `VW_LOG` env var.
- `routes/player_ops.py`: `_log_resolved_identity(app, route, supplied, ...)` is
  the single helper; every mutating route calls it and echoes the resolved key
  in its response, not the input.
- `routes/library_ops.py`: `import_character` logs the pre/post key when
  `_unique_key` suffixes a duplicate.

## Steps to verify

1. Boot with `VW_LOG=<path>` (running scratch server `bgp_1466dac35001af08VXchVqCYVD`,
   port 4444, autosave world — already up, logging to `vwlog2.txt`).
   - expected: `Server logging to <path>` appears in the log.
   - observed: `2026-10-16 22:35:55,690 INFO __main__: Server logging to
     C:\Users\Tommy\AppData\Local\Temp\kilo\vwlog2.txt`
2. Exercise a duplicate-name character (three `zombie` entries live) through
   every mutating route.
   - expected: each route logs supplied vs resolved key/id; the response echoes
     the resolved key.
   - observed:
     - `move_player` -> `supplied='zombie' resolved_key='zombie'
       resolved_id='player_zombie' area=Old Dwarven Ruins`; response
       `"player":"zombie"`.
     - `player_speak` -> `supplied='zombie' resolved_key='zombie'
       resolved_id='player_zombie' area=Old Dwarven Ruins`; response
       `"speaker":"zombie"`.
     - `update_vital` (PATCH HP=42) -> `supplied='zombie' resolved_key='zombie'
       resolved_id='player_zombie' vital=HP value=42`.
     - `set_active_player` -> `supplied='zombie' resolved_key='zombie'
       resolved_id='player_zombie'`; response `"active":"zombie"`.
3. Import a library character whose name is already held.
   - expected: `_unique_key` suffix is logged as `(uniqued)`.
   - observed: `import_character supplied='zombie' resolved_key='zombie__97e239'
     resolved_id='97e2396b' (uniqued)`; response `"player":"zombie__97e239"`.
4. Confirm no behaviour changed: every call returned 200 with the same shape
   as before the change; no route logic was altered, only logging and the
   response echo.

## Files

- `app.py` — `--log-file` / `VW_LOG` support.
- `routes/player_ops.py` — `_log_resolved_identity` + 8 call sites.
- `routes/library_ops.py` — `import_character` pre/post key log.

## Browser UI and intended live verification

Intended UI home: game view → perform a mutating character/world action → inspect the configured server log file and the response's resolved target identity. The browser action is the trigger; the log is the verification surface.

Current availability: the card records a name-resolution mismatch where a request for `zombie__c4d808` was logged/responded as `zombie`, with only one generic server trace. `VW_LOG`/`--log-file` and resolved-identity logging are not claimed as implemented.

Live steps when available:
1. Start the app with `VW_LOG=<scratch-log-path>` and open the scenario in the browser. Perform one action against a character whose node ID differs from its display name.
   - expected: the request succeeds against the intended node and the log records both the supplied identifier and the exact resolved opaque ID.
2. Repeat through a route that resolves an alias/name and through a route with an invalid target.
   - expected: each mutating route logs the identity it actually resolved; an invalid target is reported as unresolved and is not logged as a different character.
3. Read the configured log file while the server runs without relying on the launching terminal; restart with `--log-file` and repeat.
   - expected: both configuration paths write the same structured request/result evidence without duplicating root handlers.
4. Compare the browser response, `/api/state`, and log entry.
   - expected: supplied name, resolved character ID, action result, and world state agree.

This section is not a claim that the log-file option or route identity logging is implemented today.
