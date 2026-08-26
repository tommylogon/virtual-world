/**
 * prompt-builder/index.js — Module manifest.
 *
 * The prompt builder was split from the monolithic prompt-builder.js
 * (2026-08-09) into seven files, each merging its exports into the shared
 * `window.PromptBuilder` namespace via `Object.assign`:
 *
 *   helpers.js           — leaf-level utilities (light levels, articles,
 *                          relation maps, anonymous/voice labels, way handles,
 *                          plan check, second-person framing, activity +
 *                          self-speech)
 *   character-state.js   — "=== YOUR STATE ===" fragments (emotion, relations,
 *                          insanity, traits, size, perceived state, vitals,
 *                          plan context)
 *   memory-context.js    — async memory retrieval + investigation notes
 *   room-context.js      — the area context assembler (preamble, room, exits,
 *                          people, witnessed events, narrated room)
 *   context-sections.js  — shared context-fragment registry with buildContextBlock()
 *   schema-fragments.js  — shared instructional text + JSON schema fragments
 *   vital-thresholds.js  — the single source for vitals tier boundaries
 *                          (shared by describeVitals + plan-tracker criticalNeeds)
 *   contextual-actions.js — per-turn "=== AVAILABLE ACTIONS ===" block + item
 *                          action brackets (computeItemActions, carriedItemNodes)
 *   conversation-context.js — speech salience (addressed-to-you vs overheard)
 *                          marking for WITNESSED + soft anti-repeat talkiness
 *   system-prompt.js     — the static character system prompt (compact ACTIONS
 *                          core, rules, SPEECH & VOLUME)
 *   turn-prompts.js      — per-phase prompt builders (observe/decide/react/
 *                          dash follow-up)
 *
 * Load order between these files does not matter: nothing executes at load
 * time, only at call time (after every script in index.html has been
 * evaluated). The public API is flat — PromptBuilder.buildRoomContext(...)
 * etc. — so agent-engine.js needs no changes.
 *
 * Load ALL NINE files BEFORE agent-engine.js in index.html.
 */
