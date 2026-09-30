---
type: task
status: review
area: dev
priority: medium
---

# task-593: LLM inspector: label every call site, and never fall back to a bare 'LLM'

**Filed:** 2026-09-30
**Related:** 

## Goal

Every provider call the browser makes reaches the inspector under a name that says which button or subsystem made it, so 'the inspector is empty' and 'the inspector shows 17 identical LLM entries' are both distinguishable from working

## Acceptance

- TODO

## Acceptance

- [x] **Every LLM call site names itself.** Seventeen call sites across the
      browser; eleven passed no `label`, and the collector's fallback was the
      literal `'LLM'`, so all eleven were indistinguishable in the inspector. Every
      one now carries a name:
      `inspector/generate-personality`, `inspector/generate-interest-tags`,
      `inspector/generate-fear-tags`, `inspector/generate-appearance`,
      `inspector/appearance-repair`, `inspector/edit-area|item|way`,
      `ai-generator/generate`, `ai-generator/repair`, `object-responder`,
      `settings/test-connection`.
- [x] **The interest and fear generators are told apart.** They share one
      implementation (`opts.field` is `'interest_tags'` or `'fear_tags'`), so the
      label is chosen from the field rather than given the same name twice.
- [x] **The Improve flow labels by node kind.** `InspectorHelpers.improveWithAI`
      takes a new `spec.id`, supplied as `'area'` / `'item'` / `'way'` by the three
      callers, so the shared flow reports which inspector's button was pressed.
- [x] **A repair pair is distinguishable.** `ai-generator`'s repair call is the
      *second* call of a generate/repair pair and is labelled separately; an
      inspector full of `ai-generator/generate` entries could not say which half
      produced the JSON being read.
- [x] **The fallback is derived, and never a bare `'LLM'`.** `_deriveLabel()` in
      `dataset-collector.js` uses the caller's label, then the model name, then a
      shape summary of the request (`tools` / `streamed` / `structured` / `chat`).
      A future call site that forgets to label itself is therefore still
      traceable, and is visibly *unlabelled* rather than silently impersonating the
      whole system.
- [x] **Lint and typecheck clean**; no behaviour changed — a label is capture
      metadata only, and `captureRaw` is already fire-and-forget and never throws.

## Why the fallback was the real bug

The report was "the inspector does not capture the Generate from Personality,
interest or fear buttons", and the honest answer had two parts:

1. **Capture is opt-in and was off.** Both `llm-client.js` and
   `dataset-collector.js` no-op unless `config.showRawLLM` is set, which is why
   the inspector read 0/0 and said so in its empty state. Nothing was broken;
   nothing was switched on. That part is a setting, not a defect.
2. **Those buttons were exactly the unlabelled ones.** All four inspector
   *Generate* buttons sit in `inspector/agent-view.js` and all four passed no
   label. So with the setting on, the inspector filled with entries all called
   `LLM` — visible in the tick log as `LLM -> inclusionai/ling-3.0-flash...`
   repeating. The capture had worked; the output was unreadable. Eleven of
   seventeen sites were affected, so "and probably every other request" was
   right.

The constant `'LLM'` is the part worth remembering: it is a name that carries no
information, and it is indistinguishable from a capture that failed — which is
exactly the confusion it created. The derived fallback removes that class of
ambiguity rather than just labelling today's call sites.

## Architecture note: there is no server-side provider call to capture

The backend decides *that* an LLM is needed and queues the request
(`virtual_world_engine.py:907 queue_llm_respond`); the browser makes the provider
call and posts the result back to `/api/llm_respond`
(`routes/action_handlers.py:171`). So every provider request really does pass
through `llmClient`, and labelling the call sites covers all of them. The only
outbound HTTP in the backend is `mcp_server.py`'s `httpx` client, which talks to
*this* app rather than to a provider.

That is why this was a dozen lines and no new plumbing — worth stating, because
"the LLM inspector does not capture server-side calls" would have been a much
larger piece of work had the architecture been the other way round.

## Notes

- `llm-client.js` captures on **all three** exits already — error (154), streamed
  (177) and normal (182) — so nothing was missing on the send side; only the
  naming was.
- `chatWithTools` (the NL editor and the agent loop) already passes a label and
  routes through the same `chat()`, so tool-calling exchanges were never the
  problem.
