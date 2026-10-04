---
type: task
status: todo
area: refactor
priority: medium
---

# task-696: Server log file option, and mutating routes log the identity they actually resolved

**Filed:** 2026-10-04
**Related:** bug-521

## Goal

TODO

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

