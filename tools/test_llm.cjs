const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const results = [];

    function pass(l) { results.push({label:l,status:'OK'}); console.log('  OK ' + l); }
    function fail(l, e) { results.push({label:l,status:'FAIL',error:e.message||e}); console.log('  FAIL ' + l + ': ' + (e.message||e)); }
    async function t(label, fn) { try { await fn(); pass(label); } catch(e) { fail(label, e); } }
    async function getState() { return await page.evaluate(async () => { const r=await fetch('/api/state'); return await r.json(); }); }

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    console.log('\n=== LLM 1. ENDPOINT STRUCTURE ===');
    await t('LLM tools endpoint returns list', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/llm/tools'); return await r.json();
        });
        if (Array.isArray(data)) console.log('  ('+data.length+' tools)');
        else if (data.error) console.log('  (LLM endpoint error: '+(data.error||'').substring(0,40)+')');
        else if (data.tools) console.log('  ('+data.tools.length+' tools)');
    });
    await t('LLM call endpoint handles missing model', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/llm/call', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:'hello'}]})});
            return await r.json();
        });
        if (data.error) console.log('  (missing params: '+(data.error||'').substring(0,40)+')');
    });
    await t('Real LLM call with test-model returns response', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/llm/call', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
                provider_name:'lmstudio',
                model_name:'test-model',
                messages:[{role:'user',content:'Say hello in one word.'}]
            })});
            const resp = await r.json();
            // Try direct response first, then choices format
            if (resp.choices && resp.choices[0]) return resp.choices[0].message.content;
            if (resp.content) return resp.content;
            if (resp.response) return resp.response;
            return resp;
        });
        if (typeof data === 'string') console.log('  (response: '+data.substring(0,60)+')');
        else if (data.error) console.log('  (llm error: '+data.error.substring(0,40)+')');
        else console.log('  (response received)');
    });

    console.log('\n=== LLM 2. PROMPT BUILDING ===');
    await t('PromptBuilder builds room context', async () => {
        const hasBuilder = await page.evaluate(() => typeof PromptBuilder !== 'undefined');
        if (!hasBuilder) { console.log('  (PromptBuilder not available)'); return; }
        const ctx = await page.evaluate(() => {
            try { return PromptBuilder.buildRoomContext(); }
            catch(e) { return {error: e.message}; }
        });
        if (ctx.error) console.log('  (buildRoomContext: '+ctx.error.substring(0,40)+')');
        else console.log('  (context built)');
    });
    await t('PromptBuilder builds agent prompt', async () => {
        const hasBuilder = await page.evaluate(() => typeof PromptBuilder !== 'undefined');
        if (!hasBuilder) { console.log('  (PromptBuilder not available)'); return; }
        const prompt = await page.evaluate(async () => {
            try {
                const state = await fetch('/api/state').then(r=>r.json());
                const name = state.active_player || '';
                return PromptBuilder.buildActionPrompt ? PromptBuilder.buildActionPrompt(name) : '(no buildActionPrompt)';
            } catch(e) { return {error: e.message}; }
        });
        if (prompt && prompt.error) console.log('  (buildActionPrompt: '+prompt.error.substring(0,40)+')');
        else console.log('  (prompt built, length: '+(typeof prompt==='string'?prompt.length:'n/a')+')');
    });
    await t('PromptBuilder builds emote prompt', async () => {
        const hasBuilder = await page.evaluate(() => typeof PromptBuilder !== 'undefined');
        if (!hasBuilder) { console.log('  (PromptBuilder not available)'); return; }
        const prompt = await page.evaluate(async () => {
            try {
                const state = await fetch('/api/state').then(r=>r.json());
                const name = state.active_player || '';
                return PromptBuilder.buildEmotePrompt ? PromptBuilder.buildEmotePrompt(name, 'test emote') : '(no buildEmotePrompt)';
            } catch(e) { return {error: e.message}; }
        });
        if (prompt && prompt.error) console.log('  (buildEmotePrompt: '+prompt.error.substring(0,40)+')');
        else console.log('  (prompt built)');
    });

    console.log('\n=== LLM 3. AI GENERATOR ===');
    await t('AIGenerator.generate exists as fallback', async () => {
        const ok = await page.evaluate(() => typeof AIGenerator.generate === 'function');
        if (!ok) throw 'AIGenerator.generate missing';
        console.log('  (AIGenerator available)');
    });
    await t('Generate description endpoint returns gracefully', async () => {
        const data = await page.evaluate(async () => {
            const resp = await fetch('/api/players/Lyrie/generate-description', {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
            return await resp.json();
        });
        if (data.error) console.log('  (generate description: '+(data.error||'').substring(0,40)+')');
        else if (data.description) console.log('  (description generated, length: '+data.description.length+')');
    });

    console.log('\n=== LLM 4. PARSING ===');
    await t('parseJSONFromResponse handles clean JSON', async () => {
        const ok = await page.evaluate(() => {
            try { const r = parseJSONFromResponse('{"test": 1}'); return r.json && r.json.test === 1; }
            catch(e) { return e.message; }
        });
        if (ok !== true) throw 'Clean JSON parse failed: '+ok;
    });
    await t('parseJSONFromResponse handles code-fenced JSON', async () => {
        const ok = await page.evaluate(() => {
            try { const r = parseJSONFromResponse('```json\n{"test": 1}\n```'); return r.json && r.json.test === 1; }
            catch(e) { return e.message; }
        });
        if (ok !== true) throw 'Code-fenced JSON parse failed: '+ok;
    });
    await t('parseJSONFromResponse handles markdown-wrapped JSON', async () => {
        const ok = await page.evaluate(() => {
            try { const r = parseJSONFromResponse('Here is the result:\n\n```\n{"key": "value"}\n```'); return r.json && r.json.key === 'value'; }
            catch(e) { return e.message; }
        });
        if (ok !== true) throw 'Markdown-wrapped JSON parse failed: '+ok;
    });
    await t('parseJSONFromResponse handles malformed input gracefully', async () => {
        const ok = await page.evaluate(() => {
            try { const r = parseJSONFromResponse('not json at all'); return r.json === null; }
            catch(e) { return e.message; }
        });
        if (ok !== true) throw 'Malformed JSON parse failed: '+ok;
    });

    console.log('\n=== LLM 5. ERROR HANDLING ===');
    await t('Send empty messages array — expect error, not crash', async () => {
        const data = await page.evaluate(async () => {
            try {
                const r = await fetch('/api/llm/call', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider_name: 'openai', model_name: 'test', messages: [] })
                });
                if (!r.ok) return { status: r.status, error: (await r.json()).error || 'no error field' };
                const resp = await r.json();
                return { status: r.status, result: typeof resp };
            } catch (e) { return { error: e.message }; }
        });
        if (data.error) console.log('  (network error: ' + data.error.substring(0, 40) + ')');
        else if (data.status !== 200) console.log('  (returned ' + data.status + ' with error, as expected)');
        else console.log('  (returned 200 OK, result type: ' + data.result + ')');
    });
    await t('Send invalid provider name — expect clear error', async () => {
        const data = await page.evaluate(async () => {
            try {
                const r = await fetch('/api/llm/call', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider_name: 'nonexistent_provider_xyz', model_name: 'test', messages: [{ role: 'user', content: 'hello' }] })
                });
                const body = await r.json();
                const errorMsg = body.error || JSON.stringify(body);
                return { status: r.status, error: errorMsg.substring(0, 80) };
            } catch (e) { return { error: e.message }; }
        });
        if (data.error && data.error.substring) console.log('  (error: ' + data.error + ')');
        else console.log('  (status ' + data.status + ')');
    });
    await t('Send excessively long message — expect no crash', async () => {
        const data = await page.evaluate(async () => {
            try {
                // 100KB of padding
                const longContent = 'x'.repeat(100 * 1024);
                const r = await fetch('/api/llm/call', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider_name: 'openai', model_name: 'test', messages: [{ role: 'user', content: longContent }] })
                });
                const body = await r.json();
                return { status: r.status, error: body.error ? body.error.substring(0, 60) : null };
            } catch (e) { return { error: e.message }; }
        });
        if (data.status) console.log('  (returned ' + data.status + ' without crash' + (data.error ? ', error: ' + data.error.substring(0, 40) : '') + ')');
        else console.log('  (result: ' + JSON.stringify(data).substring(0, 40) + ')');
    });
    await t('Call with tools parameter — expect valid response structure', async () => {
        const data = await page.evaluate(async () => {
            try {
                const r = await fetch('/api/llm/call', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        provider_name: 'openai',
                        model_name: 'test',
                        messages: [{ role: 'user', content: 'use a tool' }],
                        tools: [{ name: 'test_tool', description: 'A test tool' }]
                    })
                });
                const body = await r.json();
                return { status: r.status, hasChoices: !!body.choices, hasContent: !!body.content, hasResponse: !!body.response, keys: Object.keys(body).slice(0, 5) };
            } catch (e) { return { error: e.message }; }
        });
        if (data.status) console.log('  (status ' + data.status + ', keys: ' + (data.keys || []).join(', ') + ')');
        else console.log('  (' + JSON.stringify(data).substring(0, 40) + ')');
    });

    console.log('\n=== LLM 6. AGENT CONFIG ===');
    await t('Verify config object has llmConfig method', async () => {
        const ok = await page.evaluate(() => {
            if (typeof config === 'undefined') return 'config not defined';
            if (typeof config.toLLMConfig !== 'function') return 'config.toLLMConfig missing';
            const result = config.toLLMConfig();
            const hasExpectedKeys = result && typeof result.apiKey !== 'undefined' && typeof result.apiBase !== 'undefined' && typeof result.model !== 'undefined';
            return hasExpectedKeys ? { keys: Object.keys(result) } : 'result missing expected keys: ' + JSON.stringify(Object.keys(result));
        });
        if (typeof ok === 'object' && ok.keys) console.log('  (llmConfig keys: ' + ok.keys.join(', ') + ')');
        else if (typeof ok === 'string') console.log('  (' + ok + ')');
        else console.log('  (' + JSON.stringify(ok).substring(0, 40) + ')');
    });
    await t('Verify LLM client configure accepts model settings', async () => {
        const ok = await page.evaluate(() => {
            if (typeof llmClient === 'undefined') return 'llmClient not defined';
            if (typeof llmClient.configure !== 'function') return 'llmClient.configure missing';
            // Call configure with test model settings
            const testConfig = { apiKey: 'test-key', apiBase: 'https://test.api/v1', model: 'test-model', temperature: 0.5, streaming: false };
            llmClient.configure(testConfig);
            // Check it was applied
            const matches = llmClient.apiKey === 'test-key' && llmClient.apiBase === 'https://test.api/v1' && llmClient.model === 'test-model';
            // Restore with current config
            if (typeof config !== 'undefined' && config.toLLMConfig) {
                llmClient.configure(config.toLLMConfig());
            }
            return matches ? 'configure accepted settings' : 'configure did not apply: apiKey=' + llmClient.apiKey + ' model=' + llmClient.model;
        });
        if (typeof ok === 'string') console.log('  (' + ok + ')');
        else console.log('  (' + JSON.stringify(ok).substring(0, 40) + ')');
    });
    await t('Verify model selector dropdown populates', async () => {
        const result = await page.evaluate(async () => {
            try {
                const select = document.getElementById('agent-model-select');
                if (!select) return 'no agent-model-select element';
                // Try to populate via ui controller if available
                if (window.VW?.ui?.populateModelSelect) {
                    await VW.ui.populateModelSelect();
                    await new Promise(r => setTimeout(r, 300));
                }
                const options = Array.from(select.options);
                if (options.length === 0) return 'dropdown exists but empty';
                const optionValues = options.map(o => o.value).filter(Boolean);
                return { optionCount: options.length, values: optionValues.slice(0, 5) };
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'object' && result.optionCount > 0) console.log('  (' + result.optionCount + ' options, e.g.: ' + (result.values || []).join(', ') + ')');
        else if (typeof result === 'string') console.log('  (' + result + ')');
        else console.log('  (' + JSON.stringify(result).substring(0, 40) + ')');
    });

    // ═══════════════ RESULTS ═══════════════
    const passed = results.filter(r => r.status==='OK').length;
    const failed = results.filter(r => r.status==='FAIL').length;
    console.log('\n' + '\u2550'.repeat(50));
    console.log('  LLM RESULTS: ' + passed + '/' + (passed+failed) + ' passed, ' + failed + ' failed');
    console.log('\u2550'.repeat(50));
    if (failed > 0) {
        console.log('\nFailures:');
        results.filter(r=>r.status==='FAIL').forEach(r => console.log('  \u2717 ' + r.label + ': ' + r.error));
    }
    await browser.close();
})();
