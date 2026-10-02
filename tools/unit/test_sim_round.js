// tests for agent/sim-round.js — simultaneous round completion (task-533)
'use strict';

const R = VWSimRound;

test('participants includes the human alongside autonomous characters', () => {
    const roster = R.participants({
        Jake: { state: 'alive' },
        Zoe: { state: 'alive' },
    });
    assertEq(roster.sort(), ['Jake', 'Zoe'], 'both participants count');
});

test('participants excludes the dead by default', () => {
    const roster = R.participants({
        Jake: { state: 'alive' },
        Zoe: { state: 'dead' },
    });
    assertEq(roster, ['Jake'], 'a dead character owes no turn');
});

test('participants includes the dead under ghostMode', () => {
    const roster = R.participants({
        Jake: { state: 'alive' },
        Zoe: { state: 'dead' },
    }, { ghostMode: true });
    assertEq(roster.sort(), ['Jake', 'Zoe'], 'ghostMode keeps the dead in');
});

test('participants skips a name with no player record', () => {
    const roster = R.participants({ Jake: { state: 'alive' }, Ghost: null });
    assertEq(roster, ['Jake'], 'null player is not a participant');
});

test('a round is not complete until every participant has gone', () => {
    const roster = ['Jake', 'Zoe'];
    assertFalse(R.isComplete(roster, ['Jake']), 'one short is not complete');
    assertTrue(R.isComplete(roster, ['Jake', 'Zoe']), 'all gone is complete');
});

test('the human holds the round open', () => {
    // The whole point: an autonomous-only round would have completed here and
    // advanced the world while the player still had their turn to take.
    const roster = ['Jake', 'Zoe'];
    assertFalse(R.isComplete(roster, ['Jake']), 'autonomics done, human pending');
});

test('an empty roster is not complete', () => {
    // Otherwise the loop would close a round every iteration and spin the clock.
    assertFalse(R.isComplete([], []), 'nobody to advance for');
    assertFalse(R.isComplete(null, ['Jake']), 'null roster is not complete');
});

test('isComplete accepts a Set as well as an array', () => {
    assertTrue(R.isComplete(['Jake', 'Zoe'], new Set(['Jake', 'Zoe'])), 'Set input');
    assertFalse(R.isComplete(['Jake', 'Zoe'], new Set(['Jake'])), 'Set short');
});

test('resolved names outside the roster do not complete the round', () => {
    const roster = ['Jake'];
    assertTrue(R.isComplete(roster, ['Jake', 'Zoe']), 'extras are ignored');
});

test('pendingFor reports exactly who still owes a turn', () => {
    assertEq(R.pendingFor(['Jake', 'Zoe'], ['Jake']), ['Zoe'], 'one pending');
    assertEq(R.pendingFor(['Jake', 'Zoe'], ['Jake', 'Zoe']), [], 'none pending');
});

test('markResolved adds to a Set and tolerates junk', () => {
    const set = new Set();
    R.markResolved(set, 'Jake');
    assertTrue(set.has('Jake'), 'marked');
    R.markResolved(set, '');
    assertEq(set.size, 1, 'an empty name is not marked');
    R.markResolved(null, 'Zoe');
    assertTrue(true, 'a null set does not throw');
});

test('a two-round cycle resets cleanly', () => {
    const roster = ['Jake', 'Zoe'];
    let resolved = new Set();
    R.markResolved(resolved, 'Jake');
    assertFalse(R.isComplete(roster, resolved), 'mid round');
    R.markResolved(resolved, 'Zoe');
    assertTrue(R.isComplete(roster, resolved), 'round closes');
    resolved = new Set();
    assertFalse(R.isComplete(roster, resolved), 'fresh round is open again');
});

// The agent-engine is DOM-heavy and not loaded in this sandbox, so this pins
// the one line that is the whole of task-533: closing a complete simultaneous
// round must run the world turn pipeline (`TurnQueue.endTurn()` -> applyTurn ->
// tick_turn). Before the fix, the loop stepped characters and never advanced
// the clock. The behavioural proof is a live-browser run (time_ticks moved);
// this guard keeps the wiring from being deleted.
test('closing a complete round calls the world turn pipeline (task-533)', () => {
    const src = __readFile('static/js/agent-engine.js');
    const start = src.indexOf('async _closeSimRoundIfComplete()');
    assertTrue(start !== -1, 'the closer must exist');
    const body = src.slice(start, start + 900);
    assertTrue(/VWSimRound\.isComplete|_simRoundComplete\(\)/.test(body),
        'it must gate on round completion');
    assertTrue(/TurnQueue\.endTurn\(\)/.test(body),
        'a complete round must call TurnQueue.endTurn()');
});
