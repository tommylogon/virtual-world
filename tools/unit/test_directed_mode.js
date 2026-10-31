/**
 * Unit tests for Directed Control Mode (task-728).
 */

const StreamControlMode = new Function(window.__readFile('static/js/stream/stream-control-mode.js') + '; return StreamControlMode;')();

test('StreamControlMode resolves directed mode and badge correctly', () => {
    const scm = new StreamControlMode({});
    
    // Test badge vocabulary
    const badge = scm.controlBadge('directed');
    assertEq(badge.emoji, '🎬', 'directed badge emoji is clapperboard');
    assertEq(badge.label, 'Directed', 'directed badge label');
    assertTrue(badge.title.includes('director reviews and edits'), 'directed badge title describes review flow');

    // Test getControlMode resolution
    window.worldState = window.worldState || {};
    window.worldState.players = {
        'Jake': { autonomy: 'directed' },
        'Kayla': { autonomy: false },
        'Lulu': { autonomy: true },
        'Rat': { simple_npc: true, autonomy: true },
    };

    assertEq(scm.getControlMode('Jake'), 'directed', 'player with autonomy directed resolves to directed');
    assertEq(scm.getControlMode('Kayla'), 'human', 'player with autonomy false resolves to human');
    assertEq(scm.getControlMode('Lulu'), 'llm', 'player with autonomy true resolves to llm');
    assertEq(scm.getControlMode('Rat'), 'npc', 'player with simple_npc resolves to npc');

    // Test unified controller field resolution
    window.worldState.players['Sammy'] = { controller: 'directed' };
    window.worldState.players['Zoe'] = { controller: 'human' };
    window.worldState.players['Kyrie'] = { controller: 'llm' };
    window.worldState.players['Goblin'] = { controller: 'npc' };
    assertEq(scm.getControlMode('Sammy'), 'directed', 'player with controller directed resolves to directed');
    assertEq(scm.getControlMode('Zoe'), 'human', 'player with controller human resolves to human');
    assertEq(scm.getControlMode('Kyrie'), 'llm', 'player with controller llm resolves to llm');
    assertEq(scm.getControlMode('Goblin'), 'npc', 'player with controller npc resolves to npc');

    // Test isAutonomous
    assertTrue(scm.isAutonomous('Jake'), 'directed character is autonomous for LLM generation');
    assertTrue(!scm.isAutonomous('Kayla'), 'human character is not autonomous');
    assertTrue(scm.isAutonomous('Lulu'), 'llm character is autonomous');
});

test('HumanTurnComposer contains thought row, prefill wiring, and reroll button', () => {
    const src = window.__readFile('static/js/agent/human-turn-composer.js');
    assertTrue(/id="htc-thought-row"/.test(src), 'template includes htc-thought-row container');
    assertTrue(/id="htc-reroll-btn"/.test(src), 'template includes htc-reroll-btn');
    assertTrue(/applyPrefill/.test(src), 'applyPrefill is defined');
    assertTrue(/opts\.prefill/.test(src), 'openPanel consumes prefill');
    assertTrue(/Directed:/.test(src), 'directed mode title indicator wired');
});

test('AgentEngine intercepts think-decide phase when character is directed', () => {
    const src = window.__readFile('static/js/agent-engine.js');
    assertTrue(src.includes("events.getControlMode(charName) === 'directed'"), 'agent-engine checks for directed mode');
    assertTrue(src.includes("HumanTurnComposer.request(charName"), 'agent-engine opens HumanTurnComposer with draft prefill');
    assertTrue(src.includes("reviewResult.reroll"), 'agent-engine supports rerolling drafts in directed mode');
    assertTrue(src.includes("HumanTurnComposer.closeTurn()"), 'agent-engine closes HumanTurnComposer after director decision');
});
