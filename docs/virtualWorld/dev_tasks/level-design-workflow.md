# Level Design Workflow — Task Hub

**Created**: 2026-08-13  
**Context**: Authoring areas, ways, items, and triggers for agent/human perception. Players live in **areas**, never in ways. Exit perception = way appearance (closed) + connection view (open) + movement rules.

---

## The loop we want

```
Edit area/way/item (inspector)  →  Agent Lens (left panel) shows exact prompt
        ↑                                    ↓
        └──────── tweak copy until match ────┘
```

No agent step required for copy validation. Inspector stays editable; lens never blocks it.

---

## Task roadmap (recommended order)

| # | Task | Priority | What it gives you |
|---|------|----------|-------------------|
| **219** | [[todo/ui/task-219-agent-lens-left-panel\|Agent Lens — left panel]] | **High** | Live `buildRoomContext` + full next-turn prompts; context follows area/agent selection |
| **220** | [[todo/ui/task-220-unified-way-editor\|Unified Way editor]] | **High** | Both sides + shared props in one save; pairs with your way templates |
| **221** | [[todo/ui/task-221-way-authoring-ux-and-tooltips\|Way UX + tooltips]] | Medium | Honest labels, exit badges (climb/jump/tags), graph edge hover, `{param:}` preview |
| **222** | [[todo/gameplay/task-222-serialize-exits-graph-only\|Graph-only exits in saves]] | Medium | Stop duplicate `exits` in JSON; one field in UI = one truth |
| **223** | [[review/gameplay/task-223-way-prevent-close-open-passages\|prevent_close for pits/ladders]] | Low | Jump pit / ladder can't be "closed" by accident |
| **201** | [[todo/ui/task-201-area-visibility-beyond-ways\|See-through / beyond-way visibility]] | Medium | Lens toggles for seeing people/items through open ways (integrates with 219) |

### Already done / in review (foundation)

| Task | Status |
|------|--------|
| [[review/characters/task-8-npc_behavior_movement\|task-8 Way go modes]] | Review — NPCs pathfind via ways |
| [[review/triggers/task-keycard-clearance-target_has_tag-unlock_way-target\|Keycard clearance]] | Review — `has_tag` on **door** (target), any tag value works (e.g. generic `clearance`) |
| [[todo/graph/task-129-graph-tooltips-environment-info\|task-129 Graph tooltips]] | Todo — area env on hover; connection edges covered by 221 |
| Way templates | User-planned — feed into task-220 editor |

---

## Mental model: one way, two area views

```
  Living Room                    Kitchen
       │                            │
       │  command: "swinging door"  │  command: "enter"
       │  view when open: "…"       │  view when open: "…"
       └──────────┬─────────────────┘
                  │
            [ way node ]
            state: closed
            appearance when closed: "…"
            requires: go | crawl | climb | jump
            tags: clearance, …
            parameters: { light: red }
            triggers: on_fail_jump, on_use_on, …
            pass_message: "You push through…"
```

**Agent exits block** (from area A) uses:

- Closed: way appearance + "It is currently closed."
- Open: `visible_in_direction` on **A→way** edge, or auto env clues from target area

**Different commands each side** (`go Ladder down` / `go Ladder up`, `jump jump across`) are intentional.

---

## Labs.json lessons (documented 2026-08-13)

| Issue | Cause | Task that helps |
|-------|-------|-----------------|
| Two texts for same ladder view in raw JSON | `rooms.exits` cache vs `graph.edges` | **222** |
| `clearance` tag on jump pit | Easy to mis-tag on way node | **221** soft hint, **220** unified editor |
| Keycard opens all `clearance` doors | By design — `has_tag target clearance` checks **door** tags | Docs only ✓ |
| Jump fail → hole | `on_fail_jump` teleport + message | Working as designed |
| Can close open pit/ladder | No guard | **223** |
| Ladder missing `requires: climb` | Authoring oversight | **221** badge in lens + exits |

---

## Agent Lens modes (task-219 detail)

### Area lens (area selected in graph)

- **View as:** pick character
- **Location:** that area (hypothetical — for level design)
- Shows: description, attention items, people, **exits block**

### Agent lens (agent selected)

- **Location:** agent's real `current_area`
- Shows: full next-turn prompt stack (system + think-decide message + context blocks)

### Way selected (v1.1)

- Two snippets: "From area A…" / "From area B…" — not a third "inside way" view

---

## Explicitly out of scope (for now)

- Graph topology / invalid connection lint (not a reported pain point)
- Replacing way templates (user owns this)
- "Passage" rename — **ways** stay ways

---

## Quick verification checklist (when 219 lands)

1. Reset/load labs scenario  
2. Open left **👁 Lens**, select Task 18 Room 5  
3. View as Kaelen — exits show `jump across` with closed pit description  
4. Edit jump view in way inspector — lens updates without running sim  
5. Select Lyrie in agent list — lens shows **her** prompts from Frozen Thicket, not selected area
