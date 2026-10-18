---
type: task
status: todo
area: ui
priority: medium
horizon: next
goal: An area's holder can be set from the inspector, not only by hand-editing a file.
wiki: "[[Persona]]"
related: [task-742, task-550]
---

# task-872: Expose held_by (area ownership) in the inspector

**Filed:** 2026-10-18
**Related:** task-742, task-550

<!-- deps:start -->
**Related:** [[task-742-faction-scoped-hostility-and-group-aware-fear-wire-or-retire-the-hostile-trait]], [[task-550-faction-and-ownership-as-tags-a-camp-s-water-is-the-camp-s]]
<!-- deps:end -->

## What

`held_by:<name>` (an area's holder) is an engine-only tag read by `engine/ownership.py` (`task-550`). A search of the front end finds it nowhere as an input: there is no surface to set an area's holder.

Narrowed 2026-10-18. The character-side `faction:<name>` tag is out of scope here: faction authoring (and the group/faction relation) belongs to [[task-742-faction-scoped-hostility-and-group-aware-fear-wire-or-retire-the-hostile-trait]], whose stated UI home is exactly that. This card keeps only the area `held_by` half, which no other card owns.

## Why

Ownership is authored data. With no surface it can only be written by hand in a file, so the ownership engine (a camp's water is the camp's) can never be exercised from the UI.

## How

1. Add a `held_by` field to the area view that writes a `held_by:<name>` tag, using the engine constant rather than a literal.
2. Reuse or extend the existing tags editor if one exists, rather than adding a second tags store.
3. Round-trip.

## Browser UI and intended live verification

The inspector's area view gains a holder field. Live steps: set a holder on an area, confirm an ownership read (or a soak) sees it, and confirm it survives a save / load.

## Steps to verify

1. Set `held_by:Goblin Camp` on an area from the inspector.
   - expected: the tag is written and read by `engine/ownership.py`.
   - observed: TODO
2. Save and reload.
   - expected: it survives.
   - observed: TODO

## Acceptance

- [ ] `held_by` (area) is settable from the inspector.
- [ ] The UI writes the engine constant (`engine/ownership.py`), not a hard-coded string.
- [ ] It round-trips a save / load.

## Files

- `engine/ownership.py`
- `static/js/inspector/area-view.ts`
- `tests/test_ownership.py`
