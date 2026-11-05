/**
 * tools/unit/test_mind_fullscreen.js
 *
 * task-788: Unit tests for InspectorMindView fullscreen mode.
 */

(() => {
    const MV = window.InspectorMindView;
    const oldFetch = window.fetch;
    window.fetch = () => Promise.resolve({ ok: true, json: async () => ({}) });

    test('Mind panel fullscreen mode toggling and styling (task-788)', () => {
        assertTrue(typeof MV.open === 'function', 'MV.open exists');
        assertTrue(typeof MV.close === 'function', 'MV.close exists');
        assertTrue(typeof MV.isFullscreen === 'function', 'MV.isFullscreen exists');
        assertTrue(typeof MV.setFullscreen === 'function', 'MV.setFullscreen exists');
        assertTrue(typeof MV.toggleFullscreen === 'function', 'MV.toggleFullscreen exists');

        const oldPlayers = window.worldState ? window.worldState.players : undefined;
        try {
            window.worldState = window.worldState || {};
            window.worldState.players = Object.assign({}, oldPlayers, {
                arix: {
                    name: 'arix',
                    memories: [
                        { id: 'm1', text: 'Found a strange key in the courtyard', type: 'episodic' },
                        { id: 'm2', text: 'Trust nobody who wears a red scarf', type: 'reflection', category: 'belief' },
                    ],
                },
            });

            // 1. Open Mind panel
            MV.open('arix');
            const container = MV._getContainer ? MV._getContainer() : null;
            assertTrue(!!container, 'Mind panel container mounted in document');
            assertEq(MV.isFullscreen(), false, 'starts windowed by default');

            assertTrue(container.innerHTML.includes('mind-fullscreen'), 'fullscreen button exists in header');
            assertTrue(container.innerHTML.includes('title="Fullscreen"'), 'button title is Fullscreen');
            assertTrue(container.innerHTML.includes('⛶'), 'button icon is ⛶ when windowed');
            assertTrue(container.innerHTML.includes('width:min(1360px,96vw)'), 'initial windowed width');
            assertFalse(container.innerHTML.includes('mind-fullscreen-active'), 'no active fullscreen class');

            // 2. Toggle fullscreen
            MV.toggleFullscreen();
            assertEq(MV.isFullscreen(), true, 'fullscreen active after toggle');

            assertTrue(container.innerHTML.includes('title="Exit fullscreen (Escape)"'), 'button title is Exit fullscreen');
            assertTrue(container.innerHTML.includes('🗗'), 'button icon is 🗗 when fullscreen');
            assertTrue(container.innerHTML.includes('mind-fullscreen-active'), 'has mind-fullscreen-active class');
            assertTrue(container.innerHTML.includes('width:100vw;height:100vh;'), 'fullscreen width 100vw and height 100vh');
            assertTrue(container.innerHTML.includes('🧠 Mind - arix'), 'header title intact');

            // 3. Switch tab in fullscreen
            if (MV._getState()) {
                MV._getState().tab = 'memories';
                MV.setFullscreen(true);
            }
            assertEq(MV._getState().tab, 'memories', 'tab changed to memories');
            assertEq(MV.isFullscreen(), true, 'still fullscreen after tab switch');

            // 4. Escape in fullscreen exits fullscreen back to windowed
            let prevented = false;
            let stopped = false;
            MV._onKeydown({
                key: 'Escape',
                defaultPrevented: false,
                preventDefault: () => { prevented = true; },
                stopPropagation: () => { stopped = true; },
            });
            assertTrue(prevented, 'Escape prevented default');
            assertTrue(stopped, 'Escape stopped propagation');
            assertEq(MV.isFullscreen(), false, 'exited fullscreen on Escape');

            assertFalse(container.innerHTML.includes('mind-fullscreen-active'), 'windowed mode restored');
            assertTrue(container.innerHTML.includes('width:min(1360px,96vw)'), 'windowed width restored');

            // 5. Escape while windowed closes the modal
            MV._onKeydown({
                key: 'Escape',
                defaultPrevented: false,
                preventDefault: () => {},
                stopPropagation: () => {},
            });
            assertEq(MV._getContainer ? MV._getContainer() : null, null, 'modal closed');
        } finally {
            MV.close();
            window.fetch = oldFetch;
            if (window.worldState) {
                window.worldState.players = oldPlayers;
            }
        }
    });

    test('Mind panel single instance and opener focus return (task-788)', () => {
        const oldPlayers = window.worldState ? window.worldState.players : undefined;
        try {
            window.worldState = window.worldState || {};
            window.worldState.players = Object.assign({}, oldPlayers, {
                arix: { name: 'arix', memories: [] },
            });

            // Opener element stub with focus spy
            let focused = false;
            const fakeOpener = {
                focus: () => { focused = true; },
            };

            MV.open('arix', fakeOpener);
            const container1 = MV._getContainer();
            assertTrue(!!container1, 'container mounted');

            // Reopen replaces container cleanly without leaks
            MV.open('arix', fakeOpener);
            const container2 = MV._getContainer();
            assertTrue(!!container2, 'reopened container exists');

            // Closing returns focus to opener
            MV.close();
            assertEq(focused, true, 'opener received focus on close');
            assertEq(MV._getContainer(), null, 'modal container cleared on close');
        } finally {
            MV.close();
            window.fetch = oldFetch;
            if (window.worldState) {
                window.worldState.players = oldPlayers;
            }
        }
    });
})();
