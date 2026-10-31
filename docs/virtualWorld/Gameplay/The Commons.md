---
type: doc
tags: [system/gameplay]
---

# The Commons

## What it is

The Commons is a shared place where characters can communicate through one of
two setting-aware presentations. The live-social mode offers a public
conversation, private group chats, and one-to-one direct messages. The
town-board mode offers public notices and private letters, with group chats
unavailable. The people using it are the scenario's existing characters;
channels and messages are communication state, not another set of minds or
memories.

## What you see / what you can do

Open **💬 The Commons…** from the game menu. Use **Communication mode** to
choose **Live social** or **Town board & letters** for the current scenario.
Live social is laid out like a messaging app. Town board & letters presents a
public notice board and one-to-one private correspondence. In either mode,
choose whose view you are inspecting, select an available channel, read its
contents and members, and write to that destination. The composer names the
character who is writing.

The Kraktooth goblin camp demonstrates the town-board presentation: Zikka posts
a warning about tracks on the public board, Vekka sends Gribba a private letter,
and the camp-watch group remains stored but unavailable until the scenario is
switched to Live social.

The conversation header tells you who can join:

- In Live social, a public conversation says **“Open conversation · anyone can
  join.”**
- In Live social, a group says **“Private group · N members.”** Its creator can
  add or remove members.
- A direct message says **“Direct message · just the two of you”** in Live
  social and appears as a private letter in Town board & letters.
- In Town board & letters, the public channel is **“Town notice board ·
  everyone can read and post.”**

Unread badges belong to the selected character's view. Opening The Commons starts
paused, so looking around does not start autonomous character turns. **Pause**
and **Step Next** control character activity; hiding the browser tab pauses it as
well.

## How it works

### Conversations and privacy

The public channel is available to every character. A private group has an
explicit member list, and only its creator can change that list. A direct
message has exactly two participants. The server checks channel membership when
listing conversations, fetching messages, reading, and posting; hiding a private
conversation in the interface is not the access control. Town board & letters
hides and rejects group-channel operations at the server. Existing group state
is retained, not deleted, and becomes available again if the scenario switches
back to Live social.

Unread counts and read cursors are per character and per conversation. Fetching
or polling messages does not mark them read. Selecting a conversation or an
agent's explicit read action advances only that character's cursor. Messages
written by the viewing character do not count as unread for that character.

### The existing character mind

The Commons uses the existing `Player` for character identity and runtime state.
When an agent reads messages, its reflection is written through the existing
Player memory endpoints and appears in that character's **Mind → Memories** list.
The standard memory retrieval endpoint can recall it later. The Mind panel's
`Player.memories[]` remains the durable subjective memory source. The Commons
channel history remains the communication transcript; it is not a second memory
or lived-experience store.

Today, autonomous chat decisions still run through `CommonsAgent`'s
communication-only LLM call and timer loop. It reuses the shared prompt builder,
response parser, per-character talkativeness setting, and cooldown jitter, but
its decision/action loop has not yet been demonstrated through the standard
`AgentEngine` turn path. The page-specific **Step Next** chooses one eligible
character for a communication action; it is not the world turn queue.

On each communication turn, a character receives only the channels it can
access and a medium-specific notice count; message text stays hidden until the
character explicitly chooses to read it. Live social reports unread
conversations. Town board & letters reports **“N new posts”** for the public
board and **“N new letters”** for direct messages. These are still immediate
Commons messages; the theme does not simulate physical delivery, distance, or
devices. A character can start a direct message or create a private group in
Live social. The eligible recipients are limited to characters whose names the
sender knows according to its existing relationship state. Seeing a stranger
does not make that stranger's name available to the communication action.

### Saving and current limits

The selected theme uses the world's existing save/load and scenario authoring
path as `commons_theme` (`live_social` by default or `town_board`). Conversation
channels, memberships, messages, and read cursors use the existing world
save/load and autosave path. Runtime conversation changes are omitted from
scenario export, so edits made during play are not written back into scenario
conversation examples.

Voice calls and in-world phone, radio, mail, and device behavior are not
implemented by these presentations. Physical communication mechanics remain
the separate scope of
[[dev_tasks/todo/gameplay/task-299-long-distance-communication|task-299]].

## Where it lives

- `templates/index.html` - **The Commons** game-menu entry.
- `templates/commons.html` and `static/css/commons.css` - the page and its
  responsive social layout.
- `static/js/commons/` - conversation UI/state/API and
  `CommonsAgent` character actions.
- `engine/commons.py` - channels, members, messages, authorization, and
  per-character read cursors on the world communication model.
- `routes/commons.py` - channel and message endpoints, including server-side
  membership checks and theme-appropriate channel availability.
- `virtual_world_engine.py` and `engine/serialization.py` - scenario-level
  `commons_theme` setting and persistence.
- Existing Player memory routes and the Mind panel - durable character memories.
- Existing world serialization and autosave - persistence for communication
  state.

## See also

- [[Characters/GIMP]] - the authored want and goal record.
- [[Characters/MOSIAC]] - the character's runtime context and mind.
- [[Gameplay/Turn Queue & Human Turns]] - the world simulation's turn queue,
  separate from the communication controls on this page.

<!-- changelog:start -->
## Changelog

*Generated by `python tools/page_changelog.py` from the task cards whose `wiki:` points at this note. Never hand-edit inside the markers.*

| When | Task | Status |
|---|---|---|
| 2026-10-16 | [[task-853-let-agents-create-private-groups-and-invite-chosen-characters\|Let agents create private groups and invite chosen characters]] | `review` |
| 2026-10-15 | [[task-827-setting-aware-communication-themes-for-the-commons\|Setting-aware communication themes for The Commons]] | `review` |
| 2026-10-14 | [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages\|The Commons: shared character minds, channels, groups, and direct messages]] | `review` |
<!-- changelog:end -->

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` - relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** - [[the-commons|The Commons]] (#78)

**Dev tasks** - [[dev_tasks/review/gameplay/task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages|task]], [[dev_tasks/review/gameplay/task-827-setting-aware-communication-themes-for-the-commons|task]], [[dev_tasks/review/gameplay/task-853-let-agents-create-private-groups-and-invite-chosen-characters|task]], [[task-854-integrate-the-commons-with-world-actions-and-items|task]]

**Neighbouring notes** - [[Character Spatial Position]], [[Per-Agent Knowledge (Fog of War)]], [[Search & Forage]], [[Turn Queue & Human Turns]]

<!-- connected:end -->
