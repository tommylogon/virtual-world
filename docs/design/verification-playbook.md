# UI Verification Playbook

A practical guide for automated agents and engineers verifying VirtualWorld UI surfaces, interactions, and state claims live.

This document is the companion to the "STOP: read this before you touch a UI" gate in `AGENTS.md`.

---

## 1. Where State Lives

Understanding where data lives prevents reporting client rendering quirks as server corruption or vice versa.

- **Turn Queue is client-side (`VW.agent`):**
  - `VW.agent.turnQueue`, `.currentTurnIndex`, `.turnNumber`, and `.initiativeRolls` live strictly in the browser memory (`static/js/agent/turn-queue.js`).
  - Closing a browser window or opening a second tab creates an independent client queue instance.
- **World State is server-side:**
  - The graph, characters, items, vitals, area nodes, and ways are held by `VirtualWorld` in Python (`/api/state`).
  - Authoritative persistence lives in `data/autosave.json` or the scenario file.
- **A second browser tab is a safe sandbox:**
  - Because client-side UI drafts are local to the tab, opening a second tab allows you to inspect DOM elements, open modals, and probe controls without disturbing an ongoing human turn session, provided you do not commit actions to the server.

---

## 2. Safe Interactions vs Unsafe Actions

When gathering evidence, verify without mutating live world state unless the test explicitly requires state transitions.

### Safe Interactions (Read-Only / Draft-Only)

These interactions inspect surfaces without advancing the simulation or mutating state:

- **Hover:**
  Reveals tooltips, free-look descriptions, and context chips. Hovering has zero turn cost (`free look - no turn cost`).
- **Chip clicks in Human Turn Composer (HTC):**
  Clicking verb or target chips in the HTC modal only drafts input into the composer command line. Nothing executes until the explicit "Act" button is pressed.
- **Opening Context Menus:**
  Opening character, item, or way menus (e.g. Talk / Examine / Trade affordances) inspects options safely.
- **`#player-room` Selector:**
  Changing the room dropdown in the debug toolbar changes the local viewport focus or teleports for inspection.
- **`HumanTurnComposer.request(characterName)`:**
  Directly opens the composer card for the specified character to inspect layout, affordances, and inventory chips without waiting for the character's scheduled turn slot.

### Unsafe Actions (State-Mutating)

Avoid these unless actively verifying turn lifecycle or state transitions:

- **Act / Commit (`#htc-act` or Enter):**
  Executes the queued verb, applies deltas to the server state, triggers vital decay, and advances the turn.
- **Dismissing HTC via Escape or Backdrop Click:**
  Dismissing the turn modal resolves with `endTurn()`, advancing the cycle and potentially triggering background NPC turns.
- **Skip-React:**
  Forfeits the character reaction turn and commits a pass.
- **Scenario Switching (`/api/scenario/load`):**
  Overwrites the current world graph and discards runtime in-memory state.
- **Server Restarts:**
  Terminates background tick threads, active polling loops, and Server-Sent Event (SSE) streams.

---

## 3. Authoritative Evidence Sources

Never report UI absence or misbehavior from an untested impression. Use these measured sources:

1. **DOM Measurements via `getBoundingClientRect()`:**
   - `offsetParent` is unreliable for elements styled with `position: fixed` or `position: sticky` (such as modals, overlays, scrims, and floating inspectors).
   - Use `el.getBoundingClientRect()` and `getComputedStyle(el)` to verify visible width, height, and display status:
     ```js
     const rect = el.getBoundingClientRect();
     const visible = rect.width > 0 && rect.height > 0 && getComputedStyle(el).display !== 'none';
     ```
2. **Whole-Container DOM Counts:**
   - Always find the true root container before counting controls or sections.
   - Report the total count and labels across all children, including scrolled or collapsible sections.
3. **`data/autosave.json` as Server Truth:**
   - Before claiming an action failed or corrupted an inventory, check `data/autosave.json` or query `GET /api/state`. If the server updated, the issue is purely in the projection layer.
4. **Event Stream Rows:**
   - Inspect `.event-row` elements in the event stream for attribution, glyphs, and mechanical result strings.
5. **Multi-Viewport Screenshots for Scrollable Panels:**
   - Panels can be several thousand pixels tall. Take a screenshot of the top, scroll to the bottom (`el.scrollTop = el.scrollHeight`), and capture the bottom viewport before evaluating available controls.

---

## 4. Server Logs & Terminal Output

Server logs (engine tick messages, route exceptions, LLM prompt dispatches, and trigger evaluations) write to the `stdout`/`stderr` of the launching terminal process.

- The browser DevTools console only records client-side JavaScript messages.
- Silent backend failures (such as a 500 handler caught internally or an unhandled generator exception) are only visible in the server's standard stream.
- In automated/headless sessions, agents must inspect the background server log (see task-696 for automated background log routing).
