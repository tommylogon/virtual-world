# task-340 — Event Stream v2: who/what/where/outcome/debug/story

**Status**: In Review — implemented 2026-08-24, all touched files pass `node --check`,
event-stream.js back under the 600-line rule (587). Browser E2E pending (user tests live).

Design source: `docs/design/event-stream-design-recommendation.md` (2026-08-18) +
`docs/design/event-stream-demo.html` v2/v2.1/v2.2 mockups built with the user before
implementation. Core goal from the user: make it easy to see **who did what where, how
it played out, find what happened and why (debug), and read what actually happened in a
fun way (story)**.

## Refactor first (600-line rule)

event-stream.js was 872 lines. Extracted move-don't-copy modules into
`static/js/stream/`, loaded BEFORE event-stream.js; every legacy symbol stays as a
delegate on the bus:

| Module | Owns |
|--------|------|
| `stream-turn-cards.js` | card open/close/bodyFor, collapse binding + restore rebind |
| `stream-filters.js` | applyFilters, actor dropdown, area filter + scope banner (+ persistence), search |
| `stream-raw-llm.js` | collapsed LLM chips, token meters, raw-response store, parse-error bubbles + streak export |
| `stream-persistence.js` | IndexedDB persist/restore (cap raised 500 → 2000) |
| `stream-scrubber.js` | timeline minimap: segments, scroll head, click-to-jump |
| `stream-control-mode.js` | isAutonomous/getControlMode/cycleControlMode |

## What was already live from the old doc

Actor filter wiring, XSS escaping, area filter + scope banner, turn cards, skill badges,
game-clock labels, parse-error viewer (task-238) — verified before starting.

## New features

- **Card fragmentation fixed**: results no longer log as `system-msg` (which closed the
  turn card mid-turn and split every acting turn into two cards). New row kinds
  (`msg-result/narrated/reflection/whisper/crisis/prune`) stay INSIDE the acting
  character's card.
- **Outcome-tinted results**: agent-engine logs results via
  `events.log(text,'msg-result',{outcome})`; success=green border+✓, failure=red+✕,
  minor=noop rows dimmed ℹ.
- **Narration marked**: AI-narrated action results render as gold 🎭 `msg-narrated`
  rows instead of being indistinguishable from engine output.
- **Whispers visible**: directed whispers render 🔒 `actor → target:` italic rows
  (task-248 data made visible).
- **Crisis replans explained**: replan row is `msg-crisis` and says WHY (critical need
  label from PlanTracker.criticalNeeds or threat).
- **Prune notifications**: ContextWindowManager pruning emits ✂ `msg-prune` (once per
  signature, not per call).
- **Collapsed LLM chips**: request/response payloads render one-line chips (click to
  expand) with ~token meters (amber ≥7k). Reordering became moot — the outcome reads
  above a one-line chip.
- **Phase pills**: observe/think/decide/act/react get colored pills per phase.
- **Area transitions**: trackAction's existing area-change detection also emits a
  `─── actor · A → B ───` divider (area-filter aware via data-stream-area).
- **Time gaps**: ≥30 unlogged game-minutes emit `— N minutes pass —`; day rollover noted.
- **Turn-queue strip**: pinned strip shows up-next order; human slot glows pink 🎤.
  Rendered on advanceTurn from VW.agent.turnQueue.
- **Timeline scrubber**: sticky minimap, colored density segments, click-to-jump,
  purple head tracks scroll.
- **Stream search**: filter-bar input hides non-matching cards + match count.
- **Story mode**: ▤ / ▥ / 📖 buttons toggle cards/compact/story (persisted in
  localStorage). Story strips mechanics and renders serif small-caps scene lines,
  italic inner voice, dialogue, narration — the session as readable fiction.
- **Reflection styling**: 🧠 memory reflections auto-rerouted to purple reflection rows.
- **Persistence debts partially paid**: cap 500→2000 (DOM keeps 5000); area filter now
  survives reloads. Structured event store still open (see follow-ups).
- **Hover relative time** on bubbles (tickToRelative surfaced).

## Deliberate deviations from the mockup/demo

- LLM-detail-after-outcome ordering NOT done via buffering (llm-client logs
  synchronously around the call) — solved by collapse instead.
- Recalled-memory annotation API exists (window._lastRecallStats consumed if set fresh)
  but nothing SETS it yet — needs a small memory-context.js hook (follow-up).
- Provenance chips on triggers not wired (needs backend node-id threading).
- Heard-from labels skipped (backend sound.py change, diminishing returns).

## Round 3 — soft failures lied about success (found via the ✕/✓ badges)

User question "did Miki understand she couldn't use the can?" exposed an engine bug:
contextual failures (`_contextual_failure` in use/consume/take actions) RETURNED their
prose instead of raising, so `/api/action` reported `success: true` (routes/action.py
only sets `failed` on ValueError). Downstream consequences: result rows showed green ✓
on failed actions, PlanTracker.trackStep counted useless attempts as PROGRESS (so the
3-strike 🚫 step-blocking never fired), and only the react-phase prose carried the
failure. Fixed by raising ValueError with the IDENTICAL message text at all soft sites:
use_item, use_item_on pre-check + both "nothing happens" returns + scenery/failure text,
eat/drink, take. The nested `use X on Y → self.use_item()` caller already catches
ValueError, so composition is unchanged. Tests updated (6 in test_descriptive_targets
now expect pytest.raises; eat-rock test likewise). Full suite: **1100 passed, 1 skipped**.
Net effect for agents: failure prose unchanged AND success=false now flows to the plan
tracker (she stops retrying dead ends) and to the stream (✕ not ✓).

## Round 2 — fidelity fixes after first live look

- **Turn cards no longer fragment via system chatter**: only user commands and hard
  errors close a card; engine system rows (match info, skill text) stay inside the
  acting turn's card. `logPhase` observe/think force a fresh card so an actor's NEXT
  turn doesn't merge into the previous one.
- **Actor inheritance**: rows logged without an explicit actor (actions, results,
  emotes, mid-turn system rows) inherit the open card's actor instead of showing ⚙️.
- **LLM chip overflow**: model names ellipsize (max 200px) while the token meter and
  recall note stay visible (flex-shrink: 0).
- **Pills tightened**: smaller padding/font so phase markers read as chips, not rows.

## Verification

- `node --check` green on event-stream.js, llm-client.js, agent-engine.js and all six
  new stream/* modules.
- Legacy callers confirmed working via delegates: main.js:748 restoreLog, main.js:779
  _persistLog interval, inspector area-view EventBus.getActionIcon.
- Pending: browser E2E (server was down per AGENTS.md no-start rule) — run a few turns,
  confirm cards stay whole, chips expand, scrubber jumps, story mode reads well,
  reload keeps area filter + more scrollback.

## Follow-ups

- Structured event store (kills raw-HTML fragility across redesigns + feeds replay export)
- Replay/story EXPORT button (story mode currently view-only)
- Set window._lastRecallStats in prompt-builder/memory-context.js for recall annotation
- Trigger provenance chips (node-id threading from backend)
