'use strict';

test('a coalesced state fetch resolves after the trailing refresh', async () => {
    const state = new WorldState();
    const originalFetch = window.fetch;
    let requestCount = 0;
    let resolveFirst;
    window.fetch = () => {
        requestCount += 1;
        if (requestCount === 1) {
            return new Promise(resolve => { resolveFirst = resolve; });
        }
        return Promise.resolve({
            json: async () => ({
                players: {
                    Explorer: {
                        turn_slots: { major: 0, minor: 1, free: 3, activity: 1 }
                    }
                }
            })
        });
    };

    try {
        const initialFetch = state.fetch();
        await Promise.resolve();
        const afterActionFetch = state.fetch();
        resolveFirst({
            json: async () => ({
                players: {
                    Explorer: {
                        turn_slots: { major: 1, minor: 1, free: 3, activity: 1 }
                    }
                }
            })
        });

        const freshState = await afterActionFetch;
        await initialFetch;
        assertEq(requestCount, 2, 'one trailing state request ran');
        assertEq(freshState.players.Explorer.turn_slots,
            { major: 0, minor: 1, free: 3, activity: 1 },
            'callers receive the post-action slot budget');
    } finally {
        if (originalFetch === undefined) delete window.fetch;
        else window.fetch = originalFetch;
    }
});
