---
type: task
status: todo
area: prompting
priority: medium
wiki: "[[Feature Map]]"
---

# task-773: Send the character's profile image to vision-capable models

**Filed:** 2026-10-11
**Related:** task-512 (Expression Pack), task-87 (paperdoll art), task-405 (raw-LLM capture)

## What

The app now holds real character art — **782 files** under `static/images/nodes/`
(`player_Arix-profile-amused-1791423330210.webp`, `area_foyer-*.webp`,
`item_dusty_overcoat-*.webp`, …), referenced from the scenario as
`properties.expressions.<emotion>.profile`. Every LLM call today carries **text
only**: the model is told what a character looks like in prose and never sees the
portrait that already exists on disk.

Send that portrait along, but only to models that can actually read an image.

## Why

- The generators that most need eyes are the ones that judge appearance:
  appearance/personality generation, interest + fear tags, and auto-dress all
  reason about "what would this person look like / wear" from prose alone, while
  an authoritative render sits one property away.
- The agent turn prompts describe the character to itself. A model that can see
  its own portrait can stay consistent with art that a human is looking at.
- It must be strictly additive: a text-only model or a provider without image
  support must produce byte-identical requests to today, or every existing
  scenario's behaviour changes for no reason.

## How

1. **Capability gate, one place.** `llm-client.ts` has no notion of what a model
   can do (`config.ts` holds only model/keys/thinking). Add a per-model image
   capability (config-driven, default off) read next to the existing
   `thinking`/`thinkingEffort` flags, so the decision lives beside the other
   provider quirks rather than at each call site.
2. **Content parts, not strings.** `LLMMessage.content` is a string everywhere
   today. Allow an array of parts — `[{type:'text',text}, {type:'image_url',
   image_url:{url}}]` — and only build it when the gate is on.
3. **Inline base64, never the local URL.** The stored value is
   `/static/images/nodes/...webp`, which a remote provider cannot fetch. Read the
   file and send a `data:image/webp;base64,...` URL (DeepSeek accepts JPEG/PNG/
   GIF/WebP data URLs; 32 MiB per inline image). Cache the encoded bytes per
   path — re-encoding on every turn would be wasteful.
4. **User/developer messages only.** DeepSeek rejects images in system or
   assistant messages. The agent's persona is the system message
   (`agent-engine.ts:133`), so the image belongs in the user turn content
   (`agent-engine.ts:743`), not the system prompt.
5. **Which calls, in order.** Start with the character-facing generators
   (`agent-view.ts:2162` tags, `:1851` auto-dress, `ai-generator.ts:62/126`
   appearance/personality) and the agent turn prompt. Area/item art and the
   WorldPainter canvas are explicitly later — same machinery, more sources.
6. **Observability.** The raw-LLM capture (task-405) already records the request
   body; confirm the image part shows up there and that a text-only model's
   captured body is unchanged.

## Steps to verify

1. Configure a vision-capable model (e.g. `deepseek-flash`) and generate fear
   tags for a character that has expressions.
   - expected: the captured request carries an `image_url` part with a base64
     data URL alongside the text; the tags reflect the portrait.
   - observed: TODO
2. Switch to a text-only model and repeat.
   - expected: the captured request body is byte-identical to today's (string
     content, no image part).
   - observed: TODO
3. A character with no `expressions` on its node.
   - expected: no image part, no error, the prompt is unchanged.
   - observed: TODO

## Acceptance

- [ ] A per-model image capability exists in config and is read by the client
      beside the other provider flags.
- [ ] When on, the character's `expressions.<emotion>.profile` (or the neutral
      render) is sent as a base64 `image_url` content part in a **user**
      message; the system prompt stays text.
- [ ] When off — or on a text-only model, or for a character with no art — the
      request body is unchanged from today.
- [ ] Encoded images are cached per path, not re-read per call.
- [ ] At least one generator produces visibly image-informed output against a
      vision model, verified live in the browser.
- [ ] The raw-LLM capture shows the part arriving, and the unit tests pin the
      text-only path as unchanged.

## Files

- `static/js/llm-client.ts` — capability read, content-part support, base64 cache
- `static/js/config.ts` — the per-model image flag
- `static/js/agent-engine.ts` — attach the portrait to the user turn
- `static/js/inspector/agent-view.ts`, `static/js/shared/ai-generator.ts` — generator call sites
- `static/js/character-art.ts` — the existing owner of profile/full render lookup

## Browser UI and intended live verification

Intended UI home: select a character with `properties.expressions.<emotion>.profile` art → run a character turn through the existing game/agent surface → inspect the Raw LLM capture in the Event Stream.

Current availability: the card records 782 profile images and text-only LLM requests. Per-model image capability, image payloads, caching, and image-informed output are planned; no image transfer is claimed as available.

Live steps when available:
1. Configure a vision-capable model and enable its image capability. Select a character with a known profile image and run one generation.
   - expected: Raw LLM capture shows the profile as a base64 `image_url` part in a user message; the system prompt remains text.
2. Repeat with a text-only model, with the capability disabled, and with a character with no art.
   - expected: each request body is unchanged from the current text-only payload and contains no image part.
3. Run two generations using the same image and inspect the request trace/cache diagnostics.
   - expected: the image is read/encoded once per path and reused; each request still contains the correct image content part.
4. Compare the vision-model response with the text-only response for an image-specific authored detail visible in the profile but absent from prose.
   - expected: only the vision-capable enabled request can ground the response in that image detail.

This section is not a claim that planned UI exists or works today.
