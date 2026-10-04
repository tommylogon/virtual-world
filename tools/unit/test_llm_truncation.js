// Truncation must never reach a caller as if it were a complete answer.
//
// The root cause was that `finish_reason` was discarded: chat() returned a
// bare string, so a half-written JSON plan was indistinguishable from a
// complete one and every parser downstream had to guess. These tests pin the
// detection, the budget escalation, and the chat() retry that together make
// "LLM output is never truncated" true at the transport layer.

test('chat-completions: finish_reason length is detected as truncation', () => {
    const c = llmClient;
    const cut = { choices: [{ message: { content: '{"steps":[{"act":"go"' }, finish_reason: 'length' }] };
    assertEq(c._truncationReason(cut, false), 'length', 'length stop is truncation');
});

test('a normal stop is NOT truncation', () => {
    const c = llmClient;
    const done = { choices: [{ message: { content: '{"steps":[]}' }, finish_reason: 'stop' }] };
    assertEq(c._truncationReason(done, false), null, 'stop is complete');
    const tool = { choices: [{ message: { content: '' }, finish_reason: 'tool_calls' }] };
    assertEq(c._truncationReason(tool, false), null, 'tool_calls is complete');
});

test('a provider that omits the stop reason does not trigger a retry', () => {
    const c = llmClient;
    // Older/local providers leave finish_reason undefined. Treating that as
    // truncation would double every request forever.
    assertEq(c._truncationReason({ choices: [{ message: { content: 'hi' } }] }, false), null,
        'missing finish_reason is not truncation');
    assertEq(c._truncationReason({}, false), null, 'empty envelope is not truncation');
    assertEq(c._truncationReason(null, false), null, 'null envelope is not truncation');
});

test('responses API: incomplete_details and status:incomplete are detected', () => {
    const c = llmClient;
    assertEq(c._truncationReason({ incomplete_details: { reason: 'max_output_tokens' } }, true),
        'max_output_tokens', 'incomplete_details reports the cap');
    assertEq(c._truncationReason({ status: 'incomplete' }, true), 'incomplete', 'bare incomplete status');
    assertEq(c._truncationReason({ status: 'completed', output_text: 'done' }, true), null,
        'a completed response is not truncation');
});

test('budget escalation doubles and then stops at the ceiling', () => {
    const c = llmClient;
    assertEq(c._nextTokenBudget(560, 1), 1120, 'first retry doubles the caller cap');
    assertEq(c._nextTokenBudget(560, 2), 2240, 'second retry doubles again');
    assertEq(c._nextTokenBudget(undefined, 1), 1024, 'no caller cap falls back to the default');
    assertEq(c._nextTokenBudget(30000, 3), 32768, 'escalation is clamped, never unbounded');
});

// The guarantee itself: chat() must re-request rather than return a fragment.
function stubFetch(responses) {
    const calls = [];
    window.fetch = async (url, init) => {
        const body = JSON.parse(init.body);
        calls.push(body);
        const next = responses.shift();
        if (next === undefined) throw new Error('stubFetch exhausted');
        return {
            ok: true,
            status: 200,
            json: async () => next,
            text: async () => JSON.stringify(next),
        };
    };
    return calls;
}

test('chat() retries a truncated answer with a bigger budget instead of returning it', async () => {
    const c = llmClient;
    const truncated = { choices: [{ message: { content: '{"steps":[{"act":"go","target":"we' }, finish_reason: 'length' }] };
    const complete = { choices: [{ message: { content: '{"steps":[{"act":"go","target":"west passage"}]}' }, finish_reason: 'stop' }] };
    const realFetch = window.fetch;
    const calls = stubFetch([truncated, complete]);
    let out, err = null;
    try {
        out = await c.chat([{ role: 'user', content: 'plan something' }], { max_tokens: 300, streaming: false, label: 'plan' });
    } catch (e) { err = String(e); }
    window.fetch = realFetch;
    assertEq(err, null, 'no error');
    assertEq(calls.length, 2, 'the truncated response was re-requested');
    assertEq(calls[0].max_tokens, 300, 'first attempt honours the caller cap');
    assertEq(calls[1].max_tokens, 600, 'retry raises the cap');
    assertEq(out, '{"steps":[{"act":"go","target":"west passage"}]}', 'the COMPLETE answer is what the caller gets');
});

test('an answer that never fits is reported, not silently returned', async () => {
    const c = llmClient;
    const truncated = { choices: [{ message: { content: 'still going' }, finish_reason: 'length' }] };
    const realFetch = window.fetch;
    const logged = [];
    // The warning goes to VW.events (the in-app event stream), not the bare
    // `events` global the sandbox stubs for the module bus.
    const realVWEvents = window.VW.events;
    window.VW.events = { log: (text) => { logged.push(text); } };
    const calls = stubFetch([truncated, truncated, truncated, truncated]);
    let out = null, err = null;
    try {
        out = await c.chat([{ role: 'user', content: 'x' }], { max_tokens: 300, streaming: false, label: 'plan' });
    } catch (e) { err = String(e); }
    window.fetch = realFetch;
    window.VW.events = realVWEvents;
    assertEq(err, null, 'still returns rather than throwing');
    assertEq(calls.length, 4, 'gives up after the truncation budget, not forever');
    assertTrue(logged.some(l => /STILL truncated/.test(l)), 'the caller is told the answer is incomplete');
});

test('the escalation doubles from the caller cap, it does not compound', async () => {
    const c = llmClient;
    const truncated = { choices: [{ message: { content: 'cut' }, finish_reason: 'length' }] };
    const realFetch = window.fetch;
    const realVWEvents = window.VW.events;
    window.VW.events = { log: () => {} };
    const calls = stubFetch([truncated, truncated, truncated, truncated]);
    await c.chat([{ role: 'user', content: 'x' }], { max_tokens: 300, streaming: false, label: 'plan' });
    window.fetch = realFetch;
    window.VW.events = realVWEvents;
    // Compounding (300*2, *4-of-600, *8-of-2400) gave 300/600/2400/19200 and a
    // local model would burn a very long doomed generation. Doubling from the
    // caller's cap is the intended shape.
    assertEq(calls.map(c2 => c2.max_tokens).join(','), '300,600,1200,2400',
        'each retry doubles the ORIGINAL cap');
});

test('a complete first response is returned on the first call, budget untouched', async () => {
    const c = llmClient;
    const complete = { choices: [{ message: { content: 'all done' }, finish_reason: 'stop' }] };
    const realFetch = window.fetch;
    const calls = stubFetch([complete]);
    const out = await c.chat([{ role: 'user', content: 'x' }], { max_tokens: 300, streaming: false, label: 'plan' });
    window.fetch = realFetch;
    assertEq(calls.length, 1, 'no retry on a complete answer');
    assertEq(calls[0].max_tokens, 300, 'budget untouched');
    assertEq(out, 'all done', 'content returned verbatim');
});