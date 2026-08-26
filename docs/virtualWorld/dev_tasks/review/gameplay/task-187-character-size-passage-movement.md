---
id: 187
title: Character Size + Passage Movement (crawl/climb/jump)
status: review
priority: medium
created: 2026-08-06
tags: [gameplay, movement, traits, ways, size]
---

# Character Size + Passage Movement (crawl/climb/jump)

## Summary

Characters get a selectable **size trait** (tiny / small / normal / huge / giant /
titanic). Ways (doors, passages, tunnels) get a **`max_size`** property plus an optional
**`requires`** movement type (`crawl` / `climb` / `jump`). Passing a way then depends on
size: walk normally, **auto-crawl** through a tight fit, or be **blocked** if
you don't fit. New movement verbs `crawl`, `climb`, `jump`, and **jump/climb failure is trigger-driven**.

## Design decisions (locked 2026-08-06)

### Size = trait, not a property

- Six mutually-exclusive traits in `data/library/traits/`:
  `size_tiny`, `size_small`, `size_normal`, `size_huge`, `size_giant`, `size_titanic`.
  The trait selector picks one; default is `normal` when none present.
- Reference scale (flavor only, no height property): normal ≈ 170 cm human,
  small ≈ 90 cm, tiny ≈ 45 cm, huge ≈ 3.4 m, giant ≈ 7 m, titanic ≈ 14 m+.
- Engine resolves a tier index from the present trait: `tiny=0 < small=1 < normal=2 <
  huge=3 < giant=4 < titanic=5`.

### Ways

- `max_size` property (dropdown: none/tiny/small/normal/huge/giant/titanic) — the
  largest size that passes **walking**.
- `requires` property (dropdown: none / crawl / climb / jump).
- Passing rules on `go`:
  - your size ≤ `max_size` → normal move.
  - `max_size` < size ≤ `max_size`+1 tier (e.g. `normal` in a `small` tunnel) →
    **auto-crawl**: `go` converts to a crawl move, narrates
    "You drop to your hands and knees and crawl through..." (no persistent condition
    in v1 — the move itself is the crawl).
  - size ≥ 2 tiers over `max_size` → **blocked**: "You don't fit through the X."
- `requires: climb` → only `climb <dir>` passes (or `go` returns "you need to climb").
- `requires: jump` → only `jump <dir>` passes.

### Movement verbs (no cost scaling)

- `crawl <dir>` — explicit crawl through a tight/crawl way.
- `climb <dir>` — only on `requires: climb` ways.
- `jump <dir>` — only on `requires: jump` ways; risky.
- **No time/energy multiplier in v1.** The way's authored `cost` applies as-is.
  The `time` field is a *duration* hint for the future stateful-action system
  (task-131) — the clock advances exactly once per turn for all characters
  (`tick_turn` → `advance_clock(1)`), never per action, so scaling it here would
  be both wrong and desync-prone. Crawl is flavor + gating only.
- `stand` — reserved for a persistent crawling state; not needed in v1 (crawl resolves
  per move).

### Jump/climb failure = trigger-driven

- No hardcoded failure in movement code. `requires: jump`/`climb` ways may carry a
  **failure trigger** (`on_fail_jump` / `on_fail_climb` trigger edges on the way node)
  that defines the consequence (damage, narrative, etc.). The engine rolls
  (Athletics/DEX) and on failure fires the way's failure trigger if present; if none,
  the move simply doesn't happen with a generic message.

## Files to Modify

1. `data/library/traits/size_*.json` — six size traits (new)
2. `engine/grapple.py` or new `engine/size.py` — size tier lookup helper
3. `engine/movement.py` — max_size checks + auto-crawl + crawl/climb/jump + multipliers
4. `routes/action.py` — `crawl`/`climb`/`jump` commands
5. `static/js/inspector/way-view.js` — `max_size` + `requires` dropdowns
6. `static/js/agent/prompt-builder.js` — action rows + size context
7. `static/js/agent-engine.js` — validate/normalize crawl/climb/jump/stand
8. `tests/test_movement.py` — size/passage tests

## Testing

- [x] Fits: normal walks a normal door (no change) — `test_go_passes_through_plain_way`
- [x] Tight fit: normal auto-crawls a small tunnel (no cost scaling) — `test_tight_fit_auto_crawls_without_scaling_cost`
- [x] Blocked: huge cannot pass a small tunnel — `test_two_tiers_over_max_size_blocked`, `test_one_tier_over_climb_way_blocked`
- [x] `climb` gated to `requires: climb` ways — `test_climb_way_rejects_go`, `test_climb_success_moves`
- [x] `jump` gated to `requires: jump` ways; failure fires the way's failure trigger — `test_jump_failure_fires_on_fail_jump_trigger`, `test_jump_success_moves`, `test_jump_failure_without_trigger_uses_generic_message`
- [x] Agent prompt lists crawl/climb/jump and surfaces size — `buildSizeContext` in prompt-builder.js, action table rows
- [x] Full suite green: 538 passed, 1 skipped (`-k "not mcp and not emote"`)

## Status

**Implemented 2026-08-06** — all eight backend + frontend touchpoints landed; moving to `review/` pending browser E2E.
