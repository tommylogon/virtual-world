---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-824, task-299]
---

# task-827: Setting-aware communication themes for The Commons

**Filed:** 2026-10-15
**Related:** task-824 (The Commons), task-299 (in-world communication devices)

<!-- deps:start -->
**Related:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]], [[task-299-long-distance-communication]]
<!-- deps:end -->

## What

Add two setting-aware Commons modes: Live social (public, group, and DM channels) and Town board & letters (public notice posts and private one-to-one letters; group conversations unavailable).

## Why

The Commons should be a setting-neutral communication surface. Its current
text-message presentation fits some worlds and makes others feel like they have
been given a modern phone without author intent.

## How

- Store the selection as the scenario's `commons_theme`, defaulting old scenarios to `live_social`.
- Keep the existing channels, memberships, messages, read cursors, Player identity, and memory paths as the only sources of truth. Theme changes only how channels are presented and which kinds are available.
- In `town_board`, hide and reject group operations without deleting saved group data; switching back to `live_social` restores access.
- Tailor UI and agent prompts to the selected medium. Report public-board unread counts as new posts and DM counts as new letters; message contents remain hidden until explicit read.
- Town-board delivery remains immediate inside The Commons. Do not introduce physical mail, distance, devices, or voice-call mechanics; those remain outside this task and in task-299's scope where applicable.

## Steps to verify

1. Select a setting-appropriate communication theme.
   - expected: The Commons labels, message presentation, and character prompt reflect the selected medium; channel ids, memberships, privacy, and read cursors remain the same.
   - observed: Verified in the browser on 2026-10-16. Switching between Live social and Town board & letters updates the labels and presentation without changing the underlying channel state. Town board presents the public channel as notices and DMs as letters; delivery remains immediate and no physical-world behavior is implied.
2. Save and reload the world with a selected theme and active conversations.
   - expected: the theme and communication state return through the existing persistence path, without a second conversation or character-memory store.
   - observed: `tests/test_commons.py` verifies theme and active conversation persistence through the existing scenario/save paths. The Kraktooth scenario now authors the town-board theme plus public, group, and DM examples.
3. Exercise public, group, and DM reads and writes under two different themes.
   - expected: server-side membership checks and per-character explicit read behavior are unchanged.
   - observed: Verified in the browser on 2026-10-16: created a public post and private letter in Town board & letters; created a group in Live social; switched to Town board and confirmed the group was hidden and unavailable; switched back and confirmed it reappeared. `python -m pytest tests/test_commons.py` passes (16 tests), including server-side group restrictions, channel access, and persistence.

## Acceptance

- [x] A world author can select Live social or Town board & letters for the scenario, and the choice survives save/load.
- [x] Live social supports public, group, and DM channels; Town board & letters supports public posts and private letters while disabling group operations.
- [x] Disabled group channels are hidden and inaccessible in Town board & letters but preserved for a switch back to Live social.
- [x] Agent prompts use mode-appropriate channel names and notification counts, hide message bodies until explicit read, and retain relationship-based known-name rules for recipients.
- [x] Channel privacy, read cursors, Player identity, and memory paths remain unchanged.
- [x] Browser verification covers both modes, public and DM communication in Town board & letters, and group behavior across a switch to and from Live social.

## Files

- The Commons authoring/configuration, presentation, and prompt integration
- Existing conversation persistence for The Commons, only where required
- The Kraktooth town-board scenario example
- Targeted tests and browser checks for theme behavior

## Browser UI and intended live verification

Verified UI home: **Communication mode** in The Commons and its scenario-level `commons_theme` setting. The Kraktooth goblin camp is authored in Town board & letters with a public notice, a private letter, and a preserved group conversation that is unavailable until switching to Live social.
