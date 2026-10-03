---
type: task
status: todo
area: ui
priority: medium
---

# task-675: Character editor: three-column body with section nav rail

**Filed:** 2026-10-02
**Related:** task-251, task-512, task-89

## Goal

Phase 3 of docs/design/full-entity-editors.md. The Bio tab is 3346px of content in a 960px viewport - 3.5x overflow across 15 sections. Give the full-surface editor a purpose-built layout: (a) promote the existing 4 tabs (Inventory, Bio, Images, Advanced) to a segmented control in the editor header, so the body is scoped to the active tab; (b) for Bio, lay the 15 sections into three columns - Identity and persona (name, description, personality, appearance, emotion, tags, aliases), Mechanics (stats, skills, traits, recipes, vitals), Knowledge (what I see, latest thoughts, memories, relationships, interest tags, fear tags); (c) keep the Appearance first-impression preview adjacent to the description it derives from rather than in another column, since it is a dependent live preview; (d) give Relationships its own row under Knowledge so it can scroll independently; (e) add a sticky left rail of section links built from the sections actually rendered; (f) Images and Inventory stay single-column - they are already narrow. Save-on-change semantics stay as they are. Verify in a live browser at 1600x1000, at 900-1200px where it should drop to two columns, and confirm the peek and the full editor cannot disagree.

## Acceptance

- TODO
