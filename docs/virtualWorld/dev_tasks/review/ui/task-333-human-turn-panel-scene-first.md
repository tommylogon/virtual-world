# Task 333 — Human Turn Panel v2: scene-first redesign

**Status:** In Review — Phase 1 implemented 2026-08-24 (scene snapshot
endpoint + discovery flags + scene-first composer); pytest 1100 green;
pending browser E2E (needs server on :4444). Phases 2–4 still todo.

## Why (from taco_bell playtest)

The current human-turn modal (`static/js/agent/human-turn-composer.js`) is a
database form, not a game interface:

- 7 labeled fields (action/item/target/relation/speech/volume/emote/memory)
  that force the player to know verb vocabulary and type exact names.
- The context area renders the **LLM persona prompt** ("You are jake
  halloway. Personality: ...") — that text is for the model, not the player —
  and it truncates, so it's noise that also hides usable info.
- The area bar reads "0 items · 0 people · 0 exits" in rooms that have all
  three — wrong data source, so the one piece of real orientation info lies.
- No answer to "what have I found, what do I see, who is here" — the three
  questions every player asks every turn.
- Speech+emote is the most common human turn in practice, but it's buried
  among fields sized for every possible action equally.

Goal: easier, faster, more natural turns for human players — and a shape
that still works when a second human joins later.

## Concept: scene-first panel

Replace the form-first modal with three zones:

### 1. Scene view (top) — answers "where am I, what/who is here"

- Render the current area the way the engine already describes it: exits
  (clickable → `go`), items visible here (clickable), characters present
  (clickable, showing their last visible emote/body language).
- Clicking an entity opens a small context menu of valid verbs for it:
  item → Examine / Take / Use / Open / Search...; character → Talk to /
  Examine / Give / Steal / Attack...; exit → Go / Examine.
  Picking one fills (or directly submits) the structured action.
- Discovery-aware: things you've examined/taken get a subtle marker;
  `current_state: "hidden"` items only appear after a successful search.
- Data source: existing graph queries + area_description output — no new
  engine state. The area-bar counts must be fixed to read the same source.

### 2. One-box input (middle) — say and act without mode-switching

- Single input, MUD-style but forgiving: text starting with a known verb
  parses into the structured action (autocomplete on item/character names
  from the live scene, not a static list); anything else is speech at the
  current volume.
- Volume (say/whisper/shout/scream) as a compact toggle next to the box;
  emote as a second small inline field — the two things humans actually do
  every turn get permanent, tiny controls.
- Advanced fields (relation, memory, raw JSON) collapse into an expander
  for the rare turns that need them. JSON mode stays for power use.

### 3. Character strip (bottom) — your own state, not your persona

- Vitals, active conditions, carried/worn items (clickable → drop/unequip/
  use). The persona prompt moves out of the player's face entirely; if the
  player wants to read their character's inner voice, a collapsible
  "what you know" section can show memories/notices.
- Turn flow: show the next actor up and the last few events inline so the
  human knows why it's their turn and what just happened.

## Design decisions round 2 (2026-08-23, Tommy's answers)

- **Look vs Examine split (corrected by Tommy 2026-08-24)**: Look at an
  item, way, area, or character is FREE — and it is not an action at all.
  The panel delivers look results as HOVER PREVIEWS on the scene chips
  (hover = what you would see; no turn end, no server action). **Examine
  remains a normal turn-ending action** in the context menus. Deep
  character examine (revealing visible non-hidden stowed/worn gear) is a
  DEFERRED bigger feature, separate line.
- **Ways must surface real richness**: pass-through message,
  visible_in_direction / view from the far side, custom direction labels
  ('up slope'/'down slope', not just N/S/E/W), see-through ways (windows,
  glass doors), doors needing forcing open, doors that close behind you,
  jump/crawl/climb requirements as disabled-with-reason entries,
  {param:x} template substitution in descriptions.
- **Conditions**: non-hidden conditions visible in a dedicated place;
  hidden conditions stay masked; grapple IS a condition so it shows.
- **Activities**: stateful ones (rest etc.) SKIP the character in the turn
  queue while active - panel shows an activity chip + stop control, and
  start controls with durations. Bathing et al. untested so far.
- **Region targeting prep**: advanced section reserves a where picker slot
  (disabled until task-211 lands).
- **Transit tag** likely redundant someday (go forward/back in two-exit
  areas) - cleanup candidate, no action now.
- **Money**: none today; future = generic super-item (coinbag with coins,
  uses = count). No engine change needed.
- **Panel exclusions LOCKED**: no live editing (editor's job), no
  save/load/reset inside the panel.
- **Unknown-name masking**: render via unknown_display_name() but needs UI
  testing; mechanism investigation -> task-339.
- **Darkness**: scene view literally degrades under low light (yes).
- **Never show numeric vitals/stats of others**; only legit path is an ITEM
  (medical scanner returning raw or representative values). Observable
  stuff (a maimed arm) comes through conditions/description.
- **No relationships-toward-you display** - not realistic.
- **Humans own their internal emotions** - no computed mood line for
  human-controlled characters.
- **Confirmation screen before Act, toggleable on/off** - yes.
- **No macros/favorite aliases for now.**
- **Event-stream pruning dropped** (history lives in the event stream).

## Phasing

1. **Phase 1 — scene view + click-to-target.** Fix area-bar data source;
   render scene entities with context menus that fill the EXISTING form
   fields (form hidden behind a "detailed" toggle). Lowest risk, biggest
   usability jump.
   - **Endpoint gap (found via v2.3 mockup)**: `TriggerSystem
     ._get_available_actions()` (trigger_system.py:1406) is not exposed by
     any route — the data-driven menu contract needs a per-entity
     available-actions fetch (or fold into a scene-snapshot endpoint).
     Mockup reference: `docs/design/human-turn-panel-v2-mockup.html` v2.3.
2. **Phase 2 — one-box input.** Verb parser + live-name autocomplete;
   speech-default behavior.
3. **Phase 3 — character strip + discovery markers.** Vitals/conditions/
   inventory strip; seen/taken/hidden states in the scene view.
4. **Phase 4 — multi-human prep.** Turn queue display, per-player panels,
   speech targeting (@character).

## Notes

- Keep the structured action schema untouched — this is purely the human
  front door; agents keep their own path.
- The event-stream grouping bug (bug_22) interacts with turn flow display;
  fix there first or together.
- Current modal file is the reference for submit semantics (Act vs End
  Turn, JSON preview, datalists) — reuse its API calls.

## Files likely touched

- `static/js/agent/human-turn-composer.js` (or successor module)
- new `static/js/agent/turn-scene-view.js` (scene rendering + context menus)
- `routes/` scene snapshot endpoint if area data isn't already fetchable
  in one call
- CSS for the panel

## Mockup feedback log (2026-08-23, v2.1)

Design decisions locked in from Tommy's playtest of
`docs/design/human-turn-panel-v2-mockup.html`:

- **Compose-then-commit**: menus never execute; every pick only fills the
  draft. Nothing fires until Act.
- **One turn = do + say + emote combined** into a single structured payload
  (e.g. go south + "stay here ill check the door" + sneaks-through emote).
  Three always-visible composer rows: ⚙ do / 🗨 say (+volume) / 🎭 emote.
- **give/steal menus list WHAT**: second-stage picker (give → your carried
  items; steal → target's visible items). Prepositions in the draft text:
  give X **to** Y, steal X **from** Y, use X **on** Y.
- **Carried/worn chips get context menus** (examine/use/eat/drink/drop,
  remove for worn).
- **Feed shows results only** — never the in-progress draft.
- **Human react phase (gap found, corrected)**: agents' react is NOT just
  memory — after the action result returns, react produces inner monologue,
  felt-emotion update, reactive speech, reactive emote, THEN memory
  (agent-engine.js:568-597, `buildResultReactionPrompt` feeds the result in).
  Humans currently get none of it: no result-processing step, no emotion
  update, no memory, and the old modal's memory field is dropped by
  `routes/action.py`. Human turn flow must mirror think→act→react:
  **compose → Act → see result → react (say/emote/inner-note bound to the
  result) → pass**, with engine-side auto-capture (deterministic memory
  line + emotion nudge, no LLM call so human turns stay instant) and the
  composer memory field persisted as manual addition. Optional later: LLM
  "inner voice" suggestion the human can accept/edit/toss.
- **Lock/unlock stays trigger-based (task-336 cancelled)**: unlock already
  has many author paths — item `on_use` (buttons), `on_use_on` keycards,
  way-level triggers checking inventory. No engine verbs; panel menus map
  Lock/Unlock picks onto `use_on <candidate> on <way>` drafts (or examine)
  and render availability from trigger presence + way state.
- **React boundaries (locked with Tommy)**: react = say + emote + optional
  memory ONLY — no second world interaction, or the turn never ends.
  Manual memory sits on top of an automatic deterministic line so multi-
  human tables don't depend on diligent journaling. Reacts ride the same
  witnessed-event pipes as agent speech/emotes → works for a future
  4-player human DND-style session out of the box.

## Mockup feedback log (2026-08-24, v2.4)

Tommy's corrections + final nice-to-have pass on
`docs/design/human-turn-panel-v2-mockup.html` (all now in the mockup):

- **Look = hover previews, not an action** (correction above). Hovering any
  chip — area button, people, things, ways, carried/worn — shows a look
  card with the entity's description/state; footer reads "free look · no
  turn cost". Examine stays in menus as the turn-ending version.
- **Activities**: character strip shows an active activity chip
  (⏸ Waiting · 5m ✕) that stops on click; "+ activity" menu starts
  Rest/Wait/Sit/Meditate with durations; toast notes the queue skips you.
- **Way richness**: custom dir labels ('under the neon arch'), see-through
  Serving Window with view-to-far-side text, Roof Hatch gated by climbing
  AND jammed (Force-it-open disabled with reason), Swinging Door closes
  behind you (toast on go). Chip markers: ⛰ climb-gated, 🔧 jammed.
- **Darkness**: header 🌙 toggle degrades the scene — dimmed chips,
  swapped dark description ({param} substitution still applies), look
  cards collapse to "...something / too dark to make out much".
- **Stranger masking**: clerk renders as "the woman behind the counter"
  via unknown_display_name semantics; Talk → introduce flips her to her
  real name (demo of task-339's mechanic candidate).
- **Confirm-before-Act**: advanced section has the toggle (default ON);
  Act opens a confirm box showing the exact payload with cancel/confirm.
- **Raw JSON mode**: "▸ raw json" swaps the composer rows for one editable
  JSON textarea with its own Act button (invalid JSON rejected).
- **Where-picker slot**: disabled select reserved under advanced for
  region targeting (task-211).
- **Autocomplete**: ⚙ do input has a datalist fed from live scene entities
  (items + known characters + way destinations).
- **Search reveals**: area search actually adds the Blue Butterfly Earring
  chip to Things you can see (previously result-text only).
- **Grapple lands**: tyler's digest grab now adds a real 'Grappled (by
  tyler)' condition chip to your condition row.

Still open from earlier logs: endpoint gap for data-driven menus
(`TriggerSystem._get_available_actions()` exposure) — Phase 1 blocker.

## Mockup feedback log (2026-08-24, v2.5)

Engine-behavior corrections from Tommy — the earlier task text/mockup was
stale documentation, the engine is the source of truth:

- **Doors auto-open on go** — no open→go two-step. Go succeeds through any
  closed way unless locked, blocked, or needing force. Menu label says
  '(opens as you go)' on closed ways instead of disabling them.
- **Dash bursts through closed doors** — dash auto-opens closed ways
  mid-stride; a locked way still stops it (and consumes the turn, no
  burst phase granted).
- **Locked is hidden knowledge** — no 🔒 on chips or hover cards until
  the character examines the way or fails to go through; the panel then
  remembers per-way ('knownLocked') and later menus show the lock.
  Implementation note for Phase 1: the scene snapshot needs this
  discovered-state flag exposed alongside way state, or the panel will
  leak locks.
- **Force-open is NOT a separate action** — going on a jammed way rolls
  the skill check inline: d20+mod vs DC in the result text; success
  bursts through AND un-jams the way; failure bounces and eats the turn.
  No 'Force' menu entry anywhere; jammed ways just say '(force check)'
  on their Go entry.
- **Closable is a way property** — not all ways can be closed; the Close
  menu entry is omitted entirely when `closable: false` (Serving Window
  demo), and the hover card notes why.
- **Blocked is a live gate** — while a Grappled condition is active,
  every Go entry renders disabled with the block reason.

## Mockup addendum (2026-08-24, v2.6)

- **Windows are full ways too** — open, close, AND go (walk/climb
  through), same auto-open-on-go rule as doors. Serving Window now demos:
  see-through even while shut (view-to-far-side on hover), Open/Close in
  its menu, Go '(opens as you go)'. The `closable: false` demo moved to
  the Dining Archway — an open arch is the natural non-closable way.

## Mockup addendum (2026-08-24, v2.7)

- **Menus never pre-leak mechanics** — Go labels are clean ('Go up →
  Rooftop'), no 'opens as you go' / 'force check' hints. Discovered-state
  flags (`knownLocked` / `knownJammed`) unlock the hints only after
  the character examines the way or fails to go through it: then chips
  show 🔒/🔧, menus show 'locked' / 'needs force', hover explains in
  diegetic wording. Result text still shows the roll — that's the feed,
  not a menu.

## Implementation log (2026-08-24, Phase 1)

Phase 1 (scene view + click-to-target) implemented against the v2.7
mockup contract:

**Backend**
- `engine/scene_snapshot.py` — new read-only module: one-call scene
  payload per player (area + light/dark, people with stranger masking via
  `unknown_display_name()`/`has_met`, visible items excluding
  `current_state: hidden` with their real `available_actions`
  from `TriggerSystem._get_available_actions()`, ways reporting only
  DISCOVERED state, and the you-strip: vitals/conditions/carrying/worn/
  activity/recent memories).
- `routes/scene.py` + app.py registration — `GET /api/scene/<player>`
  (the endpoint gap this task flagged is closed).
- Way discovery (v2.7 rules): `Player.known_way_aspects`
  ({(area, direction): set}) + `learn_way_aspect`/`knows_way_aspect`.
  Set by examining a way (engine/items/examine_actions.py) and by failed
  go attempts on locked/blocked ways and failed needs_open checks
  (engine/movement.py). The snapshot reports locked/blocked state ONLY
  when discovered — otherwise plain closed. No leaks.

**Frontend**
- `static/js/agent/turn-scene-view.js` (new) — chips for area/people/
  things/ways; hover = free-look card (no turn cost); click = data-driven
  context menu that FILLS THE DRAFT via the composer fields (compose-
  then-commit; never submits). Darkness degrades client-side
  (dimmed chips, 'something'/'too dark to make out much'). Way menu labels
  stay clean per v2.7 — no 'opens as you go'/'force check' pre-hints;
  known_locked/needs_force hints appear only after discovery.
- `human-turn-composer.js` — scene section replaces the lying area-bar
  counters AND the LLM persona-prompt dump (#htc-context hidden); the old
  field grid collapses behind a 'Detailed' toggle; JSON mode unchanged;
  submit path untouched (same promise contract).
- `api.js getScene()`; index.html loads turn-scene-view.js before the
  composer.

**Known gaps (deliberate, later phases)**
- Unmet strangers: Examine can't resolve masked names server-side, so the
  menu offers Talk-to first — feeds task-339.
- Carried/worn strip, react phase, digest/interject = Phase 3 / task-334.
- Lock/unlock has no verbs (task-336 cancelled) — unlock rides
  use-on keycards; menus omit lock entries.
- known_way_aspects is runtime-state (mirrors discovered_exits precedent,
  not serialized in Player.to_dict yet).

**Verification**: pytest tests/test_scene_snapshot.py (8 tests: masking,
hidden items, actions passthrough, way-state gating before/after
discovery, you-strip, darkness flag, movement+examine discovery wiring);
full suite 1100 passed / 1 skipped; node --check on all touched JS;
app import smoke OK. Browser E2E still to do (server needed).

## Browser-test fixes (2026-08-24, first E2E round)

- **scene unavailable (reading 'getScene')** — turn-scene-view.js called
  `window.ApiClient`; api.js declares a top-level `class ApiClient`
  which is a global *binding*, not a window property. Fixed to bare
  `ApiClient` (like the rest of the app).
- **Non-turn mode passed the turn to the next character on Act/End** —
  `_humanTurn`'s `else if (!config.turnBased)` branch rotated
  `controllingPlayer` through the roster. Removed: turn handoff is a
  turn-based concept; in non-turn mode the human keeps control.
- **Correction to the log below**: unmet strangers CAN be examined —
  `_match_character_name` (engine/matching.py) resolves exact/substring/
  fuzzy names, aliases, AND description words, so drafting the masked
  label ('the woman behind the counter') resolves server-side. The panel
  now always offers Examine with the display label; no task-339 blocker
  here (task-339 stays about the acquaintance mechanic itself).

- **500 on /api/scene (area_node_id)** — the accessor lives on the
  VirtualWorld facade (`world.area_node_id` → NodeIDHelper), not on
  PlayerManager; the test mock had masked the difference. Fixed via a
  getter chain in scene_snapshot with the canonical format as fallback;
  test fixture now sources it from the facade like production. Live
  smoke against the loaded autosave world builds the scene cleanly.

## Full redesign implemented (2026-08-24, same day)

Tommy called it: no incremental phasing — build the whole mockup. The
panel is now the v2.7 three-zone layout:

- **human-turn-composer.js rewritten** as the full panel: header (title ·
  tick · next up), scene grid + What-happened feed, You strip, composer
  rows (⚙ do one-box / 🗨 say + volume segment / 🎭 emote / 🧠 memory),
  phase bar, confirm-before-Act overlay, advanced (relation + reserved
  where-picker + confirm toggle), raw JSON mode. Old field grid and quick
  pills are gone; the submit contract is preserved.
- **One-box parser**: verb list → structured draft; use X on Y / give X
  to Y / steal X from Y prepositions; volume-led speech ("scream help");
  unknown verbs become speech. Datalist fed from the live scene.
- **You strip** (new turn-you-strip.js): vitals bars, condition chips,
  carrying/wearing chips with menus (examine/use/eat/drink/drop, remove
  for worn), activity chip with stop (drafts wake), what-you-know
  (recent memories). Backend: worn now reads EDGE_EQUIPPED edges (the
  player.equipped dict is a desync-prone cache) and strip entries carry
  actions + desc.
- **Feed + digest + interject** (new turn-feed.js): ring buffer over the
  event bus renders the panel feed; entries since the last panel close
  form the "since your turn" digest with an interject input that posts
  guest speech without consuming the turn (task-334 lanes 2+3,
  client-side).
- **React phase + dash burst + auto-memory** (task-334 lane 1):
  agent-engine._humanTurn is now compose → execute → (dash grants one
  more action slot) → deterministic auto-memory line → react (say/emote/
  memory bound to the result) → pass. Execution extracted to
  _executeHumanReply. Correction: the old claim that /api/action drops
  the memory field was wrong — client-side _storeReactionMemory always
  stored it.
- **Stranger meeting fixed at the root**: the panel bypassed
  get_area_description, so panel-only players never registered meetings
  (masked forever). scene_snapshot now mirrors the task-154 sighting
  contract (masked first sighting → register → name on next render).
  Talk-to no longer promises an introduction that doesn't exist; see
  task-339 for the full findings.

**Verification**: pytest 1100 green (one flaky run raced the live
server's autosave write — passed clean on rerun); node --check on all six
touched JS files; live scene smoke against the autosave world. Browser
E2E of the full panel still to do.
