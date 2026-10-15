---
type: task
status: done
area: ui
priority: medium
---

# Task-250: Merge Agents and Initiative Lists Into One Clickable List

**Status:** Done — implemented 2026-08-16, live-verified. Moved to review/.

## What

Combine the two left-side lists — the Agents list (`#agent-list`) and the
Initiative Order list (`#initiative-list`) — into a single list. Right now the
Agents tab shows clickable rows (select active / open inspector) but no turn
order, while the Initiative tab shows the order but the rows are not clickable.
One list should do both: the same click-to-select / open-inspector behavior on
every row, plus the turn-order markers (position, current/done/pending icons,
round, initiative roll).

## Current behavior (code)

- `renderAgentList(state)` (`ui-controller.js:25-60`) — builds `#agent-list`
  rows with status dot, vitals bar, location. Click: `selectAgent(name)` for
  all characters (since bug-19, NPC rows select too, opening the inspector /
  focus).
- `_renderInitiative(state)` (`ui-controller.js:155-199`) — builds
  `#initiative-list` rows with position, ▶️/✅/⏳ icon, name, NPC tag,
  initiative roll, status text; **no click handler**.
- Tabs: `left-tab-agents` / `left-tab-initiative` in `templates/index.html`
  (line 62-63), both panes in `left-tab-body`.
- The Initiative tab also hosts the **Turn-Based Mode checkbox**,
  **Turn Order select**, and the **🎲 Re-roll** button (index.html:80-89) — these
  need a new home after the merge.

## How

- `templates/index.html`: removed the `⚔️ Initiative` tab button and its pane. Moved the
  Turn-Based Mode checkbox + Turn Order select (and the 🎲 Re-roll button, now in the Agents
  heading) into the Agents tab, below the agent list.
- `static/js/ui-controller.js`: `renderAgentList()` now renders turn-order markers (position,
  ▶️/✅/⏳ icon, initiative roll, status, round header) on every agent row **when
  `config.turnBased` and a turn queue exist**, ordered by `agent.turnQueue`; otherwise it keeps
  the original roster with a "Turn-based mode is off…" hint. Rows stay clickable in both modes.
  `_renderInitiative()` is deprecated and folded into the merged list; `renderTurnInfo()` no
  longer calls it. `switchLeftTab()` tab list dropped 'initiative'.
- Re-roll button visibility handled in `renderAgentList()` (initiative order + turn-based only).

## Steps to verify

- `node --check` on ui-controller.js; `pytest` guard suites pass (62).
- Live: turn-based ON + initiative → 14 rows ordered by queue with pos/▶️/⏳ icon, rolls,
  status, round header, click-to-select, re-roll visible. Turn-based OFF → alphabetical rows,
  no markers, hint shown, re-roll hidden. Initiative tab gone; settings live under Agents.

## Notes / open questions

- Should the initiative markers still show in non-turn-based mode (e.g. nothing,
  since there is no order)?
- The row content differs a lot today (vitals bar + location vs order status).
  Combine both — or keep the agent row as the base and append order info?
- Is "select active" the right click action for the ordered rows, or should
  normal agents also open the inspector (match simple-NPC behavior)?

## Why

TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Left panel → Agents list; Turn-Based Mode and Turn Order
controls directly below the list.

Current availability: The merged roster and mode controls are recorded as
implemented and live-verified on 2026-08-16. The separate Initiative tab was
removed; turn-modal, event-stream, and full-round views remain their own
surfaces.

Live steps when available:
1. Enable Turn-Based Mode, select Initiative, and inspect every row in Agents.
   - expected: rows follow the initiative queue and show position, current/
     pending/done state, initiative roll, and round; clicking an NPC row
     selects it and opens its inspector.
2. Disable Turn-Based Mode and inspect the same list and controls.
   - expected: the roster returns to alphabetical order, turn markers and
     re-roll are hidden, and the non-turn-based hint appears.
3. Advance one actor and compare the row marker with the turn modal header and
   the event stream's `up next` strip.
   - expected: the same current actor leads all three views; none of those
     separate turn surfaces is replaced by the roster.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
