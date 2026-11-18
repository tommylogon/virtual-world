/**
 * bug-565 - the room block must describe the acting character's area, not the
 * server's single active-player view. In a multi-agent run those differ, and a
 * wrong area leaks another room's items, people and exits into the prompt.
 */

test('bug-565: the character own area wins over the scene area', () => {
    const state = {
        current_area: 'library',
        areas: { library: { name: 'library' }, foyer: { name: 'foyer' } },
    };
    const player = { current_area: 'foyer' };
    const got = window.PromptBuilder.resolveCharacterArea(state, player, state.areas.library);
    assertEq(got.name, 'foyer', 'prompt follows the character, not state.current_area');
});

test('bug-565: a preview may inspect another area', () => {
    const state = {
        current_area: 'library',
        areas: { library: { name: 'library' }, foyer: { name: 'foyer' } },
    };
    const player = { current_area: 'foyer' };
    const got = window.PromptBuilder.resolveCharacterArea(state, player, state.areas.library, true);
    assertEq(got.name, 'library', 'preview keeps the requested area');
});

test('bug-565: an unknown own area falls back to the requested area', () => {
    const state = {
        current_area: 'library',
        areas: { library: { name: 'library' } },
    };
    const player = { current_area: 'nowhere' };
    const got = window.PromptBuilder.resolveCharacterArea(state, player, state.areas.library);
    assertEq(got.name, 'library', 'no fabricated area');
});

function makePeopleHereState(lightValue, personOverrides = {}, playerOverrides = {}) {
    worldState.data = { time_ticks: 5, areas: { foyer: { name: 'foyer', environment: { light: lightValue } } }, players: {}, graph: { nodes: [], edges: [] } };
    if (typeof worldState.getItemsInArea !== 'function') worldState.getItemsInArea = () => [];
    if (typeof worldState.getCarriedItems !== 'function') worldState.getCarriedItems = () => [];
    if (typeof worldState.getEquippedItems !== 'function') worldState.getEquippedItems = () => ({});
    if (typeof worldState.getNodeByIdentifier !== 'function') worldState.getNodeByIdentifier = () => null;
    if (typeof worldState.getNode !== 'function') worldState.getNode = () => null;
    const player = {
        name: 'Alice',
        current_area: 'foyer',
        relationships: { Bob: { type: 'acquaintance', known: true } },
        traits: {},
        conditions: {},
        ...playerOverrides,
    };
    const area = { name: 'foyer', ambient_light: lightValue, environment: { light: lightValue } };
    const state = {
        current_area: 'foyer',
        areas: { foyer: area },
        players: { Alice: player },
        players_in_area: [
            {
                name: 'Bob',
                state: 'awake',
                description: 'A tall guard in uniform.',
                holding: ['Pistol'],
                wearing: ['Trenchcoat'],
                ...personOverrides,
            },
        ],
    };
    return { state, player, area };
}

test('bug-588: People here renders visible held and worn items cleanly in lit room', () => {
    const { state, player, area } = makePeopleHereState(80);
    const parts = window.PromptBuilder.buildRoomContextParts(state, 'Alice', player, area, false);
    assertTrue(parts.people.includes('People here:'), 'People here header present');
    assertTrue(parts.people.includes('[wearing: Trenchcoat]'), 'worn item rendered');
    assertTrue(parts.people.includes('[holding: Pistol]'), 'held item rendered');
    assertTrue(parts.people.includes('A tall guard in uniform.'), 'appearance prose intact');
});

test('bug-588: People here gates held and worn items in dim and pitch_black light', () => {
    for (const light of [30, 10]) {
        const { state, player, area } = makePeopleHereState(light);
        const parts = window.PromptBuilder.buildRoomContextParts(state, 'Alice', player, area, false);
        assertFalse(parts.people.includes('Pistol'), `held item hidden at light=${light}`);
        assertFalse(parts.people.includes('Trenchcoat'), `worn item hidden at light=${light}`);
    }
});

test('bug-588: People here hides held and worn items when blind, reveals with dark_vision in dim', () => {
    const blindCtx = makePeopleHereState(80, {}, { conditions: { blind: true } });
    const blindParts = window.PromptBuilder.buildRoomContextParts(blindCtx.state, 'Alice', blindCtx.player, blindCtx.area, false);
    assertFalse(blindParts.people.includes('Pistol'), 'held item hidden when blind');

    const dvCtx = makePeopleHereState(30, {}, { traits: { dark_vision: true } });
    const dvParts = window.PromptBuilder.buildRoomContextParts(dvCtx.state, 'Alice', dvCtx.player, dvCtx.area, false);
    assertTrue(dvParts.people.includes('[holding: Pistol]'), 'dark_vision reveals held item in dim light');
});
