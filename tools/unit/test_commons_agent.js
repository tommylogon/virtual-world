function commonsHarness(reply) {
    const saved = {
        state: window.CommonsState,
        api: window.CommonsApi,
        llm: window.llmClient,
        promptBuilder: window.PromptBuilder.buildCommunicationPrompt,
    };
    const calls = [];
    let decisionPrompt = '';
    let memoryWritten = '';
    window.CommonsState = {
        isPaused: false,
        participants: { Mira: { active: true, blocked: false } },
    };
    window.PromptBuilder.buildCommunicationPrompt = (player, memories, channels, known) => {
        decisionPrompt = JSON.stringify({ player, memories, channels, known });
        return decisionPrompt;
    };
    window.CommonsApi = {
        getCharacterContext: async (name) => {
            calls.push(['character', name]);
            return { name, traits: { patient: true }, personality: 'careful', description: 'A quiet traveler.' };
        },
        retrieveMemories: async (name, query) => {
            calls.push(['recall', name, query]);
            return { memories: [{ text: 'I promised to check messages from Lysa.' }] };
        },
        getState: async (name) => {
            calls.push(['phone', name]);
            return {
                channels: [
                    { id: 'public', kind: 'public', name: 'Public', unread_count: 0, members: [] },
                    { id: 'group-night', kind: 'group', name: 'Night watch', unread_count: 2, members: ['Mira', 'Lysa'] },
                ],
                participants: { Mira: {}, Lysa: {}, User: { active: false } },
            };
        },
        readMessages: async (...args) => {
            calls.push(['read', ...args.slice(0, 6)]);
            return { messages: [{ id: 6, author: 'Lysa', text: 'The door is open.' }] };
        },
        postMessage: async (...args) => calls.push(['post', ...args.slice(0, 3)]),
        createChannel: async (body) => {
            calls.push(['create-channel', body]);
            return { channel: { id: 'dm-mira-lysa', kind: 'dm', members: ['Mira', 'Lysa'] } };
        },
        storeMemory: async (name, text) => {
            calls.push(['memory', name]);
            memoryWritten = text;
        },
    };
    window.llmClient = {
        chat: async (messages) => {
            calls.push(['llm']);
            decisionPrompt = messages[1].content;
            return JSON.stringify(reply);
        },
    };
    return {
        calls,
        get prompt() { return decisionPrompt; },
        get memory() { return memoryWritten; },
        restore() {
            window.CommonsState = saved.state;
            window.CommonsApi = saved.api;
            window.llmClient = saved.llm;
            window.PromptBuilder.buildCommunicationPrompt = saved.promptBuilder;
            CommonsAgent.controllers = {};
        },
    };
}

test('the commons: explicit group read uses the shared Player memory endpoint and never prompts with unread text', async () => {
    const h = commonsHarness({
        inner_monologue: 'I should check the group.',
        communication: {
            action: 'read_chat', channel_id: 'group-night', read_mode: 'range',
            n: 2, from_id: 5, to_id: 6,
        },
        memory: { text: 'I felt relieved by the update.', importance: 6, tags: ['friendship'] },
    });
    try {
        await CommonsAgent.actCharacter('Mira');
        assertTrue(h.prompt.includes('I promised to check messages from Lysa.'));
        assertTrue(h.prompt.includes('group-night'));
        assertFalse(h.prompt.includes('The door is open.'));
        assertEq(h.calls.find(call => call[0] === 'read').slice(0, 7), [
            'read', 'Mira', 'group-night', 'range', 2, 5, 6,
        ]);
        assertFalse(h.calls.some(call => call[0] === 'post'));
        assertTrue(h.memory.includes('I read the conversation: Lysa: The door is open.'));
        assertTrue(h.memory.includes('I felt relieved by the update.'));
        assertTrue(h.calls.some(call => call[0] === 'recall' && call[1] === 'Mira'));
        assertTrue(h.calls.some(call => call[0] === 'memory' && call[1] === 'Mira'));
    } finally {
        h.restore();
    }
});

test('the commons: send routes only to the selected authorized channel', async () => {
    const h = commonsHarness({
        inner_monologue: 'I will answer the night watch.',
        communication: { action: 'send_chat', channel_id: 'group-night', text: 'I am on my way.' },
        memory: null,
    });
    try {
        await CommonsAgent.actCharacter('Mira');
        assertEq(h.calls.find(call => call[0] === 'post'), [
            'post', 'Mira', 'I am on my way.', 'group-night',
        ]);
        assertFalse(h.calls.some(call => call[0] === 'read'));
    } finally {
        h.restore();
    }
});

test('the commons: a character can start a two-person DM and send its first message', async () => {
    const h = commonsHarness({
        inner_monologue: 'This belongs between Lysa and me.',
        communication: { action: 'start_dm', recipient: 'Lysa', text: 'Are you near the gate?' },
        memory: null,
    });
    try {
        await CommonsAgent.actCharacter('Mira');
        assertEq(h.calls.find(call => call[0] === 'create-channel'), [
            'create-channel', { creator: 'Mira', kind: 'dm', other: 'Lysa' },
        ]);
        assertEq(h.calls.find(call => call[0] === 'post'), [
            'post', 'Mira', 'Are you near the gate?', 'dm-mira-lysa',
        ]);
    } finally {
        h.restore();
    }
});

test('the commons: think action does not read, send, or create a conversation', async () => {
    const h = commonsHarness({
        inner_monologue: 'I will let the conversation wait.',
        communication: { action: 'think' },
        memory: null,
    });
    try {
        await CommonsAgent.actCharacter('Mira');
        assertFalse(h.calls.some(call => ['read', 'post', 'create-channel', 'memory'].includes(call[0])));
    } finally {
        h.restore();
    }
});

test('the commons: shared prompt builder uses existing Player persona and hides message bodies', () => {
    const prompt = PromptBuilder.buildCommunicationPrompt(
        { name: 'Mira', personality: 'careful and dry-witted', traits: { patient: true }, state: 'awake' },
        '- I promised to check the night watch.',
        [{ id: 'group-night', kind: 'group', name: 'Night watch', unread_count: 1, members: ['Mira', 'Lysa'] }],
        ['Lysa']
    );
    assertTrue(prompt.includes('Personality: careful and dry-witted'));
    assertTrue(prompt.includes('group-night'));
    assertTrue(prompt.includes('I promised to check the night watch.'));
    assertFalse(prompt.includes('The door is open.'));
});

test('the commons: shared response parser normalizes communication and Player memory', () => {
    const parsed = ResponseParser.parseCommunication(JSON.stringify({
        inner_monologue: 'I should answer.',
        communication: {
            action: 'send_chat', channel_id: 'group-night', text: 'I am here.',
            read_mode: 'range', n: 80, from_id: 4, to_id: 8,
        },
        memory: { text: 'I kept my promise.', importance: 7, tags: ['conversation'] },
    }));
    assertEq(parsed.action, 'send_chat');
    assertEq(parsed.channelId, 'group-night');
    assertEq(parsed.n, 50);
    assertEq(parsed.memory.text, 'I kept my promise.');
});

test('the commons: memory reflection writes to the existing Player memories endpoint', async () => {
    const realFetch = window.fetch;
    let request = null;
    window.fetch = async (url, options) => {
        request = { url, options };
        return { ok: true, json: async () => ({ status: 'success' }) };
    };
    try {
        await CommonsApi.storeMemory('Mira', 'I kept my promise to Lysa.', 6, ['conversation', 'chat']);
        assertEq(request.url, '/api/players/Mira/memories/entry');
        const payload = JSON.parse(request.options.body);
        assertEq(payload.text, 'I kept my promise to Lysa.');
        assertEq(payload.category, 'social');
        assertFalse(Object.hasOwn(payload, 'commons'));
        assertFalse(Object.hasOwn(payload, 'chat_memories'));
    } finally {
        window.fetch = realFetch;
    }
});

test('the commons: recall uses the standard Player memory retrieval endpoint', async () => {
    const realFetch = window.fetch;
    let request = null;
    window.fetch = async (url, options) => {
        request = { url, options };
        return { ok: true, json: async () => ({ memories: [] }) };
    };
    try {
        await CommonsApi.retrieveMemories('Mira', 'messages from Lysa');
        assertEq(request.url, '/api/players/Mira/memories/retrieve');
        assertEq(request.options.method, 'POST');
        assertEq(JSON.parse(request.options.body), {
            query: 'messages from Lysa',
            max_results: 5,
            reinforce: true,
        });
    } finally {
        window.fetch = realFetch;
    }
});
