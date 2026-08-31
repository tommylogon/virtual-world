# Task-330: Trigger Effect â€” LLM-Generated Response

**Status**: Todo — blocked 2026-08-30: engine-side LLM provider was removed (task-99, backend LLM modules). Trigger effects fire server-side; llm_respond needs a server LLM path (provider route or browser round-trip callback). Composition design (on_speech + speech_matches gate) stays valid — implement once the LLM host question is settled.
**Filed**: 2026-08-23

## Summary

New trigger effect type `llm_respond` (name TBD): when a trigger fires, the engine
requests an LLM-generated spoken response on behalf of the node, using instructions
and/or a static message from the effect's parameters. Lets world objects hold simple
conversations without being full characters/agents.

## Motivation (Tommy's examples)

- A **magic mirror** that tells you to fuck off unless you said the right password.
- Shopkeepers/merchants with simple dialogue that reacts to what you actually said,
  without spinning up a full agent turn for each.

The password gate composes with EXISTING trigger conditions: `on_speech` +
`speech_matches` â†’ `llm_respond{instructions:"reveal the vault"}`, else branch /
second trigger â†’ plain `message` effect ("The mirror stays silent."). No new
condition machinery needed.

## Proposed shape

```json
{
  "type": "llm_respond",
  "params": {
    "instructions": "You are a grumpy magic mirror. Stay in character. Be brief.",
    "fallback_message": "The mirror remains silent.",
    "max_words": 40
  }
}
```

- `instructions` â€” persona/behavior prompt for the generation.
- `fallback_message` â€” used when no API key / call fails / empty reply.
- Optional extras to decide during design: `name` (attribution label), cooldown.

## KEY ARCHITECTURAL CONSTRAINT

**LLM calls are browser-side only** (`AGENTS.md`: backend LLM modules removed;
API keys live in browser IndexedDB). The Python engine CANNOT generate the text.
Sketch:

1. Backend `_execute_effects()` sees `llm_respond` â†’ records a pending-response
   request (on the node, the area event queue, or a new lightweight store) with
   context: speaker name, the speech heard, area, instructions params.
2. Frontend polls `worldState.fetch()` as usual â†’ picks up pending requests â†’
   generates via `VW.llm` (reuse the pattern in `static/js/shared/ai-generator.js`
   â€” system+user messages, parse, fallback).
3. Frontend posts the result back through the normal action endpoint
   (`speak <line>` attributed to the object's display name) or a small dedicated
   route that logs it as an area/speech event.
4. Request is marked consumed; `fallback_message` covers offline/no-key/failure.

## Files likely touched

- `engine/trigger_system.py` â€” effect registration + pending-request store
- `shared/trigger-types.js` + `shared/trigger-editor.js` â€” effect type in editor UI
- `agent-engine.js` or a small `agent/object-responder.js` â€” pickup + generation
- Possibly a routes module for consume/report-back if not reusing `/api/action`
- Serialization if pending requests must survive autosave (probably NOT â€” transient)

## Open questions

- Attribution: does the object "speak" into the room (visible to all agents in the
  area) or whisper back only to the speaker?
- Do object responses enter nearby agents' conversation memory? (Probably yes via
  normal speech pipeline â€” free ambient dialogue.)
- Cost/rate limiting: one LLM call per qualifying trigger hit could be chatty;
  per-node cooldown param?
- Behavior-side twin filed separately as task-331 (same runtime, different executor).

