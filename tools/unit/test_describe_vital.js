/**
 * Unit tests for describeVital - per-vital natural language (task-337 / task-905).
 *
 * Qualitative physical sensations without arcade imperative barks (task-905).
 */
'use strict';
const PB = window.PromptBuilder;

test('describeVital returns empty for missing or healthy vitals', () => {
    assertEq(PB.describeVital({}, 'Hunger'), '', 'missing vital');
    assertEq(PB.describeVital({ Hunger: 20 }, 'Thirst'), '', 'healthy drive');
    assertEq(PB.describeVital({ Energy: 80 }, 'Energy'), '', 'healthy energy');
    assertEq(PB.describeVital({ Sanity: 90 }, 'Sanity'), '', 'healthy sanity');
    assertEq(PB.describeVital({ Bladder: 30 }, 'Bladder'), '', 'relieved bladder');
});

test('describeVital Hunger drive: low=fed, high=starving', () => {
    assertEq(PB.describeVital({ Hunger: 5 }, 'Hunger'), '', 'well-fed');
    assertEq(PB.describeVital({ Hunger: 30 }, 'Hunger'), 'You are hungry. Your stomach grumbles for food.', 'mild hunger');
    assertEq(PB.describeVital({ Hunger: 60 }, 'Hunger'), 'You are very hungry; your stomach aches with a gnawing, hollow pang.', 'urgent hunger');
    assertEq(PB.describeVital({ Hunger: 100 }, 'Hunger'), 'You are starving - your body trembles with weakness and your stomach aches hollow.', 'starving');
});

test('describeVital Hunger names the carried item, and a threat outranks eating', () => {
    assertEq(
        PB.describeVital({ Hunger: 60 }, 'Hunger', { carriedFood: ['granola_bar'] }),
        'You are very hungry and your energy is flagging - you have granola_bar with you.',
        'names the carried food',
    );
    assertEq(
        PB.describeVital({ Hunger: 30 }, 'Hunger', { hasThreat: true }),
        'You are hungry. Your stomach grumbles for food (a hostile presence is in the room).',
        'threat qualifier',
    );
});

test('describeVital Thirst drive: low=hydrated, high=deadly', () => {
    assertEq(PB.describeVital({ Thirst: 5 }, 'Thirst'), '', 'hydrated');
    assertEq(PB.describeVital({ Thirst: 30 }, 'Thirst'), 'You are thirsty. Your throat feels dry.', 'mild thirst');
    assertEq(PB.describeVital({ Thirst: 80 }, 'Thirst'), 'You are very thirsty; your throat is dry and parched.', 'urgent thirst');
    assertEq(PB.describeVital({ Thirst: 100 }, 'Thirst'), 'You are desperately dehydrated - your mouth is like sandpaper and your throat is cracked and dry.', 'dying');
});

test('describeVital Thirst prefers a named drink over the generic imperative', () => {
    assertEq(
        PB.describeVital({ Thirst: 30 }, 'Thirst', { carriedDrink: ['water_bottle'] }),
        'You are thirsty - you have water_bottle with you.',
        'names the carried drink',
    );
});

test('describeVital Bladder drive: low=relieved, high=bursting', () => {
    assertEq(PB.describeVital({ Bladder: 5 }, 'Bladder'), '', 'relieved');
    assertEq(PB.describeVital({ Bladder: 70 }, 'Bladder'), 'You could use a bathroom soon. A mild pressure builds.', 'mild');
    assertEq(PB.describeVital({ Bladder: 95 }, 'Bladder'), 'You are about to burst - you desperately need a bathroom.', 'urgent');
});

test('describeVital Energy: 0=collapse, low=exhausted, high=fine', () => {
    assertEq(PB.describeVital({ Energy: 0 }, 'Energy'), 'You are collapsing from exhaustion - your legs buckle and your vision blurs.', 'zero energy');
    assertEq(PB.describeVital({ Energy: 10 }, 'Energy'), 'You are exhausted. Every movement feels heavy.', 'low energy');
    assertEq(PB.describeVital({ Energy: 40 }, 'Energy'), 'You are getting tired. A yawn escapes you.', 'tired');
    assertEq(PB.describeVital({ Energy: 80 }, 'Energy'), '', 'fine');
});

test('describeVitals stays in sync with describeVital', () => {
    const player = { vitals: { Energy: 10, Hunger: 80, Thirst: 95, Sanity: 90, Social: 60, Bladder: 50 } };
    const combined = PB.describeVitals(player);
    assertTrue(combined.includes(PB.describeVital(player.vitals, 'Energy')), 'includes energy desc');
    assertTrue(combined.includes(PB.describeVital(player.vitals, 'Hunger')), 'includes hunger desc');
    assertTrue(combined.includes(PB.describeVital(player.vitals, 'Thirst')), 'includes thirst desc');
});
