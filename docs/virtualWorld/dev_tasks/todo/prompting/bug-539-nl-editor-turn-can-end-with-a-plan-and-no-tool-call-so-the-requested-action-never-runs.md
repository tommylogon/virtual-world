---
type: bug
status: todo
area: prompting
priority: medium
wiki: "[[Feature Map]]"
---

# bug-539: NL editor turn can end with a plan and no tool call, so the requested action never runs

**Filed:** 2026-10-10
**Related:** 

## What

Driving the NL editor live 2026-10-10 in scenario 'labs': 'add zoe to area 18' -> clarify -> 'your choice' -> 'create a new please' -> create_node made player_Zoe -> 'next lets add 50 memories to zoe' -> 'do that' -> the assistant replied 'I'll add Zoe to Task 18 - Room 1 first, then add 50 memories to her. Let me start with placing her in the area:' with NO tool call and the turn ended. The attach and the memories never ran; Zoe was left in no area. This violates the NL system prompt's rule 16 (ACT, DON'T NARRATE): a turn that needs a tool must call it in the same response. Investigate why the agent loop accepted a prose-only assistant message as terminal (no tool_calls) and whether the loop should re-prompt or fail loudly when the user's request is clearly unfulfilled, rather than presenting a plan as the answer.

**Second reproduction, 2026-10-10 (multi-call).** Prompt: `add a distinct new item to each of Task 1 through Task 10`. After one real `list_nodes` call, the model emitted **six** `search_library_items` calls **as text** (`<|tool_calls|>…`), `output.tool_calls` empty, and the turn ended with nothing staged. So this is **not rare** — it reproduces readily on turns that want several parallel tool calls, which is exactly when the work matters. It also blocked the task-422 budget test: the round-cap notice can never be reached if the turn dies on the first multi-call step.

**Third run, 2026-10-10 — it is the MODEL, not the loop.** The same prompt re-run on **deepseek v4.1** succeeded end-to-end: real tool calls throughout (list_nodes, list_library_summary, search_library_items, request_clarification, 16 spawn_library_item), and the round cap fired visibly ("Stopped at the 5-round limit; the edit may be incomplete."). So the malformed-tool-call behaviour is specific to the **free preview model** (`dots-studio/dots-3-note-preview:free`), whose parallel function-calling is broken. Two remedies: (a) pin the NL agent loop to a model that is reliable at multi-call turns (the deepseek run is the evidence); (b) keep a loop-side guard anyway — a no-`tool_calls` response carrying tool-call markup should re-prompt or fail loudly rather than ending silently, so a bad model degrades loudly instead of doing nothing.

## Why

**Mechanism observed 2026-10-10 (raw provider response).** The turn did not merely narrate — the model returned its tool calls **as text** in the assistant message body:

> `<|tool_calls|><|invoke|>search_library_items<|parameter|>query||<|parameter|>tags[]string<|parameter|>[]<|/invoke|>…<|/tool_calls|>`

with `output.tool_calls` empty. So there were no calls to run, and the loop took the message as a terminal answer. Model in play: `dots-studio/dots-3-note-preview:free` (via OpenRouter). It is **intermittent** — an earlier turn in the same session emitted real `🔧 create_node` calls that ran. The recovery belongs in the loop, not the prompt: (a) a response with no `tool_calls` whose text carries tool-call markup should be re-prompted or failed loudly, not ended; (b) rule 16 (ACT, DON'T NARRATE) cannot help when the model *believes* it already called the tool.

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Natural Language editor → submit the multi-step request → review the assistant's proposed operation and tool-call/activity trace before the turn ends.

Current availability: the card records a live `labs` turn where the assistant narrated that it would place Zoe and add memories but emitted no tool call; Zoe remained unattached. This reproduction is recorded in the card, not re-run in this update.

Live steps when available:
1. In `labs`, submit `add zoe to area 18`, answer the clarification with `your choice`, then request creation and attachment as the card describes. Inspect the NL transcript and tool-call trace after each turn.
   - expected: if a turn says it will perform an operation, the corresponding tool call appears in that same assistant response; the created Zoe is attached to the selected area.
2. Continue with `add 50 memories to zoe` and confirm the action.
   - expected: the memory operation is called and the resulting record count changes by the requested amount; narration alone cannot close the turn successfully.
3. Cause one tool-call failure in a scratch scenario.
   - expected: the UI reports the failed operation and leaves the request visibly incomplete/retryable; it does not present the narrated plan as executed.
4. Compare the transcript, tool trace, graph attachment, and `/api/state` memories.
   - expected: each visible claim corresponds to an operation and resulting world state.

This section is not a claim that planned UI exists or works today.
