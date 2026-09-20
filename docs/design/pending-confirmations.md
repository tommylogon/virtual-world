# Pending confirmations

Decisions and findings that need **your** call. Each item has the evidence,
the options, and my recommendation. Tick an item and I'll act on it; if you
disagree with an option, say which one instead.

Created 2026-09-20 during the `static/js` documentation survey.

---

## A. Prompt / vitals findings (from the prompt-builder pass)

### A1. I already changed a prompt — confirm or revert
- **What:** `prompt-builder/character-state.js` had two identical
  `if (v < T.WARNING)` branches for `Social`, so the second was unreachable and
  `[social_need: moderate: consider speaking to someone]` **never fired**.
- **Change made:** added `SOCIAL_MILD = 65` to `agent/vital-thresholds.js` and
  pointed the branch at it. A mild loneliness tier now surfaces at 50–65.
- **Impact:** agent prompts/behaviour change.
- **Confirm:** keep 65, pick a different threshold, or revert to the dead branch.
- **Evidence:** `static/js/agent/prompt-builder/character-state.js:370,378`;
  `static/js/agent/vital-thresholds.js` (`SOCIAL_MILD`).

### A2. `voiceLabel()` ignores the authored `known` registry
- **What:** `anonymousName()` honours `player.known` (authored "who knows
  whom"); `voiceLabel()` — used for speech heard **without** line of sight —
  does not. A character you're authored as knowing is still described as
  *"a woman's voice"*.
- **Likely an oversight**, but it changes what characters are told.
- **Options:** (a) add the same `known` check to `voiceLabel`; (b) leave as-is
  (intentional: you must have *met* them, and meeting requires sight).
- **My recommendation:** (a) — it makes the two label paths consistent.
- **Evidence:** `static/js/agent/prompt-builder/helpers.js:104` vs `:136`;
  consumer `prompt-builder/room-context.js:681`.

### A3. `includeMemory` accepted but never wired (reaction phase)
- **What:** `buildReactionPrompt` accepts `includeMemory`, but
  `MEMORY_INSTRUCTION_REACTION` is never inserted into the prompt — so the model
  gets a `memory` field in its JSON schema with **no instruction** for filling
  it. The original author left it commented out deliberately.
- **Options:** (a) wire it in (uncomment); (b) delete the parameter and the
  constant; (c) leave as-is.
- **Impact:** (a) changes model behaviour for the reaction phase.
- **Evidence:** `prompt-builder/turn-prompts.js` header NOTE;
  `prompt-builder/schema-fragments.js:24-31`.

### A4. `MEMORY_INSTRUCTION_REACTION` vs `MEMORY_INSTRUCTION_REACT` — probable copy/paste drift
- **What:** the two constants differ only by `"not a recap"` vs
  `"not a recap of the room"`. Already flagged in-code ("Left as two constants
  pending a decision").
- **Options:** (a) unify to one constant; (b) keep both.
- **My recommendation:** (a) — unify; it's the same instruction.
- **Evidence:** `prompt-builder/schema-fragments.js:13-17,24-31`.

### A5. Tier numbers still hardcoded outside `vital-thresholds.js`
- **What:** `vital-thresholds.js` declares itself "the ONE source for vitals
  tier boundaries", but `character-state.js` still hardcodes:
  Entertainment `10/25/50`, Sanity `< 75`, and the whole Temperature band
  `33/35/36/38/40/42`.
- **Options:** (a) move them into `vital-thresholds.js` (adds
  `ENTERTAINMENT_*`, `SANITY_STRAINED`, `TEMP_*`); (b) accept that prose-local
  numbers are fine and update the file's header to say so.
- **My recommendation:** (a) for Sanity/Entertainment (cheap, removes drift);
  (b) is defensible for the Temperature band.
- **Evidence:** `character-state.js:393,395-407`; `vital-thresholds.js:1-10`.

### A6. `decide` recomputes `relationshipNL` internally
- **What:** unlike the other phases, `buildDecisionPrompt` does not receive
  `relationshipNL` — it recomputes it via `buildRelationshipContext`
  (flagged in-code as "worth unifying the calling convention").
- **Options:** (a) unify the parameter across phases; (b) leave.
- **Impact:** refactor only; output should be identical if done carefully.
- **Evidence:** `prompt-builder/turn-prompts.js` header NOTE.

---

## B. Carried over from this session (still unconfirmed)

### B1. Graph map — needs your visual pass
- Right-click → 🗺 Add background image; drag / corner-resize / top-dot rotate /
  crop. Resize is **scale-about-centre**. I could not test this interactively.
- **Confirm:** do the handles behave as expected? Any inverted axis or wrong
  crop direction is a one-line sign fix — tell me which handle.
- **Also:** **unlock nodes re-enables physics**, which will pull nodes off your
  laid-out map. Option to make unlock restore positions instead: say so.
- **Evidence:** `static/js/graph/graph-background.js`.

### B2. The camp scenario has no `name`
- The app labels it `world_template`, so the graph layout persistence key falls
  back and the Save/Commit path is risky (could overwrite `world_template.json`).
- **Confirm:** give the scenario a `name`/`meta.title` (task-408).
- **Evidence:** `data/scenarios/kraktooth_goblin_camp.json` (no `name`).

### B3. Cold-blooded `Temperature: 20` on Croak-Mother
- A frog with `Temperature: 20` in Blackmarsh (18 °C) triggers
  "Critical body temp". Either a bad authored start or the temperature band not
  knowing about cold-blooded animals.
- **Confirm:** intended, or should animals have their own comfort band?
- **Evidence:** scenario player `Croak-Mother`; `character-state.js:400-407`.

### B4. Scenario character-node duplication (46 → 23)
- 22 bare-named orphan nodes plus a `player_human_explorer` artifact; raw JSON
  keys don't match their `id` fields, so dedupe must go through `WorldGraph`.
- **Confirm:** proceed with a dedupe tool (task-408)?
- **Evidence:** `docs/virtualWorld/dev_tasks/todo/world/task-408-*.md`.

---

## C. Done this session (recorded so it isn't re-litigated)

- **Readable names:** 163 single-letter locals renamed (`v`/`T`/`n` →
  `value`/`thresholds`/`vitals` …) across 11 files.
- **TypeScript:** adopted incrementally; toolchain wired (`npm run build:ts`,
  `npm run typecheck`) and `agent/rate-limiter.ts` converted as the template.
  The suggested order for the next files is in
  `docs/design/typescript-migration.md` — tell me if you want a different order.

## D. Housekeeping (no decision needed, just FYI)
- 98 of 133 `static/js` modules still await a `@module` contract header — listed
  at the bottom of `docs/design/js-module-index.md`.
- Next subsystem queued for documentation: `inspector/` (13 files, including the
  2226-line `agent-view.js`).
