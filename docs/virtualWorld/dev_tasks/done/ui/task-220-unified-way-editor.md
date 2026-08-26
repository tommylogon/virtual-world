---
group: UI & Settings
wiki: "[[dev_tasks/level-design-workflow]]"
---

# Unified Way Editor (Both Sides, One Save)

**Filed**: 2026-08-13  
**Priority**: High  
**Status**: In Review — implemented 2026-08-13, pending browser verify

---

## Problem

A way is one passage connecting two areas, but authoring splits across:

- Way node (state, appearance when closed, `requires`, tags, parameters, triggers, pass_message)
- Connection edge A→way (`direction` / command, `visible_in_direction`, cardinal)
- Connection edge way→A (return path)
- Same for side B

Designers tab-hop in `way-view.js` (Info / Behavior / Connections / Tags / Triggers) and mentally merge "Living Room → swinging door → Kitchen" with different commands each side (`go swinging door` vs `enter`, `go Ladder down` vs `go Ladder up`, `jump jump across`).

## Goal

One inspector layout for a way that shows **shared passage properties** and **both area sides** with explicit command names per side. Single save writes way node + both connection edges atomically.

Pairs with **way templates** (user-planned separately) — template picks pre-fill this form.

## UI mockup

```
┌─ Way: swinging door ─────────────────────────────────────┐
│ SHARED                                                    │
│ State: [closed ▼]   Requires movement: [go ▼]             │
│ Appearance when closed/locked/blocked: [textarea]         │
│ On traverse (pass_message): [textarea]                    │
│ Parameters: key=val  (live resolved preview)              │
│ Tags: [TagMultiselect]   ☐ one-way  ☐ see_through  …     │
│ Triggers: [existing editor]                               │
├─ FROM Living Room ───────────────────────────────────────┤
│ Command (go ___): [swinging door]                         │
│ View when open: [textarea — visible_in_direction]           │
│ Cardinal: [optional ▼]                                    │
├─ FROM Kitchen ───────────────────────────────────────────┤
│ Command (go ___): [enter]                                   │
│ View when open: [textarea]                                │
│ Cardinal: [optional ▼]                                    │
├─ PREVIEW (task-219 lens snippet) ────────────────────────┤
│ Closed glance (Living Room): "…"                          │
│ Open glance (Living Room): "…"                              │
│ ⚠ Tag audit: jump way should not have clearance           │
└───────────────────────────────────────────────────────────┘
                    [ Save way ]
```

## Field labels (rename in UI)

| Current | New label |
|---------|-----------|
| Description (way) | **Appearance when closed/locked/blocked** |
| pass_message | **On traverse narration** |
| direction (edge) | **Command** (`go ___`) |
| visible_in_direction | **View when open (from this area)** |
| requires (way) | **Required movement verb** (go / crawl / climb / jump) |

Different commands per side are **first-class** — not bugs (stairs up vs down, jump across, narrative verbs).

## Save behavior

One `saveWayPassage(wayId, payload)` that:

1. Updates way node properties
2. Updates area→way edges for both areas (direction, visible_in_direction, cardinal)
3. Ensures way→area return edges keep correct `direction` (return command)
4. Calls `worldState.fetch()` once
5. Does **not** require author to touch area inspector exit list separately

## Authoring helpers (soft warnings, not topology lint)

Display inline ⚠ when:

- `{param:key}` in description but key missing from way parameters
- Tag on way looks wrong for type (e.g. `clearance` on jump pit — labs lesson)
- `requires: jump` but command doesn't match movement table (informational)
- Parameter resolved preview differs from raw (show both)

Optional: warn if serialized `areas.exits` cache drifts from graph (until task-222 removes cache)

## Implementation

### Files

- `static/js/inspector/way-view.js` — refactor Connections + Info into unified layout (or `way-passage-editor.js`)
- `routes/graph.py` — optional batch endpoint `PATCH /api/ways/<id>/passage` if multi-edge save needs atomicity
- Reuse `InspectorWayView._updateCardinal` for opposite cardinal sync

### Out of scope

- Way templates content (separate user track — this editor is the target surface)
- Pathfinding / movement engine changes
- Graph topology validation (user reports no broken connections today)

## Verification

- [x] Unified **Passage** tab: shared props + both area sides + preview + **Save way** batch (`saveWayPassage`)
- [x] Field renames applied (appearance, on traverse, command, view when open, required movement verb)
- [x] Tag sanity warnings + param preview reused from task-221 helpers
- [ ] Edit Living Room↔Kitchen swinging door: both commands + both views in one screen (browser)
- [ ] Save once → agent lens shows updated exit lines from both areas (browser)
- [ ] Ladder: separate commands on each side visible (browser)
- [ ] Jump way: `requires: jump` visible on shared row (browser)

## Related

- [[review/characters/task-8-npc_behavior_movement|task-8]] — NPC `go` uses these commands
- [[todo/ui/task-219-agent-lens-left-panel|task-219]]
- [[todo/ui/task-221-way-authoring-ux-and-tooltips|task-221]]
