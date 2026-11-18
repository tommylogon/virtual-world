/**
 * tools/unit/test_mind_what_i_see.js
 *
 * bug-607: Unit tests for InspectorMindView._whatISeeHtml perception parity -
 * hidden items, lighting/blindness rules, hidden/stealthed actors, and unmet
 * stranger name masking.
 */

(() => {
    const MV = window.InspectorMindView;

    function withMockWorld(worldObj, fn) {
        const prevWorldState = window.worldState;
        try {
            window.worldState = worldObj;
            return fn();
        } finally {
            window.worldState = prevWorldState;
        }
    }

    test('_whatISeeHtml excludes hidden items unless known and respects lighting/blindness (bug-607)', () => {
        assertTrue(typeof MV._whatISeeHtml === 'function', 'MV._whatISeeHtml exists');

        const baseItems = [
            { id: 'item_crate', name: 'heavy wooden crate', properties: { weight: 20, current_state: 'idle' } },
            { id: 'item_key', name: 'brass key', properties: { weight: 1, current_state: 'idle' } },
            { id: 'item_trapdoor', name: 'secret trapdoor', properties: { weight: 15, current_state: 'hidden' } },
            { id: 'item_latch', name: 'concealed latch', hidden: true, weight: 2 },
            { id: 'item_stash', name: 'known stash', properties: { weight: 2, current_state: 'hidden' } },
        ];

        const makeWorld = (light, playerExtras = {}) => {
            const data = {
                areas: {
                    Cellar: {
                        name: 'Cellar',
                        description: 'A damp stone cellar.',
                        ambient_light: light,
                        items: baseItems,
                    },
                },
                players: {
                    Alice: Object.assign({
                        name: 'Alice',
                        current_area: 'Cellar',
                        known: ['item_stash'],
                        met: [],
                    }, playerExtras),
                },
            };
            return {
                data,
                areas: data.areas,
                players: data.players,
            };
        };

        // Normal light (50): non-hidden items + authored known hidden item visible; unknown hidden items excluded
        withMockWorld(makeWorld(50), () => {
            const html = MV._whatISeeHtml('Alice');
            assertTrue(html.includes('heavy wooden crate'), 'Normal light shows crate');
            assertTrue(html.includes('brass key'), 'Normal light shows key');
            assertTrue(html.includes('known stash'), 'Authored known hidden item is visible');
            assertFalse(html.includes('secret trapdoor'), 'Hidden item (current_state=hidden) excluded');
            assertFalse(html.includes('concealed latch'), 'Hidden item (hidden=true) excluded');
        });

        // Dim light (30): only weight >= 3 visible
        withMockWorld(makeWorld(30), () => {
            const html = MV._whatISeeHtml('Alice');
            assertTrue(html.includes('heavy wooden crate'), 'Dim light shows heavy crate');
            assertFalse(html.includes('brass key'), 'Dim light hides small key');
            assertFalse(html.includes('secret trapdoor'), 'Dim light excludes hidden trapdoor');
        });

        // Pitch black (10 and 0): no items visible without dark_vision
        for (const darkLight of [10, 0]) {
            withMockWorld(makeWorld(darkLight), () => {
                const html = MV._whatISeeHtml('Alice');
                assertFalse(html.includes('heavy wooden crate'), `Pitch black (${darkLight}) hides crate`);
                assertFalse(html.includes('brass key'), `Pitch black (${darkLight}) hides key`);
                assertFalse(html.includes('Items:'), `Pitch black (${darkLight}) omits Items line`);
            });
        }

        // Pitch black with dark_vision: non-hidden items visible, hidden still excluded
        withMockWorld(makeWorld(10, { traits: { dark_vision: true } }), () => {
            const html = MV._whatISeeHtml('Alice');
            assertTrue(html.includes('heavy wooden crate'), 'Dark vision sees crate');
            assertTrue(html.includes('brass key'), 'Dark vision sees key');
            assertFalse(html.includes('secret trapdoor'), 'Dark vision still excludes hidden trapdoor');
        });

        // Blind: only previously seen non-hidden items visible
        withMockWorld(makeWorld(80, {
            conditions: { blind: true },
            memory_index: { item_key: { tick: 1 } },
        }), () => {
            const html = MV._whatISeeHtml('Alice');
            assertTrue(html.includes('brass key'), 'Blind character remembers examined key');
            assertFalse(html.includes('heavy wooden crate'), 'Blind character does not see unexamined crate');
            assertFalse(html.includes('secret trapdoor'), 'Blind character does not see hidden trapdoor');
        });
    });

    test('_whatISeeHtml excludes hidden/stealthed NPCs and masks unmet stranger real names (bug-607)', () => {
        const players = {
            Alice: {
                name: 'Alice',
                current_area: 'Lobby',
                met: ['Bob'],
                known: [],
            },
            Bob: {
                name: 'Bob',
                current_area: 'Lobby',
                state: 'awake',
                description: 'A cheerful clerk in a blue vest.',
                tags: ['male'],
            },
            MarcusVance: {
                name: 'MarcusVance',
                current_area: 'Lobby',
                state: 'awake',
                description: 'A tall man in a torn trench coat. He looks exhausted.',
            },
            ElenaRostova: {
                name: 'ElenaRostova',
                current_area: 'Lobby',
                state: 'awake',
                description: 'A sharp-eyed detective.',
                tags: ['woman'],
            },
            ShadowRogue: {
                name: 'ShadowRogue',
                current_area: 'Lobby',
                state: 'stealthed',
                description: 'A cloaked figure.',
            },
            HiddenSpy: {
                name: 'HiddenSpy',
                current_area: 'Lobby',
                state: 'hidden',
                description: 'A silent observer.',
            },
            FlaggedSneak: {
                name: 'FlaggedSneak',
                current_area: 'Lobby',
                hidden: true,
                description: 'A crouching figure.',
            },
        };

        const data = {
            current_area: 'Lobby',
            areas: {
                Lobby: { name: 'Lobby', description: 'A bright hotel lobby.', ambient_light: 60, items: [] },
            },
            players,
        };

        withMockWorld({
            data,
            areas: data.areas,
            players: data.players,
            hasMet: (viewer, target) => Array.isArray(data.players[viewer]?.met) && data.players[viewer].met.includes(target),
        }, () => {
            const html = MV._whatISeeHtml('Alice');
            assertTrue(html.includes('Bob'), 'Met character keeps real name');
            assertFalse(html.includes('MarcusVance'), 'Unmet stranger real name (MarcusVance) must not leak');
            assertFalse(html.includes('ElenaRostova'), 'Unmet stranger real name (ElenaRostova) must not leak');
            assertTrue(html.includes('the tall man in a torn trench coat'), 'Unmet stranger without speaker tag uses masked description');
            assertTrue(html.includes('the woman'), 'Unmet stranger with woman tag uses masked tag label');
            assertFalse(html.includes('ShadowRogue'), 'Stealthed player must be excluded');
            assertFalse(html.includes('HiddenSpy'), 'Hidden state player must be excluded');
            assertFalse(html.includes('FlaggedSneak'), 'hidden=true player must be excluded');
        });
    });

    test('_whatISeeHtml respects players_in_area snapshot when area matches and falls back otherwise (bug-607)', () => {
        const players = {
            Alice: { name: 'Alice', current_area: 'Lobby', met: [], known: [] },
            Bob: { name: 'Bob', current_area: 'Cellar', met: [], known: [] },
            VictorKrum: { name: 'VictorKrum', current_area: 'Lobby', description: 'A brooding violinist.', tags: ['man'] },
            Lurker: { name: 'Lurker', current_area: 'Lobby', state: 'stealthed', description: 'Unseen.' },
            CellarDweller: { name: 'CellarDweller', current_area: 'Cellar', description: 'A pale caretaker.' },
            CellarGhost: { name: 'CellarGhost', current_area: 'Cellar', state: 'hidden', description: 'A ghost.' },
        };

        const data = {
            current_area: 'Lobby',
            areas: {
                Lobby: { name: 'Lobby', description: 'Lobby.', ambient_light: 60, items: [] },
                Cellar: { name: 'Cellar', description: 'Cellar.', ambient_light: 60, items: [] },
            },
            players,
            players_in_area: [
                { name: 'VictorKrum', state: 'awake', description: 'A brooding violinist.' },
                { name: 'Lurker', state: 'stealthed', description: 'Unseen.' },
            ],
        };

        withMockWorld({
            data,
            areas: data.areas,
            players: data.players,
        }, () => {
            // Alice is in Lobby (matches snapshot current_area)
            const aliceHtml = MV._whatISeeHtml('Alice');
            assertFalse(aliceHtml.includes('VictorKrum'), 'Snapshot stranger real name must not leak');
            assertTrue(aliceHtml.includes('the man'), 'Snapshot stranger masked via PromptBuilder.anonymousName');
            assertFalse(aliceHtml.includes('Lurker'), 'Stealthed actor in snapshot is excluded');

            // Bob is in Cellar (does NOT match Lobby snapshot) - falls back to worldState.players
            const bobHtml = MV._whatISeeHtml('Bob');
            assertFalse(bobHtml.includes('VictorKrum'), 'Lobby snapshot must not bleed into Cellar character');
            assertFalse(bobHtml.includes('CellarDweller'), 'Cellar stranger real name must not leak');
            assertTrue(bobHtml.includes('the pale caretaker'), 'Cellar stranger is masked');
            assertFalse(bobHtml.includes('CellarGhost'), 'Hidden Cellar character is excluded');
        });
    });
})();
