---
group: Prompt & Narrative Quality
---
# Review Rich Narration / Area Description Output Quality

**Status**: In Review — implemented (verified 2026-08-08 code audit; moved from todo). Hybrid approach per the task's Fix Option 1: `buildNarratedRoomContext()` (`prompt-builder.js:831`) builds the full room context and replaces only the `Description:` line with LLM narration; the old full-replacement rich-observation path is gone. AI-narration of action results also lives in `agent-engine.js`. Pending: visual/E2E review of the hybrid output.

**Filed**: 2026-07-30
**Priority**: Low
**Status**: Design

---

## Problem

When rich narration mode is on, the area description is generated via LLM and used as the `observeContext` in the observation prompt. This replaces `buildRoomContext()` output. The generated descriptions are often verbose and may not include all the structural information (exits, items, inventory) that the standard room context provides.

Additionally, the observe path in rich mode builds its own inventory string but doesn't include the `Appearance:` or `From where you stand...` sections from `buildRoomContext()`.

## Fix Options

1. **Hybrid**: Use rich narration for the narrative portion, then append the standard structural sections (exits, items, inventory, appearance)
2. **Full replacement**: Rely entirely on the LLM-generated description and accept it may omit structural details
3. **Structured request**: Improve the prompt sent to the narration LLM to request specific sections

## Related

- `_generateRichObservation()` in `agent-engine.js`
- `buildRoomContext()` and `buildNarratedRoomContext()` in `prompt-builder.js`
