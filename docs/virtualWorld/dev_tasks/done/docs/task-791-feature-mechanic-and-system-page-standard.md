---
type: task
status: done
area: docs
priority: high
horizon: now
effort: M
wiki: "[[Feature Map]]"
---

# task-791: Feature, mechanic and system page standard

**Filed:** 2026-10-12
**Related:** 

## What

Define and document the three-tier page standard every vault note follows: a **feature** page (what you do or use), its **mechanics** (how it works), and the **system** (where it lives — code, data, config). Replace the scaffolded stub format with a hand-written template.

## Why

We settled the model (feature = what you do/use, mechanic = how it works, system = the implemented whole) but nothing encodes it. The generated Features/ stubs do not follow it, and a new page has no shape to copy. This is the keystone: the Commands collapse, the Environment family and the deep-doc re-home are all 'apply this template'.

## How

Amend AGENTS.md's 'Writing documentation (the Ways standard)' section to name the three tiers and the three readers (player / author / engineer). Add a page template (headings + what goes in each). Use `Ways.md` and `World Building/Movement.md` as the two worked exemplars.

## Steps to verify

1. Open AGENTS.md and the template.
   - expected: the three tiers are named, with what belongs in each.
   - observed: TODO
2. Write a stub page from the template cold.
   - expected: no guessing about structure.
   - observed: TODO

## Acceptance

- [ ] AGENTS.md states the feature / mechanic / system tiers and their readers
- [ ] a page template exists with fixed headings
- [ ] Ways.md and Movement.md are named as the exemplars
- [ ] a new page can be written from the template without guessing

## Files

- `AGENTS.md`
- `docs/virtualWorld/World Building/Ways.md`
- `docs/virtualWorld/World Building/Movement.md`
