/**
 * Unit tests for AI narration and system messages (bug-517).
 */
'use strict';

test('narrationUI.getNarratedActionResult combines system messages into output context (bug-517)', async () => {
    if (!window.narrationUI && typeof window.__readFile === 'function') {
        if (typeof window.fetch === 'undefined') {
            window.fetch = async () => ({ ok: false, json: async () => ({}) });
        }
        if (typeof window.document === 'undefined') {
            window.document = { getElementById: () => null };
        }
        const src = window.__readFile('static/js/narration-ui.js');
        (new Function(src))();
    }

    const NUI = window.narrationUI;
    assertTrue(!!NUI, 'narrationUI is available');

    const oldEvents = window.events;
    window.events = { log: () => {} };

    // 1. None mode returns null
    NUI.mode = 'none';
    const resNone = await NUI.getNarratedActionResult('You open the chest.', 'Hero', 'open chest', ['A trap clicks!']);
    assertEq(resNone, null, 'returns null when mode is none');

    // 2. AI mode combines output and system messages in prompt
    let promptCaptured = null;
    const oldClient = window.llmClient;
    window.llmClient = {
        chat: async (messages) => {
            promptCaptured = messages;
            return 'You pry open the chest and spring a hidden trap mechanism.';
        },
    };
    const oldConfig = window.config;
    window.config = { apiKey: 'fake-key', model: 'fake-model' };

    NUI.mode = 'ai';
    const resAi = await NUI.getNarratedActionResult('You open the chest.', 'Hero', 'open chest', ['A trap clicks!']);

    assertTrue(!!promptCaptured, 'llmClient.chat was called');
    const userPrompt = promptCaptured.find((m) => m.role === 'user')?.content || '';
    assertTrue(userPrompt.includes('You open the chest.'), 'user prompt has action output');
    assertTrue(userPrompt.includes('A trap clicks!'), 'user prompt includes system consequence');
    assertEq(resAi, 'You pry open the chest and spring a hidden trap mechanism.', 'returns narrated result');

    // Restore globals
    window.llmClient = oldClient;
    window.config = oldConfig;
    window.events = oldEvents;
    NUI.mode = 'none';
});
