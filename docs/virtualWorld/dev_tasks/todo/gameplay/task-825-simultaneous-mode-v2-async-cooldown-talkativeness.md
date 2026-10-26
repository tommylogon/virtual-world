---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
---

# task-825: Simultaneous mode v2: async cooldown timers with talkativeness and reactive cadence

**Filed:** 2026-10-14
**Related:** task-824, task-854

## What

Replace batch-at-once simultaneous turns with independent per-character async cooldown timers, and implement human-like reactive conversational cadence in The Commons (startup talkativeness randomization, cold-start timer staggering, mention fast-tracking, and floor-yielding, strictly excluding simple NPCs).

## Why

The original simultaneous turn mode and initial Commons pacing triggered characters on fixed identical intervals (e.g. all waking up at T=25s), producing artificial thundering herds where multiple LLMs fire simultaneously and talk over each other. Real conversations require asymmetric pacing, randomized starting cadence, reactive wake-up upon direct mentions or DMs, and floor-yielding cooldown extensions so participants do not monologue. Simple NPCs must be excluded from LLM timers.

## How

1. **Startup Talkativeness Randomization & Staggering**
   - For all active LLM participants (`control_mode === 'llm'`) in `CommonsAgent.scheduleAll(initialStartup)`:
     - If talkativeness is unconfigured in `config.talkativenessByCharacter`, assign a randomized baseline pace across the active range (15s to 60s).
     - On initial startup, stagger the initial countdowns across a random phase offset (e.g. 15% to 85% of base cooldown) so characters wake up at distinct seconds instead of all at T=25s.
     - Strictly ignore `User`, humans (`control_mode === 'human'`), and simple NPCs (`control_mode === 'npc'`).
2. **Reactive Notification Wake-Up**
   - In `CommonsAgent.onMessageReceived(message)`:
     - Identify other active LLM members in the channel.
     - If the message is a direct message or contains an @mention of their name, accelerate their pending deadline to 1.5s - 3.5s so they react quickly to direct communication.
3. **Dynamic Burst Governor & Floor-Yielding**
   - When a character acts and successfully posts a message in a channel, evaluate burst momentum:
     - Characters roll a burst chance weighted by their talkativeness pace and personality traits (`impulsive`, `talkative` vs `stoic`, `reserved`).
     - On burst hit (under safety cap of 3), fast-track next turn to 1.5s - 3.5s for rapid double-texting.
     - On burst miss or when reaching the cap, reset burst momentum and apply standard cooldown (+8s if coming off a multi-message burst) to yield the floor.
   - Physical state gating: sleeping or unconscious characters (`state: 'sleeping' | 'unconscious'`) are excluded from timers.
4. **Clean Verification**
   - Unit tests in `tools/unit/test_commons_agent.js` covering startup randomization, simple NPC exclusion, initial staggering, mention wake-up, physical state gating, and burst governor double-texting with safety caps.

## Integration

This augments both `VWSimultaneous` turn infrastructure and `CommonsAgent` async timer loops:

| Mode | Behavior |
|---|---|
| No turns | As today |
| Sequential | Round-robin, one at a time |
| Random | Random order per round |
| Simultaneous (async) | Independent per-character cooldown timers with reactive cadence |

## Browser UI and intended live verification

Intended UI home: `/commons` participants panel and turn-mode selector -> **Simultaneous**

Current availability: always (The Commons page is live in the app with talkativeness sliders)

Live steps when available:
1. Open http://localhost:4444/commons and observe the Participants panel
   - expected: Active LLM characters show randomized turn pace sliders rather than all defaulting to identical 25s values; simple NPCs show 'Simple NPC: no LLM turn' note with disabled controls.
2. Resume simulation in The Commons
   - expected: Characters start their initial turns at staggered intervals rather than all firing simultaneously at 25 seconds.
3. Post a message mentioning a character (e.g. '@Mira hello') or send a Direct Message
   - expected: Target character's presence accelerates and responds promptly rather than waiting for a full initial cooldown cycle.
4. Observe character turns after a message is sent
   - expected: The speaker yields the floor and does not post consecutive messages before others have an opportunity to react.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Commons participants show randomized starting talkativeness and desynchronized startup execution with simple NPCs excluded.
   - observed: Planned; to be tested upon implementation.
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: Inspecting /commons and posting direct messages verifies reactive wake-up and floor-yielding cadence without console errors.
   - observed: Planned; to be tested upon implementation.
3. Run the targeted regression test for the mechanism.
   - expected: Node unit tests in tools/unit/test_commons_agent.js and tools/unit/test_simultaneous.js pass with 0 failures; npm run build:ts compiles with 0 errors.
   - observed: Planned; to be tested upon implementation.

## Acceptance

- [ ] Unconfigured LLM characters receive randomized starting talkativeness on startup (excluding simple NPCs and humans).
- [ ] Initial countdown timers are staggered on startup to eliminate the 25s thundering herd.
- [ ] `CommonsAgent.onMessageReceived` fast-tracks recipients on direct messages and @mentions to 1.5s - 3.5s.
- [ ] Characters that post a message evaluate burst momentum (double-texting under cap 3) or yield the floor.
- [ ] Sleeping or unconscious characters (`state: 'sleeping' | 'unconscious'`) are excluded from timers.
- [ ] Simple NPCs (`control_mode === 'npc'`) are never scheduled for LLM turns or randomized.
- [ ] Unit tests pass cleanly in `tools/unit/test_commons_agent.js`.
- [ ] TypeScript compiles with 0 errors.

## Files

- `static/js/commons/commons-agent.ts`
- `static/js/commons/commons-state.ts`
- `static/js/commons/commons-ui.ts`
- `tools/unit/test_commons_agent.js`
