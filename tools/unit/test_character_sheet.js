/**
 * tools/unit/test_character_sheet.js
 *
 * task-733: Full-page character sheet, persona view, and person compiler integration.
 */

var PV = window.InspectorPersonaView;
var AV = window.InspectorAgentView;
window.worldState = window.worldState || {};
window.worldState.getNode = window.worldState.getNode || (() => null);

test('InspectorPersonaView declares weaknesses tone as danger', () => {
    assertTrue(!!PV, 'InspectorPersonaView is defined');
    assertEq(PV._PERSONA_TONES.weaknesses, 'danger', 'weaknesses tone is danger');
    assertEq(PV._PERSONA_TONES.fears, 'danger', 'fears tone is danger');
    assertEq(PV._PERSONA_TONES.interests, 'info', 'interests tone is info');
});

test('InspectorAgentView Bio tab offers Character Sheet authoring navigation', () => {
    assertTrue(!!AV, 'InspectorAgentView is defined');
    const player = {
        name: 'Alden',
        personality: 'Quiet observer',
        base_description: 'Tall, lean',
        skills: { Perception: 2 },
        traits: { observant: true },
    };
    const bioHtml = AV._renderBioTab('Alden', player, {}, null, 'Alden', false, '#bc8cff', false);
    assertTrue(bioHtml.includes('Character Sheet'), 'compact Bio tab has Character Sheet banner');
    assertTrue(bioHtml.includes("InspectorAgentView._switchAgentTab('Persona')"), 'wired to Persona tab switch');

    const fullBioHtml = AV._renderBioTab('Alden', player, {}, null, 'Alden', false, '#bc8cff', true);
    assertTrue(fullBioHtml.includes('Character Sheet'), 'full-surface Bio rail has Character Sheet link');
});

test('InspectorPersonaView renders Capabilities fold when bound with capabilities schema', () => {
    const fakeContainer = {
        id: 'mind-persona',
        replaceChildren: () => {},
        querySelector: () => null,
        querySelectorAll: () => [],
    };
    const mockState = {
        charName: 'Alden',
        escName: 'Alden',
        tab: 'Persona',
        persona: {
            status: 'ok',
            record: {
                identity: { pronouns: 'they/them', age: 31 },
                capabilities: { skills: ['Stealth'], weaknesses: ['clumsy'] },
            },
            schema: {
                properties: {
                    identity: { properties: { pronouns: {}, age: {} } },
                    appearance: { properties: {} },
                    personality: { properties: {} },
                    capabilities: { properties: { skills: {}, languages: {}, weaknesses: {} } },
                    narrative: { properties: {} },
                },
            },
            openSections: ['Capabilities'],
            hints: {},
            suggestions: {},
            stale: false,
            dirty: false,
            preview: null,
            msg: '',
            warnings: [],
            dollFacing: 'front',
        },
    };
    PV.bind(mockState, fakeContainer);
    const html = PV.html();
    assertTrue(html.includes('Capabilities'), 'renders Capabilities fold in persona form');
    assertTrue(html.includes('data-fold="Capabilities"'), 'declares Capabilities fold container');
    PV.unbind();
});
