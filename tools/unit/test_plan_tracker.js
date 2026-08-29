/** Unit tests for plan-tracker.js — critical needs + crossing-gated replanning (task-92). */
'use strict';
const PT = window.PlanTracker;

function freshTracker(name) {
    PT.reset(name);
    window.worldState.data.time_ticks = 0;
}

// ── criticalNeeds ──

test('criticalNeeds flags low energy, high-driven hunger/thirst', () => {
    // After task-337 flip: drives (Hunger/Thirst/Bladder) are high=urgent.
    // Energy/Sanity/Social remain low=urgent.
    const out = PT.criticalNeeds({ Energy: 20, Hunger: 30, Thirst: 95 });
    assertEq(out.length, 2, 'two critical needs');
    assertTrue(out[0].includes('exhaustion'), 'energy label');
    assertTrue(out[1].includes('thirst'), 'thirst label');
});

test('criticalNeeds includes sanity, social, and inverted bladder', () => {
    const out = PT.criticalNeeds({ Sanity: 24, Social: 10, Bladder: 95 });
    assertEq(out.length, 3, 'three critical needs');
    assertTrue(out[2].includes('bladder'), 'bladder label');
});

test('criticalNeeds empty when all vitals healthy', () => {
    assertEq(PT.criticalNeeds({ Energy: 80, Hunger: 80, Thirst: 80, Sanity: 90, Social: 60, Bladder: 10 }).length, 0, 'no needs');
});

test('criticalNeeds handles missing vitals object', () => {
    assertEq(PT.criticalNeeds(undefined).length, 0, 'undefined vitals');
});

// ── shouldReplan crossing gate ──

test('replans when a need first crosses into critical', () => {
    freshTracker('Cross1');
    PT.setPlan('Cross1', ['step one']);
    assertTrue(PT.shouldReplan('Cross1', 5, false, { Hunger: 90 }), 'first crossing fires');
});

test('does NOT replan every turn while the same need stays critical', () => {
    freshTracker('Cross2');
    PT.setPlan('Cross2', ['step one']);
    assertTrue(PT.shouldReplan('Cross2', 5, false, { Hunger: 90 }), 'crossing fires');
    assertFalse(PT.shouldReplan('Cross2', 6, false, { Hunger: 91 }), 'same signature holds');
    assertFalse(PT.shouldReplan('Cross2', 9, false, { Hunger: 92 }), 'still holding before 5 turns');
});

test('re-nudges after 5 turns if the need is still critical', () => {
    freshTracker('Cross3');
    PT.setPlan('Cross3', ['step one']);
    assertTrue(PT.shouldReplan('Cross3', 5, false, { Hunger: 90 }), 'crossing fires');
    assertFalse(PT.shouldReplan('Cross3', 8, false, { Hunger: 91 }), 'holding');
    assertTrue(PT.shouldReplan('Cross3', 10, false, { Hunger: 92 }), 're-nudge at +5');
});

test('a NEW critical need re-fires immediately', () => {
    freshTracker('Cross4');
    PT.setPlan('Cross4', ['step one']);
    assertTrue(PT.shouldReplan('Cross4', 5, false, { Hunger: 90 }), 'hunger crossing');
    assertFalse(PT.shouldReplan('Cross4', 6, false, { Hunger: 91 }), 'holding');
    assertTrue(PT.shouldReplan('Cross4', 7, false, { Hunger: 91, Thirst: 90 }), 'new need fires now');
});

test('clearing the need resets the signature', () => {
    freshTracker('Cross5');
    PT.setPlan('Cross5', ['step one']);
    assertTrue(PT.shouldReplan('Cross5', 5, false, { Hunger: 90 }), 'starving crossing fires');
    assertFalse(PT.shouldReplan('Cross5', 7, false, { Hunger: 20 }), 'fed — no fire');
    assertTrue(PT.shouldReplan('Cross5', 9, false, { Hunger: 95 }), 'starves again — fires fresh');
});

test('threat alert always replans regardless of needs', () => {
    freshTracker('Threat1');
    PT.setPlan('Threat1', ['step one']);
    assertTrue(PT.shouldReplan('Threat1', 3, true, {}), 'threat fires');
});

test('stale plan (>=10 turns) still triggers replan without needs', () => {
    freshTracker('Stale1');
    PT.setPlan('Stale1', ['step one']);
    assertFalse(PT.shouldReplan('Stale1', 5, false, {}), 'fresh plan holds');
    assertTrue(PT.shouldReplan('Stale1', 15, false, {}), 'stale plan fires');
});

// ── trackStep ──

test('trackStep advances progress on word overlap', () => {
    freshTracker('Track1');
    PT.setPlan('Track1', ['eat the bread', 'go north']);
    PT.trackStep('Track1', 'use bread', 'You eat the bread.', true);
    assertEq(PT.getProgress('Track1'), 1, 'advanced past eat step');
});

test('trackStep blocks a step after 3 failures', () => {
    freshTracker('Track2');
    PT.setPlan('Track2', ['open the vault']);
    PT.trackStep('Track2', 'open vault', 'It is locked.', false);
    PT.trackStep('Track2', 'open vault', 'It is locked.', false);
    assertEq(PT.getProgress('Track2'), 0, 'still on step after 2 fails');
    PT.trackStep('Track2', 'open vault', 'It is locked.', false);
    assertEq(PT.getProgress('Track2'), 1, 'skipped after 3 fails');
});
