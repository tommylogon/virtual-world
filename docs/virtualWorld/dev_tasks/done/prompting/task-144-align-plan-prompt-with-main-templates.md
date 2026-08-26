---
group: Prompt & Narrative Quality
---
# Align Plan Generation Prompt with Main Prompt Templates

**Filed**: 2026-07-30
**Priority**: Medium
**Status**: Done
**Completed**: 2026-08-03

---

## Problem

The plan generation prompt uses different section names than the main prompt templates:

| Main templates | Plan prompt |
|---------------|-------------|
| `=== YOUR STATE ===` | `=== CONDITION ===` |
| `Carrying: ...` (context setter) | `=== CURRENT WORLD ===` (full context setter) |
| `=== RECENTLY / JUST HAPPENED ===` | `=== MOST RECENT OUTCOME ===` |

## Cause

The plan prompt is built in a separate code path (likely `plan-manager.js`) that doesn't reuse `buildRoomContext()` or the standard template functions. It constructs its own prompt from scratch with different section names, duplicating the personality preamble in the process.

## Scope

- Locate the plan prompt builder
- Align section names with the main templates (`=== YOUR STATE ===`, `=== YOUR THOUGHTS ===`, `=== RECENTLY ===`)
- Ensure personality is only included once (currently duplicated from the user message preamble)
- Reuse `buildRoomContext()` if feasible

## Files

- `static/js/agent/plan-manager.js` — likely the plan prompt builder

## Done

- Plan prompt now starts with the bare `buildRoomContext()` output (no `=== CURRENT WORLD ===` header), matching the observe/decide templates.
- `=== CONDITION ===` → `=== YOUR STATE ===`
- `=== MOST RECENT OUTCOME ===` → `=== RECENTLY ===`
- `=== MOST RECENT THOUGHT ===` → `=== YOUR THOUGHTS ===` (own section after YOUR STATE, matching DECIDE)
- Removed the duplicated `You are {name}. {personality}` line — the roomContext preamble already carries it.
- `buildRoomContext()` gained an `includePlan` param (default `true`); plan generation passes `false` so the generator doesn't see its own active plan (it's already fed via `=== PREVIOUS PLAN ===`).
- Kept `=== WORLD KNOWLEDGE ===`, `=== PREVIOUS PLAN ===`, threat note, and plan rules.

## Files Modified

1. `static/js/agent/plan-manager.js` — prompt section rename/dedupe, `buildRoomContext(..., false)`
2. `static/js/agent/prompt-builder.js` — `includePlan` param on `buildRoomContext`
