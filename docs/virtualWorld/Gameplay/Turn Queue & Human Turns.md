# Turn Queue & Human Turns

How turn order works, how the human turn panel knows it's someone's turn,
and why the always-available command line is not a bug.

Source of truth: `static/js/agent/turn-queue.js` (state lives on AgentEngine
as `.turnQueue` / `.currentTurnIndex` / `.turnNumber` / `.initiativeRolls`).
Config flags come from browser settings (`config.js`, IndexedDB):
`config.turnBased`, `config.turnOrder`, `config.ghostMode`,
`config.controllingPlayer`.

## The queue

- `TurnQueue.initialize()` builds the queue from all non-dead players
  (dead included when `ghostMode`), sorted by `config.turnOrder`:
  - **sequential** (default): alphabetical
  - **random**: shuffled
  - **initiative**: d20 + DEX modifier per character, highest first,
    alphabetical tiebreaker (rolls stored on `initiativeRolls`)
- Index resets to 0; `turnNumber` resets too.
- `TurnQueue.reconcile()` re-runs initialization whenever the live roster
  differs from the queue (character added/killed mid-run) while preserving
  `turnNumber` so the clock doesn't reset.

## Advancing

- `TurnQueue.advance()` steps `currentTurnIndex` forward (wrapping) and
  sets `config.controllingPlayer` to the character whose turn it now is —
  this is what the human turn panel keys off.
- When the index wraps past the last actor, **one full turn cycle ends**:
  `endTurn()` increments `turnNumber` and calls `ApiClient.applyTurn()`,
  which advances the clock and applies decay/tick effects ONCE per cycle
  (never inside individual commands — see AGENTS.md activity gotcha).
  World state is refetched afterward so fresh turn_events render before
  the backend clears them.
- `random` order reshuffles each cycle (`reshuffleRandom`, task-310);
  `rerollInitiatives()` re-rolls d20+DEX for initiative order while
  keeping the current actor current.

## Human turns vs the command line

Two separate input paths, both intentional:

1. **The human turn panel** (turn modal/composer) appears when the queue
   slot belongs to a character under human control
   (`config.controllingPlayer`). It plays by queue rules: compose an
   action, end turn, advance passes control to the next actor.
2. **The always-available command line / guest-speaker path** writes into
   the event stream from outside any queue slot. This is a deliberate
   godmode-level override for director-style input — it does NOT wait for
   turns and does NOT consume the typing character's queued slot unless a
   feature explicitly ties them together.

Don't "fix" the command line being available out-of-turn, and don't make
the panel appear outside the controlled character's slot — both behaviors
are the design.

## The scene-first panel (task-333, full redesign)

The human turn panel is the mockup's three-zone layout: scene grid
(clickable area/people/things/ways chips) beside a "What happened" feed,
the You strip (vitals, conditions, carrying/wearing chips, activity,
"what you know"), and a composer of four always-visible rows —
⚙ do / 🗨 say (+volume) / 🎭 emote / 🧠 memory. **One turn = do + say +
emote together** in a single structured payload. Hover = free look (no
turn cost); click = a context menu that only FILLS the draft — nothing
fires until Act (compose-then-commit, with a toggleable confirm screen).
Raw JSON mode and an advanced expander (relation, reserved where-picker,
confirm toggle) live under the composer.

Turn shape mirrors the agents' think→act→react (task-334): compose →
Act → (a successful dash grants ONE more action slot) → deterministic
auto-memory line → react phase (say/emote/memory bound to the result —
no second world interaction) → pass. A "since your turn" digest with an
interject input (guest speech, doesn't consume the turn) greets the next
panel open.

- Data comes from `GET /api/scene/<player>` (`engine/scene_snapshot.py`):
  people (stranger-masked via `unknown_display_name()`), visible items
  with their real `available_actions`
  (`TriggerSystem._get_available_actions()` contract), ways out, and your
  own vitals/conditions/carrying/wearing (worn reads EDGE_EQUIPPED
  edges, not the desync-prone `player.equipped` cache).
- **Hidden way state is per-player knowledge**: locks/blocked/needs-force
  are only reported after this character examined the way or failed to go
  through it (`Player.known_way_aspects`, set in movement + examine).
  Until then a locked door reads as plain closed — to the panel AND to
  the room description.
- **Names are learned by HEARING them spoken** (task-339): a name said
  aloud in earshot — self-intro, direct address, third-party mention —
  teaches it to everyone present who doesn't know it yet. Seeing someone
  is recognition only (stable masked label); re-looking never reveals a
  name. Examine masks unmet names unless the character wears a
  `nametag`-tagged item.
- Way rules reflected by menus: doors auto-open on go/dash unless locked,
  blocked, or needing force (`needs_open` = the on-go skill check); there
  are no lock/unlock verbs (task-336 cancelled) — unlocking rides
  use-on keycards.
- Darkness degrades the scene client-side when
  `scene.area.dark` (ambient light < 40).

## Multi-human

The queue is name-based, not agent-based: any number of queue entries can
be human-controlled. Each human acts only when their entry comes up;
agent slots fire automatically via the autopilot interval. Future
react-phase/digest work (task-334) builds directly on these semantics.

## Related

- task-310 random reshuffle · task-322 R5 vital thresholds consumed per
  turn · task-334 react phase design · task-241 non-turn-based stepping ·
  task-333 scene panel (mockup: `docs/design/human-turn-panel-v2-mockup.html`)
