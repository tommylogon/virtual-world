# Task: Plan Loop-Breaking — Step Tracking & Failure Bailout

**Status**: In Review — implemented (verified 2026-08-08 code audit; moved from todo). `_planProgress`/`_planFailures` tracked in `agent-engine.js`, `_trackPlanStep` gates on the backend `success` flag and blocks steps after 3 failures, `_shouldReplan` fires on stalled/blocked steps, step position rendered as `(done)`/`(CURRENT)` in the plan context, and failures feed plan regeneration. The raw `storeMemory(action → result)` violation is gone (memories come only from the reaction phase). Pending: the failure-aware repeat-warning extension from §6.

## Goal

Break the "replan → re-echo the same step" loop seen throughout
`event_log_2026-08-02T12-00-06.txt`:

- Lyrie replanned ~24 times, nearly every plan repeating *"wrap my Short Forest Cape
  snugly over my Soft Linen Shift"* / *"use Create Flame to start a warming fire"* even
  though both repeatedly failed.
- Kaelen replanned ~20 times, always *"light the stove with kindling"* while the stove
  didn't exist and `take twigs` kept failing.

Root cause: plans are static string arrays (`plan-manager.js`). No step is ever
marked complete, "PLAN FOLLOW" references a *"next step"* that nothing defines
(`prompt-builder.js:774`), and `_shouldReplan` (`agent-engine.js:547-553`)
regenerates an identical plan when it fires. So the model re-attempts step 1 every
turn, forever.

## Design principle — system knowledge vs character knowledge

These are two different stores and must stay separate (they should agree, but never
be the same content):

| | System state | Character memory |
|---|---|---|
| Owned by | `agent-engine.js`, `player.py` (facts) | MemoryStore / `player.memories[]` (narrative) |
| Examples | `_plans`, `_planProgress`, `_planFailures`, `visited_areas`, `discovered_items`, action results, "what haven't I done" candidates | "I conjured a small flame in the frozen hollow — it felt nice, but I was scared of setting the forest on fire." |
| Form | exact, authoritative, machine-readable | subjective, first-person, emotional, LLM-synthesized |
| Drives | loop-breaking, novelty mechanics, suggestions | what the model "remembers" and reasons from |

**Current violation:** `agent-engine.js:327` stores raw system strings as character
memory — `storeMemory(charName, \`${finalAction} → ${outputText}\`, ...)`. The
character should never "remember" `use create flame on dry leaves → no purchase`.
That fact belongs in system state; the character gets a synthesized narrative memory
from the observe/reaction phase (that's where `_generateRichObservation` /
`buildResultReactionPrompt` come in).

**Rules for this task:**
1. All counters/plan state are **system state** — never written to `storeMemory` raw.
2. When the system marks a step `[BLOCKED]`, the *memory* written must be a
   character-POV thought, e.g. *"I've tried to light the stove three times and it
   won't catch. Maybe it needs real fuel."* — not `"plan step 2 is not achievable"`.
3. If system facts and character memory diverge (e.g. emote claimed success after a
   failure — see `task-186-agent-validation-and-feedback` emote gating), **system wins**
   and corrects the memory.

## Changes

### 0. Stop writing raw system strings to character memory
- `agent-engine.js:327`: replace `storeMemory(charName, \`${finalAction} →
  ${outputText}\`)` with (a) keeping the action+result in **system state** (a
  per-character `lastActionFact` or the existing `config.lastActionResult`) and
  (b) letting the reaction phase synthesize the character memory. Investigation
  Notes in `prompt-builder.js:191-306` must read from system state, not from parsed
  `player.memories[]` strings.

### 1. `static/js/agent-engine.js` — track plan step progress (system state)
- Add `this._planProgress[charName]` (int index into `_plans[charName]`).
- After an action succeeds, mark the current step done: best-effort match of the
  executed action against the current plan step (verb + item names overlap), and if
  matched (or if the step's intent was satisfied) advance the index.
- Reset progress to 0 on new plan / replan.

### 2. `static/js/agent/prompt-builder.js` — surface step position
- `buildPlanContext` / `buildDecisionPrompt` PLAN FOLLOW should read
  `VW.agent._planProgress` and render:
  `"Your plan (step {N+1} of {M}): 1. ... 2. ... (completed) 3. ... (CURRENT)"`.
  This tells the model exactly which step to execute next.

### 3. Failure bailout — don't replay impossible steps
- Track consecutive failures per step: `this._planFailures[charName][stepIndex]`
  (system state).
- When the same step fails ≥ 3 times, mark it `[BLOCKED: <last error>]` (system
  marker), advance the index past it, and write a **character-POV high-importance
  memory** (see rule 2 above).
- Include all `[BLOCKED]`/completed info in the next `PlanManager.generate` prompt
  (`plan-manager.js:74-93`) so a replan does **not** regenerate the same broken step.

### 4. `static/js/agent/plan-manager.js` — feed failures into regeneration
- Before generating, collect `_planFailures` + `_planProgress` and append:
  `"Your previous plan failed on these steps: ... — do not repeat them; find an
  alternative or pursue a different goal."`

### 5. Replan trigger sanity
- `_shouldReplan` (line 547) is fine, but make it also fire when the *current* step
  is blocked (index not advancing after N turns), so the agent isn't stuck holding a
  dead plan.

### 6. Repeat-tracking — fix the gap, don't duplicate
- `prompt-builder.js:258-260` only warns to move on for `examine` repeats:
  `actionInfo.filter(a => a.verb === 'examine' && a.count >= 3)`. Lyrie's repeated
  `use create flame on dry leaves` was *counted* but never warned about.
- Extend the warning to **all known verbs** and make it **failure-aware** (count only
  attempts whose result matches the failure signals from
  `task-186-agent-validation-and-feedback`): "You've tried '<action>' 3 times and it
  failed — pick a different approach."
- **No new counter system:** reuse the existing `actionCounts` map in
  `prompt-builder.js:193` (or the plan-level `_planFailures` for step blocking).
  One count per concern — action-attempts live in the investigation-notes builder,
  plan-step failures live in `_planFailures`. Do not add a third parallel counter.

## Files Modified
- `static/js/agent-engine.js`
- `static/js/agent/prompt-builder.js`
- `static/js/agent/plan-manager.js`
- `docs/virtualWorld/AI & Narration/` (agent planning doc if present)
