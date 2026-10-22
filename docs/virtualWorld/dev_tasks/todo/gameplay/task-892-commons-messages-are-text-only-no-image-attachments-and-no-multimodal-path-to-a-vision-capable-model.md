---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-824, task-891, task-299]
---

# task-892: Commons messages are text-only: no image attachments, and no multimodal path to a vision-capable model

**Filed:** 2026-10-21
**Related:** task-824 (The Commons itself), task-891 (editing and deleting messages - the two share the message record and the feed renderer), task-299 (long-distance communication, the other place in-world media mechanics are scoped)

<!-- deps:start -->
**Related:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]], [[task-891-commons-messages-cannot-be-edited-or-deleted-by-the-human-or-by-the-character-that-wrote-them]], [[task-299-long-distance-communication]]
<!-- deps:end -->

## What

A Commons message is text-only, and it has to be. The message record carries `text` and nothing else (`engine/commons.py:175`), the LLM request format is `content?: string` (`static/js/llm-client.ts:21`), and the prompt the agent sends is a single `user` string (`static/js/commons/commons-agent.ts:161-169`).

The request is to let a message carry an image, so that a character (or the human) can post a picture and the other side can actually see it - which means the image has to reach a model that can look at it.

This card is deliberately split into two halves, because only one of them is unblocked today:

- **Half A (blocked, needs a decision):** images in the *model's* view. Today there is no multimodal path anywhere in this app. `LLMMessage.content` is a string, so an OpenAI-style `content: [{type:'text'},{type:'image_url'}]` array cannot even be sent. There is no model-capability metadata either - `config.ts` stores `model` and `provider` as bare strings with no notion of which models are vision-capable. And the app's default is a local LM Studio server running `glm-4-9b-0414`, which is text-only. So 'when we get a model that has image capabilities' is a real precondition, and the honest shape of half A is *a capability flag plus a multimodal request path*, not a Commons feature.

- **Half B (unblocked, and the point):** images in the *user's* view. A message can carry an image attachment that the reader sees inline in the feed and can click to enlarge, whether or not any model involved can perceive it. The human and the other characters read the image; only the model's ability to *understand* it depends on the provider.

Half B is the part worth doing now. A Commons where you can post a picture is a better Commons even if the character looking at it can only read the caption.

## Why

The Commons is the only place a character's public speech is kept, and right now that record is entirely verbal. A character who shows you something - a wound, a letter, a map, a face - has to describe it in prose and trust the reader to imagine it. That is the simulacra gap in miniature: the world has images (803 files under `static/`, a whole `character-art.ts` resolver for emotion-aware portraits) and the Commons cannot show any of them.

There is also a simulation reason. A message that carries an image is a *reference* to something in the world - a character's current portrait, an item, a place. That reference is a fact the simulation can act on. A character looking at a picture of a place they have never visited is a different situation from a character reading a description of it, and the difference is exactly the kind of thing this engine exists to model.

The half-split is deliberate. Half A is a platform capability that has to be built once and used by every LLM caller in the app, not a Commons feature. Half B is a Commons feature that works today and gets better when half A lands. Doing them in one card would block the useful half behind the model question.

## How

**Half B - attachments (do this first).**

1. **Storage.** Extend the message record with an `attachments` list. Each attachment needs a stable id, a mime type, a byte size, and a way to fetch the bytes. The bytes should not be inlined into the message dict - the message list is held in memory and serialized wholesale (`engine/serialization.py:415` writes `commons.to_dict()`), and a base64 image per message would bloat every save. A reference (an id, or a path under an uploads directory) is the right shape.
2. **Route.** `POST /api/commons/messages` accepts an optional `attachments` list, and a new route serves or serves-and-validates the bytes. Enforce a size cap and a mime allowlist server-side; the client is not a trust boundary. Reuse the existing `require_access` check so an attachment cannot be smuggled into a channel the poster cannot post in.
3. **UI.** The composer gets an attach control; `renderMessages()` (`commons-ui.ts:313`) renders an inline thumbnail under the message text, with a click-to-enlarge lightbox. A message with an attachment and no text is legal - a picture on its own is a message - so the `text` emptiness check at `routes/commons.py:200` needs to become 'no text AND no attachments'.
4. **The caption.** Every attachment should carry a caption, because a character who cannot see the image still needs to know what it is. The caption goes in the message text or in the attachment record, and it is what the model sees. That is the bridge to half A.

**Half A - multimodal model path (blocked on a decision).**

5. **Capability metadata.** Add a per-model capability flag (vision yes/no) to the model/provider configuration in `config.ts`, so the app can know whether the selected model can perceive an image instead of guessing from the model name. This needs the settings UI to expose it, and it needs a sensible default of 'no' so a local text-only model keeps working.
6. **Request format.** `LLMMessage.content` (`llm-client.ts:21`) has to widen from `string` to `string | Array<{type:'text'|'image_url', ...}>` for the Chat Completions shape, and the Responses API shape differs again (it uses `input_image` / `input_text`). `llm-client.ts` already carries both builders (`_buildResponsesBody` and the chat path), so both need the multimodal form.
7. **Where images come from.** An attachment the character is *sending* is not the same as an image the character is *looking at*. A character looking at a picture in the feed needs the image to be resolved into the request. That resolution is the expensive part: bytes have to be fetched and either inlined as a data URL or uploaded and referenced, per request, for every character that reads a channel with pictures in it. A model that reads a channel with twenty image messages pays for twenty images every turn. This is a real cost and it needs a policy, not an accident - most likely: images are described by caption to the model by default, and the raw image is sent only when the model has vision AND the message is recent AND the turn budget allows it.
8. **Non-vision fallback.** When the model has no vision, the caption is the whole message to the model. The character should not pretend it cannot see the picture at all, because the *reader* saw it; the fiction is that the picture is described, and the caption is that description.

**The decision half A needs, and should not be assumed:** does an image sent to The Commons get *perceived* by the receiving characters (so the simulation treats it as seen), or is it decoration that only the human sees? The first is the interesting one and it costs real inference; the second is cheap and honest. The Commons doc should say which one it is, per its own 'what you can do' section.

## Browser UI and intended live verification

Intended UI home: /commons -> the composer at the bottom of the conversation, and the message feed.

Current availability: Not implemented. Verified 2026-10-21: the message record has no attachments field, the LLM message type is text-only (`LLMMessage.content?: string`), and there is no model-capability metadata in the config. The character art system (`static/js/character-art.ts`) already resolves emotion-aware portraits for the graph and the turn composer, so image resolution exists as a concept - it is simply not connected to the Commons.

Live steps when available:
1. Open /commons and use the attach control in the composer to choose an image.
2. expected: a caption field and an attach control; a message with only an image and no text can be sent.
3. Post the message and read the feed.
4. expected: the image renders inline under the message and opens full size on click; the reader sees the image whether or not any model involved can perceive it.
5. Step a character that has read the channel and inspect what it received.
6. expected: with a text-only model the character receives the caption as the message content and does not claim to have seen the image.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] A message can carry one or more image attachments with a caption.
- [ ] A message with an attachment and no text is accepted and rendered.
- [ ] The feed renders the attachment inline, and it can be opened full size.
- [ ] Attachments are size-capped and mime-restricted server-side, and an attachment cannot be posted to a channel the poster cannot access.
- [ ] A character with a text-only model receives the caption as the message content, and the character does not claim to have seen an image it could not see.
- [ ] Model vision capability is explicit configuration rather than inferred from a model name, and defaults to off.
- [ ] The LLM request path can carry a multimodal message when the selected model has vision, in both the Chat Completions and Responses formats.
- [ ] The Commons doc states plainly whether an attached image is perceived by the receiving characters or is visible only to the human.

## Files

- `engine/commons.py`
- `routes/commons.py`
- `static/js/commons/commons-api.ts`
- `static/js/commons/commons-ui.ts`
- `static/js/llm-client.ts`
- `static/js/config.ts`
- `static/js/ui/settings-view.ts`
- `static/js/agent/prompt-builder/character-state.ts`
- `docs/virtualWorld/Gameplay/The Commons.md`
