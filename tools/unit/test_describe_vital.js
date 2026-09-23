/**
 * Unit tests for describeVital — per-vital natural language (task-337).
 *
 * Hunger/Thirst expectations were updated for the Maslow changes (task-425/432):
 * the physiological tiers now end in an imperative moodlet — "EAT your X" when
 * something is carried, "FIND SOMETHING TO EAT NOW" when nothing is — and bend to
 * a hostile presence in the room. The older prose tails ("Your stomach feels
 * empty.") are gone; do not restore them.
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
    assertEq(PB.describeVital({ Hunger: 30 }, 'Hunger'), 'You are hungry. FIND SOMETHING TO EAT NOW.', 'mild hunger');
    assertEq(PB.describeVital({ Hunger: 60 }, 'Hunger'), 'You are very hungry and it is draining you. FIND SOMETHING TO EAT NOW.', 'urgent hunger');
    assertEq(PB.describeVital({ Hunger: 100 }, 'Hunger'), 'You are STARVING — your body cannot hold you up. FIND SOMETHING TO EAT NOW.', 'starving');
});

test('describeVital Hunger names the carried item, and a threat outranks eating', () => {
    assertEq(
        PB.describeVital({ Hunger: 60 }, 'Hunger', { carriedFood: ['granola_bar'] }),
        'You are very hungry and it is draining you. EAT your granola_bar.',
        'names the carried food',
    );
    assertEq(
        PB.describeVital({ Hunger: 30 }, 'Hunger', { hasThreat: true }),
        'You are hungry. FIND SOMETHING TO EAT NOW (but a hostile presence is in the room — flee/defend first, eat only if safe).',
        'threat qualifier',
    );
});

test('describeVital Thirst drive: low=hydrated, high=deadly', () => {
    assertEq(PB.describeVital({ Thirst: 5 }, 'Thirst'), '', 'hydrated');
    assertEq(PB.describeVital({ Thirst: 30 }, 'Thirst'), 'You are thirsty. FIND SOMETHING TO DRINK NOW.', 'mild thirst');
    assertEq(PB.describeVital({ Thirst: 80 }, 'Thirst'), 'You are very thirsty and it is draining you. FIND SOMETHING TO DRINK NOW.', 'urgent thirst');
    assertEq(PB.describeVital({ Thirst: 100 }, 'Thirst'), 'You are DYING of thirst — your throat is cracked and dry. FIND SOMETHING TO DRINK NOW.', 'dying');
});

test('describeVital Thirst prefers a named drink over the generic imperative', () => {
    assertEq(
        PB.describeVital({ Thirst: 30 }, 'Thirst', { carriedDrink: ['water_bottle'] }),
        'You are thirsty. DRINK your water_bottle.',
        'names the carried drink',
    );
});

test('describeVital Bladder drive: low=relieved, high=bursting', () => {
    assertEq(PB.describeVital({ Bladder: 5 }, 'Bladder'), '', 'relieved');
    assertEq(PB.describeVital({ Bladder: 70 }, 'Bladder'), 'You could use a bathroom soon. A mild pressure builds.', 'mild');
    assertEq(PB.describeVital({ Bladder: 95 }, 'Bladder'), 'You are about to burst — you desperately need a bathroom.', 'urgent');
});

test('describeVital Energy: 0=collapse, low=exhausted, high=fine', () => {
    assertEq(PB.describeVital({ Energy: 0 }, 'Energy'), 'You are collapsing from exhaustion — your legs buckle and your vision blurs.', 'zero energy');
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
