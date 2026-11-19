/** Unit tests for plan-tracker.js — critical needs + crossing-gated replanning (task-92). */
'use strict';
var PT = window.PlanTracker;

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

test('trackStep preserves failure count after 3 failures so shouldReplan and prompt warning can detect it', () => {
    freshTracker('Track2');
    PT.setPlan('Track2', ['open the vault', 'take gold']);
    PT.trackStep('Track2', 'open vault', 'It is locked.', false);
    PT.trackStep('Track2', 'open vault', 'It is locked.', false);
    assertEq(PT.getProgress('Track2'), 0, 'still on step after 2 fails');
    assertEq(PT.getFailures('Track2')[0], 2, '2 failures recorded');
    PT.trackStep('Track2', 'open vault', 'It is locked.', false);
    assertEq(PT.getProgress('Track2'), 0, 'does not skip past failed step before replan');
    assertEq(PT.getFailures('Track2')[0], 3, '3rd failure preserved on current step');
    assertEq(PT.shouldReplan('Track2', 1, false, {}), 'current step failed repeatedly', 'shouldReplan triggers on 3rd failure');
});

test('trackStep ignores stop words — "the" alone never completes a step', () => {
    freshTracker('Track3');
    PT.setPlan('Track3', ['examine the Streetlight (copy)']);
    PT.trackStep('Track3', 'go the round the corner to elm street', 'You are in Elm Street.', true);
    assertEq(PT.getProgress('Track3'), 0, 'stop-word-only overlap does not advance');
    PT.trackStep('Track3', 'examine streetlight', 'A weathered lamppost.', true);
    assertEq(PT.getProgress('Track3'), 1, 'real overlap advances');
});

test('trackStep — targeted actions need a target match, not just the action', () => {
    freshTracker('Track4');
    PT.setPlan('Track4', ['approach the round the corner to oak lane']);
    PT.trackStep('Track4', 'approach the order counter', 'You stop at the counter.', true);
    assertEq(PT.getProgress('Track4'), 0, 'shared action with different target does not advance');
    PT.trackStep('Track4', 'approach the round the corner to oak lane', 'You stop at the corner.', true);
    assertEq(PT.getProgress('Track4'), 1, 'same action and target advances');
});

test('trackStep — bare-action actions still advance on the action', () => {
    freshTracker('Track5');
    PT.setPlan('Track5', ['look around to check for anyone nearby or threats in oak lane']);
    PT.trackStep('Track5', 'look', 'Bright light floods the area.', true);
    assertEq(PT.getProgress('Track5'), 1, 'targetless action advances on action match');
});

test('shouldReplan returns a reason string for each trigger', () => {
    freshTracker('Reason1');
    assertEq(PT.shouldReplan('Reason1', 1, false, {}), 'no plan', 'no plan reason');
    PT.setPlan('Reason1', ['step one'], 1);
    assertEq(PT.shouldReplan('Reason1', 2, false, {}), null, 'fresh plan holds');
    assertEq(PT.shouldReplan('Reason1', 12, false, {}), 'plan aged out', 'age reason');
    PT.setPlan('Reason1', ['step one', 'step two'], 1);
    PT.trackStep('Reason1', 'do x', 'fail', false);
    PT.trackStep('Reason1', 'do x', 'fail', false);
    assertEq(PT.shouldReplan('Reason1', 2, false, {}), null, '2 fails holds');
    PT.trackStep('Reason1', 'do x', 'fail', false);
    assertEq(PT.getProgress('Reason1'), 0, 'stays on failed step');
    assertEq(PT.shouldReplan('Reason1', 2, false, {}), 'current step failed repeatedly', '3 fails triggers replan');
    PT.setPlan('Reason1', ['step one'], 1);
    PT.trackStep('Reason1', 'step one', 'done', true);
    assertEq(PT.getProgress('Reason1'), 1, 'completed single-step plan');
    assertEq(PT.shouldReplan('Reason1', 2, false, {}), 'plan completed', 'completed plan triggers replan');
    assertEq(PT.shouldReplan('Reason1', 2, true, {}), 'threat detected', 'threat reason');
});

test('hasPlan returns false once all plan steps are completed', () => {
    freshTracker('HasPlan1');
    assertFalse(PromptBuilder.hasPlan('HasPlan1'), 'no plan -> false');
    assertFalse(PlanManager.hasPlan('HasPlan1'), 'PlanManager no plan -> false');
    PT.setPlan('HasPlan1', ['eat bread', 'go north'], 1);
    assertTrue(PromptBuilder.hasPlan('HasPlan1'), 'active plan -> true');
    assertTrue(PlanManager.hasPlan('HasPlan1'), 'PlanManager active plan -> true');
    PT.trackStep('HasPlan1', 'eat bread', 'yum', true);
    assertTrue(PromptBuilder.hasPlan('HasPlan1'), '1 of 2 done -> still true');
    PT.trackStep('HasPlan1', 'go north', 'arrived', true);
    assertFalse(PromptBuilder.hasPlan('HasPlan1'), '2 of 2 done -> PromptBuilder.hasPlan false');
    assertFalse(PlanManager.hasPlan('HasPlan1'), '2 of 2 done -> PlanManager.hasPlan false');
});

test('buildPlanContext emits stuck-step warning for active failed step', () => {
    freshTracker('Warn1');
    PT.setPlan('Warn1', ['open the vault', 'take gold'], 1);
    PT.trackStep('Warn1', 'open vault', 'locked', false);
    PT.trackStep('Warn1', 'open vault', 'locked', false);
    const beforeWarn = PromptBuilder.buildPlanContext('Warn1');
    assertFalse(beforeWarn.includes('has failed repeatedly'), 'no warning after 2 failures');
    PT.trackStep('Warn1', 'open vault', 'locked', false);
    const afterWarn = PromptBuilder.buildPlanContext('Warn1');
    assertTrue(afterWarn.includes('Your current step "open the vault" has failed repeatedly'), 'warning shown for active step after 3 failures');
});
