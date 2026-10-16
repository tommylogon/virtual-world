---
type: task
status: todo
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

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

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
