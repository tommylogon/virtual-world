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
