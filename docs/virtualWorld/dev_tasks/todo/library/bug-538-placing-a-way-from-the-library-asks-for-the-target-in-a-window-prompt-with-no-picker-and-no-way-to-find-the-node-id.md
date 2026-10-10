---
type: bug
status: todo
area: library
priority: medium
related: [task-751]
---

# bug-538: Placing a way from the Library asks for the target in a window.prompt, with no picker and no way to find the node id

**Filed:** 2026-10-10
**Related:** 

## What

Placing a way from the library opens a browser window.prompt asking the author to type a target node id. There is no picker, no search and no way to discover the id, so the placement is effectively unusable by hand. Replace the prompt with the same placement flow items use (a target picker / openForRoom over the graph), so an author picks the destination area or way from a searchable list or by clicking the graph. Surfaced 2026-10-10 while trying to verify task-659 (library way spawn carries insulation/sound_barrier) - the spawn could not be reached by hand.

## Why

**Overlap with task-751 — read this first.** The *native-popup* half is already ticketed: **task-751** (`review/ui`) replaces every native `alert`/`confirm`/`prompt` with the in-app `dialog.*` module (`static/js/shared/dialog.ts`, already built), and this site — `library-browser.ts`'s way import (`Connect FROM area name:` / `Connect TO area name:` prompts) — is one of its ~20 `prompt()` call sites. But task-751 only swaps the widget; it would still ask for a **typed name/id**. The distinct fault here is that a placement target needs a **picker**, not free text: the author cannot know the id. So this card survives task-751 as *"the way placement needs a target picker (a searchable list, or click-the-graph)"*, and its native-popup half is discharged by task-751.

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
