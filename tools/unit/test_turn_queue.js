/**
 * Unit tests for TurnQueue paused / inert character exclusion (task-933).
 */

function withTurnQueueEnv(env, fn) {
    const prevWorldState = window.worldState;
    const prevConfig = window.config;
    const prevVW = window.VW;
    try {
        window.worldState = env.worldState;
        window.config = env.config;
        window.VW = env.VW;
        return fn();
    } finally {
        window.worldState = prevWorldState;
        window.config = prevConfig;
        window.VW = prevVW;
    }
}

test('TurnQueue.initialize excludes paused, inert, and simple_npc+autonomy:false characters', () => {
    withTurnQueueEnv({
        worldState: {
            players: {
                Alice: { state: 'awake', controller: 'llm', simple_npc: false, autonomy: true },
                Bob: { state: 'awake', controller: 'paused', simple_npc: true, autonomy: false },
                Charlie: { state: 'awake', controller: 'inert', simple_npc: true, autonomy: false },
                Diana: { state: 'awake', simple_npc: true, autonomy: false },
                Eve: { state: 'awake', controller: 'human', simple_npc: false, autonomy: false },
            }
        },
        config: { turnBased: true, turnOrder: 'sequential', ghostMode: false },
        VW: { agent: { turnQueue: [], currentTurnIndex: 0, initiativeRolls: {}, turnNumber: 0 } },
    }, () => {
        TurnQueue.initialize();
        assertEq(window.VW.agent.turnQueue, ['Alice', 'Eve'], 'only non-paused characters enter the queue');
    });
});

test('TurnQueue.initialize excludes paused characters even when server turn_order_info includes them', () => {
    withTurnQueueEnv({
        worldState: {
            players: {
                Alice: { id: 'p_alice', state: 'awake', controller: 'llm' },
                Bob: { id: 'p_bob', state: 'awake', controller: 'inert' },
                Charlie: { id: 'p_charlie', state: 'awake', simple_npc: true, autonomy: false },
            },
            turn_order_info: {
                order: ['p_alice', 'p_bob', 'p_charlie'],
                mode: 'sequential',
            }
        },
        config: { turnBased: true, turnOrder: 'sequential', ghostMode: false },
        VW: { agent: { turnQueue: [], currentTurnIndex: 0, initiativeRolls: {}, turnNumber: 0 } },
    }, () => {
        TurnQueue.initialize();
        assertEq(window.VW.agent.turnQueue, ['Alice'], 'server order does not re-insert paused characters');
    });
});

test('TurnQueue.reconcile removes newly paused characters and restores unpaused characters', () => {
    withTurnQueueEnv({
        worldState: {
            players: {
                Alice: { state: 'awake', controller: 'llm' },
                Bob: { state: 'awake', controller: 'llm' },
            }
        },
        config: { turnBased: true, turnOrder: 'sequential', ghostMode: false },
        VW: { agent: { turnQueue: [], currentTurnIndex: 0, initiativeRolls: {}, turnNumber: 3 } },
    }, () => {
        TurnQueue.initialize();
        window.VW.agent.turnNumber = 3;
        assertEq(window.VW.agent.turnQueue, ['Alice', 'Bob'], 'initial queue');

        // Pause Bob via controller: 'paused'
        window.worldState.players.Bob.controller = 'paused';
        const rebuiltPause = TurnQueue.reconcile();
        assertTrue(rebuiltPause === true, 'reconcile rebuilt when Bob paused');
        assertEq(window.VW.agent.turnQueue, ['Alice'], 'Bob excluded after pause');
        assertEq(window.VW.agent.turnNumber, 3, 'turnNumber preserved across reconcile');

        // Unpause Bob back to llm, pause Alice via simple_npc: true, autonomy: false
        window.worldState.players.Bob.controller = 'llm';
        window.worldState.players.Alice.controller = '';
        window.worldState.players.Alice.simple_npc = true;
        window.worldState.players.Alice.autonomy = false;
        const rebuiltSwap = TurnQueue.reconcile();
        assertTrue(rebuiltSwap === true, 'reconcile rebuilt when Alice paused and Bob unpaused');
        assertEq(window.VW.agent.turnQueue, ['Bob'], 'Bob restored and Alice excluded');
    });
});
