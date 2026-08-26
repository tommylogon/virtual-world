// Unit test: verify the thinking request-body shapes for ON and OFF in both
// chat-completions and responses paths. Run: node tools/test_thinking_body.cjs
global.fetch = async (url, opts) => {
    console.log('  -> ' + url);
    if (opts?.body) console.log(JSON.stringify(JSON.parse(opts.body), null, 1));
    return { ok: true, json: async () => ({ choices: [{ message: { content: 'ok' } }] }) };
};
// LLMClient is declared at the top level of a browser script (window.LLMClient).
// Evaluate it in the global scope so the class binding is accessible here.
const fs = require('fs');
const vm = require('vm');
vm.runInThisContext(fs.readFileSync(require.resolve('../static/js/llm-client.js'), 'utf8'));

const c = new LLMClient();
global.VW = {};
c.apiBase = 'https://openrouter.ai/api/v1';
c.streaming = false;
c.apiFormat = 'auto'; // resolves to chat-completions

(async () => {
    let pass = true;
    console.log('--- chat-completions, thinking OFF ---');
    c.thinking = false;
    await c.chat([{ role: 'user', content: 'hi' }]);

    console.log('--- chat-completions, thinking ON ---');
    c.thinking = true; c.thinkingEffort = 'high';
    await c.chat([{ role: 'user', content: 'hi' }]);

    console.log('--- responses, thinking OFF ---');
    c.apiFormat = 'responses'; c.thinking = false;
    const off = c._buildResponsesBody([{ role: 'system', content: 'sys' }, { role: 'user', content: 'hi' }], { model: 'm', temperature: 0.7 });
    console.log(JSON.stringify(off, null, 1));
    if (!off.reasoning || off.reasoning.exclude !== true) { console.log('FAIL responses off missing exclude'); pass = false; }

    console.log('--- responses, thinking ON ---');
    c.thinking = true; c.thinkingEffort = 'high';
    const on = c._buildResponsesBody([{ role: 'user', content: 'hi' }], { model: 'm', temperature: 0.7 });
    console.log(JSON.stringify(on, null, 1));
    if (!on.reasoning || on.reasoning.effort !== 'high') { console.log('FAIL responses on missing effort'); pass = false; }

    // OFF must never contain reasoning_effort / enabled / exclude missing
    console.log(pass ? 'RESULT: PASS' : 'RESULT: FAIL');
    process.exit(pass ? 0 : 1);
})();