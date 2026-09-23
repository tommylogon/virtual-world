---
type: task
status: inprogress
area: gameplay
priority: medium
---

# task-481: Per-character soak orders (multi-human timeskip)

**Filed:** 2026-09-23
**Related:** task-464, task-437, task-244, task-101, task-472

## Goal

A timeskip in a shared world is **not** a table consensus and **not** a blocking
server jump. It is an **order attached to one character**, declared on that
player's turn in the turn composer ("go west for an hour"). While the order is
active the character is driven by the declared policy on every turn of the normal
game loop, exactly like an agent or a distant NPC, so a turn with a thousand
characters in soak still finishes in seconds. Humans who did not declare keep
taking their normal attended turns; nearby NPCs stay high fidelity; every agent
and every far-away NPC soaks.

Confirmed decisions (2026-09-23):
- **Duration is game-minutes elapsed over normal turns**, not wall-clock and not a
  private fast-forward.
- **While an order runs the character is genuinely `simulation_mode: background`**
  (soak tier drives it, the LLM loop does not ask it for decisions), restored to
  its previous mode when the order ends.
- **Promotion does not pause the table.** A promoted character is simply put back
  into the turn queue and acts on its next turn by normal turn order (if that
  happens before human 3's turn, human 2 still acts first).
- **The blocking `advance`/`advance_world` jump is the degenerate fast path**, used
  only when nothing attended remains (solo, or everyone already soaking).

## Acceptance

- [x] `engine/soak.py`: `declare` / `cancel` / `remaining` / `apply_orders`;
      an order carries intent, span, target/heading/watch tags, and the discovery
      baseline.
- [x] `apply_orders` runs from `tick_turn` after the background pass; a policy
      step per turn, the span decremented by the frame length.
- [x] Genuine background mode while ordered; restored on finish/cancel.
- [x] `process_due` skips ordered characters so the generic need policy never
      competes with the declared intent.
- [x] Promotion on fear, hostile condition, critical vital, or a watched
      discovery: order cleared, `frightened` applied for fear, one resume memory,
      a `soak_end` turn event — and no table pause.
- [x] API: `POST /api/world/soak`, `DELETE /api/world/soak`; `POST
      /api/world/timeskip` now **declares an order** when another attended human
      exists instead of blocking the world, and still fast-forwards when alone.
- [x] The **initiative/roster list** shows an active soak (⏩ intent + minutes
      left) from the state payload; the **turn composer deliberately shows
      nothing** about it (status belongs in the list).
- [x] Turn-based `advance()` steps past characters with an active soak order, so
      a soaking human is not prompted for an attended turn (bounded, so an
      all-soaking table cannot spin).
- [x] Promotion re-queues by the normal order rule: sequential is already
      alphabetic, random already shuffled, **initiative re-rolls for the
      promoted character** and re-sorts keeping the current character current,
      and simultaneous modes do not use this queue at all
      (`TurnQueue.syncSoakPromotions`, driven from `reconcile()` on each fetch).
- [x] Cancel from the roster row: a ✕ on the soak badge calls
      `DELETE /api/world/soak?character=<name>` (defaults to the active
      character; 404 for an unknown name, clean no-op when there is no order).
- [ ] Save/load: orders are deliberately transient; a reload abandons the order.

## Verification

`python -m pytest tests/test_soak_orders.py -q` → 14 passed (incl. the state
payload reporting the order for the roster). Targeted soak/background/timeskip/
fear/checks → 111 passed. `tools/unit` → 133 passed (incl. 3 soak-queue cases).
lint / typecheck / module-index clean.
