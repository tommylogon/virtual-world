/**
 * tools/unit/test_turn_you_strip.js
 *
 * Unit tests for TurnYouStrip chip display names and durability separator (task-682).
 */

const YS = window.TurnYouStrip;

window.VitalColor = {
    percent: () => 100,
    suffix: () => '',
    bar: () => '#57c98f'
};

test('TurnYouStrip durabilityLabel detects broken items via state or uses', () => {
    assertEq(YS.durabilityLabel({ current_state: 'broken' }), 'broken', 'detects broken state');
    assertEq(YS.durabilityLabel({ uses: 0, max_uses: 5 }), 'broken', 'detects 0 uses as broken');
    assertEq(YS.durabilityLabel({ uses: 1, max_uses: 10 }), 'about to break', 'detects low ratio');
    assertEq(YS.durabilityLabel({ uses: 10, max_uses: 10 }), 'pristine', 'detects pristine');
    assertEq(YS.durabilityLabel({ current_state: 'normal', uses: -1, max_uses: -1 }), '', 'unlimited item has no durability label');
});

test('TurnYouStrip renders item chips with readable separator between name and broken state', () => {
    const host = document.createElement('div');
    const you = {
        name: 'Tester',
        vitals: { HP: 100, Energy: 80 },
        carrying: [
            {
                name: 'energy drink',
                current_state: 'broken'
            },
            {
                name: 'calling_cards',
                display_name: 'calling cards'
            }
        ],
        wearing: []
    };

    const handlers = {
        menu: () => {},
        apply: () => {},
        reactDraft: () => {}
    };

    YS.render(host, you, handlers);

    // host.children[0] is row1 (vitals), host.children[1] is row2 (inventory)
    const row2 = host.children[1];
    assertTrue(!!row2, 'row2 rendered');

    // Filter children for tys-inv buttons
    const invButtons = (row2.children || []).filter(c => c.className && c.className.includes('tys-inv'));
    assertEq(invButtons.length, 2, 'renders 2 carrying chips');

    const firstChip = invButtons[0];
    const durTag = (firstChip.children || []).find(c => c.className === 'tys-dur');
    assertTrue(!!durTag, 'durability tag rendered inside chip');
    assertEq(durTag.textContent, ' - broken', 'durability tag has leading separator');
    assertEq(firstChip.textContent, 'energy drink', 'base chip text is item name');

    const secondChip = invButtons[1];
    assertEq(secondChip.textContent, 'calling cards', 'prefers display_name over raw snake_case name');
});
