---
type: task
status: todo
area: ui
priority: medium
---

# task-675: Character editor: three-column body with section nav rail

**Filed:** 2026-10-02
**Related:** task-251, task-512, task-89

## What

Phase 3 of docs/design/full-entity-editors.md. The Bio tab is 3346px of content in a 960px viewport - 3.5x overflow across 15 sections. Give the full-surface editor a purpose-built layout: (a) promote the existing 4 tabs (Inventory, Bio, Images, Advanced) to a segmented control in the editor header, so the body is scoped to the active tab; (b) for Bio, lay the 15 sections into three columns - Identity and persona (name, description, personality, appearance, emotion, tags, aliases), Mechanics (stats, skills, traits, recipes, vitals), Knowledge (what I see, latest thoughts, memories, relationships, interest tags, fear tags); (c) keep the Appearance first-impression preview adjacent to the description it derives from rather than in another column, since it is a dependent live preview; (d) give Relationships its own row under Knowledge so it can scroll independently; (e) add a sticky left rail of section links built from the sections actually rendered; (f) Images and Inventory stay single-column - they are already narrow. Save-on-change semantics stay as they are. Verify in a live browser at 1600x1000, at 900-1200px where it should drop to two columns, and confirm the peek and the full editor cannot disagree.

## Acceptance

- TODO

## Browser UI and intended live verification

Intended UI home: Character full-surface editor → Bio tab, opened from the inspector's expand control or a canvas-node double-click. Its header has segmented Inventory/Bio/Images/Advanced tabs; Bio has a sticky section-navigation rail and three content columns.

Current availability: The card measured the existing Bio content at 3,346px across 15 sections in a 960px viewport. This layout is planned; the frame prerequisite is task-673.

Live steps when available:
1. At 1600×1000, open the full character editor and select Bio.
   - expected: Identity/persona, Mechanics, and Knowledge are distinct columns; Appearance preview sits beside its source description; Relationships has its own row; the rail links only to sections currently rendered.
2. Use each rail link to jump to Relationships, then scroll that section independently.
   - expected: the active section is reachable without losing the other columns' scroll positions or hiding its heading under the sticky header.
3. Resize to 900–1200px, then below the confirmed responsive breakpoint.
   - expected: three columns drop to two at the stated range and then reflow without horizontal clipping; Inventory and Images remain single-column.
4. Edit a character field from the peek, open the full editor, edit it there, then return to the peek.
   - expected: both views read the same character data and neither displays a stale copy.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

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
