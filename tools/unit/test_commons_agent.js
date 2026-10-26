function commonsHarness(reply, knownCharacters = ['Lysa'], theme = 'live_social') {
    const saved = {
        state: window.CommonsState,
        api: window.CommonsApi,
        llm: window.llmClient,
        promptBuilder: window.PromptBuilder.buildCommunicationPrompt,
    };
    const calls = [];
    let decisionPrompt = '';
    let memoryWritten = '';
    window.CommonsState = Object.assign(Object.create(saved.state || {}), {
        manualPaused: false,
        visibilityPaused: false,
        participants: { Mira: { active: true, blocked: false, control_mode: 'llm' } },
        characterTurns: {},
        lastActed: null,
        selectedDrawerCharacter: null,
    });
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
                participants: { Mira: {}, Lysa: {}, Joren: {}, User: { active: false } },
                known_characters: knownCharacters,
                theme,
            };
        },
        readMessages: async (...args) => {
            calls.push(['read', ...args.slice(0, 6)]);
            return { messages: [{ id: 6, author: 'Lysa', text: 'The door is open.' }] };
        },
        postMessage: async (...args) => calls.push(['post', ...args.slice(0, 3)]),
        createChannel: async (body) => {
            calls.push(['create-channel', body]);
            return {
                channel: {
                    id: body.kind === 'group' ? 'group-mira-watch' : 'dm-mira-lysa',
                    kind: body.kind,
                    members: body.members || ['Mira', body.other],
                },
            };
        },
        storeMemory: async (name, text) => {
            calls.push(['memory', name]);
            memoryWritten += `${memoryWritten ? ' ' : ''}${text}`;
        },
    };
    window.llmClient = {
        chatWithTools: async (messages) => {
            calls.push(['llm-tool-turn', messages.length]);
            if (messages.length === 2) {
                decisionPrompt = messages[1].content;
                const action = reply.communication?.action;
                if (action && action !== 'think') {
                    const fields = { ...reply.communication };
                    delete fields.action;
                    const map = { read_mode: 'mode', from_id: 'from_id', to_id: 'to_id', group_name: 'group_name' };
                    const args = {};
                    for (const [key, value] of Object.entries(fields)) args[map[key] || key] = value;
                    return { content: '', tool_calls: [{ id: 'legacy-action', function: { name: action, arguments: JSON.stringify(args) } }] };
                }
                if (reply.memory?.text) return { content: '', tool_calls: [{ id: 'remember', function: { name: 'remember', arguments: JSON.stringify(reply.memory) } }] };
                return { content: reply.inner_monologue || '', tool_calls: [] };
            }
            const actionMessages = messages.filter(message => message.role === 'assistant' && message.tool_calls?.length);
            const actionCall = actionMessages[actionMessages.length - 1]?.tool_calls?.[0];
            if (actionCall?.function?.name !== 'remember' && reply.memory?.text) {
                return { content: '', tool_calls: [{ id: 'remember', function: { name: 'remember', arguments: JSON.stringify(reply.memory) } }] };
            }
            return { content: reply.inner_monologue || '', tool_calls: [] };
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

test('the commons: a character can read and then optionally reply in the same turn', async () => {
    const h = commonsHarness({ inner_monologue: 'I will consider what she said.', communication: { action: 'think' }, memory: null });
    const original = window.llmClient.chatWithTools;
    let calls = 0;
    try {
        window.llmClient.chatWithTools = async (messages) => {
            calls++;
            if (calls === 1) return { content: '', tool_calls: [{ id: 'read-first', function: { name: 'read_chat', arguments: JSON.stringify({ channel_id: 'group-night', mode: 'latest', n: 5 }) } }] };
            if (calls === 2) {
                assertTrue(messages.some(message => message.role === 'tool' && message.content.includes('The door is open.')));
                return { content: '', tool_calls: [{ id: 'reply-second', function: { name: 'send_chat', arguments: JSON.stringify({ channel_id: 'group-night', text: 'I am on my way.' }) } }] };
            }
            return { content: 'I should go help.', tool_calls: [] };
        };
        await CommonsAgent.actCharacter('Mira');
        assertEq(calls, 3);
        assertTrue(h.calls.some(call => call[0] === 'read' && call[2] === 'group-night'));
        assertTrue(h.calls.some(call => call[0] === 'post' && call[2] === 'I am on my way.'));
        assertTrue(window.CommonsState.lastActed.summary.includes('read 1 message'));
        assertTrue(window.CommonsState.lastActed.summary.includes('sent a message'));
    } finally {
        window.llmClient.chatWithTools = original;
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

test('the commons: a character can create a group with named invitees and send its first message', async () => {
    const h = commonsHarness({
        inner_monologue: 'I should bring Lysa and Joren together.',
        communication: {
            action: 'start_group',
            group_name: 'North gate watch',
            recipients: ['Lysa', 'Joren'],
            text: 'Meet by the north gate.',
        },
        memory: null,
    }, ['Lysa', 'Joren']);
    try {
        await CommonsAgent.actCharacter('Mira');
        assertTrue(h.prompt.includes('"known":["Lysa","Joren"]'));
        assertEq(h.calls.find(call => call[0] === 'create-channel'), [
            'create-channel', {
                creator: 'Mira', kind: 'group', name: 'North gate watch',
                members: ['Mira', 'Lysa', 'Joren'],
            },
        ]);
        assertEq(h.calls.find(call => call[0] === 'post'), [
            'post', 'Mira', 'Meet by the north gate.', 'group-mira-watch',
        ]);
    } finally {
        h.restore();
    }
});

test('the commons: an agent cannot start a group with an invitee whose name it does not know', async () => {
    const h = commonsHarness({
        inner_monologue: 'I should not be able to invite a stranger.',
        communication: {
            action: 'start_group',
            group_name: 'Private plans',
            recipients: ['Lysa', 'Stranger'],
            text: 'Meet privately.',
        },
        memory: null,
    });
    try {
        await CommonsAgent.actCharacter('Mira');
        assertTrue(h.prompt.includes('"known":["Lysa"]'));
        assertFalse(h.calls.some(call => ['create-channel', 'post'].includes(call[0])));
    } finally {
        h.restore();
    }
});

test('the commons: an agent cannot start a DM with a character whose name it does not know', async () => {
    const h = commonsHarness({
        inner_monologue: 'I do not know this person.',
        communication: { action: 'start_dm', recipient: 'Stranger', text: 'Hello.' },
        memory: null,
    });
    try {
        await CommonsAgent.actCharacter('Mira');
        assertFalse(h.calls.some(call => ['create-channel', 'post'].includes(call[0])));
    } finally {
        h.restore();
    }
});

test('the commons: an agent cannot create a group without a name, invitee, and opening message', async () => {
    const h = commonsHarness({
        inner_monologue: 'This group request is incomplete.',
        communication: {
            action: 'start_group',
            group_name: 'Incomplete group',
            recipients: ['Lysa'],
            text: '',
        },
        memory: null,
    });
    try {
        await CommonsAgent.actCharacter('Mira');
        assertFalse(h.calls.some(call => ['create-channel', 'post'].includes(call[0])));
    } finally {
        h.restore();
    }
});

test('the commons: town-board mode ignores group creation decisions', async () => {
    const h = commonsHarness({
        inner_monologue: 'A group is not available in this mode.',
        communication: {
            action: 'start_group', group_name: 'Private plans',
            recipients: ['Lysa'], text: 'Meet at dusk.',
        },
        memory: null,
    }, ['Lysa'], 'town_board');
    try {
        await CommonsAgent.actCharacter('Mira');
        assertFalse(h.calls.some(call => ['create-channel', 'post'].includes(call[0])));
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

test('the commons: stepOne allows a character to act when simulation is paused', async () => {
    const h = commonsHarness({
        inner_monologue: 'I should send a quick update.',
        communication: { action: 'send_chat', channel_id: 'group-night', text: 'Taking one step.' },
        memory: null,
    });
    window.CommonsState.manualPaused = true;
    try {
        await CommonsAgent.stepOne();
        assertTrue(window.CommonsState.isPaused);
        assertEq(h.calls.find(call => call[0] === 'post'), [
            'post', 'Mira', 'Taking one step.', 'group-night',
        ]);
    } finally {
        h.restore();
    }
});

test('the commons: human and simple NPC control modes never receive Commons LLM turns', async () => {
    for (const controlMode of ['human', 'npc']) {
        const h = commonsHarness({
            inner_monologue: 'This must not be generated.',
            communication: { action: 'send_chat', channel_id: 'group-night', text: 'Must not be sent.' },
            memory: null,
        });
        try {
            window.CommonsState.participants.Mira.control_mode = controlMode;
            CommonsAgent.isRunning = true;
            CommonsAgent.resetTimer('Mira');
            const inFlight = new AbortController();
            CommonsAgent.controllers.Mira = inFlight;
            CommonsAgent.reconcileParticipants();
            assertTrue(inFlight.signal.aborted);
            delete CommonsAgent.controllers.Mira;
            await CommonsAgent.stepOne('Mira');
            await CommonsAgent.actCharacter('Mira');
            assertFalse(CommonsAgent.timers.Mira);
            assertFalse(h.calls.some(call => call[0] === 'llm-tool-turn'));
            assertFalse(h.calls.some(call => ['read', 'post'].includes(call[0])));
        } finally {
            CommonsAgent.isRunning = false;
            CommonsAgent.timers = {};
            CommonsAgent.deadlines = {};
            h.restore();
        }
    }
});

test('the commons: random talkativeness picks a persistable cooldown inside the slider range', () => {
    const originalRandom = Math.random;
    const originalPaces = window.config.talkativenessByCharacter;
    window.config.talkativenessByCharacter = {};
    try {
        Math.random = () => 0;
        assertEq(CommonsAgent.randomizeTalkativeness('Mira', false), 5);
        Math.random = () => 0.999999;
        assertEq(CommonsAgent.randomizeTalkativeness('Mira', false), 120);
        assertEq(window.config.talkativenessByCharacter.Mira, 120);
    } finally {
        Math.random = originalRandom;
        if (originalPaces === undefined) delete window.config.talkativenessByCharacter;
        else window.config.talkativenessByCharacter = originalPaces;
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
    assertTrue(prompt.includes('start_group'));
    assertTrue(prompt.includes('whose names you know'));
    assertTrue(prompt.includes('Characters whose names you know and may contact: Lysa'));
    assertFalse(prompt.includes('The door is open.'));
});

test('the commons: town-board prompt reports new posts and letters, not unread chats or groups', () => {
    const prompt = PromptBuilder.buildCommunicationPrompt(
        { name: 'Mira', personality: 'careful and dry-witted', traits: { patient: true }, state: 'awake' },
        '- I promised to check the board.',
        [
            { id: 'public', kind: 'public', name: 'Public', unread_count: 2, members: [] },
            { id: 'dm-lysa', kind: 'dm', name: 'Mira · Lysa', unread_count: 3, members: ['Mira', 'Lysa'] },
            { id: 'group-night', kind: 'group', name: 'Night watch', unread_count: 5, members: ['Mira', 'Lysa'] },
        ],
        ['Lysa'],
        'town_board'
    );
    assertTrue(prompt.includes('TOWN BOARD AND LETTERS'));
    assertTrue(prompt.includes('2 new posts'));
    assertTrue(prompt.includes('3 new letters'));
    assertTrue(prompt.includes('Delivery is immediate'));
    assertFalse(prompt.includes('group-night'));
    assertFalse(prompt.includes('start_group'));
    assertFalse(prompt.includes('5 unread'));
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

    const group = ResponseParser.parseCommunication(JSON.stringify({
        communication: {
            action: 'start_group', group_name: 'North gate watch',
            recipients: ['Lysa', 'Lysa', ' Joren '], text: 'Meet here.',
        },
    }));
    assertEq(group.action, 'start_group');
    assertEq(group.groupName, 'North gate watch');
    assertEq(group.recipients, ['Lysa', 'Joren']);
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

test('the commons: communication mode selection uses its world settings endpoint', async () => {
    const realFetch = window.fetch;
    let request = null;
    window.fetch = async (url, options) => {
        request = { url, options };
        return { ok: true, json: async () => ({ theme: 'town_board' }) };
    };
    try {
        const result = await CommonsApi.setTheme('town_board');
        assertEq(request.url, '/api/commons/theme');
        assertEq(request.options.method, 'POST');
        assertEq(JSON.parse(request.options.body), { theme: 'town_board' });
        assertEq(result.theme, 'town_board');
    } finally {
        window.fetch = realFetch;
    }
});

test('the commons: actCharacter records inner monologue and updates lastActed and drawer state', async () => {
    const h = commonsHarness({
        inner_monologue: 'The trail is getting colder; I should ask if anyone saw tracks.',
        communication: { action: 'send_chat', channel_id: 'group-night', text: 'Did anyone see tracks?' },
        memory: null,
    });
    try {
        await CommonsAgent.actCharacter('Mira');
        assertEq(window.CommonsState.lastActed.charName, 'Mira');
        assertTrue(window.CommonsState.lastActed.action.includes('sent a message'));
        const turns = window.CommonsState.characterTurns['Mira'];
        assertTrue(Array.isArray(turns) && turns.length > 0);
        assertEq(turns[0].inner, 'The trail is getting colder; I should ask if anyone saw tracks.');
        assertTrue(turns[0].action.includes('sent a message'));

        window.CommonsState.openDrawer('Mira');
        assertEq(window.CommonsState.selectedDrawerCharacter, 'Mira');
        window.CommonsState.closeDrawer();
        assertEq(window.CommonsState.selectedDrawerCharacter, null);
    } finally {
        h.restore();
    }
});


test('the commons: startup schedules randomized talkativeness and staggered countdowns excluding simple NPCs', () => {
    const originalRandom = Math.random;
    const originalPaces = window.config.talkativenessByCharacter;
    const originalSetTimeout = setTimeout;
    const scheduled = [];
    setTimeout = (fn, delay) => {
        const id = scheduled.length + 1;
        scheduled.push({ id, fn, delay });
        return id;
    };
    window.config.talkativenessByCharacter = {};
    window.CommonsState = {
        isPaused: false,
        participants: {
            User: { control_mode: 'human', active: true, blocked: false },
            Mira: { control_mode: 'llm', active: true, blocked: false },
            Krikka: { control_mode: 'npc', active: true, blocked: false },
            Vekka: { control_mode: 'llm', active: true, blocked: false },
        },
    };
    CommonsAgent.timers = {};
    CommonsAgent.deadlines = {};
    CommonsAgent.remainingMs = {};
    CommonsAgent.isRunning = true;

    try {
        Math.random = () => 0.5;
        CommonsAgent.scheduleAll(true);

        // Mira (LLM) should have received randomized talkativeness and a scheduled timer
        assertTrue(Number.isFinite(window.config.talkativenessByCharacter.Mira));
        assertTrue(window.config.talkativenessByCharacter.Mira >= 5 && window.config.talkativenessByCharacter.Mira <= 120);
        assertTrue(CommonsAgent.timers.Mira !== undefined);
        assertTrue(Number.isFinite(CommonsAgent.deadlines.Mira));

        // Vekka (LLM) should also be scheduled
        assertTrue(Number.isFinite(window.config.talkativenessByCharacter.Vekka));
        assertTrue(window.config.talkativenessByCharacter.Vekka >= 5 && window.config.talkativenessByCharacter.Vekka <= 120);
        assertTrue(CommonsAgent.timers.Vekka !== undefined);

        // Krikka (simple NPC) and User must NEVER receive talkativeness or timers
        assertEq(window.config.talkativenessByCharacter.Krikka, undefined);
        assertEq(CommonsAgent.timers.Krikka, undefined);
        assertEq(CommonsAgent.timers.User, undefined);
    } finally {
        CommonsAgent.isRunning = false;
        CommonsAgent.clearScheduledTimers(false);
        setTimeout = originalSetTimeout;
        Math.random = originalRandom;
        if (originalPaces === undefined) delete window.config.talkativenessByCharacter;
        else window.config.talkativenessByCharacter = originalPaces;
    }
});

test('the commons: onMessageReceived fast-tracks mentioned or DM recipients while yielding floor after posting', async () => {
    const h = commonsHarness({
        inner_monologue: 'Replying to the direct message.',
        communication: { action: 'send_chat', channel_id: 'group-night', text: 'On my way.' },
        memory: null,
    });
    const originalNow = Date.now;
    let fakeNow = 1000000;
    Date.now = () => fakeNow;
    const originalSetTimeout = setTimeout;
    const scheduled = [];
    setTimeout = (fn, delay) => {
        const id = scheduled.length + 1;
        scheduled.push({ id, fn, delay });
        return id;
    };
    CommonsAgent.isRunning = true;
    window.CommonsState.isPaused = false;
    window.CommonsState.channels = [
        { id: 'group-night', kind: 'group', members: ['Mira', 'User'] },
        { id: 'public', kind: 'public', members: ['Mira', 'Vekka', 'Krikka'] },
    ];
    window.CommonsState.participants = {
        User: { control_mode: 'human', active: true, blocked: false },
        Mira: { control_mode: 'llm', active: true, blocked: false },
        Vekka: { control_mode: 'llm', active: true, blocked: false },
        Krikka: { control_mode: 'npc', active: true, blocked: false },
    };

    try {
        // Schedule Mira with a 60-second deadline
        CommonsAgent.deadlines.Mira = fakeNow + 60000;
        CommonsAgent.timers.Mira = 123;

        // Message mentioning Mira arrives in DM
        CommonsAgent.onMessageReceived({
            author: 'User',
            channel_id: 'group-night',
            text: 'Hey @Mira are you there?',
        });

        // Mira deadline must be accelerated (under 5 seconds)
        assertTrue(CommonsAgent.deadlines.Mira <= fakeNow + 5000);
        assertTrue(CommonsAgent.deadlines.Mira >= fakeNow + 1500);

        // Simple NPC Krikka should never be given a timer
        assertEq(CommonsAgent.timers.Krikka, undefined);

        // Test floor-yielding: when Mira acts and posts, didPost is true
        const didPost = await CommonsAgent.actCharacter('Mira');
        assertTrue(didPost);

        // Reset timer with floor-yielding penalty should add 12s extra delay
        CommonsAgent.resetTimer('Mira', didPost ? 12000 : 0);
        const lastScheduled = scheduled[scheduled.length - 1];
        assertTrue(lastScheduled && lastScheduled.delay >= 12000);
    } finally {
        CommonsAgent.isRunning = false;
        CommonsAgent.clearScheduledTimers(false);
        setTimeout = originalSetTimeout;
        Date.now = originalNow;
        h.restore();
    }
});


test('the commons: sleeping or unconscious characters are excluded from timers', () => {
    window.CommonsState = {
        isPaused: false,
        participants: {
            Mira: { control_mode: 'llm', active: true, blocked: false, state: 'sleeping' },
            Vekka: { control_mode: 'llm', active: true, blocked: false, state: 'unconscious' },
            Lysa: { control_mode: 'llm', active: true, blocked: false, state: 'awake' },
        },
    };
    CommonsAgent.isRunning = true;
    CommonsAgent.timers = {};
    CommonsAgent.deadlines = {};
    const scheduled = [];
    const origSetTimeout = setTimeout;
    setTimeout = (fn, delay) => {
        const id = scheduled.length + 1;
        scheduled.push({ id, fn, delay });
        return id;
    };

    try {
        CommonsAgent.resetTimer('Mira');
        CommonsAgent.resetTimer('Vekka');
        CommonsAgent.resetTimer('Lysa');

        // Sleeping and unconscious characters should not have timers
        assertEq(CommonsAgent.timers.Mira, undefined);
        assertEq(CommonsAgent.timers.Vekka, undefined);
        // Awake LLM character should have a timer scheduled
        assertTrue(CommonsAgent.timers.Lysa !== undefined);
    } finally {
        CommonsAgent.isRunning = false;
        CommonsAgent.clearScheduledTimers(false);
        setTimeout = origSetTimeout;
    }
});

test('the commons: burst governor allows double-texting and caps consecutive bursts', () => {
    window.CommonsState = {
        isPaused: false,
        participants: {
            Mira: { control_mode: 'llm', active: true, blocked: false, state: 'awake' },
        },
    };
    CommonsAgent.isRunning = true;
    CommonsAgent.burstCounts = {};
    const scheduled = [];
    const origSetTimeout = setTimeout;
    const origRandom = Math.random;
    setTimeout = (fn, delay) => {
        const id = scheduled.length + 1;
        scheduled.push({ id, fn, delay });
        return id;
    };
    Math.random = () => 0.01; // Force burst chance to pass

    const playerImpulsive = {
        name: 'Mira',
        traits: { impulsive: true, talkative: true },
        tags: ['impulsive'],
    };

    try {
        // Burst 1: didPost is true, burst rolls success -> fast-tracks to 1.5s - 3.5s
        CommonsAgent.handlePostTurnCadence('Mira', { didPost: true, player: playerImpulsive });
        assertEq(CommonsAgent.burstCounts.Mira, 1);
        let last = scheduled[scheduled.length - 1];
        assertTrue(last && last.delay >= 1500 && last.delay <= 3500);

        // Burst 2: second rapid message
        CommonsAgent.handlePostTurnCadence('Mira', { didPost: true, player: playerImpulsive });
        assertEq(CommonsAgent.burstCounts.Mira, 2);

        // Burst 3: third rapid message (reaches cap of 3 for impulsive)
        CommonsAgent.handlePostTurnCadence('Mira', { didPost: true, player: playerImpulsive });
        assertEq(CommonsAgent.burstCounts.Mira, 3);

        // Burst 4: cap reached, burst momentum resets to 0 and yields floor
        CommonsAgent.handlePostTurnCadence('Mira', { didPost: true, player: playerImpulsive });
        assertEq(CommonsAgent.burstCounts.Mira, undefined);
        last = scheduled[scheduled.length - 1];
        assertTrue(last && last.delay >= 8000);
    } finally {
        CommonsAgent.isRunning = false;
        CommonsAgent.clearScheduledTimers(false);
        setTimeout = origSetTimeout;
        Math.random = origRandom;
    }
});
