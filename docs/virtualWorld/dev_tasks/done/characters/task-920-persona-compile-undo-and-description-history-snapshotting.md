---
type: task
status: done
area: characters
priority: medium
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903"]
---

# task-920: Persona compile undo and description history snapshotting

**Filed:** 2026-10-31
**Related:** task-903

## What

Snapshot previous `base_description`, `personality`, `interest_tags`, and `fear_tags` before committing a persona compile, allowing the author to revert back to their prior authored prose with a single click in the Persona tab.

## Why

Compiling a structured persona block rewrites the character's primary prose fields. If the compiled result is less nuanced than hand-crafted prose, authors currently have no easy way to revert without manually restoring from git or backups.

## How

- Store `_last_precompile_snapshot` on `Node.properties` (or in client session history) containing `{ "base_description": ..., "personality": ..., "interest_tags": ..., "fear_tags": ... }`.
- Add a "Revert to pre-compile" button in the Persona tab sticky bar when a snapshot is present.
- Provide an API endpoint `POST /api/players/<name>/record/revert_compile` to restore the snapshot.

## Acceptance

- [x] Compiling a persona automatically captures a snapshot of the overwritten fields.
- [x] Authors can revert compiled prose back to the pre-compile state.
- [x] Snapshot does not leak into public scenario exports or bloated graph payloads.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
