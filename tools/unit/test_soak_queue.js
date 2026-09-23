/**
 * Unit tests for soak-order re-queueing in the turn queue (task-481).
 * The sandbox global is `window`, so `config`/`worldState`/`VW` stubs resolve.
 */

function _state() {
    return {
        players: {
            P1: { state: 'alive', stats: { DEX: 10 }, soak: { intent: 'travel', remaining_minutes: 5 } },
            P2: { state: 'alive', stats: { DEX: 10 } },
            P3: { state: 'alive', stats: { DEX: 10 } }
        }
    };
}

test('soak promotion re-rolls initiative and keeps the current character', () => {
    window.worldState = _state();
    window.config = { turnBased: true, turnOrder: 'initiative' };
    window.VW = { agent: { turnQueue: ['P1', 'P2', 'P3'], currentTurnIndex: 1,
        initiativeRolls: { P1: 1, P2: 20, P3: 10 }, turnNumber: 0 } };

    TurnQueue.syncSoakPromotions();          // baseline: P1 is soaking
    delete window.worldState.players.P1.soak; // the order ends
    const changed = TurnQueue.syncSoakPromotions();

    assertTrue(changed === true, 'promotion detected');
    assertTrue(typeof window.VW.agent.initiativeRolls.P1 === 'number', 'P1 re-rolled');
    const idx = window.VW.agent.turnQueue.indexOf('P2');
    assertEq(window.VW.agent.currentTurnIndex, idx, 'current character stays current');
});

test('soak promotion leaves sequential order alone', () => {
    window.worldState = {
        players: {
            Q1: { state: 'alive', soak: { intent: 'idle', remaining_minutes: 3 } },
            Q2: { state: 'alive' }
        }
    };
    window.config = { turnBased: true, turnOrder: 'sequential' };
    window.VW = { agent: { turnQueue: ['Q1', 'Q2'], currentTurnIndex: 0,
        initiativeRolls: {}, turnNumber: 0 } };

    TurnQueue.syncSoakPromotions();
    delete window.worldState.players.Q1.soak;
    const changed = TurnQueue.syncSoakPromotions();

    assertTrue(changed === true, 'promotion detected');
    assertEq(window.VW.agent.turnQueue, ['Q1', 'Q2'], 'order untouched');
});

test('a dead character leaving soak is not treated as a promotion', () => {
    window.worldState = {
        players: {
            R1: { state: 'alive', soak: { intent: 'idle', remaining_minutes: 3 } },
            R2: { state: 'alive' }
        }
    };
    window.config = { turnBased: true, turnOrder: 'sequential' };
    window.VW = { agent: { turnQueue: ['R1', 'R2'], currentTurnIndex: 0,
        initiativeRolls: {}, turnNumber: 0 } };

    TurnQueue.syncSoakPromotions();
    window.worldState.players.R1.state = 'dead';
    delete window.worldState.players.R1.soak;
    assertFalse(TurnQueue.syncSoakPromotions(), 'no re-queue for the dead');
});
