/**
 * test_simultaneous.js — the turn-mode dial vocabulary (task-101).
 *
 * Covers mode normalisation (including the legacy boolean), the act countdown,
 * and the per-room grouping/readiness used by "simultaneous per room".
 */

test('simultaneous: isSimultaneous covers both variants only', () => {
    assertTrue(VWSimultaneous.isSimultaneous('simultaneous'));
    assertTrue(VWSimultaneous.isSimultaneous('simultaneous_room'));
    assertFalse(VWSimultaneous.isSimultaneous('sequential'));
    assertFalse(VWSimultaneous.isSimultaneous('random'));
    assertFalse(VWSimultaneous.isSimultaneous('initiative'));
    assertFalse(VWSimultaneous.isSimultaneous(''));
});

test('simultaneous: isRoomMode only matches the per-room variant', () => {
    assertTrue(VWSimultaneous.isRoomMode('simultaneous_room'));
    assertFalse(VWSimultaneous.isRoomMode('simultaneous'));
    assertFalse(VWSimultaneous.isRoomMode('sequential'));
});

test('simultaneous: normalizeMode folds the legacy boolean', () => {
    assertEq(VWSimultaneous.normalizeMode('true'), 'simultaneous');
    assertEq(VWSimultaneous.normalizeMode(true), 'simultaneous');
    assertEq(VWSimultaneous.normalizeMode('simultaneous_room'), 'simultaneous_room');
    assertEq(VWSimultaneous.normalizeMode('simultaneous'), 'simultaneous');
    assertEq(VWSimultaneous.normalizeMode('initiative'), 'initiative');
    assertEq(VWSimultaneous.normalizeMode('random'), 'random');
});

test('simultaneous: normalizeMode falls back to the ordered mode', () => {
    assertEq(VWSimultaneous.normalizeMode(undefined, 'initiative'), 'initiative');
    assertEq(VWSimultaneous.normalizeMode('nonsense', 'random'), 'random');
    assertEq(VWSimultaneous.normalizeMode(undefined, undefined), 'sequential');
    assertEq(VWSimultaneous.normalizeMode('nonsense', 'simultaneous'), 'sequential');
});

test('simultaneous: cooldownFor derives from Social, traits and Energy', () => {
    assertEq(VWSimultaneous.cooldownFor(null), 8);
    assertEq(VWSimultaneous.cooldownFor({ vitals: { Social: 50, Energy: 100 } }), 8);
    assertEq(VWSimultaneous.cooldownFor({ vitals: { Social: 0, Energy: 100 } }), 10);
    assertEq(VWSimultaneous.cooldownFor({ vitals: { Social: 100, Energy: 100 } }), 6);
    assertEq(VWSimultaneous.cooldownFor({ vitals: { Energy: 100 }, traits: { impatient: true } }), 6);
    assertEq(VWSimultaneous.cooldownFor({ vitals: { Energy: 100 }, traits: { patient: true } }), 10);
    assertEq(VWSimultaneous.cooldownFor({ vitals: { Energy: 100 }, traits: { sprinter: true } }), 7);
    assertEq(VWSimultaneous.cooldownFor({ vitals: { Social: 50, Energy: 20 } }), 9);
});

test('simultaneous: cooldownFor clamps to 3..15', () => {
    assertEq(
        VWSimultaneous.cooldownFor({
            vitals: { Social: 100, Energy: 100 },
            traits: { impatient: true, sprinter: true },
        }),
        3
    );
    assertEq(
        VWSimultaneous.cooldownFor({ vitals: { Social: 0, Energy: 10 }, traits: { patient: true } }),
        13
    );
});

test('simultaneous: groupByRoom filters and sorts within a room', () => {
    const players = {
        Zed: { current_area: 'Hall', state: 'awake' },
        Amy: { current_area: 'Hall', state: 'awake' },
        Bob: { current_area: 'Yard', state: 'awake' },
        Dead: { current_area: 'Hall', state: 'dead' },
        Human: { current_area: 'Hall', state: 'awake' },
    };
    const rooms = VWSimultaneous.groupByRoom(players, {
        isAutonomous: name => name !== 'Human',
        ghostMode: false,
    });
    assertEq(rooms, { Hall: ['Amy', 'Zed'], Yard: ['Bob'] });
});

test('simultaneous: ghost mode admits the dead', () => {
    const players = { Dead: { current_area: 'Hall', state: 'dead' } };
    assertEq(VWSimultaneous.groupByRoom(players, { ghostMode: false }), {});
    assertEq(VWSimultaneous.groupByRoom(players, { ghostMode: true }), { Hall: ['Dead'] });
});

test('simultaneous: roomCooldown is the fastest member', () => {
    const players = {
        Fast: { vitals: { Social: 100, Energy: 100 } },
        Slow: { vitals: { Social: 0, Energy: 10 }, traits: { patient: true } },
    };
    assertEq(VWSimultaneous.roomCooldown(['Fast', 'Slow'], players), 6);
    assertEq(VWSimultaneous.roomCooldown([], players), 8);
});

test('simultaneous: firstReadyRoom picks the first elapsed room in roster order', () => {
    const rooms = { Hall: ['Amy'], Yard: ['Bob'] };
    assertEq(VWSimultaneous.firstReadyRoom(rooms, { Hall: 3, Yard: 0 }), 'Yard');
    assertEq(VWSimultaneous.firstReadyRoom(rooms, { Hall: 0, Yard: 0 }), 'Hall');
    assertEq(VWSimultaneous.firstReadyRoom(rooms, { Hall: 3, Yard: 2 }), null);
    assertEq(VWSimultaneous.firstReadyRoom(rooms, {}), 'Hall');
});

test('simultaneous: tickCountdowns decrements positives only', () => {
    const countdowns = { a: 0, b: 2 };
    VWSimultaneous.tickCountdowns(countdowns);
    assertEq(countdowns, { a: 0, b: 1 });
    VWSimultaneous.tickCountdowns(countdowns);
    assertEq(countdowns, { a: 0, b: 0 });
    VWSimultaneous.tickCountdowns(countdowns);
    assertEq(countdowns, { a: 0, b: 0 });
});
