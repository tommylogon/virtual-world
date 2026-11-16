/**
 * Unit tests for attended LLM agents following assigned pursuits (task-856).
 */

var PT = window.PlanTracker;
var PB = window.PromptBuilder;

test('seedFromPlayer seeds PlanTracker from player.active_pursuit and server plan', () => {
    PT.reset('Mikka');
    const player = {
        name: 'Mikka',
        active_pursuit: {
            assignment_id: 'pursuit_mikka_scrap',
            template_id: 'haul',
            label: 'scrap_run',
            reason: 'Move scrap to the workshop for repairs.'
        },
        plan: {
            assignment_id: 'pursuit_mikka_scrap',
            index: 1,
            steps: [
                { kind: 'travel', to: 'Scrap Pile' },
                { kind: 'take', spec: 'scrap' },
                { kind: 'travel', to: 'Workshop' },
                { kind: 'drop', spec: 'scrap' }
            ]
        }
    };

    const seeded = PT.seedFromPlayer('Mikka', player, 5);
    assertTrue(seeded, 'plan was seeded');
    const plan = PT.getPlan('Mikka');
    assertEq(plan.length, 4, 'four steps converted');
    assertEq(plan[0], 'go Scrap Pile', 'step 1 translated');
    assertEq(plan[1], 'take scrap', 'step 2 translated');
    assertEq(plan[2], 'go Workshop', 'step 3 translated');
    assertEq(plan[3], 'drop scrap', 'step 4 translated');
    assertEq(PT.getProgress('Mikka'), 1, 'progress reflects server index');
    assertEq(PT.getActivePursuitId('Mikka'), 'pursuit_mikka_scrap', 'pursuit id recorded');
});

test('active pursuit plan does not age out at 10 turns without threat or crisis', () => {
    PT.reset('Mikka');
    const player = {
        name: 'Mikka',
        active_pursuit: { assignment_id: 'haul_task', label: 'haul', reason: 'Deliver goods' },
        plan: { index: 0, steps: ['go Forest', 'take Wood'] }
    };
    PT.seedFromPlayer('Mikka', player, 0);

    // Turn 12: normal plan without pursuit would age out; active pursuit stays
    const reason = PT.shouldReplan('Mikka', 12, null, { Energy: 80, Hunger: 80, Thirst: 80 });
    assertEq(reason, null, 'active pursuit plan does not age out');
});

test('buildPlanContext carries pursuit undertaking reason and steps', () => {
    PT.reset('Arix');
    window.worldState = window.worldState || {};
    window.worldState.players = window.worldState.players || {};
    window.worldState.players['Arix'] = {
        name: 'Arix',
        active_pursuit: {
            assignment_id: 'patrol_01',
            label: 'patrol',
            reason: 'Secure the eastern watchtower against incursions.'
        },
        plan: {
            assignment_id: 'patrol_01',
            index: 0,
            steps: [
                { kind: 'travel', to: 'East Tower' },
                { kind: 'wait' }
            ]
        }
    };

    const ctx = PB.buildPlanContext('Arix');
    assertTrue(ctx.includes('=== YOUR PLAN ==='), 'plan header included');
    assertTrue(ctx.includes('Undertaking: Secure the eastern watchtower against incursions.'), 'undertaking reason present');
    assertTrue(ctx.includes('1. go East Tower (CURRENT)'), 'current step indicated');
    assertTrue(ctx.includes('2. wait'), 'second step present');
});
