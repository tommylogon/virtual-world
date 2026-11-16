// Unit tests for task-773: Send the character's profile image to vision-capable models

function stubFetch(responses) {
    const calls = [];
    window.fetch = async (url, init) => {
        const body = init?.body ? JSON.parse(init.body) : {};
        calls.push({ url, body, headers: init?.headers });
        const next = responses.shift();
        if (next === undefined) return { ok: true, status: 200, json: async () => ({ choices: [{ message: { content: 'ok' } }] }) };
        return {
            ok: true,
            status: 200,
            json: async () => next,
            text: async () => JSON.stringify(next),
        };
    };
    return calls;
}

test('vision disabled: request body is byte-identical text-only', async () => {
    const c = llmClient;
    c.configure({ visionEnabled: false });

    // Mock worldState with a character having profile art
    window.worldState = {
        getNode: (id) => id === 'char1' ? {
            id: 'char1',
            name: 'Arix',
            properties: {
                expressions: {
                    neutral: { profile: '/static/images/nodes/player_Arix-profile-neutral.webp' }
                }
            }
        } : null
    };

    const realFetch = window.fetch;
    const calls = stubFetch([{ choices: [{ message: { content: 'text response' } }] }]);

    try {
        await c.chat([
            { role: 'system', content: 'You are Arix.' },
            { role: 'user', content: 'What do you see?' }
        ], { actor: 'char1', streaming: false });

        assertEq(calls.length, 1, 'one fetch call made');
        const msgs = calls[0].body.messages;
        assertEq(msgs.length, 2, '2 messages sent');
        assertEq(typeof msgs[0].content, 'string', 'system message is string');
        assertEq(typeof msgs[1].content, 'string', 'user message remains string');
        assertEq(msgs[1].content, 'What do you see?', 'user message text is untouched');
    } finally {
        window.fetch = realFetch;
    }
});

test('vision disabled: strips image parts from multimodal messages', async () => {
    const c = llmClient;
    c.configure({ visionEnabled: false });

    const realFetch = window.fetch;
    const calls = stubFetch([{ choices: [{ message: { content: 'ok' } }] }]);

    try {
        await c.chat([
            { role: 'user', content: [{ type: 'text', text: 'Check this image' }, { type: 'image_url', image_url: { url: 'data:image/png;base64,123' } }] }
        ], { streaming: false });

        assertEq(calls.length, 1);
        const userMsg = calls[0].body.messages[0];
        assertEq(typeof userMsg.content, 'string', 'collapsed to string');
        assertEq(userMsg.content, 'Check this image', 'only text preserved');
    } finally {
        window.fetch = realFetch;
    }
});

test('vision enabled: attaches character profile image to user message as base64 image_url', async () => {
    const c = llmClient;
    c.configure({ visionEnabled: true });
    c.clearImageCache();

    const origResolve = c.resolveImageDataUrl;
    c.resolveImageDataUrl = async (url) => `data:image/webp;base64,TESTMOCKDATA_${url}`;

    window.worldState = {
        getNode: (id) => id === 'char1' ? {
            id: 'char1',
            name: 'Arix',
            properties: {
                expressions: {
                    neutral: { profile: '/static/images/nodes/player_Arix-profile-neutral.webp' }
                }
            }
        } : null
    };

    const realFetch = window.fetch;
    const calls = stubFetch([{ choices: [{ message: { content: 'I see my reflection' } }] }]);

    try {
        await c.chat([
            { role: 'system', content: 'You are Arix.' },
            { role: 'user', content: 'Describe yourself.' }
        ], { actor: 'char1', streaming: false });

        assertEq(calls.length, 1);
        const msgs = calls[0].body.messages;
        assertEq(typeof msgs[0].content, 'string', 'system message remains text-only');
        assertEq(Array.isArray(msgs[1].content), true, 'user message is multimodal array');
        assertEq(msgs[1].content[0].type, 'text', 'first part is text');
        assertEq(msgs[1].content[0].text, 'Describe yourself.', 'prompt text preserved');
        assertEq(msgs[1].content[1].type, 'image_url', 'second part is image_url');
        assertEq(msgs[1].content[1].image_url.url, 'data:image/webp;base64,TESTMOCKDATA_/static/images/nodes/player_Arix-profile-neutral.webp');
    } finally {
        c.resolveImageDataUrl = origResolve;
        window.fetch = realFetch;
    }
});

test('vision enabled: character without art leaves prompt text-only', async () => {
    const c = llmClient;
    c.configure({ visionEnabled: true });

    window.worldState = {
        getNode: (id) => id === 'no_art_char' ? {
            id: 'no_art_char',
            name: 'Bob',
            properties: {}
        } : null
    };

    const realFetch = window.fetch;
    const calls = stubFetch([{ choices: [{ message: { content: 'ok' } }] }]);

    try {
        await c.chat([
            { role: 'system', content: 'You are Bob.' },
            { role: 'user', content: 'Hello Bob' }
        ], { actor: 'no_art_char', streaming: false });

        assertEq(calls.length, 1);
        const msgs = calls[0].body.messages;
        assertEq(typeof msgs[1].content, 'string', 'user message remains text string');
    } finally {
        window.fetch = realFetch;
    }
});

test('image cache: resolves and caches base64 data url per path', async () => {
    const c = llmClient;
    c.clearImageCache();

    let fetchCount = 0;
    const realFetch = window.fetch;
    window.fetch = async (url) => {
        fetchCount++;
        return {
            ok: true,
            status: 200,
            blob: async () => ({ type: 'image/webp' })
        };
    };

    // Mock FileReader
    class MockFileReader {
        readAsDataURL() {
            setTimeout(() => {
                this.result = 'data:image/webp;base64,SIMULATED_BYTES';
                this.onloadend();
            }, 5);
        }
    }
    const realFileReader = window.FileReader;
    window.FileReader = MockFileReader;

    try {
        const url1 = await c.resolveImageDataUrl('/static/images/test.webp');
        assertEq(url1, 'data:image/webp;base64,SIMULATED_BYTES', 'first resolve returns data url');
        assertEq(fetchCount, 1, 'fetch called once');

        const url2 = await c.resolveImageDataUrl('/static/images/test.webp');
        assertEq(url2, 'data:image/webp;base64,SIMULATED_BYTES', 'second resolve returns cached data url');
        assertEq(fetchCount, 1, 'fetch NOT called a second time (served from cache)');
    } finally {
        window.fetch = realFetch;
        window.FileReader = realFileReader;
    }
});
