---
type: doc
tags: [system/ai, topic/reflection, topic/turns]
---

# Agent Engine

## What you can do

The Agent Engine powers autonomous LLM-driven characters that observe the world, think, speak, and act - using the same `/api/action` endpoint as human players, so they live by the same rules. In reactive mode each turn splits into a think-decide phase (inner monologue plus a structured action, speech, emote, and affect impulses) and a react phase (responding to the outcome); non-reactive mode combines both into a single call. The engine handles turn ordering, rate limits, needs- and threat-driven replanning, memory intermediator synthesis, two-stage prose-to-action interpretation, and involuntary reactions like sneezes mid-speech. See [[Simulation Philosophy]] and [[Characters/Interiority & Subtext]] for the design principles behind actor isolation and internal state.

## Architecture

The engine lives in `static/js/agent-engine.ts` as the `AgentEngine` class (`window.VW.agent`, global `agent`). It coordinates several sub-modules:

| Module | File | Role |
|--------|------|------|
| `AgentEngine` | `agent-engine.ts` | Main loop, turn orchestration, affect dispatch, inner monologue persistence |
| `PromptBuilder` | `agent/prompt-builder/` (`index.ts`) | Pure functions for building LLM prompts (plus async `memory-context.ts`) |
| `TurnQueue` | `agent/turn-queue.ts` | Turn ordering, pause/inert filtering, and advancement |
| `AgentMemory` | `agent/memory-manager.ts` | Memory storage + reflection (backend `Player.memories`) |
| `PlanManager` | `agent/plan-manager.ts` | Typed multi-step plan generation, MOSIAC + GIMP goal wiring, repair |
| `PlanTracker` | `agent/plan-tracker.ts` | Plan step progress, failure counts, pursuit seeding, replan triggers |
| `PlanGrounding` | `agent/plan-grounding.ts` | Typed plan-step grounding validator (paths, items, people, areas) |
| `RateLimiter` | `agent/rate-limiter.ts` | API rate limiting |
| `ContextWindowManager` | `static/js/context-window.ts` | Token budget and context pruning |
| `ResponseParser` | `agent/response-parser.ts` | Parse/validate LLM JSON output, normalize multi-emotion impulses |
| `ActionNormalizer` | `agent/action-normalizer.ts` | Normalize structured actions into `/api/action` commands |
| `ActionInterpreter` | `agent/action-interpreter.ts` | Two-stage cognition: translate creative prose into structured turn JSON |
| `ThreatDetector` | `agent/threat-detector.ts` | Flag nearby threats for replanning |
| `HumanTurnComposer` | `agent/human-turn-composer.ts` | Human-turn (composer) drive path |
| `TurnSceneView` | `agent/turn-scene-view.ts` | Render current turn scene for the event stream |

## Agent Loop

### Step Cycle (`step()`)

Each agent step processes one character's turn:

1. **Rate limit check** - waits if RPM limit is exceeded
2. **Turn queue** - determines whose turn it is (turn-based mode via `TurnQueue`, filtering dead and `paused`/`inert` characters and preferring server `turn_order_info` when present)
3. **Simple NPC check** - skips LLM work for `simple_npc` characters (they act via backend `tick_turn` / `process_simple_npcs`). Simple NPCs are still **in the turn queue**; their turn just advances without an LLM call. NPC actions are logged to the event stream via `record_turn_event()`.
4. **Rest/Sleep/Unconscious check** - skips if character is busy/resting or unconscious
5. **Reflection** - every 5 turns per character (`charTurnCount % 5 === 0`), triggers memory summarization (reactive mode)
6. **Memory Intermediator synthesis** - `PromptBuilder.buildMemoryContext()` retrieves top scored memories and, when context cues change, synthesizes a single mood-congruent conscious thought (`=== I REMEMBER (CONSCIOUS THOUGHT) ===`) under Strict Actor Isolation
7. **Threat/needs-aware replan** - before think-decide, `PlanTracker.seedFromPlayer()` seeds any server `player.plan` / `active_pursuit`, and `PlanTracker.shouldReplan()` checks for new threats, completed/aged-out plans, repeated step failures, or vitals crossing a critical threshold; if needed, regenerates the plan via `PlanManager.generate()`
8. **Reactive mode** (multi-action loop up to `MAX_ACTIONS_PER_TURN = 5`, gated by turn slots):
   - **Think-decide** (`buildReactionPrompt`): one call produces inner monologue + structured action + speech/volume + emote + optional `emotion` / `learned_names`. When `config.interpreterModelEnabled` is active, `ActionInterpreter.interpretProseToAction()` translates freeform prose into the canonical turn schema.
   - **Act**: execute the normalized action via `ApiClient.action()`, optional AI narration, then the emote (gated on the action not failing or being rejected). Invalid verbs become a natural in-world rejection that flows into the react phase instead of vanishing silently. `PlanTracker.trackStep()` records step success or failure.
   - **React** (`buildResultReactionPrompt`): character reacts to the action outcome with inner monologue, speech/volume, emote, and optional `emotion` / `learned_names`. The prompt makes clear only a moment has passed since the character's own action - others haven't had time to respond, so silence isn't a snub.
9. **Non-reactive mode** (1 LLM call): single `buildReactionPrompt` produces everything in one response; action executed asynchronously.
10. **Turn advancement** - advances the turn queue

### Fresh per-turn context (no assistant replay across turns)

`step()` clears `characterHistories[charName]` at the start of each turn, and `think-decide`, `result-reaction`, and `combined` calls each send a fresh `[system, user]` message pair so stale assistant outputs are not replayed as active context. Continuity across phases and turns comes from `=== YOUR STATE ===`, `=== I REMEMBER (CONSCIOUS THOUGHT) ===`, `=== RECENTLY ===` / `=== WHAT HAPPENED ===`, and `events.getCharacterState()`.

## Character Control Modes & Autonomy (task-244)

Every character resolves to a control mode via `events.getControlMode(charName)`
(`event-stream.ts`):

| Mode | Condition | Who drives |
|------|-----------|------------|
| `'npc'` | `player.simple_npc` | Backend `tick_turn` - scripted behaviors, no LLM |
| `'human'` | `player.autonomy === false` | The human, via commands; the engine **skips their turn** |
| `'llm'` | default | Agent engine - full autonomous LLM turns |

- The `autonomy` flag is **persisted on the player** in the backend graph, so a human stays
  human across reloads. Toggle it from the agent inspector.
- A human-mode turn pauses only that character's progression (`agent-engine.ts`) - the rest
  of the roster keeps cycling when it's their turn.

## Per-Turn State Tracking & Instincts

- **Character state** - `events.getCharacterState(charName)` tracks `lastThought`,
  `lastSpeech`, `lastAction`, `actionHistory` (last 20 with tick + result), `currentArea`,
  `lastActionResult`. Consumers: plan manager (`lastThought`), prompt memory context
  (`actionHistory` -> recent-actions block), agent lens, inspector.
- **Needs/threat-driven replanning (task-92)** - `PlanTracker.shouldReplan()`
  (`agent/plan-tracker.ts`) regenerates the plan when vitals **cross** a critical threshold or
  a new threat appears, re-nudging at most every 5 turns to avoid churn.
- **Closeness gates behavior (task-94)** - `relationshipGuidance(closeness)`
  (`prompt-builder/character-state.ts`) turns each relationship score into a behavioral
  directive on the People-here line ("you want them gone; refuse help..." at <= -50).
- **Speech salience + conversation instinct** - `prompt-builder/conversation-context.ts`
  labels heard lines as *addressed to you* vs *overheard* (salience), and
  `buildConversationInstinct()` nudges characters to join ongoing conversations they're part of.
- **Parse-error inspection (task-238)** - malformed LLM responses are stored in an EventBus
  ring buffer (`events.logParseError`, last 20) and surface as clickable bubbles that expand
  the raw response, so bad outputs are debuggable from the stream itself.

## Involuntary Reactions (task-166, task-534)

`agent/involuntary.ts` post-processes every speech line and emote an attended
character emits, so a hiccup or a sneeze lands *inside* the line instead of
replacing it. It is a LIVEGAME layer only: background NPCs and simple NPCs have
no speech/emote emission path, so the cheap tier never pays for it, and the roll
is **per emitted line, not per turn** (it stays correct under the
timeframe-and-flow model, task-436/437).

**Where the flavor comes from**

| Source | Example | Odds |
|---|---|---|
| Active condition | `frightened` → stutter, `hypothermia` → shiver, `sick`/`poisoned` → cough, `social_breakdown`/`hallucinating` → ramble, `paranoid` → stutter, `sneeze` → sneeze | per-condition `chance` on `SPEECH_TRIGGERS` |
| Condition emote pool | `itch`, `goosebumps`, `sneeze`, plus the conditions above, each with its own pronoun-aware suffix list in `EMOTE_TRIGGERS` | none - see below |
| Situational startle | a new shout/scream in `recent_hearing` → yelp | `STARTLE_SPEECH_CHANCE` / `STARTLE_EMOTE_CHANCE` |
| Trait | `jittery` (aliases `nervous`, `clumsy`) multiplies every roll by `NERVOUS_BOOST` | ~1.8 |
| Random baseline | hiccup / burp / yelp with no trigger at all | `RANDOM_SPEECH_CHANCE` 0.06, `RANDOM_EMOTE_CHANCE` 0.04 |

**Non-obvious behaviors worth knowing**

- **Condition-driven emotes have no chance roll at all.** The `EMOTE_TRIGGERS`
  loop fires the pool unconditionally whenever the condition is present; only
  the *speech* path and the random baseline roll. A conditioned sneeze therefore
  always shows up as an emote, and never as the random baseline tic.
- **The two condition loops resolve ties differently.** `speech()` keeps rolling
  past a condition whose roll fails and can land on a later one, so with two
  active conditions either may fire; `emote()` returns on the **first** matching
  condition in table order and never considers the next. With both `sneeze` and
  `frightened` active, the emote is decided by declaration order, not by
  severity - reorder the table and the output changes.
- **A startle short-circuits everything.** When the engine reports
  `context.startled`, both `speech()` and `emote()` take the yelp branch first and
  never reach the condition pools, so an active condition silently loses to a
  loud noise on that line.
- **A startle fires once per hearing entry, per turn.** `AgentEngine._detectStartle()`
  tracks which entries already startled a character so a lingering shout does
  not yelp forever, and caches the result per turn so the speech and the emote
  agree instead of disagreeing inside one turn.
- **The body-reaction conditions are applied by content, not by this module.**
  `itch`, `goosebumps` and `sneeze` live in `engine/player_conditions.py` with
  catalog entries in `data/library/conditions/`. All three are non-erotic and
  carry `"mature": false`, so they are never hidden or stripped by the world's
  `mature_content` toggle. A trigger or action has to apply the condition; if
  nothing does, it simply never fires.
- **Injection happens before the text is sent**, so the room and the event stream
  both see the interrupted line.

## Structured Actions (task-160)

The LLM emits a **structured action object** instead of free-text commands:

```json
{
  "inner_monologue": "...",
  "action": "use_on",
  "item": "rusty_key",
  "target": "front_door",
  "speech": "Please fit, please fit.",
  "volume": "whisper",
  "emote": "slides the key into the lock"
}
```

- **`volume`** is `whisper | say | shout | scream` (default `say`). The volume word is the
  **key**, never a value inside speech - `{"speech":"whisper psst"}` is explicitly wrong in
  the prompt. `speak`/`talk` normalize → `say`. Legacy top-level `say`/`whisper` keys still
  work as a fallback.
- **`normalizeStructuredAction()`** (`agent/action-normalizer.ts`) converts `{action, item,
  target, relation}` into a command string for `/api/action`:
  - `use rusty_key on front_door` (multi-word names stay whole)
  - `use create flame` (use ALONE for self-use items)
  - `put ink_pen on table` (spatial placement, `relation` = on/under/beside/behind/at/in)
  - `give rusty_key to Lyrie` (hand to a same-area character)
  - `steal key from Miki`, `go north`, `rest 30`, etc.
  - Free-text fallback for anything unsupported / legacy plain strings

### Multi-emotion and multi-target affect updates

Turns can declare multiple simultaneous feelings, each optionally directed at a specific person (see [[Characters/Interiority & Subtext]]):

- **Schema (`StructuredFormats`)** - `static/js/shared/json-schemas.ts` defines `EMOTION` as `null`, a single `{label, intensity, toward}` object, or an array of `{label, intensity, toward}` items on both `agentAction` and `agentReact`. Prompt schemas request this via the `emotion_toward` fragment (`schema-fragments.ts`).
- **Parsing (`ResponseParser`)** - `ResponseParser.extractEmotion()` (`agent/response-parser.ts`) normalizes both single objects and arrays, lowercasing `label`, clamping `intensity` to `1-10` (default `5`), and preserving `toward` (`string | null`).
- **Two-stage interpretation (`ActionInterpreter`)** - When `config.interpreterModelEnabled` is enabled, `ActionInterpreter.interpretProseToAction()` (`agent/action-interpreter.ts`) translates creative character prose into the canonical turn schema using `ResponseParser.parseReaction()` and `normalizeEmotionPayload()` (supporting a string label, single object, or array of `{label, intensity, toward}`).
- **Dispatch (`AgentEngine._applyFeltEmotion()`)** - `AgentEngine._applyFeltEmotion()` (`agent-engine.ts`) iterates over the single or array impulse list and dispatches `ApiClient.getPlayerEmotions(charName, body)` for each entry: when `toward` is present it forwards `toward` so the backend records a person-directed experience (`felt_toward`); otherwise it sends `delta: intensity * 1.5` as a global affect spike.

### A malformed action payload is recovered, not executed

Some models nest the action one level deep:

```json
{ "action": { "action": "take", "item": "lighter" } }
```

`normalizeStructuredAction()` unwraps one level, so the command is rebuilt as
`take lighter`. A payload with **no** verb in the nested object is not recoverable: the
normalizer returns no command, and `ResponseParser.parseReaction()` raises a
`schema_invalid` parse error instead. The agent engine then takes its one-shot retry, and
the corrective prompt tells the model that `"action"` must be a plain verb string.

The raw model output is preserved in the parse-error bubble, so the failure is diagnosable
rather than a mystery.

### Failure categories, and what the character is told

`classifyAction()` splits a refused action into categories, because they are not the same
kind of failure and must not collapse into one:

| Category | What it means | What the character is told |
|---|---|---|
| `schema_invalid` | the payload was not a command (a stringified object, or prose) | "Your command was malformed, so it never reached the world. Nothing happened." |
| `unknown_verb` | a well-formed command using a verb the engine does not implement | "You tried to X, but that is not something you know how to do. Nothing happened." |
| `empty` | no action was chosen (a speech-only turn) | "You did not act." |

The wording is the point. A malformed command is an **engine-side** refusal, and the earlier
blanket "You try to X, but you can't do that" let characters invent supernatural barriers to
explain a bad JSON payload. A well-formed command the **world** refuses (a locked door) is a
different path: that comes back from the backend as an action result, not as a skip.

`rejectionText()` (`agent/action-normalizer.ts`) holds this policy next to the classifier
that produces the category, so the two cannot drift.

### Action verbs the LLM is told about (ACTIONS table)

`go, dash, crawl, climb, jump, open, close, take, drop, use, use_on, put/place, give, steal,
examine, read/search, wear/equip, remove/unequip, attack, grab, escape/struggle, rest, wait,
inventory, stats, look, fumble, relieve` - plus ghost-only `manifest`/`vanish`.

- `crawl <dir>` / `climb <dir>` / `jump <dir>` are the passage-movement verbs (task-187):
  `go` auto-crawls tight (one tier over `max_size`) and crawl-only ways; climb/jump ways need
  the matching verb and roll an Athletics check that can fail.
- `grab <character>` is a grapple attempt (falls back to `take` for items); `escape`/`struggle`
  break a grapple with a STR save (task-4).
- The player-state block injects **size context** when a `size_*` trait is present ("You are
  huge. Some passages are too tight for you...") via `buildSizeContext()` in `agent/prompt-builder/`.

## Planning: typed steps, grounded against what exists

A character plans in **typed steps** (`{"act", "item", "target", "text", "note", "area", "until", "duration"}`), not prose.
`PlanManager.generate()` (`agent/plan-manager.ts`) enforces this shape with `StructuredFormats.plan` (`shared/json-schemas.ts`, `{"steps": [PLAN_STEP, ...]}`) and salvages complete step objects from truncated JSON responses via `_salvageTypedSteps()`.
Before a plan is accepted, every step is validated against the facts the plan prompt was
built from (`agent/plan-grounding.ts`): the items in the room, the things the character
carries, the people present, the visible paths, and the areas it knows.

### MOSIAC and GIMP context in planning

`PlanManager.generate()` wires subjective motivational state and active goals directly into the planning prompt:

- **MOSIAC (`PromptBuilder.buildMosiacContext(player)`)** - `prompt-builder/character-state.ts` renders Motivation (`M`), Intention (`I`), Pending Offers and Active Obligations (`O`), Schedule (`S`), and Attention needs (`A`) without raw debug telemetry. `buildReactionPrompt` and `buildCommunicationPrompt` also include `mosiac` in `buildContextBlock`.
- **GIMP goals (`_formatGoalsContext(player)`)** - `agent/plan-manager.ts` formats active, proposed, and blocked entries from `player.goals` (filtering out `reached` and `dropped`) into `=== YOUR GOALS ===`, including motivation (`why`) and deadlines (`due tick N`).
- **Maslow critical-needs priority** - `PlanTracker.criticalNeeds(player.vitals)` prepends `=== CRITICAL NEEDS (MASLOW - address these FIRST) ===` when physiological vitals are critical (filtering out hunger/thirst/sleep for `is_slasher`, `undead`, or `ghost` characters).

### Step completion, failure tracking, and replanning (`PlanTracker`)

`PlanTracker` (`agent/plan-tracker.ts`) owns per-character `plans`, `planTick`, `planProgress`, `planFailures`, and `activePursuitId`:

- **Step tracking (`trackStep()`)** - On `succeeded === false`, increments `planFailures[charName][idx]` and logs a blocked-step notice at 3 failures. On success, advances `planProgress[charName]` when the executed action matches the current step's non-stop-word tokens (requiring a target token match when the action is not bare-verb).
- **Replan triggers (`shouldReplan()`)** - Returns a reason string (`'threat detected'`, critical need label on threshold crossing or every 5 turns, `'no plan'`, `'plan completed'`, `'plan aged out'` after 10 turns when no `activePursuitId` is set, or `'current step failed repeatedly'` at 3+ failures) or `null`.
- **Server seeding (`seedFromPlayer()`)** - Seeds `PlanTracker` from `player.plan` or `player.active_pursuit` when present so server-assigned pursuits and plans are tracked in the same loop.

### Target types decide which fact list a step resolves against

A step names a target, and the target's **type** decides where it must be found:

| Type | Where it lives | Legal acts |
|---|---|---|
| PATH (a door, an exit) | the exit list | `go`, `dash`, `approach`, `open`, `close` |
| ITEM (a thing you can pick up) | items here / carried | `take`, `use`, `eat`, `drink`, `search`, `examine`, `drop` |
| PERSON | people here | `speak`, `give`, `attack`, `grab`, `steal` |
| AREA | known areas | `go` |

This split is why `open dining_room_door` is legal. A door is a **path** here, not an item -
it was being rejected because the check only consulted the item pool, while the prompt had
just listed that door under "From where you stand, you can see the following paths".

A step that names room-description scenery ("search the dining table") is still rejected:
a described table is not an interactable. The rejection says so, and teaches the route that
does work - `go` there first, then `look` to see what that room actually lists.

### A repair replaces only the rejected steps

One bounded re-composition is allowed. The repair prompt lists the original plan step by
step, each marked `[KEEP]` or `[REJECTED]` with its reason, and states the contract:
reproduce the `[KEEP]` steps exactly, replace only the `[REJECTED]` ones, same count, same
order.

The result is then **merged back**: a step that already grounded is restored verbatim at
its original position, the repaired steps fill the rejected positions, and the whole merged
plan is re-grounded end to end before it is accepted. A repair cannot throw away a
verified step, and a repair that invents scenery again is dropped rather than executed.

### The plan verb list cannot drift from the executor

`PlanGrounding.ACTS` is the intersection of a curated plan-intent list and the executor's
verb registry (`agent/action-verbs.generated.js`, mirrored from `engine/action_verbs.py`).
A plan verb the engine does not implement can never be advertised, and the planner never
offers engine plumbing ("manifest", "do", "i") as a plan step. `perform` is the one
plan-only verb: it names a sustained activity the world resolves when the step runs.

## Prompt Building

All prompt construction lives in `static/js/agent/prompt-builder/` (pure functions, plus async `memory-context.ts`). Submodules: `system-prompt.ts`, `turn-prompts.ts`, `character-state.ts`, `conversation-context.ts`, `memory-context.ts`, `context-sections.ts`, `schema-fragments.ts`, `helpers.ts`, `room-context.ts`, `contextual-actions.ts`, `capture.ts`, `index.ts`.

### Capturing a turn prompt (`captureTurnPrompt()`)

`capture.ts` assembles the exact system and user messages one character would
receive on its next turn, using the same call sequence `agent-engine.ts` uses
at turn start: room parts, vitals, emotion, relationships, memory, system
prompt, reaction prompt. The character's own room wins over the scene's active
player, and the memory block is fetched in the live turn's mode (not the
preview mode), so the captured prompt is the prompt, not an approximation of
it.

The benchmark harnesses (the Benchmark Lab page, `/bench`) send that capture
to every model they compare. A hand-written approximation inside a benchmark
measures the approximation, not the game, so there is exactly one capture
path and the harnesses call it.

On the output side, `/bench` loads `shared/json-utils.js`,
`agent/action-verbs.generated.js`, `agent/action-normalizer.js`, and
`agent/response-parser.js` so model responses pass through the same
`repairJSON()` -> `ActionNormalizer.normalizeStructuredAction()` ->
`ActionNormalizer.classifyAction()` pipeline as a live turn before calling
`POST /api/action/validate` (`validate_action_command` in
`routes/action_handlers.py`). The dry-run validator temporarily binds
`active_player` to the benchmarked character (and simulated area when
selected), resolves self-contained verbs (`relieve`, `look`, `search`, `rest`,
`plan`, etc.) before target-required checks, splits compound preposition
commands (`use X on/in Y`, `put/place/stow X in/on/... Y`, `give X to Y`,
`steal X from Y`), and rejects unregistered verbs against the action verb
registry. The **Turn Context** panel also provides an optional **Preferred
Action (+1 Score)** field (with room-grounded autocomplete suggestions and
comma-separated alternatives) that awards `+1` to a model card's validation
score when the normalized command or engine `resolved_target` matches.

### System Prompt (`buildCharacterSystemPrompt()`)

- World lore (common knowledge shared by all agents)
- ACTIONS table (structured-object examples, one action per response)
- Rules (multi-word names stay whole, `use` vs `use_on`, put needs a `relation`, give/steal need a same-area target)
- Ghost/death instructions when applicable
- Items vs flavor distinction

**Character identity** ("You are X. Personality: Y.") is injected as the first line of every user message via `buildCharacterPreamble()`.

### Prompt Templates

All templates share the same **user-message layout** (assembled from `buildRoomContextParts()` + `assembleMessageHead()`, reordered 2026-08-18):

```text
[Tick N]
You are X. Personality: ...
=== YOUR STATE ===        ← vitals, emotion, insanity, traits, size, activity, grappled, ghost/dead
=== I REMEMBER (CONSCIOUS THOUGHT) ===  ← synthesized recollection (Strict Actor Isolation)
Your appearance / Carrying
Room description → paths → items → People here (with inline relationship labels)
=== AVAILABLE ACTIONS ===
=== WITNESSED ===
[=== YOUR PLAN ===]
<phase section>
```

### Pursuit context (planned)

An active pursuit is a different prompt concept from both the current Activity
and `=== YOUR PLAN ===`. An Activity such as sleeping is part of the character's
current state and is already described in `=== YOUR STATE ===`; `=== YOUR PLAN
===` is the immediate step list. The proposed `=== CURRENT PURSUIT ===` block
will pair readable motive with structured objective, where, when, requirements,
supplies, progress, and stop conditions. Place it after `=== YOUR STATE ===`
and before memory so the reason is visible alongside the character's current
condition. The agent can continue, adapt, pause, replace, or decline it after an
interruption. The LLM prompt builder does not yet read `Player.active_pursuit`;
see [[Character Pursuits]] and task-704. Calendar schedule cues use the existing
world date/time and environment state.

- **Relationships are NOT in `=== YOUR STATE ===`** - each "People here" line carries an inline
  type label when known (`jake halloway - a close friend - (awake)`), no scores.
- **Memory context is its own `=== I REMEMBER (CONSCIOUS THOUGHT) ===` block** right after YOUR STATE, not a state
  fragment.
- The react template keeps its minimal `[Tick N] You are still in ...` context, then
  `=== YOUR STATE ===` -> `=== I REMEMBER (CONSCIOUS THOUGHT) ===` -> `=== WHAT HAPPENED ===`.

### Heard speech: delivery and who made the noise

A `=== WITNESSED ===` speech line is `[Heard< from the X>] <speaker> <verb>: "<text>"`, and both
the verb and the speaker label are read off the hearing entry rather than assumed.

**Delivery is reported.** `speech.py` stamps `speech_level` on every hearing entry, and
`PromptBuilder.speechVerb` maps it to the verb - `whispered`, `said`, `shouted`, `screamed`,
`sang`. It used to be the string literal `said` in the render, so a scream reached the model as
conversation. The turn-event description deliberately keeps its literal `said:` marker: that is a
machine-parsed format (item sound capture and the salience regex depend on it) and is not the prose
the character reads. `engine/narration.py` keeps a matching `SPEECH_VERBS` for the server-side
`listen()` report.

**A heard stranger is labelled by what is making the sound.** `PromptBuilder.voiceLabel` and
`anonymousName` read from **one** `SPEAKER_TAGS` table, because they drifted and the drift was
visible: a tabby read "an animal" in the room and, through a wall, **"a man's voice"** - the seen map
had `animal`, the heard map did not, so it fell through to the pronoun heuristic, and animal
descriptions are freely written with "his" (whiskers: *"darker striping along his flanks"*).

Resolution order for an unrecognised speaker:

1. **Known to the viewer** → their real name.
2. **Tagged as a non-human** → a species label (`"a cat's voice"`, `"a wolfs's voice"`), most
   specific first so `bird|raven` is the raven; `"an animal's voice"` when the species tag is
   unmapped. This is checked **before** the gender tags, because these characters carry both -
   `male|animal|worg` read as "a man's voice" when the gender tag was consulted first.
3. **Tagged `anthro`** → exempt, because an anthropomorph is presented as a person: it falls
   through to the gender label so it agrees with the "the woman" the same character gets when seen.
4. **Gender tag** → `"a man's voice"` / `"a woman's voice"`.
5. **Pronouns in the description** → last resort, and **never for a non-human**. "his" in a sentence
   about a cat's flanks is evidence about the cat.
6. Otherwise `"a voice"`.

A genuine non-speaking noise (a yowl from the next room) is not speech at all and already goes
through the `sound_source` path, rendering as `[Heard from the X from the item] <pattern>.`

Species labels are keyed by the tags the character library already carries (`animal`, `rabbit`,
`bear`, `bird`, `boar`, `frog`, `raven`, `sheep`, `wolf`, `worg`), so the list needed no new
vocabulary - but note those species tags are **not registered** in `data/library/tags/`, unlike
`animal` itself. `whiskers` needed an explicit `cat` tag to read as a cat rather than "an animal".

| Template | Phase | Memory field | Output |
|----------|-------|--------------|--------|
| `buildReactionPrompt` | Think-decide / combined | Retired (task-949) | `{"inner_monologue","action","item","target","speech","volume","emote"[,"emotion","learned_names"]}` |
| `buildResultReactionPrompt` | React | Retired (task-949) | `{"inner_monologue","speech","volume","emote","emotion","learned_names"}` |

`buildObservationPrompt` and `buildDecisionPrompt` were removed from `turn-prompts.ts` (2026-09-20); `buildReactionPrompt` covers both think and decide.

### Room Context & the Attention List (`buildRoomContext()`)

`buildRoomContext()` (line 582) builds the area description injected into the agent's user message. Since the interest system landed (2026-08-05, task-98 Phase 2), room items render as an **"Items that catch your attention"** list instead of the old "everything gets a full description" block:

- **Unexamined only** - items already examined or taken (in `player.discovered_items`) are omitted; their facts live in `=== MY INVESTIGATION NOTES ===`.
- **Interest-sorted** - items matching `player.interest_tags` (exact tag +2, keyword-in-name +1) surface first; then the rest.
- **Weight-ordered** - within each tier, heavier items first (bigger = easier to see; missing/0 weight sinks).
- **Capped at 15** (`ATTENTION_MAX`) - one uniform path for all room sizes, no small/large threshold. Emphasis (sorting) is always on; the cap just bites when a room has more than 15 unexamined items.
- **Natural trailer, no truncation** - ends with `There are more items around that you can look for.` when the cap bit, or `...and not much else.` when everything visible fit.
- **Light logic unchanged** - pitch black/dim/dark-vision filtering is untouched; attention sorting only refines within each light branch.

### People here + spatial position (task-135)

Each person line can include a **position suffix** from `spatial_position` / `at_way_id`:

```text
  - the woman (awake) beside the piano - A musician…
  - the stranger at the north - A tall figure…
```

- **Stranger labels** - unmet characters show `unknown_display_name()` (`the man`, `the woman`), not database names. The suffix uses the same anonymous label for character anchors.
- **Relationship labels** - met characters get an inline type label (`- a close friend -`) before
  `(state)`, from `buildRelationshipLabel()` (no `(65/100)` scores).
- **Targeting** - combines appearance handle + location (`attack the man`, `go north`). Backend `_match_character_name()` also resolves description words in the same area.
- **Physical actions walk you there** - open/go/give/grab/attack set position automatically; `examine room` steps back. See [[Gameplay/Character Spatial Position]] and `system-prompt.ts` Rules.

## Memory in the agent

See [[AI & Narration/Memory System]], [[Simulation Philosophy]], and [[Characters/Interiority & Subtext]]. Key points:

- **Intermediator synthesis + cue-change gating** - `PromptBuilder.buildMemoryContext()` (`prompt-builder/memory-context.ts`) scores and retrieves relevant traces, then computes a cue signature (`_computeCueSignature(areaId, actors, dialogue, emotion, needs, memories)`). `_synthesizeConsciousThought()` checks `config.memoryIntermediator !== false` and caches the result in `_intermediatorCache` keyed by character and cue signature; only when cues change does it call `memClient.chat()` (`label: 'intermediator'`, `reasoningEffort: 'low'`) to synthesize top traces (annotated with relative age, conflict, and uncertainty flags) into one brief first-person conscious thought (`2-4` sentences). Unless `skipPersist` or `commonsRecordMemories === false` applies, that thought is persisted as a `reflection` memory (`source: 'intermediator'`).
- **Strict Actor Isolation (task-947 / task-949)** - `=== I REMEMBER (CONSCIOUS THOUGHT) ===` emits ONLY the synthesized conscious recollection (zero raw DB memory rows are dumped into the actor prompt).
- **End-of-turn memory retired (task-949)** - `config.endOfTurnMemory` and Reactor `memory` creation are retired (`prompt-builder/turn-prompts.ts`). Instead, `AgentEngine._persistInnerMonologue()` (`agent-engine.ts`) persists the actor's `inner_monologue` as a `reflection` memory (`source: 'inner_monologue'`, deduplicated within +/- 1 tick).
- Speech/emotes are log-only, not memories.

## Agent Configuration

| Property | Type | Description |
|----------|------|-------------|
| `personality` | string | Core personality prompt |
| `description` | string | Appearance |
| `state` | string | `awake`, `sleeping`, `dead`, `unconscious` |
| `simple_npc` | boolean | Skip LLM calls, act via backend NPC tick |
| `npc_behavior` | string | `wander`, `still`, `patrol`, `flee`, `guard` |
| `npc_action_interval` | int | Ticks between autonomous NPC actions |
| `npc_state` | string | `idle`, `curious`, `hostile`, etc. |
| `behaviors` | array | Event-driven behavior definitions |
| `emotion` | object | `{current, intensity, description}` |
| `traits` | object | `dark_vision`, `slasher`, etc. |
| `equipped` | object | Worn items by slot |

Settings panel controls: API key/base/model/temperature, turn-based mode + order, reactive mode, ghost mode, manual mode, streaming, RPM/TPM limits.

## Difference Between LLM Agents and Simple NPCs

- **LLM agents** (`simple_npc: false`): full LLM decision-making, fresh per-turn context with synthesized conscious memory and reflection, multi-step typed plans, structured actions. 2+ LLM calls/turn in reactive mode (plus intermediator synthesis when cues change, and optional `ActionInterpreter` pass).
- **Simple NPCs** (`simple_npc: true`): no LLM calls, behavior driven by `behaviors[]` + `npc_behavior` pattern, controlled by backend `tick_turn`. Suitable for animals, minor NPCs, environmental entities.

## Reading the LLM trace

Every LLM call is logged as a collapsed chip in the event stream, and the export carries
the identity of the call:

| Field | Where it comes from | Why |
|---|---|---|
| `actor_id` | the character the call was **for**, passed by the caller | the chip used to guess the actor from "whose turn is it", so a prompt written for one character was filed under another one's name |
| `request_id` | generated per call, shared by the request chip and its response chip | pairs a request with its response without relying on ordering |
| `phase` | the turn phase (`plan`, `think-decide`, `result-reaction`, ...) | says which stage of the turn produced the payload |

The display column `actor` is unchanged and still a label. `actor_id` is the truth.

## Related

- [[Simulation Philosophy]]
- [[Characters/Interiority & Subtext]]
- [[dev_tasks/done/prompting/task-160-parameterized-actions-in-prompts|task-160: Parameterized actions]]
- [[dev_tasks/done/characters/task-178-unify-memory-systems|task-178: Unified memory]]
- [[Rules Engine/Conditions System]]
- [[Gameplay/Character Spatial Position]]
- [[AI & Narration/Memory System]]
- [[AI & Narration/Turn-Based System]]

<!-- changelog:start -->
## Changelog

*Generated by `python tools/page_changelog.py` from the task cards whose `wiki:` points at this note. Never hand-edit inside the markers.*

| When | Task | Status |
|---|---|---|
| - | [[task-90-delayed_event_queue\|task-90-delayed_event_queue]] | `done` |
<!-- changelog:end -->

## Where it lives

- **`static/js/agent-engine.ts`** (`AgentEngine`, `window.VW.agent`, `agent`) - main loop, turn orchestration, affect dispatch (`_applyFeltEmotion`), inner monologue persistence (`_persistInnerMonologue`)
- **`static/js/agent/prompt-builder/`** - prompt builders: `system-prompt.ts`, `turn-prompts.ts`, `character-state.ts`, `conversation-context.ts`, `memory-context.ts`, `context-sections.ts`, `schema-fragments.ts`, `helpers.ts`, `room-context.ts`, `contextual-actions.ts`, `capture.ts`, `index.ts`
- **`static/js/agent/turn-queue.ts`** - turn ordering, pause/inert filtering, and advancement
- **`static/js/agent/memory-manager.ts`** (`AgentMemory`) - memory storage + reflection
- **`static/js/agent/plan-manager.ts`** - typed multi-step plan generation, MOSIAC + GIMP goal wiring, and constrained plan repair
- **`static/js/agent/plan-grounding.ts`** - typed plan-step grounding validator (target types: paths, items, people, areas)
- **`static/js/agent/plan-tracker.ts`** - step progress, failure tracking, pursuit seeding, and `shouldReplan()`
- **`static/js/agent/rate-limiter.ts`** - API rate limiting
- **`static/js/context-window.ts`** (`ContextWindowManager`) - token budget and context pruning
- **`static/js/agent/response-parser.ts`** - parse/validate LLM JSON output and multi-emotion impulses
- **`static/js/agent/action-normalizer.ts`** - normalize structured actions into `/api/action` commands
- **`static/js/agent/action-interpreter.ts`** (`ActionInterpreter`) - two-stage prose-to-action translation
- **`static/js/agent/threat-detector.ts`** - flag nearby threats for replanning
- **`static/js/agent/human-turn-composer.ts`** - human-turn composer drive path
- **`static/js/agent/turn-scene-view.ts`** - render current turn scene for the event stream
- **`static/js/agent/involuntary.ts`** - involuntary reactions (hiccups, sneezes mid-speech)
- **`static/js/shared/json-schemas.ts`** (`StructuredFormats`) - strict JSON schemas (`agentAction`, `agentReact`, `plan`, `insights`, etc.)
- **`static/js/agent/action-verbs.generated.js`** - generated executor verb registry (mirrored from `engine/action_verbs.py`)
- **`routes/action.py`** - `/api/action` endpoint (agents use the same endpoint as humans)
- **`engine/narration.py`** - `SPEECH_VERBS` for server-side hearing report
- **`engine/speech.py`** - `speech_level` stamping on hearing entries

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply`  -  relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Read next**  -  [[Memory System#Memory dynamics (task-685)]], [[Narration System#Integration with Agent Engine]]

**Dev tasks**  -  [[dev_tasks/done/prompting/bug-559-available-actions-prompt-block-lists-verbs-the-turn-budget-cannot-afford-causing-infinite-llm-rejection-loops|bug]], [[dev_tasks/done/refactor/task-899-agent-engine-10-fixes-for-step-run-lifecycle-state-leaks-and-race-conditions|task]], [[dev_tasks/done/triggers/task-90-delayed_event_queue|task]], [[dev_tasks/review/gameplay/task-885-play-mode-vs-edit-mode-unity-style-simulation-sandbox|task]], [[dev_tasks/review/prompting/bug-523-plan-grounding-facts-use-unmasked-real-names-leaking-strangers-and-rejecting-targets-the-room-showed|bug]], [[dev_tasks/review/prompting/task-905-prune-prompt-rulebook-duplication-strip-mosiac-debug-stats-and-ground-vitals-in-narrative-sensation|task]] … +4 more

**Neighbouring notes**  -  [[LLM Providers]], [[Memory Dynamics]], [[Memory System]], [[Memory Weaver]], [[Narration System]], [[Turn-Based System]]

<!-- connected:end -->
