# Presence Gap Analysis — Chat RP vs VirtualWorld

**Date:** 2026-08-23
**Purpose:** Evidence-based list of what the agent experience already does well, what
genuinely hurts the "characters feel present" feeling, and candidate fixes — so we can
re-verify each item and decide what to build. Nothing here is implemented yet.

**Method:** compared exported engine logs against a hand-played multi-character chat RP
session (character card + live play). The chat session is the benchmark: two humans, one
LLM character, dense banter, ~25 exchanges.

**Logs reviewed:**
- `data/exports/event_log_2026-08-10T21-45-19.txt` (Task 18 door puzzle, Jane two, old format)
- `data/exports/lyrie 28082026.txt` (Frozen Thicket solo run, Lyrie, new format, 2026-08-18)
- `data/exports/Untitled-1.txt` (Task 17 conditions test, partial)

**Caveat:** the Aug 10 log predates the Aug 16–23 work (contextual actions, speech
salience, conversation instinct, social gating, emotional states). Several findings were
already partially addressed between logs; each item below says whether it still needs
verification in a current-build run.

---

## Part 1 — Already working (verified in logs)

These were previously suspected missing and are NOT; do not re-litigate without new evidence.

1. **Inner monologue is first-class.** `inner_monologue` is a schema field, rendered as 💭
   events (Aug 10 log: 2,267 monologue vs 41 speech events). Voice consistency across a
   session is strong (Lyrie's "little everflame friend" register never breaks).
2. **Memory writes are experiential.** React-pass memories are first-person, tagged,
   importance-rated: *"I accidentally put out my everflame ember… I should be more careful
   next time"* (`clumsiness/magic/loss`, Lyrie log L2245). Backstory memories surface in
   recall (Great Baking Incident block, Lyrie log L53–58).
   - *Correction (Tommy, 2026-08-23):* recall is keyword-based by design; `[just now]`
     stamps are turn-fresh writes pending tick→time conversion. Re-verify stamp aging in
     current build.
3. **POV filtering exists.** `=== WITNESSED ===` separates `[the stranger] said:` from
   `[Heard] a voice said:` (Aug 10 L40994–40997). Not all-knowing by default.
4. **Contextual actions replaced the verb table.** New-format prompts list concrete
   `=== AVAILABLE ACTIONS ===` per turn (Lyrie log L30–41).
5. **Emotional state injection.** `=== YOUR STATE ===` includes affect lines ("quite
   anxious and hopeful", Lyrie log L48).
6. **Simulation produces story beats.** Body temperature drove the whole Lyrie run:
   shivering → seek warm hollow → summon flame → extinguish accident → distress → lesson.
7. **Micro-arc continuity works.** The ember mistake produced a memory that was *referenced
   under pressure two turns later* ("if I don't put it out this time", Lyrie log L~113).
   That is the same mechanism that makes chat RP characters feel continuous.

---

## Part 2 — Confirmed issues

Each: evidence → impact → proposed action → how to verify.

### G1. Emote pronoun stitching bug (rendering)
- **Evidence:** "Lyrie hugs **yourself**" (L229), "hugs **your knees**" (L440), double
  periods `sigh..` (L2046, L2258, L3206), Lyrie log.
- **Impact:** constant low-grade uncanny; breaks immersion every few turns.
- **Action:** normalize second-person pronouns to third when prefixing an emote with the
  actor's name; collapse duplicate trailing punctuation. Tiny renderer fix.
- **Verify:** grep any new export for `<name> (yourself|your |you )` pattern = zero hits.

### G2. Engine outcome lines are stubs next to model prose
- **Evidence:** model side "It felt nice and safe, like a little friend." vs engine side
  "You use the create flame." / "You extinguish the everflame ember." (Lyrie log).
- **Impact:** the world reads like a debug print while characters read like literature;
  tonal whiplash every action resolution.
- **Action options:** (a) outcome prose templates per action verb with slot-filled variety,
  (b) optional light narration pass weaving ⚙️ results into a sentence, (c) leave engine
  lines terse but make the UI typography de-emphasize them.
- **Verify:** blind read of an export: outcome lines shouldn't be identifiable as
  "the machine ones".

### G3. Prompt boilerplate ratio still high
- **Evidence:** rules/examples blocks re-sent on every decision call (~100 lines even in
  new format); situational content ~30 lines (both logs).
- **Impact:** model attention budget spent on API documentation; form-following voice.
- **Action:** hoist static rules into the system prompt (provider-side prompt caching where
  available); slim per-call context to situation + delta.
- **Verify:** token accounting per call; qualitative voice shift test.

### G4. No pacing authority (director vacuum)
- **Evidence:** solo runs loop (hollow↔thicket ping-pong, returning to abandoned areas);
  Aug 10 run: 430 ticks, one puzzle loop, nothing escalates. Chat benchmark: the human
  director called every beat change ("that's about when the date turns bad").
- **Impact:** scenes drift toward need-satisfying mundanity; competent but flat.
- **Action candidates:** lightweight director pressure (scene tension value, beat goals),
  instigator behaviors for NPCs, or explicit human-director controls. Director-studio's
  Focus→Monologue→Action weave is a working prototype of the shape.
- **Verify:** 30-turn multi-agent run with zero human input should produce at least one
  escalation (argument, revelation, arrival) not caused by random wander.

### G5. Emotional accumulation is thin in practice
- **Evidence:** Aug 10 log repeats `You feel fine — no pressing needs right now.` every
  turn; emotional state line exists (new format) but appears as a single adjective line.
  Contrast benchmark: one rejection colored 20+ exchanges.
- **Impact:** characters reset to neutral between beats unless something big just happened.
- **Action:** verify current emotional-states persistence across turns; if it decays too
  fast, add mood inertia (events set a baseline that tints N subsequent prompts).
- **Verify:** after a distressing event, check the next 3–5 decision prompts carry tint.

### G6. Memory reliability — false positives
- **Evidence:** Aug 10 L41014: *"I have nothing on me — no keycard"* while ground truth was
  `Carrying: keycard`; self-corrected two turns later (L21602).
- **Impact:** confident wrong memories are worse than gaps; they cause ghost-correction loops.
- **Action:** keyword recall can retrieve stale contradicted entries; consider recency +
  contradiction marking (later observation about same entity_ids downgrades earlier).
- **Verify:** inventory-state mismatch scenarios in a test run; count false-memory events.

### G7. Presentation is telemetry, not scene (umbrella issue)
- **Evidence:** stream renders `💭…💬…⚡ act go Door 1 / ▶️ go Door 1 / ⚙️ …` fragments
  (both logs) vs benchmark's continuous authored prose.
- **Impact:** this IS most of the felt gap. Content is present; typesetting isn't.
- **Action:** optional "scene view" renderer composing a turn's events into paragraphs
  (monologue italic, speech quoted, emotes woven, engine results as connective tissue).
  Pure presentation layer — no engine change required.
- **Verify:** read a scene-view export next to the chat benchmark; ask "who wrote which?".

### G8. Social density unverified in current build
- **Evidence:** neither reviewed log exercises multi-agent conversation (solo puzzle runs);
  salience/conversation-instinct/social-gating landed Aug 21–23, post-logs.
- **Impact:** unknown whether banter emerges or agents wait politely for turn structure.
- **Action:** run the mansion scenario (or `taco_bell_date.json`) with 2+ autonomous
  agents + human, export, evaluate against Part 1 checklist + G4/G5.
- **Verify:** count unsolicited addressations between agents; check RESPONSE PRIORITY rule
  actually fires on witnessed speech.

---

## Part 3 — Ideas ranked (impact ÷ effort)

| # | Idea | Addresses | Effort |
|---|------|-----------|--------|
| 1 | Emote pronoun/punctuation normalizer | G1 | XS |
| 2 | Scene-view renderer (presentation only) | G7 | M |
| 3 | Hoist static rules to cached system prompt | G3 | S |
| 4 | Mood inertia for emotional states | G5 | S |
| 5 | Outcome prose templates per verb | G2 | M |
| 6 | Multi-agent social soak test + eval harness | G8, G4 | M |
| 7 | Memory contradiction/recency weighting | G6 | M |
| 8 | Director pressure prototype (tension/beat goals) | G4 | L |

## Part 4 — Open questions

- Does tick→time memory stamp conversion exist in the current build? (Tommy says yes/planned — verify.)
- Do provider-side cached system prompts work with our OpenAI-compatible providers?
- Should scene-view live in the event stream UI or as an export filter first?

---

## Part 5 — Verification round 1: mansion multi-agent run (2026-08-23)

Log: `data/exports/mansion_event_log_2026-08-23T15-04-54.txt` — 7 characters
(elena vance, kyrie johansen, jake halloway, sammy lopez, miki, the butcher,
kayla jenkins), ~240 ticks, 29 LLM calls.

### Resolved by this run

| Item | Result | Evidence |
|------|--------|----------|
| G1 pronoun stitching | **FIXED** — 0 leaks in rendered emotes | line scan over all 💭/🎭 renders |
| Memory stamp aging | **LIVE** — recalls show "1 minute ago"/"2 minutes ago"; `[just now]` only for same-turn writes | 22/43 recall blocks aged |
| G3 prompt boilerplate | **MOSTLY SOLVED** — static rules/schema ≈ 7–8% of call-body chars (~82k of ~1.05M) | boundary scan ACTIONS→first dynamic section |
| G8 social emergence | **PASSING** — collaborative deduction chain across 5 agents: diary/skull rule relayed room-to-room → Blackwood calling cards → loose tile under rug → love letters w/ "m." initial → key taped in vase. Direct addressation, distinct voices, building on findings | speech stream ticks 10–246 |
| Conversation instinct | live — "You feel sociable right now — inclined to speak up." drives speech | === CONVERSATION === ×51 |
| Anti-repeat guard | live — ANTI-REPEAT rule references agent's own prior lines | decision prompts |
| Cross-area hearing | attributed via ways: "[Heard from the library_door_back] a woman's voice said:" | WITNESSED blocks, 23/29 non-empty |
| Threat autonomy | butcher runs independent horror logic off-screen ("Intruders in my house. The Entity demands sacrifice.") | butcher decide pass |

### Still open after this run

| Item | Result | Evidence |
|------|--------|----------|
| **G5 emotional accumulation** | **CONFIRMED OPEN** — 43/43 state blocks read "You feel fine — no pressing needs right now."; zero dynamic affect despite horror stimuli (stalking butcher, haunted-house tension). The Lyrie-run emotion line did not appear on this code path | all `=== YOUR STATE ===` bodies |
| G2 engine outcome prose | unchanged (terse ⚙️ lines); less jarring at this event density but still stubs vs model prose | outcome lines throughout |
| G7 scene-view rendering | untested (presentation layer not built yet) | — |
| G4 pacing authority | partially exercised: butcher acts as an organic instigator/threat, which may be enough pressure in horror scenarios; calm scenarios remain untested | butcher behavior |

### Round 2: taco_bell_date first load (2026-08-23, later)

Two-agent run of the authored date scenario (Miki + Jake both autonomous).

| Item | Result | Evidence |
|------|--------|----------|
| **G5 emotional states** | **RESOLVED (rendering)** — "miki doki is quite anxious." renders when the character has an emotion set; mansion run was empty because every character was neutral/healthy. Vitals-derived inner life also fires: Sanity 70 → `=== YOUR MIND ===` unease text; Social 40 → "You feel isolated." | decision prompts, turn 0 |
| Authored-beat reproduction | **The earring arc replayed itself**: seeded memory ("missing… it matters") + hidden item under table → Miki crawls under the booth mid-date, nearly cries, writes an importance-8 memory (*"I told jake 'i'm fine' while absolutely not being fine"*, tags relief/grief/hope). No director involved — graph props + memories were enough | turns 0–1 |
| Vitals → characterful behavior | Jake's hunger 10 triggered CRITICAL NEEDS plan-first rules, but he satisfied them in voice: steals the burrito as "date tax" — the same beat hand-written in the source RP | jake decide turn 1 |
| POV stranger labels | bare `[Heard] a woman's voice said:` pre-introduction — correct; names withheld until introduced | witnessed blocks |

**Bugs found & fixed in `taco_bell_date.json`:**
1. World lore rendered `[general] undefined:` — prompt builder expects `entry.title`
   (`system-prompt.js:112`), scenario used `name`. Added title.
2. Second-person converter verb artifact: "grinning like he knows…" → "like you knows".
   Reworded description to avoid pronoun+verb constructions (converter family, G1).

**Open follow-ups:**
- Does anything *update* `emotion` during play (events/mood engine), or does it stay at
  its seed value? Watch across a longer run.
- Ambient dread flavor ("the shadows seem to watch you") is horror-generic; fine for
  sanity<75 anywhere but worth a scene-appropriate variant pool eventually.
- Steering prefixes before JSON in assistant turns ("Take the earring.",
  "React silently, emotional.") — confirm these are the intended mode-steering mechanism.

### New observations

- Recall quality is planning-grade and relationship-aware: *"miki's following me in.
  good. i don't want her wandering off alone"* (elena, decision prompt).
- Witnessed-empty blocks (6/29) occur only when a character is genuinely alone — correct.
- Next highest-leverage move: wire emotional states into the multiplayer decision-prompt
  path (they rendered in the solo Lyrie run but not here), then re-export and re-check.
