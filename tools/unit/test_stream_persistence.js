/**
 * tools/unit/test_stream_persistence.js
 *
 * task-779: Unit tests for structured record event stream persistence.
 */
'use strict';

(() => {
    if (typeof window.EventLogExport === 'undefined' && typeof __readFile === 'function') {
        eval(__readFile('static/js/ui/event-log-export.js'));
    }
    if (typeof window.StreamPersistence === 'undefined' && typeof __readFile === 'function') {
        eval(__readFile('static/js/stream/stream-persistence.js'));
    }

    test('StreamPersistence.persist saves structured records via EventLogExport.projectStreamRows', async () => {
        const savedCalls = [];
        const configCalls = {};
        const origStorage = window.storage;
        window.storage = {
            saveEventLog: async (records) => { savedCalls.push(records); },
            setConfig: async (k, v) => { configCalls[k] = v; },
            getConfig: async (k) => configCalls[k] || null,
        };

        const mockBus = {
            _lineSeq: 5,
            _cards: { rebindAll: () => {} },
            _knownActors: new Set(),
            _filters: { updateAgentFilterDropdown: () => {}, restoreSaved: () => {} },
        };
        const persistence = new StreamPersistence(mockBus);

        const streamEl = document.createElement('div');
        streamEl.id = 'event-stream';

        // Add a turn card with explicit children
        const card = document.createElement('div');
        card.className = 'turn-card';
        card.setAttribute('data-actor', 'Arix');

        const header = document.createElement('div');
        header.className = 'turn-card-header';
        const colSpan = document.createElement('span'); colSpan.className = 'turn-card-collapse'; colSpan.textContent = '▾';
        const actSpan = document.createElement('span'); actSpan.className = 'turn-card-actor'; actSpan.textContent = 'Arix';
        const tckSpan = document.createElement('span'); tckSpan.className = 'turn-card-tick'; tckSpan.textContent = '[Turn 1 | Day 1, Month 1, Year 1]';
        header.appendChild(colSpan);
        header.appendChild(actSpan);
        header.appendChild(tckSpan);

        const body = document.createElement('div');
        body.className = 'turn-card-body';

        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble msg-bubble-action';
        bubble.setAttribute('data-actor', 'Arix');
        bubble.setAttribute('data-tick', '10');
        bubble.setAttribute('data-type', 'action');
        bubble.setAttribute('data-seq', '1');
        bubble.setAttribute('data-stream-area', 'Kitchen');

        const iconSpan = document.createElement('span'); iconSpan.className = 'bubble-icon'; iconSpan.textContent = '▶️';
        const tickSpan = document.createElement('span'); tickSpan.className = 'bubble-tick'; tickSpan.textContent = '[Tick 10 | 08:50]';
        const actorSpan = document.createElement('span'); actorSpan.className = 'bubble-actor'; actorSpan.textContent = 'Arix';
        const textSpan = document.createElement('span'); textSpan.className = 'bubble-text'; textSpan.textContent = 'takes knife';
        bubble.appendChild(iconSpan);
        bubble.appendChild(tickSpan);
        bubble.appendChild(actorSpan);
        bubble.appendChild(textSpan);

        body.appendChild(bubble);
        card.appendChild(header);
        card.appendChild(body);
        streamEl.appendChild(card);

        const origGetEl = document.getElementById;
        document.getElementById = (id) => (id === 'event-stream' ? streamEl : origGetEl.call(document, id));

        try {
            await persistence.persist();

            assertEq(savedCalls.length, 1, 'saveEventLog was called once');
            const records = savedCalls[0];
            assertTrue(Array.isArray(records), 'saved records is an array');
            assertEq(records.length, 1, 'one projected record saved');
            const rec = records[0];
            assertEq(rec.type, 'action');
            assertEq(rec.actor, 'Arix');
            assertEq(rec.area, 'Kitchen');
            assertEq(rec.seq, 1);
            assertEq(rec.turn, 1);
            assertEq(rec.card_actor, 'Arix');
            assertFalse(rec.card_collapsed, 'card_collapsed is false when body is visible');
            assertEq(configCalls['event_log_version'], '2');
        } finally {
            document.getElementById = origGetEl;
            window.storage = origStorage;
        }
    });

    test('StreamPersistence.restore drops legacy pre-v2 HTML format logs cleanly', async () => {
        const savedCalls = [];
        const configCalls = { event_log_version: '1' };
        const origStorage = window.storage;
        window.storage = {
            loadEventLog: async () => [{ id: 0, html: '<div class="msg-bubble">old html</div>' }],
            saveEventLog: async (records) => { savedCalls.push(records); },
            setConfig: async (k, v) => { configCalls[k] = v; },
            getConfig: async (k) => configCalls[k] || null,
        };

        const mockBus = {
            _lineSeq: 0,
            _cards: { rebindAll: () => {} },
            _knownActors: new Set(),
            _filters: { updateAgentFilterDropdown: () => {}, restoreSaved: () => {} },
        };
        const persistence = new StreamPersistence(mockBus);

        const streamEl = document.createElement('div');
        streamEl.id = 'event-stream';
        const origGetEl = document.getElementById;
        document.getElementById = (id) => (id === 'event-stream' ? streamEl : origGetEl.call(document, id));

        try {
            await persistence.restore();

            assertEq(savedCalls.length, 1, 'pre-v2 log was cleared');
            assertEq(savedCalls[0].length, 0, 'empty array saved to clear pre-v2 log');
            assertEq(configCalls['event_log_version'], '2', 'version bumped to 2');
            assertEq(streamEl.children.length, 0, 'no legacy HTML was rendered');
        } finally {
            document.getElementById = origGetEl;
            window.storage = origStorage;
        }
    });

    test('StreamPersistence.restore reconstructs stream DOM and restores state from records', async () => {
        const records = [
            {
                seq: 1,
                tick: 10,
                time: '08:50',
                day: 'Day 1, Month 1, Year 1',
                turn: 1,
                actor: 'Arix',
                card_actor: 'Arix',
                card_collapsed: true,
                area: 'Kitchen',
                type: 'action',
                text: 'takes knife',
            },
            {
                seq: 2,
                tick: 11,
                time: '08:55',
                day: 'Day 1, Month 1, Year 1',
                turn: 1,
                actor: 'Arix',
                card_actor: 'Arix',
                card_collapsed: true,
                area: 'Kitchen',
                type: 'rawllm',
                text: '',
                payload: { header: 'LLM turn call', body: '{"thought": "take knife"}' },
            },
        ];

        const origStorage = window.storage;
        window.storage = {
            loadEventLog: async () => records,
            saveEventLog: async () => {},
            setConfig: async () => {},
            getConfig: async (k) => (k === 'event_log_version' ? '2' : null),
        };

        let rebindCalled = false;
        let updateFilterCalled = false;
        let restoreSavedCalled = false;
        const mockBus = {
            _lineSeq: 0,
            _cards: { rebindAll: () => { rebindCalled = true; } },
            _knownActors: new Set(),
            _filters: {
                updateAgentFilterDropdown: () => { updateFilterCalled = true; },
                restoreSaved: () => { restoreSavedCalled = true; },
            },
        };
        const persistence = new StreamPersistence(mockBus);

        const streamEl = document.createElement('div');
        streamEl.id = 'event-stream';
        const origGetEl = document.getElementById;
        document.getElementById = (id) => (id === 'event-stream' ? streamEl : origGetEl.call(document, id));

        try {
            await persistence.restore();

            // 1. Line sequence continuity
            assertEq(mockBus._lineSeq, 3, 'maxSeq (2) + 1 restored to _lineSeq');

            // 2. Turn card grouping and collapsed state
            assertEq(streamEl.children.length, 1, 'one turn card reconstructed');
            const card = streamEl.children[0];
            assertTrue(card.classList.contains('turn-card'), 'child is turn card');
            const body = card.querySelector('.turn-card-body');
            assertTrue(body !== null, 'body exists');
            assertEq(body.style.display, 'none', 'collapsed state restored');

            // 3. Rebound handlers and known actors
            assertTrue(rebindCalled, 'cards.rebindAll was called');
            assertTrue(mockBus._knownActors.has('Arix'), 'Arix added to _knownActors');
            assertTrue(updateFilterCalled, 'updateAgentFilterDropdown called');
            assertTrue(restoreSavedCalled, 'restoreSaved filters called');
        } finally {
            document.getElementById = origGetEl;
            window.storage = origStorage;
        }
    });
})();
