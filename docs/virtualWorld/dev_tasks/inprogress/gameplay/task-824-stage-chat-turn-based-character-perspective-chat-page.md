---
type: task
status: inprogress
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-714, task-727, task-820, task-825]
---

# task-824: The Commons: shared character minds, channels, groups, and direct messages

**Filed:** 2026-10-14
**Status:** in progress (scope revised 2026-10-15)
**Related:** task-825 (shared async pacing and talkativeness)

<!-- deps:start -->
**Related:** [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-727-lived-log-to-memory-bridge-phrase-lived-entries-into-first-person-memories]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]], [[task-825-simultaneous-mode-v2-async-cooldown-talkativeness]]
<!-- deps:end -->

## What

Finish Stage Chat as a social app / phone surface for the existing characters.
Characters can read and write in a public conversation, private group chats with
explicit membership, and one-to-one direct messages. The page presents those
conversations in a familiar social layout with a channel list, unread indicators,
message history, member lists, and a composer that names the destination.

Stage Chat owns communication state: conversations, memberships, messages, and
per-character read cursors. Character identity, personality, cognition, and
memories remain on the existing `Player` and standard agent path. Do not create a
second character, persona, mind, or memory store for chat.

## Why

The current public-only implementation is a useful starting point, but its
acceptance explicitly excludes private messages and groups. Its `StageChatAgent`
also builds a separate prompt and decision loop. That conflicts with the
project's existing `Player` identity and memory model and the user's requirement
that chat reuse the characters the simulation already has.

The existing Stage Chat model tracks one public log and a global read cursor.
The existing app already has character identity and memories on `Player`, a
standard `AgentEngine` / prompt-building / response-parsing path, and shared
memory retrieval and storage. The implementation must trace and reuse those
paths instead of treating an endpoint or helper's existence as proof it is
wired.

## How

- Trace the standard character turn from `Player` through prompt construction,
  memory recall, decision, response parsing, and memory storage. Integrate chat
  reading and sending at that seam; do not maintain a second chat persona or
  parallel decision loop.
- Keep conversation data in the communication layer. Before adding a new
  channel abstraction, check for an existing conversation/message model that
  can represent the behavior. If none fits, extend Stage Chat with public,
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
  Stage-Chat-specific memory, experience, or transcript store. Stage Chat's
  channel messages are the communication transcript, not a second character
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
  behavior. Do not add an independent talkativeness source for Stage Chat.
- Add targeted mechanism tests for privacy, explicit reads, shared Player
  memory, and destination routing, plus a minimal wired scenario. Verify the
  actual page and its channel flows live before moving this card to review.

## Steps to verify

1. Trace one Stage Chat character action through the normal agent and Player
   memory path.
   - expected: the existing Player identity, cognition, and memory are used;
     a read/reflection appears in that character's existing Mind → Memories
     list and is available to standard memory retrieval; there is no parallel
     chat persona or memory store. Verify against `worldState.players[name].memories`
     and the existing `/api/players/<name>/memories/retrieve` route. Keep the
     channel transcript in Stage Chat and do not mistake the Mind panel's
     transient timeline or AgentEngine display history for durable memory.
   - observed: VERIFIED 2026-10-15 in both the game and isolated `TESTING=True` app. The live Vekka Mind → Memories tab showed 8 entries and the saved test-world Lyrie Mind → Memories tab showed 13 entries, including `I read Lyrie's night-watch message and decided to check the north gate. Stage Chat memory-path verification.` The Mind renderer reads `worldState.players[name].memories`; Stage Chat recall and reflection call the existing `/api/players/<name>/memories/retrieve` and `/api/players/<name>/memories/entry` routes. `test_stage_chat_memory_uses_existing_player_memories_collection`, `stage chat: memory reflection writes to the existing Player memories endpoint`, and `stage chat: recall uses the standard Player memory retrieval endpoint` verify the same collection and routes. No Stage Chat memory field was added. The Mind panel's timeline and conversation display remain separate views, not replacement storage.
2. Open `/stage-chat`, inspect the full responsive interface, and interact with
   the public conversation, a private group, and a DM. Use the in-memory test
   world so browser writes cannot change the user's autosave:
   `python -c "from app import create_app; app=create_app({'TESTING': True}); app.run(port=4481, threaded=True)"`.
   Open `http://127.0.0.1:4481/stage-chat` at 1440×900 and 390×844. At each
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
   - observed: VERIFIED 2026-10-15 in the isolated in-memory app. At the requested 390×844 phone viewport (browser CSS viewport 487×1055 at device scale 0.8), the expanded page had 17 rendered controls; top and bottom screenshots were checked, all three character pacing sliders were visible, and document/body widths matched at 481px with no horizontal overflow. The overflow was traced to the phone-owner row sharing the first flex line; the mobile topbar now gives that row a full line. At 1440×900 desktop viewport (CSS viewport 1800×1125), the three-column layout measured 285/1260/255px with no horizontal overflow and 17 rendered controls when pacing was expanded. Both dialogs were opened and cancelled. Public post, `Ravine Watch` group, and Kaelen–Lyrie DM flows were exercised while paused; rat could not see either private conversation, Lyrie could, and the channels/messages remained after reload in the same test process.
3. Read a private group and a DM as an authorized character, then request each
   as a non-member / non-participant through the API.
   - expected: authorized readers receive only their channel's messages;
     unauthorized reads and sends are rejected without leaking message text.
     In the browser, use the Network panel or `fetch()` against the exact
     `/api/stage-chat/messages?as=<non-member>&channel_id=<private-id>` URL and
     `/api/stage-chat/read` POST body; record each status and response body.
   - observed: VERIFIED 2026-10-15. `test_routes_filter_channels_by_perspective_and_reject_private_reads_and_sends` asserts the authorized read returns the message, non-member read and send return 403, and the denied response contains no private message text. In the browser, the member and non-member phone perspectives showed the group/DM only to Kaelen and Lyrie.
4. Let a character choose whether to read and whether to send a message.
   - expected: rendering and unread polling do not reveal or mark messages read;
     an explicit read updates only that character's cursor and feeds the normal
     Player memory path.
   - observed: VERIFIED 2026-10-15. `test_public_chat_read_cursor_advances_only_on_explicit_read` asserts the cursor is unchanged by posting, advances to the explicitly read message id, and leaves unread messages for the next read. `stage chat: explicit group read uses the shared Player memory endpoint and never prompts with unread text` proves unread bodies are absent from the decision prompt and only appear in the memory write after the explicit read; `stage chat: think action does not read, send, or create a conversation` covers choosing to wait. The browser test opened the group/DM as Lyrie and marked those reads only for Lyrie.
5. Save and reload the world after creating a group, DM, messages, and read
   state.
   - expected: the existing save/load path restores those communication records
     without creating chat-specific character identity or memory data. A
     successful Stage Chat write also reaches the existing autosave hook.
   - observed: VERIFIED 2026-10-15. `test_saved_world_round_trips_chat_communication_but_scenario_export_drops_runtime_chat` checks channels, memberships, messages, and per-character cursors round-trip through `VirtualWorld.to_dict()` / `load_from_dict()`, while scenario export omits runtime chat. `test_stage_chat_messages_and_read_cursors_use_standard_autosave` asserts both a post and explicit read call the existing `save_autosave` hook and persist cursor id 1. `test_kraktooth_scenario_authors_public_group_and_dm_conversations` loads the authored Kraktooth scenario and verifies its public post, `Camp Watch` group, Vekka–Zikka DM, and existing character membership. Live on `/stage-chat`, Vekka saw all three channels and the seeded group/DM text; Rag-Tail saw only Public. Scenario source can seed initial Stage Chat data, but runtime changes are not exported back into scenarios.

## Remaining before review

- **Blocker: standard agent decision/action seam is not integrated.** `templates/stage_chat.html` loads the shared `config`, `llm-client`, PromptBuilder, and ResponseParser modules, then `StageChatAgent`; it does not bootstrap `AgentEngine`, `WorldState`, or the standard event-stream/context-window dependencies. `StageChatAgent.actCharacter()` therefore calls `llmClient.chat()` directly with a communication-only prompt/parser and applies the channel action itself. The normal `AgentEngine.step()` expects a world-action turn and its `_callLLMMessages()` uses shared mutable context/abort state, while The Commons can have multiple per-character timers in flight. Simply loading or calling the engine singleton would bypass required initialization and make overlapping calls unsafe. Keep the existing Player/memory behavior; integrate through a shared, concurrency-safe decision/action seam and prove the selected communication branch before moving this card to review.
- Related task-825 is still `todo`; Stage Chat reads its shared per-character talkativeness config and cooldown jitter helper, but the parent async-turn task itself has not been verified or moved to review.

## Acceptance

- [ ] Stage Chat uses existing `Player` identity, personality, and standard
  agent decision / response path; no parallel chat mind or persona exists.
- [x] Chat recall and reflection use the existing Player memory system; no
  separate Stage Chat memory store exists.
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
- [x] Successful Stage Chat writes use the existing autosave hook.
- [x] Stage Chat reuses task-825's talkativeness settings and pacing mechanism.
- [x] Targeted tests assert the authorization branch, cursor value, Player
  memory path, and selected destination; live UI checks cover all three channel
  types.
- [x] Authored scenario content demonstrates a public post, a private group,
  and a DM without inventing a separate character or mind model.

## Files

- `engine/stage_chat.py` (communication model)
- `routes/stage_chat.py` (channel APIs and server-side authorization)
- `app.py` (route Stage Chat mutations through the existing autosave hook)
- Existing world serialization/save-load path, only where required for
  communication state
- `static/js/stage-chat/**` (shared agent integration and social UI)
- `templates/stage_chat.html` and `static/css/stage-chat.css`
- `tests/test_stage_chat.py` and targeted frontend tests
- An existing scenario with real characters and authored channel examples
