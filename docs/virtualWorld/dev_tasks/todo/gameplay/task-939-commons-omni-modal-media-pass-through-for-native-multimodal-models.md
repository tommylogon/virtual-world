---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-824, task-892, task-935]
---

# task-939: The Commons omni-modal media pass-through for native multimodal AI models

**Filed:** 2026-11-09
**Related:** task-824, task-892, task-935

<!-- deps:start -->
**Related:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]], [[task-892-commons-messages-are-text-only-no-image-attachments-and-no-multimodal-path-to-a-vision-capable-model]], [[task-935-commons-dialogue-testing-memory-toggle]]
<!-- deps:end -->

## What

Enable native multi-modal media attachments (image, audio, and video) in The Commons, routing the raw media directly into supported omni-modal models (such as Liquid AI LFM3-Omni-2B, Gemini Multimodal, and GPT-4o) without server-side transcription workarounds:

1. **Commons Message Media Attachments**:
   - Extend Commons message schema (`engine/commons.py`) with an `attachments` list:
     - `id`: Unique attachment identifier.
     - `mime_type`: Supported MIME types (`image/*`, `audio/*`, `video/*`).
     - `url`: Path to stored asset under `static/assets/uploads/`.
     - `caption`: Optional human or author caption.
   - Extend Commons composer in `static/js/commons/commons-ui.ts` with a media attachment button and upload handler.
2. **Native Omni-Modal Router & Pass-Through**:
   - In `static/js/commons/commons-agent.ts` and `engine/llm_client.py`:
     - Detect whether the active model supports the attachment's modality (via `data/model_bench/model_registry.json` or model capability flags).
     - For omni-modal models: construct the provider's native multi-part payload (e.g. Gemini `parts` array with `inline_data`, or OpenAI multimodal content blocks).
     - Pass the media directly to the inference endpoint. The omni-modal model watches, listens, or reads the file natively and produces an authentic in-character reaction in `inner_monologue` and dialogue.
3. **Text-Only Fallback**:
   - If the receiving character's model is text-only (e.g. standard Llama 3 8B), substitute the raw media with the attachment's `caption` or a diegetic system note: `[Media attachment: audio clip (24s) - device cannot play audio]`.

## Why

Next-generation omni-modal architectures (such as Liquid AI's LFM3-Omni-2B or Gemini) are unified end-to-end models designed to perceive video, audio, and images simultaneously. Forcing media through external ffmpeg frame-splitters or speech-to-text engines is slow, CPU-intensive, destroys auditory tone and visual cadence, and adds unnecessary dependencies. By treating The Commons as a clean pass-through router, supported models can natively experience in-game media as genuine sensory input.

## How

1. In `engine/commons.py`:
   - Update `post_message` to accept an optional `attachments` list containing `{ id, mime_type, url, caption }`.
   - Update message serialization in `to_dict()` and `from_dict()`.
2. In `routes/commons.py`:
   - Implement `POST /api/commons/upload` to store uploaded media files into `static/assets/uploads/commons/` and return metadata.
3. In `static/js/commons/commons-agent.ts`:
   - When building prompt messages for a character's turn, check if unread messages contain attachments.
   - If model capability supports the MIME type, format the message content as an array of parts (text prompt + media block).
4. In `static/js/commons/commons-ui.ts`:
   - Render attachment previews in the chat stream: inline images, playable `<audio>` controls for voice notes, and compact `<video>` players for video clips.

## Browser UI and intended live verification

Intended UI home: The Commons drawer composer and message stream.

Current availability: Commons messages only accept and render plain text strings. No file attachment affordance or multimodal prompt forwarding exists.

Live steps when available:
1. Open The Commons drawer in the browser UI and select a channel (e.g. `#general`).
   - expected: Composer displays an attachment paperclip button next to the text input.
2. Click the attachment button and upload an audio note or image file (e.g. `evidence_photo.jpg`).
   - expected: Attachment thumbnail appears in the composer staging area with an optional caption field.
3. Type *"Take a look at this footprint"* and press send.
   - expected: Message appears in the chat stream with the image rendered inline.
4. Advance simulation turn so an omni-modal agent character (e.g. configured with Gemini or LFM3) processes the message.
   - expected: Agent's turn inspects the image natively and produces a response referencing visual details from the photograph in character.
5. If the recipient uses a text-only model, trigger their turn.
   - expected: Agent responds to the caption and acknowledges receiving an image attachment.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In browser UI, inspect Commons composer for attachment controls.
   - expected: Attachment button allows selecting image, audio, or video files.
   - observed: Only single-line text input exists.
2. Post message with attachment via API: `POST /api/commons/messages`.
   - expected: Accepts `attachments` array and persists to Commons state.
   - observed: Message schema rejects or drops unknown attachment fields.
3. Inspect prompt builder output when character is assigned an omni-modal model.
   - expected: Formats multi-part payload containing media URI / inline data.
   - observed: Only builds plain text strings.
4. Run tests: `pytest tests/test_commons.py`.
   - expected: All unit tests pass.

## Acceptance

- [ ] Commons message schema supports an `attachments` list for image, audio, and video files.
- [ ] Commons UI supports uploading, previewing, and displaying media attachments inline.
- [ ] Prompt builder forwards raw media attachments natively to omni-modal models (LFM3, Gemini, GPT-4o).
- [ ] Text-only models receive clean diegetic caption fallbacks without crashing.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `engine/commons.py`
- `routes/commons.py`
- `static/js/commons/commons-ui.ts`
- `static/js/commons/commons-agent.ts`
- `static/js/llm-client.ts`
- `tests/test_commons.py`
