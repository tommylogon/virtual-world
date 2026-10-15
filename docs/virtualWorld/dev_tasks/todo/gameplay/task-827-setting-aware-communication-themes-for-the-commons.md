---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-824, task-299]
---

# task-827: Setting-aware communication themes for The Commons

**Filed:** 2026-10-15
**Related:** task-824 (The Commons), task-299 (in-world communication devices)

<!-- deps:start -->
**Related:** [[task-824-stage-chat-turn-based-character-perspective-chat-page]], [[task-299-long-distance-communication]]
<!-- deps:end -->

## What

Let a world author choose how The Commons' conversations are presented for the
scenario's setting. A fantasy world might frame them as letters or notices; a
modern world might use SMS or instant messages; another setting might use voice
calls. Keep the public conversation, private groups, and direct messages usable
under each theme.

## Why

The Commons should be a setting-neutral communication surface. Its current
text-message presentation fits some worlds and makes others feel like they have
been given a modern phone without author intent.

## How

- Find the existing scenario/world authoring and persistence seam for this
  setting choice before adding a new setting store.
- Treat the theme as presentation and communication framing over The Commons'
  existing channels, memberships, messages, and read cursors. Do not add a
  second conversation store, character, persona, memory, or lived-experience
  source.
- Make the selected theme visible in the UI and in the character's existing
  communication prompt, while preserving the selected character's `Player`
  identity and standard memory routes.
- Keep authorization, unread state, explicit reads, save/load, and autosave
  behavior independent of the chosen theme.
- Decide explicitly whether a voice-call theme is only a presentation of the
  existing conversation transcript or should invoke task-299's in-world device
  and activity mechanics. A theme must not imply physical phones, radios,
  distance rules, or call state unless that mechanic is actually wired.
- Verify at least two different themes over the same public, group, and DM
  model in the browser.

## Steps to verify

1. Select a setting-appropriate communication theme.
   - expected: The Commons labels, message presentation, and character prompt
     reflect it; channel ids, memberships, privacy, and read cursors remain the
     same.
   - observed: TODO
2. Save and reload the world with a selected theme and active conversations.
   - expected: the theme and communication state return through the existing
     persistence path, without a second conversation or character-memory store.
   - observed: TODO
3. Exercise public, group, and DM reads and writes under two different themes.
   - expected: server-side membership checks and per-character explicit read
     behavior are unchanged.
   - observed: TODO

## Acceptance

- [ ] A world author can select a communication theme using the existing
  authoring and persistence model.
- [ ] The Commons presents and prompts for communication in the selected
  setting's medium without replacing its shared channel model.
- [ ] Public, group, and DM membership, authorization, unread state, and
  explicit read cursors behave identically across themes.
- [ ] Existing `Player` identity and memory paths remain the only character
  mind and durable subjective-memory sources.
- [ ] Save/load and autosave preserve the theme and conversation state.
- [ ] Voice-call behavior is clearly bounded against task-299's physical device
  and activity mechanics.
- [ ] Browser verification covers at least two themes and all three channel
  types.

## Files

- The Commons authoring/configuration, presentation, and prompt integration
- Existing Stage Chat conversation persistence, only where required
- Targeted tests and browser checks for theme behavior
