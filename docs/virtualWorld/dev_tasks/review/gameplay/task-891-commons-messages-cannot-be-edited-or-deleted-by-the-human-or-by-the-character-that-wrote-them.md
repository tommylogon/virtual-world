---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-824, task-888, task-892]
---

# task-891: Commons messages cannot be edited or deleted, by the human or by the character that wrote them

**Filed:** 2026-10-21
**Related:** task-824 (The Commons itself), task-888 (the inner-world drawer, which reads the same message feed), task-892 (image attachments on messages - the two share the message record and the same feed renderer)

<!-- deps:start -->
**Related:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]], [[task-888-the-commons-active-character-indicator-and-character-inner-stream-sidebar]], [[task-892-commons-messages-are-text-only-no-image-attachments-and-no-multimodal-path-to-a-vision-capable-model]]
<!-- deps:end -->

## What

A message posted to The Commons is immutable. There is no way to correct a typo, retract something posted in error, or remove a message that should not be there - by the human whose perspective is active, or by the character who wrote it.

The gap is in three places at once. The engine's `Commons.post_message()` (`engine/commons.py:175`) appends a message dict and there is no `edit_message` or `delete_message` to go with it. The API exposes only `GET`/`POST` on `/api/commons/messages` (`routes/commons.py:168`) plus `/api/commons/read`; there is no `PATCH` or `DELETE` verb on a message id. And the client has `postMessage` and `readMessages` but no edit or delete (`static/js/commons/commons-api.ts`).

The user-facing consequence is that `own` in the feed (`commons-ui.ts:319`, `message.author === CommonsState.perspective`) marks a message as yours and then offers you nothing to do with it.

The right shape is one capability with two actors, not two capabilities. A character editing their own message and the human editing their own message are the same operation with a different author, and both must be enforced server-side - the client cannot be trusted to check who is asking.

## Why

Every messaging surface the user already knows has this, and its absence makes The Commons feel like a broadcast rather than a conversation. A character that misreads a situation and posts something wrong has no way to take it back; the reader believes it forever. The human has the same gap and it is worse, because the human is the one who notices the typo first.

There is a second reason that is specific to this simulation rather than to chat UIs generally: a character who can retract what they said is a character whose *record* of what they said is honest. The Commons is the only place a character's public speech is kept, and it is currently an append-only log that no one can take responsibility for. The characters' own memories (`Player.memories[]`) are separate and already reflect what was read, so an edited message and a deleted message should have defined consequences there too - the character read a thing that no longer exists, and that is exactly the kind of detail the simulation is for.

This also has to work for the *agent* side, not just the human. The Commons agents are paced characters that post on their own turn (`commons-agent.ts:228`); a character that can be scripted to post nonsense and then fix itself is a character that behaves like a person rather than a printer.

## How

1. **Engine (`engine/commons.py`).** Add `edit_message(message_id, author, text)` and `delete_message(message_id, author)` to `Commons`. Both must:
   - verify the message exists and that `message["author"] == author` - a character may only touch its own messages, and the human ('User') may only touch messages they wrote;
   - refuse to edit a message in a channel the actor cannot access (`require_access`), matching `post_message`;
   - record the edit rather than silently mutating: an `edited` flag plus `original_text` and `edited_at`, so a reader can see that a message changed. A message that was edited is not the same as a message that was always that way.
   - A delete should keep a tombstone rather than splicing the list, because `read_messages` advances a per-character read cursor by message id and a removed id would otherwise be re-delivered forever or silently skipped by characters that had already read it. The tombstone keeps the id sequence stable.
2. **API (`routes/commons.py`).** Add `PATCH /api/commons/messages/<message_id>` for an edit and `DELETE /api/commons/messages/<message_id>` for a delete. Both take the acting author and do the authorization on the server. Reuse the existing `_known_member` and `_failure` helpers so the error shape matches the rest of the route module. A delete on a message the actor did not write returns 403, not 404 - the client needs to tell 'not yours' from 'gone'.
3. **Client (`static/js/commons/commons-api.ts`).** `editMessage(id, author, text)` and `deleteMessage(id, author)`.
4. **UI (`static/js/commons/commons-ui.ts`).** In `renderMessages()`, when `message.author === CommonsState.perspective`, show an edit and a delete affordance on that message. Edit opens an inline field with the current text; delete asks for confirmation first, because a delete is not undoable in the UI. Both re-render the feed and re-sync from the server, since another character may have read the message in between.
5. **Agent side (`static/js/commons/commons-agent.ts`).** The characters' own messages need the same affordance in a way a human UI cannot provide. Two options, and the choice matters:
   - an explicit `edit_message` / `delete_message` action in the communication decision schema (`response-parser.ts` `parseCommunication` already parses a fixed `allowedActions` list - `read_chat`, `send_chat`, `start_dm`, `start_group`, `think` - so this is an extension of an existing list, not a new mechanism);
   - or an authored character trait ('a character who says something wrong and takes it back'), which reads more like a person and is harder to prompt reliably.
   The recommendation is the first, with the trait as a later refinement, because a model that has the action available will use it when the situation calls for it, and a trait needs content to be authored for it.
6. **Consequences in the character's record.** A delete and an edit should be visible to the character that read the message. The character's `Player.memories[]` entry for that conversation should reflect what actually happened, or the simulation keeps a public record that contradicts the character's own memory. This is the part that makes the feature a simulation feature rather than a chat feature.

Not in scope: editing or deleting *another* character's messages (moderation is a separate problem), and editing messages in the scenario-authored example data (`engine/serialization.py:710` deliberately drops runtime conversation state from scenario export).

## Browser UI and intended live verification

Intended UI home: /commons -> the message feed, on a message the current perspective wrote.

Current availability: Not implemented. Verified 2026-10-21: there is no edit or delete route, no engine method, no client method, and no affordance in the feed. The feed does mark the perspective's own messages with the 'own' class, so the ownership is known - only the action is missing.

Live steps when available:
1. Open /commons as the User perspective (or switch perspective to a character) and post a message.
2. expected: the posted message carries the 'own' class and shows edit and delete affordances.
3. Click edit, change the text, and save.
4. expected: the feed shows the new text with an 'edited' marker, and a reload shows the same.
5. Click delete on another message and confirm.
6. expected: the message is removed from the feed, its id is not re-delivered to a character that had already read it, and the author of that message could not have deleted it.

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

- [ ] A message the current perspective wrote shows edit and delete affordances; another character's message does not.
- [ ] The human can edit the text of a message they wrote, and the feed shows the new text with an 'edited' marker.
- [ ] The human can delete a message they wrote, after a confirmation step.
- [ ] A character can retract or correct a message it posted, through the agent path, and the change is reflected in the feed.
- [ ] The server refuses an edit or delete of a message the actor did not write, with 403 rather than 404.
- [ ] A deleted message keeps its id in the sequence, so a character's read cursor is not corrupted and the message is not re-delivered.
- [ ] An edited message records that it was edited and what it said before, so the change is visible rather than silent.
- [ ] A character that read a message that was later edited or deleted has that reflected in its own record.
- [ ] `python -m pytest tests/test_commons.py` passes, with cases for the new engine methods, the authorization refusals, and the read-cursor behaviour after a delete.

## Files

- `engine/commons.py`
- `routes/commons.py`
- `static/js/commons/commons-api.ts`
- `static/js/commons/commons-ui.ts`
- `static/js/commons/commons-agent.ts`
- `static/js/agent/response-parser.ts`
- `tests/test_commons.py`
