# task-943: Two-Stage Actor-to-Interpreter Pipeline via Canonical ResponseParser

**Status:** todo  
**Lane:** gameplay  
**Created:** 2026-11-10  
**Updated:** 2026-11-10  
**Dependencies:** task-933, task-942  

---

## 1. Context & Motivation

Current VirtualWorld cognition forces an LLM to be a novelist and an API transaction client at the same instant. Under this dual burden, small/local models (e.g. 8B) suffer attention collapse: defaulting to biological maintenance loops (`Attention: bladder` -> `action: relieve`) during high-stakes dramatic beats, dropping whisper targets, and emitting wooden dialogue.

Instead of reinventing an ad-hoc intermediate format, this task decouples creative character roleplay from mechanical extraction by adding an **Action Interpreter** translation layer that outputs the **exact canonical schema defined by `ResponseParser.ts`**.

---

## 2. Architecture: Pure Separation of Concerns

```
┌──────────────────────────────────────────────────────────┐
│ 1. Narrative Actor (Agent or Director)                   │
│    • Inhabits character voice, immediate senses, beat    │
│    • Emits 2-4 sentences of unconstrained prose          │
│    • No JSON rules, no action schema in actor prompt     │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼ Raw Roleplay Prose
┌──────────────────────────────────────────────────────────┐
│ 2. Action Interpreter (Dedicated Fast Model)             │
│    • Pluggable model (local e.g. lfm3-1.7b, or OpenRouter)│
│    • Strictly transcribes prose into canonical schema    │
│    • ZERO intermediate dialects - reuses ResponseParser  │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼ Canonical Engine Dictionary
┌──────────────────────────────────────────────────────────┐
│ 3. Canonical Parser & Grounding Engine                   │
│    • ResponseParser.parseReaction() handles normalization│
│    • Engine validates reach, budget, slots, entities     │
│    • Executes world mutation through existing pipeline   │
└──────────────────────────────────────────────────────────┘
```

---

## 3. The Canonical Engine Contract (No Ad-Hoc Schemas)

The interpreter outputs the exact canonical fields that `ResponseParser` and `AgentEngine` already consume:

```json
{
  "inner_monologue": "string (what character privately thinks or feels) or null",
  "action": "single verb from available affordances or null",
  "item": "interacted item name or null",
  "target": "target entity, exit, or person or null",
  "speech": "spoken words without quotes or null",
  "volume": "whisper | say | shout | scream",
  "emote": "physical body language or null",
  "memory": "what the character will personally remember or null",
  "emotion": "emotion label (e.g. uneasy, determined, terrified) or null"
}
```

Rules:
1. **No invented schemas:** No `thought` instead of `inner_monologue`. No `say` instead of `speech`. No dropped `memory` or `item`/`target`.
2. **Direct delegation:** The raw text from the interpreter LLM passes directly to `ResponseParser.parseReaction()`, ensuring all existing repair heuristics and normalization rules apply.
3. **Model Selection:** Users can toggle a dedicated interpreter worker in Settings (e.g., fast local model like `lfm3-1.7b@q4_0` or OpenRouter `dots-studio/dots-3-note-preview:free`), or fall back to the active main profile.

---

## 4. Implementation Checklist

- [x] Add `interpreterModelEnabled`, `interpreterApiBase`, `interpreterModel`, `interpreterApiKey`, `interpreterApiFormat` to `ConfigManager` and Settings modal.
- [x] Create `static/js/agent/action-interpreter.ts` registered under `@module agent/action-interpreter`.
- [x] Align extraction prompt to emit strictly canonical keys (`inner_monologue`, `speech`, `item`, `target`, `memory`).
- [ ] Refactor `ActionInterpreter.interpretProseToAction` to delegate directly to `ResponseParser.parseReaction()`.
- [ ] Update unit tests in `tools/unit/test_action_interpreter.js` to assert against canonical keys.
- [ ] Connect interpreter into `AgentEngine.draftTurnForCharacter` when two-stage cognition toggle is enabled.
- [ ] Verify zero em-dashes and clean TypeScript build.
