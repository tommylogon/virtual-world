/**
 * task-352 — the client tier mirror (agent/action-tiers.js) must classify verbs
 * the same way engine/action_tiers.py does, and `canPay` must reproduce
 * `spend_slot`'s downgrade (a higher slot pays for a lower action). The turn
 * prompt hides verbs `canAfford` rejects, so a wrong answer here hides a verb
 * the character could still pay for (or shows one it cannot).
 *
 * The table itself is guarded against drift by tools/action_tiers_index.py
 * --check; these tests pin the *resolution logic* the generator hand-writes.
 */

test('tierOf reads the table for ordinary verbs', () => {
    assertEq(ActionTiers.tierOf('take'), 'major', 'take is major');
    assertEq(ActionTiers.tierOf('approach'), 'minor', 'approach is minor');
    assertEq(ActionTiers.tierOf('look'), 'free', 'look is free');
    assertEq(ActionTiers.tierOf('wait'), 'activity', 'wait is an activity');
    assertEq(ActionTiers.tierOf('some unknown verb'), 'major', 'unknown defaults to major');
});

test('tierOf honours a per-item action_costs override', () => {
    const props = { action_costs: { use: { tier: 'free' } } };
    assertEq(ActionTiers.tierOf('use', props), 'free', 'override wins over the table');
    assertEq(ActionTiers.tierOf('take', props), 'major', 'other verbs keep the table tier');
});

test('tierOf treats an intrinsic ability as minor (engine default)', () => {
    assertEq(ActionTiers.tierOf('use', { tags: ['spell'] }), 'minor', 'spell-tagged use is minor');
    assertEq(ActionTiers.tierOf('use', { tags: 'ability, fire' }), 'minor', 'comma-string tags parse');
    assertEq(ActionTiers.tierOf('use', { tags: ['food'] }), 'major', 'non-ability keeps the table tier');
});

test('canPay downgrades: a higher slot pays for a lower action', () => {
    assertTrue(ActionTiers.canPay({ major: 1, minor: 0, free: 0 }, 'minor'), 'major slot pays a minor');
    assertTrue(ActionTiers.canPay({ major: 1, minor: 0, free: 0 }, 'free'), 'major slot pays a free');
    assertFalse(ActionTiers.canPay({ major: 0, minor: 1, free: 3 }, 'major'), 'a minor slot cannot pay a major');
    assertTrue(ActionTiers.canPay({ major: 0, minor: 1, free: 3 }, 'minor'), 'exact slot pays');
});

test('canPay keeps activity its own slot (no downgrade)', () => {
    assertTrue(ActionTiers.canPay({ major: 1, minor: 1, free: 3, activity: 1 }, 'activity'), 'activity slot present');
    assertFalse(ActionTiers.canPay({ major: 1, minor: 1, free: 3, activity: 0 }, 'activity'), 'a major slot cannot pay activity');
});

test('canAfford hides only what the budget cannot pay, and never hides with no budget', () => {
    const emptyButFree = { major: 0, minor: 0, free: 1, activity: 0 };
    assertFalse(ActionTiers.canAfford('take', null, emptyButFree), 'no major left hides take');
    assertFalse(ActionTiers.canAfford('approach', null, emptyButFree), 'no minor (and no major) hides approach');
    assertTrue(ActionTiers.canAfford('look', null, emptyButFree), 'a free slot still buys look');
    assertTrue(ActionTiers.canAfford('take', null, null), 'no budget published -> never hide');
    assertTrue(ActionTiers.canAfford('take', null, undefined), 'undefined budget -> never hide');
});
