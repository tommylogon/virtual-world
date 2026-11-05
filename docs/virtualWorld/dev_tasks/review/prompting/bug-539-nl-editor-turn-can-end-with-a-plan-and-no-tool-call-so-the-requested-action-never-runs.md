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

**Second reproduction, 2026-10-10 (multi-call).** Prompt: `add a distinct new item to each of Task 1 through Task 10`. After one real `list_nodes` call, the model emitted **six** `search_library_items` calls **as text** (`<|tool_calls|>…`), `output.tool_calls` empty, and the turn ended with nothing staged. So this is **not rare** - it reproduces readily on turns that want several parallel tool calls, which is exactly when the work matters. It also blocked the task-422 budget test: the round-cap notice can never be reached if the turn dies on the first multi-call step.

**Third run, 2026-10-10 - it is the MODEL, not the loop.** The same prompt re-run on **deepseek v4.1** succeeded end-to-end: real tool calls throughout (list_nodes, list_library_summary, search_library_items, request_clarification, 16 spawn_library_item), and the round cap fired visibly ("Stopped at the 5-round limit; the edit may be incomplete."). So the malformed-tool-call behaviour is specific to the **free preview model** (`dots-studio/dots-3-note-preview:free`), whose parallel function-calling is broken. Two remedies: (a) pin the NL agent loop to a model that is reliable at multi-call turns (the deepseek run is the evidence); (b) keep a loop-side guard anyway - a no-`tool_calls` response carrying tool-call markup should re-prompt or fail loudly rather than ending silently, so a bad model degrades loudly instead of doing nothing.

## Why

**Mechanism observed 2026-10-10 (raw provider response).** The turn did not merely narrate - the model returned its tool calls **as text** in the assistant message body:

> `<|tool_calls|><|invoke|>search_library_items<|parameter|>query||<|parameter|>tags[]string<|parameter|>[]<|/invoke|>…<|/tool_calls|>`

with `output.tool_calls` empty. So there were no calls to run, and the loop took the message as a terminal answer. Model in play: `dots-studio/dots-3-note-preview:free` (via OpenRouter). It is **intermittent** - an earlier turn in the same session emitted real `🔧 create_node` calls that ran. The recovery belongs in the loop, not the prompt: (a) a response with no `tool_calls` whose text carries tool-call markup should be re-prompted or failed loudly, not ended; (b) rule 16 (ACT, DON'T NARRATE) cannot help when the model *believes* it already called the tool.

## How

**The gap is in the prose-tool-call fallback, not in the prompt.** The NL editor
does have a fallback for models that write tool calls as text
(`static/js/nl-editor/agent-loop.ts:441-446`): when the provider returns no
native `tool_calls`, `_extractXmlToolCalls()` parses the assistant prose and the
loop continues with the parsed calls. The parser supports five shapes:

| Shape | Markup | Regex |
|---|---|---|
| A | `<tool_name><k>v</k></tool_name>` | `agent-loop.ts:183` |
| B | `<tool_call>tool_name<parameter name="k">v</parameter></tool_call>` | `agent-loop.ts:191` |
| C | `<invoke name="tool_name">...</invoke>` | `agent-loop.ts:198` |
| D | `<function=tool_name>...</function>` | `agent-loop.ts:204` |
| E | a JSON tool-call object anywhere in the prose | `agent-loop.ts:213-249` |

**The card's recorded markup matches none of them.** The reproduction recorded
`<|tool_calls|><|invoke|>search_library_items<|parameter|>query||<|parameter|>tags[]string<|parameter|>[]<|/invoke|>...<|/tool_calls|>`. That markup uses the pipe-delimited `<|...|>` form with a *positional* `<|parameter|>value<|/parameter|>` body, and it carries no `name=` attribute, so:

- Shape A does not match: the tag names are `tool_calls`, `invoke`, `parameter`, all of which contain a `|` and so are not `[a-zA-Z_][a-zA-Z0-9_]*`.
- Shape B does not match: the tag is `<|tool_calls|>`, not `<tool_call>`.
- Shape C does not match: it requires `\bname="..."` and the markup has no `name=` attribute.
- Shape D does not match: it requires `<function=...>`.

Measured: each of the four regexes returns 0 matches against the recorded
markup string. The fallback therefore returns an empty array, `effectiveToolCalls`
stays `null`, and `agent-loop.ts:460-463` breaks out of the loop and treats the
prose as the final answer. The turn ends silently with the request unfulfilled.

**Neither remedy in the card has been applied.** (a) The model is not pinned: the
loop takes whatever `_activeModel()` returns (`agent-loop.ts:48`, `:590-591`) and
there is no reliability check on it. (b) There is no loop-side guard: a response
with no `tool_calls` is unconditionally a terminal answer, with no check for
tool-call markup in the text and no re-prompt or loud failure. The round cap
(`budget.maxIterations`, `agent-loop.ts:36`, `:45-57`) cannot help, because the
turn dies on the first multi-call step and never reaches the cap.

## Steps to verify

1. Feed the recorded markup to the prose fallback.
   - expected: the tool call is parsed and the loop continues with a real call.
   - observed: FAILS. `_extractXmlToolCalls()` returns 0 calls for the recorded
     `<|tool_calls|><|invoke|>...` markup; Shapes A-D each match 0 times
     (Shape E expects JSON, and the markup is XML-ish). The loop then breaks at
     `agent-loop.ts:460-463` with the request unfulfilled.
2. Confirm the loop has no guard for a tool-call-shaped prose terminal message.
   - expected: a response whose text carries tool-call markup but whose
     `tool_calls` is empty is re-prompted or fails loudly.
   - observed: FAILS. `agent-loop.ts:460-463` breaks on any empty
     `effectiveToolCalls`, with no markup check and no re-prompt.
3. Confirm the model is not pinned to a reliable one.
   - expected: the NL agent loop uses a model known to emit native `tool_calls`.
   - observed: FAILS. `_activeModel()` (`agent-loop.ts:590-591`) supplies whatever
     the session has selected, with no reliability constraint.
4. Re-run the live `labs` reproduction in the browser.
   - expected: the attach and the memory operations run; narration alone cannot
     close the turn.
   - observed: not re-run in this turn. The static findings above are what the
     code path shows, not a fresh live reproduction.

## Acceptance

- [ ] The prose-tool-call fallback parses the pipe-delimited `<|tool_calls|>` /
      `<|invoke|>` / positional `<|parameter|>` shape, so a model that emits it
      produces real tool calls instead of a silent terminal turn.
- [ ] A response with no native `tool_calls` whose text carries tool-call markup
      is re-prompted or fails loudly, rather than ending the turn silently.
- [ ] The NL agent loop is pinned to a model that emits native `tool_calls` for
      multi-call turns, with the model choice visible in the UI.
- [ ] A live `labs` run of `add a distinct new item to each of Task 1 through
      Task 10` completes the operations, and the round cap is reachable rather
      than being pre-empted by a dead first step.

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

## Files

- `static/js/nl-editor/agent-loop.ts` - `_extractXmlToolCalls()` (the five prose
  shapes, lines 137-251), the fallback call site (lines 441-446), the terminal
  break (lines 460-463), and `_activeModel()` (lines 590-591)

## Reconnaissance (2026-10-20) - still valid

Re-checked the cited code on 2026-10-20 against the newer NL editor work
(task-422 budget, task-461 validation gate, task-422/425 round caps). The card's
premise still holds and its two proposed remedies still have not been applied.

- The prose fallback exists and runs (`agent-loop.ts:441-446`), but it does not
  cover the recorded markup. Measured against the card's own reproduction
  string, Shapes A, B, C and D each return 0 matches; only Shape E (JSON) is
  even applicable in principle and the recorded markup is XML-ish.
- There is no loop-side guard: `agent-loop.ts:460-463` treats any response with
  no effective tool calls as the final answer, with no check for tool-call
  markup in the prose and no re-prompt.
- The model is not pinned: `_activeModel()` returns the session's selection with
  no reliability constraint.

Verdict: STILL_VALID. The card stays in todo.
