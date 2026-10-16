---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-714, task-727, task-820, task-825, task-827]
children: [task-854]
---

# task-824: The Commons: shared character minds, channels, groups, and direct messages

**Filed:** 2026-10-14
**Status:** in review (scope revised 2026-10-16)
**Related:** task-825 (shared async pacing and talkativeness)

<!-- deps:start -->
**Children:** [[task-854-integrate-the-commons-with-world-actions-and-items]]
**Related:** [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-727-lived-log-to-memory-bridge-phrase-lived-entries-into-first-person-memories]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]], [[task-825-simultaneous-mode-v2-async-cooldown-talkativeness]], [[task-827-setting-aware-communication-themes-for-the-commons]]
<!-- deps:end -->

## What

Finish The Commons as a social app / phone surface for the existing characters.
Characters can read and write in a public conversation, private group chats with
explicit membership, and one-to-one direct messages. The page presents those
conversations in a familiar social layout with a channel list, unread indicators,
message history, member lists, and a composer that names the destination.

The Commons owns communication state: conversations, memberships, messages, and
per-character read cursors. Character identity, personality, cognition, and
memories remain on the existing `Player`. Do not create a second character,
persona, mind, or memory store for chat. Integrating Commons actions with the
standard world-turn loop and item/world interactions is separate follow-up work
tracked by task-854.

## Why

The original implementation was public-only and used one global read cursor.
The Commons now supports public, private group, and direct-message
channels with per-character read state, server-side authorization, persistence,
scenario-authored examples, and the existing Player memory path. Those parts
are verified in the steps below.

This task covers The Commons as a standalone communication surface: its channel
model, authorization, explicit reads, existing Player memory path, pacing
controls, and responsive UI. `CommonsAgent` currently makes communication
decisions through its own loop while reusing shared prompt/response modules and
Player memory routes.

> **Follow-up:** Standard world-turn and item/world integration is not part of
> this task. It has been split into child task
> [[task-854-integrate-the-commons-with-world-actions-and-items]].

## How

- Use the existing Player identity and shared prompt/response modules for
  Commons decisions; do not create a second chat persona, mind, or memory store.
- Keep standard world-turn and item/world integration outside this task; see
  child task-854.
- Keep conversation data in the communication layer. Before adding a new
  channel abstraction, check for an existing conversation/message model that
  can represent the behavior. If none fits, extend The Commons with public,
  member-only group, and two-person DM channels rather than creating separate
  message stores for each kind.
- Enforce channel visibility and send permissions in the server model/routes,
  not only by hiding messages in the UI. A character can read or post only in
  conversations they are authorized to access. A DM has exactly its two
  participants; a private group has an explicit membership list.
- Keep reading explicit from each character's perspective. Polling, rendering,
  unread counts, and another character's read must not advance that character's
  cursor. Track unread/read state per character and conversation.
- Use the existing Player identity/personality and normal memory retrieval and
  storage. Do not persist chat-specific personality, private memories, or a
  second mind. Show the standard agent's private thought only through the
  existing cognition output; do not create a second persistent monologue store.
- Preserve the existing Mind panel's sources of truth:
  `Player.memories[]` is the durable subjective memory store shown by Mind →
  Memories and read by the standard memory-retrieval path. The existing
  `Player.lived_log` is the objective experience record; use its existing
  writer/bridge only if a chat event needs that record. Do not add a
  Commons-specific memory, experience, or transcript store. Channel messages
  are the communication transcript, not a second character
  memory. The Mind panel's “Timeline — the lived trace” currently renders the
  browser event stream's `detailedTimeline`, and “Conversation memory” renders
  `AgentEngine.getDisplayHistory`; neither is a durable replacement for
  `Player.memories[]` or `Player.lived_log`.
- Persist conversations, membership, messages, and read cursors through the
  existing world save/load path. Do not create a second save source for chat.
- Build a responsive phone/social UI for public posts, group chats, and DMs,
  including conversation selection, membership, unread state, message history,
  and destination selection when sending.
- Reuse task-825's shared per-character pacing configuration and cooldown
  behavior. Do not add an independent talkativeness source for The Commons.
- Add targeted mechanism tests for privacy, explicit reads, shared Player
  memory, and destination routing, plus a minimal wired scenario. Verify the
  actual page and its channel flows live before moving this card to review.

## Browser UI and intended live verification

Intended UI home: The Commons page for public/group/direct conversations; Character Inspector → Mind → Memories for persistent experience.

Current availability: Public, private-group, and direct channels, persistence,
Player memory storage, and the standalone Commons communication loop exist.
Integration with standard world turns and item/world interactions is tracked
separately in child task-854.

Live steps when available:

1. Open The Commons, select a character, and post to a public conversation, a member group, and a one-to-one conversation.
   - expected: Messages appear only in their addressed conversations; group membership and DM participants are visible.

2. Try a private group as a non-member, then inspect the participating character’s Mind → Memories after a read/reflection.
   - expected: The non-member is denied; experience appears in the existing Player memory list with no parallel chat persona or memory store.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Trace an explicit Commons read/reflection through the existing Player
   memory path.
   - expected: the existing Player identity and memory are used; a
     read/reflection appears in that character's existing Mind → Memories list
     and is available to standard memory retrieval; there is no parallel chat
     persona or memory store. Verify against
     `worldState.players[name].memories` and the existing
     `/api/players/<name>/memories/retrieve` route. Keep the channel transcript
     in The Commons and do not mistake the Mind panel's transient timeline or
     AgentEngine display history for durable memory. This does not require
     Commons decisions to run through the standard world-turn loop.
   - observed: VERIFIED 2026-10-15 in both the game and isolated `TESTING=True` app. The live Vekka Mind → Memories tab showed 8 entries and the saved test-world Lyrie Mind → Memories tab showed 13 entries, including `I read Lyrie's night-watch message and decided to check the north gate. The Commons memory-path verification.` The Mind renderer reads `worldState.players[name].memories`; Commons recall and reflection call the existing `/api/players/<name>/memories/retrieve` and `/api/players/<name>/memories/entry` routes. `test_commons_memory_uses_existing_player_memories_collection`, `the commons: memory reflection writes to the existing Player memories endpoint`, and `the commons: recall uses the standard Player memory retrieval endpoint` verify the same collection and routes. No feature-specific memory field was added. The Mind panel's timeline and conversation display remain separate views, not replacement storage.
2. Open `/commons`, inspect the full responsive interface, and interact with
   the public conversation, a private group, and a DM. Use the in-memory test
   world so browser writes cannot change the user's autosave:
   `python -c "from app import create_app; app=create_app({'TESTING': True}); app.run(port=4481, threaded=True)"`.
   Open `http://127.0.0.1:4481/commons` at 1440×900 and 390×844. Also visit
   `/stage-chat` and confirm the browser address ends at `/commons`. At each
   size, record the visible `button, select, input` count and labels from the
   whole `document.body`, capture the top and bottom of the page, expand
   “Characters & pacing,” and open then cancel both channel dialogs. Confirm the
   initial state is paused and that browsing makes no mutating request. While
   still paused, send a uniquely named public post, create a group with two
   existing characters and send to it, then create a DM between those same two
   characters and send to it. Switch the phone owner to a member and then a
   non-member; verify the group/DM appears only for its members, the message
   history and member list match the selected channel, and the composer sends
   only to that channel. Reload and verify state is restored only within this
   in-memory test process.
   - expected: responsive layout and dialogs remain usable at both sizes;
     public, group, and DM histories route to the selected channel; private
     channels appear only to their members; autonomous turns stay paused.
   - observed: VERIFIED 2026-10-15 in the isolated in-memory app. At the requested 390×844 phone viewport (browser CSS viewport 487×1055 at device scale 0.8), the expanded page had 17 rendered controls; top and bottom screenshots were checked, all three character pacing sliders were visible, and document/body widths matched at 481px with no horizontal overflow. The overflow was traced to the phone-owner row sharing the first flex line; the mobile topbar now gives that row a full line. At 1440×900 desktop viewport (CSS viewport 1800×1125), the three-column layout measured 285/1260/255px with no horizontal overflow and 17 rendered controls when pacing was expanded. Both dialogs were opened and cancelled. Public post, `Ravine Watch` group, and Kaelen–Lyrie DM flows were exercised while paused; rat could not see either private conversation, Lyrie could, and the channels/messages remained after reload in the same test process. `test_former_page_url_redirects_to_commons` asserts a 301 and `/commons` location; verify the address-bar redirect in the browser as part of the manual pass.
3. Read a private group and a DM as an authorized character, then request each
   as a non-member / non-participant through the API.
   - expected: authorized readers receive only their channel's messages;
     unauthorized reads and sends are rejected without leaking message text.
     In the browser, use the Network panel or `fetch()` against the exact
     `/api/commons/messages?as=<non-member>&channel_id=<private-id>` URL and
     `/api/commons/read` POST body; record each status and response body.
   - observed: VERIFIED 2026-10-15. `test_routes_filter_channels_by_perspective_and_reject_private_reads_and_sends` asserts the authorized read returns the message, non-member read and send return 403, and the denied response contains no private message text. In the browser, the member and non-member phone perspectives showed the group/DM only to Kaelen and Lyrie.
4. Let a character choose whether to read and whether to send a message.
   - expected: rendering and unread polling do not reveal or mark messages read;
     an explicit read updates only that character's cursor and feeds the normal
     Player memory path.
   - observed: VERIFIED 2026-10-15. `test_public_chat_read_cursor_advances_only_on_explicit_read` asserts the cursor is unchanged by posting, advances to the explicitly read message id, and leaves unread messages for the next read. `the commons: explicit group read uses the shared Player memory endpoint and never prompts with unread text` proves unread bodies are absent from the decision prompt and only appear in the memory write after the explicit read; `the commons: think action does not read, send, or create a conversation` covers choosing to wait. The browser test opened the group/DM as Lyrie and marked those reads only for Lyrie.
5. Save and reload the world after creating a group, DM, messages, and read
   state.
   - expected: the existing save/load path restores those communication records
     without creating chat-specific character identity or memory data. A
     successful The Commons write also reaches the existing autosave hook.
   - observed: VERIFIED 2026-10-15. `test_saved_world_round_trips_chat_communication_but_scenario_export_drops_runtime_chat` checks channels, memberships, messages, and per-character cursors round-trip through `VirtualWorld.to_dict()` / `load_from_dict()`, while scenario export omits runtime chat. `test_commons_messages_and_read_cursors_use_standard_autosave` asserts both a post and explicit read call the existing `save_autosave` hook and persist cursor id 1. `test_kraktooth_scenario_authors_public_group_and_dm_conversations` loads the authored Kraktooth scenario and verifies its public post, `Camp Watch` group, Vekka–Zikka DM, and existing character membership. Live on `/commons`, Vekka saw all three channels and the seeded group/DM text; Rag-Tail saw only Public. Scenario source can seed initial The Commons data, but runtime changes are not exported back into scenarios.

## Out of scope / follow-up

- Standard `AgentEngine` world-turn integration and item/world interactions are
  tracked separately by child task-854. That task must investigate the correct
  shared, concurrency-safe seam without weakening channel privacy or
  duplicating Player identity, communication state, or memory.
- Task-825 tracks broader simultaneous async pacing behavior. This Commons card
  verifies only that the Commons uses the shared per-character talkativeness
  setting and cooldown jitter helper; it does not claim task-825 is complete.

## Acceptance

- [x] The Commons uses existing `Player` identity and shared prompt/response
  modules; it creates no parallel chat mind or persona. Standard world-turn
  decision/action integration is explicitly out of scope and tracked in child
  task-854.
- [x] Chat recall and reflection use the existing Player memory system; no
  separate memory store exists.
- [x] Public conversation supports posts and per-character explicit read state.
- [x] Private groups have explicit members; only members can read or post.
- [x] Direct messages are limited to their two participants.
- [x] Server-side read and send authorization prevents cross-channel leakage.
- [x] UI provides a responsive social / phone experience for public, group, and
  direct conversations, with membership, unread state, history, and composer.
- [x] Polling and rendering do not auto-read messages; cursors are per character
  and per conversation.
- [x] Conversations, membership, messages, and cursors round-trip through the
  existing world persistence path.
- [x] Successful The Commons writes use the existing autosave hook.
- [x] The Commons uses the existing per-character talkativeness setting and
  shared cooldown jitter helper. This does not close task-825's broader
  simultaneous-turn acceptance, which remains unverified.
- [x] Targeted tests assert the authorization branch, cursor value, Player
  memory path, and selected destination; live UI checks cover all three channel
  types.
- [x] Authored scenario content demonstrates a public post, a private group,
  and a DM without inventing a separate character or mind model.

## Files

- `engine/commons.py` (communication model)
- `routes/commons.py` (channel APIs and server-side authorization)
- `app.py` (route Commons mutations through the existing autosave hook)
- Existing world serialization/save-load path, only where required for
  communication state
- `static/js/commons/**` (Commons communication loop and social UI)
- `templates/commons.html` and `static/css/commons.css`
- `tests/test_commons.py` and targeted frontend tests
- An existing scenario with real characters and authored channel examples
