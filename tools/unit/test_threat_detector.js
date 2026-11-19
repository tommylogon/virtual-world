/**
 * Unit tests for ThreatDetector target-, weapon-, affinity-, and disarm-awareness
 * and _vitalsScene / PlanManager agreement (bug-592, bug-590).
 */
'use strict';

test('ThreatDetector.isHostileTurnAction recognizes combat, attack, and disarm', () => {
    assertTrue(window.ThreatDetector.isHostileTurnAction('combat'), 'combat is hostile');
    assertTrue(window.ThreatDetector.isHostileTurnAction('attack'), 'attack is hostile');
    assertTrue(window.ThreatDetector.isHostileTurnAction('disarm'), 'disarm is hostile');
    assertTrue(window.ThreatDetector.isHostileTurnAction('COMBAT'), 'case-insensitive combat');
    assertFalse(window.ThreatDetector.isHostileTurnAction('move'), 'move is not hostile');
    assertFalse(window.ThreatDetector.isHostileTurnAction('say'), 'say is not hostile');
    assertFalse(window.ThreatDetector.isHostileTurnAction(undefined), 'undefined is not hostile');
});

test('ThreatDetector and _vitalsScene agree on combat, attack, and disarm turn events', () => {
    const prevWorldState = window.worldState;
    try {
        for (const action of ['combat', 'attack', 'disarm']) {
            const state = {
                current_area: 'Hall',
                players_in_area: [{ name: 'Hero' }, { name: 'Raider' }],
                players: {
                    Hero: { name: 'Hero', vitals: { Hunger: 40 } },
                    Raider: { name: 'Raider', state: 'idle', traits: {}, relationships: {} },
                },
                turn_events: [{ actor: 'Raider', action, description: 'lunges at Hero' }],
            };
            window.worldState = {
                data: state,
                hasMet: () => true,
                getItemsInArea: () => [],
            };

            const alert = window.ThreatDetector.getThreatAlert('Hero', state.players.Hero, 'Hall', state.turn_events);
            assertTrue(Boolean(alert && alert.includes('Raider')), `ThreatDetector alerts on ${action}`);

            const vitalsText = window.PromptBuilder.describeVitals(state.players.Hero, state, 'Hero');
            assertTrue(
                vitalsText.includes('(a hostile presence is in the room)'),
                `_vitalsScene reports threat on ${action}`
            );
        }

        const safeState = {
            current_area: 'Hall',
            players_in_area: [{ name: 'Hero' }, { name: 'Raider' }],
            players: {
                Hero: { name: 'Hero', vitals: { Hunger: 40 } },
                Raider: { name: 'Raider', state: 'idle', traits: {}, relationships: {} },
            },
            turn_events: [{ actor: 'Raider', action: 'move', description: 'walks across the hall' }],
        };
        window.worldState = {
            data: safeState,
            hasMet: () => true,
            getItemsInArea: () => [],
        };

        assertEq(
            window.ThreatDetector.getThreatAlert('Hero', safeState.players.Hero, 'Hall', safeState.turn_events),
            null,
            'ThreatDetector returns null on non-hostile action'
        );
        const safeVitals = window.PromptBuilder.describeVitals(safeState.players.Hero, safeState, 'Hero');
        assertFalse(
            safeVitals.includes('(a hostile presence is in the room)'),
            '_vitalsScene does not report threat on non-hostile action'
        );
    } finally {
        window.worldState = prevWorldState;
    }
});

test('ThreatDetector escalates visibly held weapons on non-allies and ignores benign held items', () => {
    const prevWorldState = window.worldState;
    try {
        const armedState = {
            current_area: 'Lobby',
            players_in_area: [
                { name: 'Hero', holding: [] },
                { name: 'Stranger', state: 'idle', holding: ['pistol'], wearing: ['trench coat'] },
            ],
            players: {
                Hero: { name: 'Hero', relationships: {} },
                Stranger: { name: 'Stranger', state: 'idle', traits: {}, relationships: {} },
            },
            turn_events: [],
        };
        window.worldState = { data: armedState, hasMet: () => true, getItemsInArea: () => [] };

        const threats = window.ThreatDetector.getThreats('Hero', [], armedState);
        assertEq(JSON.stringify(threats), JSON.stringify(['Stranger']), 'visibly armed stranger is flagged in getThreats');

        const alert = window.ThreatDetector.getThreatAlert('Hero', armedState.players.Hero, 'Lobby', [], armedState);
        assertTrue(Boolean(alert && alert.includes('IMMEDIATE DANGER')), 'armed stranger triggers IMMEDIATE DANGER');
        assertTrue(Boolean(alert && alert.includes('Stranger')), 'alert names Stranger');
        assertTrue(Boolean(alert && alert.includes('pistol')), 'alert names visible weapon');

        // Benign held items do not escalate threat
        const benignState = {
            current_area: 'Lobby',
            players_in_area: [
                { name: 'Hero', holding: [] },
                { name: 'Stranger', state: 'idle', holding: ['coffee mug', 'lantern'], wearing: ['coat'] },
            ],
            players: {
                Hero: { name: 'Hero', relationships: {} },
                Stranger: { name: 'Stranger', state: 'idle', traits: {}, relationships: {} },
            },
            turn_events: [],
        };
        window.worldState = { data: benignState, hasMet: () => true, getItemsInArea: () => [] };

        assertEq(window.ThreatDetector.getThreats('Hero', [], benignState).length, 0, 'benign held items are not threats');
        assertEq(
            window.ThreatDetector.getThreatAlert('Hero', benignState.players.Hero, 'Lobby', [], benignState),
            null,
            'benign held items produce null alert'
        );
    } finally {
        window.worldState = prevWorldState;
    }
});

test('ThreatDetector attributes third-party hostility toward bystanders (actor -> target)', () => {
    const prevWorldState = window.worldState;
    try {
        const state = {
            current_area: 'Courtyard',
            players_in_area: [
                { name: 'Hero', holding: [] },
                { name: 'Bystander', state: 'idle', holding: [] },
                { name: 'Raider', state: 'idle', holding: ['dagger'] },
            ],
            players: {
                Hero: { name: 'Hero', relationships: {} },
                Bystander: { name: 'Bystander', state: 'idle', traits: {}, relationships: {} },
                Raider: { name: 'Raider', state: 'idle', traits: {}, relationships: {} },
            },
            turn_events: [
                { actor: 'Raider', action: 'combat', description: 'slashes Bystander in the arm with dagger' },
            ],
        };
        window.worldState = { data: state, hasMet: () => true, getItemsInArea: () => [] };

        const threats = window.ThreatDetector.getThreats('Hero', state.turn_events, state);
        assertEq(JSON.stringify(threats), JSON.stringify(['Raider']), 'only Raider is in getThreats, not Bystander');

        const alert = window.ThreatDetector.getThreatAlert('Hero', state.players.Hero, 'Courtyard', state.turn_events, state);
        assertTrue(Boolean(alert && alert.includes('IMMEDIATE DANGER')), 'third-party attack triggers IMMEDIATE DANGER');
        assertTrue(Boolean(alert && alert.includes('Raider')), 'alert identifies attacker Raider');
        assertTrue(Boolean(alert && alert.includes('Bystander')), 'alert identifies target Bystander');
        assertTrue(Boolean(alert && alert.includes('not directly attacking you')), 'alert distinguishes third-party target from observer');
        assertFalse(Boolean(alert && alert.includes('hostile toward you')), 'does not blindly claim attacker is hostile toward observer');
    } finally {
        window.worldState = prevWorldState;
    }
});

test('ThreatDetector friend-disarming-aggressor standoff: ally disarming or holding disarmed weapon is not labeled hostile toward you', () => {
    const prevWorldState = window.worldState;
    try {
        // Phase 1: Aggressor Carl attacks Bob while ally Bob fails/attempts to disarm or holds a knife in defense
        const activeStandoffState = {
            current_area: 'Bar',
            players_in_area: [
                { name: 'Alice', holding: [] },
                { name: 'Bob', state: 'idle', holding: [] },
                { name: 'Carl', state: 'idle', holding: ['pistol'] },
            ],
            players: {
                Alice: {
                    name: 'Alice',
                    relationships: { Bob: { closeness: 65, label: 'close friend' } },
                },
                Bob: {
                    name: 'Bob',
                    state: 'idle',
                    traits: {},
                    relationships: { Alice: { closeness: 65, label: 'close friend' } },
                },
                Carl: {
                    name: 'Carl',
                    state: 'idle',
                    traits: {},
                    relationships: { Alice: { closeness: -30 }, Bob: { closeness: -40 } },
                },
            },
            turn_events: [
                { actor: 'Carl', action: 'combat', target: 'Bob', description: 'attacks Bob with pistol and misses' },
                { actor: 'Bob', action: 'disarm', target: 'Carl', item: 'pistol', outcome: 'failed', description: 'tried to disarm pistol from Carl and failed' },
            ],
        };
        window.worldState = { data: activeStandoffState, hasMet: () => true, getItemsInArea: () => [] };

        const standoffThreats = window.ThreatDetector.getThreats('Alice', activeStandoffState.turn_events, activeStandoffState);
        assertEq(JSON.stringify(standoffThreats), JSON.stringify(['Carl']), 'only aggressor Carl is flagged as threat, never intervening ally Bob');

        const standoffAlert = window.ThreatDetector.getThreatAlert(
            'Alice', activeStandoffState.players.Alice, 'Bar', activeStandoffState.turn_events, activeStandoffState
        );
        assertTrue(Boolean(standoffAlert && standoffAlert.includes('Carl')), 'standoff alert names aggressor Carl');
        assertTrue(Boolean(standoffAlert && standoffAlert.includes('Your ally Bob')), 'standoff alert recognizes ally Bob');
        assertTrue(Boolean(standoffAlert && standoffAlert.includes('not hostile toward you')), 'standoff alert clarifies Bob is not hostile toward Alice');

        // Phase 2: Ally Bob succeeds in disarming Carl and catches the pistol
        const disarmedHeldByAllyState = {
            current_area: 'Bar',
            players_in_area: [
                { name: 'Alice', holding: [] },
                { name: 'Bob', state: 'idle', holding: ['pistol'] },
                { name: 'Carl', state: 'idle', holding: [] },
            ],
            players: activeStandoffState.players,
            turn_events: [
                {
                    actor: 'Bob',
                    action: 'disarm',
                    target: 'Carl',
                    item: 'pistol',
                    outcome: 'success',
                    description: 'disarmed pistol from Carl, catching it in their right hand',
                },
            ],
        };
        window.worldState = { data: disarmedHeldHeldStateOr(disarmedHeldByAllyState), hasMet: () => true, getItemsInArea: () => [] };

        const postDisarmThreats = window.ThreatDetector.getThreats(
            'Alice', disarmedHeldByAllyState.turn_events, disarmedHeldByAllyState
        );
        assertEq(postDisarmThreats.length, 0, 'neither ally Bob nor disarmed Carl is in getThreats');

        const contextAlert = window.ThreatDetector.getThreatAlert(
            'Alice', disarmedHeldByAllyState.players.Alice, 'Bar', disarmedHeldByAllyState.turn_events, disarmedHeldByAllyState
        );
        assertTrue(Boolean(contextAlert && contextAlert.includes('THREAT CONTEXT')), 'downgrades to THREAT CONTEXT when ally holds disarmed weapon');
        assertFalse(Boolean(contextAlert && contextAlert.includes('IMMEDIATE DANGER')), 'does not emit IMMEDIATE DANGER when ally holds disarmed weapon');
        assertFalse(Boolean(contextAlert && contextAlert.includes('Your current plan is INVALID')), 'does not invalidate plan when ally holds disarmed weapon');
        assertTrue(Boolean(contextAlert && contextAlert.includes('Your ally Bob disarmed Carl')), 'explains ally Bob disarmed Carl');
        assertTrue(Boolean(contextAlert && contextAlert.includes('not hostile toward you')), 'does not falsely label ally Bob hostile toward Alice');
    } finally {
        window.worldState = prevWorldState;
    }
});

function disarmedHeldHeldStateOr(s) { return s; }

test('ThreatDetector post-disarm, drop, throw, and release de-escalation clears immediate danger and does not lock calm turns', () => {
    const prevWorldState = window.worldState;
    try {
        const players = {
            Alice: {
                name: 'Alice',
                relationships: { Bob: { closeness: 65, label: 'ally' }, Carl: { closeness: -40 } },
            },
            Bob: {
                name: 'Bob',
                state: 'idle',
                traits: {},
                relationships: { Alice: { closeness: 65, label: 'ally' } },
            },
            Carl: {
                name: 'Carl',
                state: 'idle',
                traits: {},
                relationships: { Alice: { closeness: -45 }, Bob: { closeness: -50 } },
            },
        };

        // 1. Ally Bob disarms Carl and drops/throws the pistol in the same round
        for (const deescAction of ['drop', 'throw', 'release']) {
            const state = {
                current_area: 'Bar',
                players_in_area: [
                    { name: 'Alice', holding: [] },
                    { name: 'Bob', state: 'idle', holding: [] },
                    { name: 'Carl', state: 'idle', holding: [] },
                ],
                players,
                turn_events: [
                    { actor: 'Bob', action: 'disarm', target: 'Carl', item: 'pistol', outcome: 'success', description: 'disarmed pistol from Carl' },
                    { actor: 'Bob', action: deescAction, item: 'pistol', description: `${deescAction}s the pistol` },
                ],
            };
            window.worldState = { data: state, hasMet: () => true, getItemsInArea: () => [] };

            assertEq(window.ThreatDetector.getThreats('Alice', state.turn_events, state).length, 0, `no threats after disarm + ${deescAction}`);
            assertEq(
                window.ThreatDetector.getThreatAlert('Alice', players.Alice, 'Bar', state.turn_events, state),
                null,
                `alert clears cleanly to null after disarm + ${deescAction}`
            );
        }

        // 2. Aggressor Carl drops or throws his own weapon
        for (const deescAction of ['drop', 'throw', 'release']) {
            const state = {
                current_area: 'Bar',
                players_in_area: [
                    { name: 'Alice', holding: [] },
                    { name: 'Carl', state: 'idle', holding: ['pistol'] }, // even if snapshot still lists pistol before refresh
                ],
                players,
                turn_events: [
                    { actor: 'Carl', action: deescAction, item: 'pistol', description: `dropped the pistol` },
                ],
            };
            window.worldState = { data: state, hasMet: () => true, getItemsInArea: () => [] };

            assertEq(window.ThreatDetector.getThreats('Alice', state.turn_events, state).length, 0, `Carl de-escalates on ${deescAction}`);
            assertEq(
                window.ThreatDetector.getThreatAlert('Alice', players.Alice, 'Bar', state.turn_events, state),
                null,
                `alert clears when aggressor performs ${deescAction}`
            );
        }

        // 3. Subsequent calm turn: Carl has negative closeness (-45) but is unarmed and performs non-hostile action
        const calmNextTurnState = {
            current_area: 'Bar',
            players_in_area: [
                { name: 'Alice', holding: [] },
                { name: 'Bob', state: 'idle', holding: [] },
                { name: 'Carl', state: 'idle', holding: [] },
            ],
            players,
            turn_events: [
                { actor: 'Carl', action: 'say', description: 'raises his empty hands and steps back' },
            ],
        };
        window.worldState = { data: calmNextTurnState, hasMet: () => true, getItemsInArea: () => [] };

        assertEq(
            window.ThreatDetector.getThreats('Alice', calmNextTurnState.turn_events, calmNextTurnState).length,
            0,
            'unarmed negative-closeness actor on calm turn is not locked in threats'
        );
        assertEq(
            window.ThreatDetector.getThreatAlert('Alice', players.Alice, 'Bar', calmNextTurnState.turn_events, calmNextTurnState),
            null,
            'subsequent calm turn does not lock in IMMEDIATE DANGER'
        );
    } finally {
        window.worldState = prevWorldState;
    }
});

test('ThreatDetector grades danger posture by traits, affinity, weapon state, and shock freeze', () => {
    const prevWorldState = window.worldState;
    try {
        const players = {
            Raider: { name: 'Raider', state: 'idle', traits: { hostile: true }, holding: ['pistol'], relationships: {} },
            Ally: { name: 'Ally', state: 'idle', traits: {}, holding: [], relationships: {} },
            Protector: {
                name: 'Protector', traits: { protective: true, brave: true }, holding: ['knife'],
                relationships: { Ally: { closeness: 75 } },
            },
            CalmWatch: { name: 'CalmWatch', traits: { calm: true }, holding: [], relationships: {} },
            Coward: { name: 'Coward', traits: { cowardly: true }, holding: [], relationships: {} },
            FrozenObserver: { name: 'FrozenObserver', traits: {}, flags: { frozen_by_fear: true }, holding: [], relationships: {} },
        };
        const state = {
            current_area: 'Bar',
            players_in_area: [
                { name: 'Raider', state: 'idle', holding: ['pistol'] },
                { name: 'Ally', state: 'idle', holding: [] },
                { name: 'Protector', state: 'idle', holding: ['knife'] },
                { name: 'CalmWatch', state: 'idle', holding: [] },
                { name: 'Coward', state: 'idle', holding: [] },
                { name: 'FrozenObserver', state: 'idle', holding: [] },
            ],
            players,
            turn_events: [{ actor: 'Raider', action: 'attack', target: 'Ally', description: 'aims pistol at Ally' }],
        };
        window.worldState = { data: state, hasMet: () => true, getItemsInArea: () => [] };

        const protAlert = window.ThreatDetector.getThreatAlert('Protector', players.Protector, 'Bar', state.turn_events, state);
        const calmAlert = window.ThreatDetector.getThreatAlert('CalmWatch', players.CalmWatch, 'Bar', state.turn_events, state);
        const cowardAlert = window.ThreatDetector.getThreatAlert('Coward', players.Coward, 'Bar', state.turn_events, state);
        const frozenAlert = window.ThreatDetector.getThreatAlert('FrozenObserver', players.FrozenObserver, 'Bar', state.turn_events, state);

        assertEq(!protAlert.includes('Your current plan is INVALID'), true, 'no uniform forced plan-invalid override');
        assertEq(protAlert.includes('POSTURE [STAND / INTERVENE]'), true, 'protective/allied observer gets STAND / INTERVENE');
        assertEq(calmAlert.includes('POSTURE [ASSESS]'), true, 'calm observer gets ASSESS');
        assertEq(cowardAlert.includes('POSTURE [EVADE]'), true, 'cowardly observer gets EVADE');
        assertEq(frozenAlert.includes('SHOCK / HESITATION'), true, 'shock-frozen observer gets SHOCK / HESITATION');
    } finally {
        window.worldState = prevWorldState;
    }
});
