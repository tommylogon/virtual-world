/**
 * Unit tests for subjective time perception in contextual-actions and character-state.
 */
'use strict';

test('contextual-actions offers guess time outdoors or near a timepiece, not in a sealed indoor room', () => {
    const prevWorldState = window.worldState;
    try {
        const stateBase = {
            current_area: 'Cave',
            players_in_area: [{ name: 'Hero' }],
            players: { Hero: { name: 'Hero', vitals: { Energy: 80 } } },
        };
        const nodes = {
            area_cave: { id: 'area_cave', type: 'area', name: 'Cave', properties: { tags: ['indoor'] } },
            area_yard: { id: 'area_yard', type: 'area', name: 'Yard', properties: { tags: ['outdoor'] } },
            player_Hero: { id: 'player_Hero', type: 'character', name: 'Hero', properties: {} },
            item_clock: { id: 'item_clock', type: 'item', name: 'Wall Clock', properties: { tags: ['clock'] } },
        };
        let roomItems = [];
        window.worldState = {
            data: stateBase,
            graph: { nodes: Object.values(nodes), edges: [] },
            getNode: (id) => nodes[id] || null,
            getNodeByIdentifier: (name) => Object.values(nodes).find(n => n.name === name || n.id === name) || null,
            getItemsInArea: () => roomItems,
            isHiddenArea: () => false,
            findPlayerNodeId: () => 'player_Hero',
        };

        // 1. Sealed indoor cave without timepiece -> no guess time
        const caveBlock = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase, 'Hero', stateBase.players.Hero, { id: 'area_cave', name: 'Cave', exits: {} }
        );
        assertFalse(caveBlock.includes('guess time'), 'sealed cave should not offer guess time');

        // 2. Indoor room WITH a wall clock -> offers timepiece guess time
        roomItems = [nodes.item_clock];
        const clockBlock = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase, 'Hero', stateBase.players.Hero, { id: 'area_cave', name: 'Cave', exits: {} }
        );
        assertTrue(clockBlock.includes('guess time  -  check the time on the Wall Clock'), 'clock room should offer timepiece hint');

        // 3. Outdoor yard without timepiece -> offers sky survival guess time
        roomItems = [];
        const yardBlock = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase, 'Hero', stateBase.players.Hero, { id: 'area_yard', name: 'Yard', exits: {} }
        );
        assertTrue(yardBlock.includes('guess time  -  estimate the time from the sky'), 'outdoor yard should offer sky hint');
    } finally {
        window.worldState = prevWorldState;
    }
});

test('describeScheduleHorizon adapts time phrasing by timepiece, open sky, indoor cave, and goblin lens', () => {
    const prevWorldState = window.worldState;
    try {
        const nodes = {
            area_room: { id: 'area_room', type: 'area', name: 'Classroom', properties: { tags: ['indoor'] } },
            area_yard: { id: 'area_yard', type: 'area', name: 'Courtyard', properties: { tags: ['outdoor'] } },
            item_clock: { id: 'item_clock', type: 'item', name: 'Wall Clock', properties: { tags: ['clock'] } },
        };
        let roomItems = [];
        window.worldState = {
            data: { game_time: '07:30' },
            graph: { nodes: Object.values(nodes), edges: [] },
            getNode: (id) => nodes[id] || null,
            getNodeByIdentifier: (name) => Object.values(nodes).find(n => n.name === name || n.id === name) || null,
            getItemsInArea: () => roomItems,
        };
        const schedule = [{ start: 480, activity: 'homeroom', area: 'Hall' }]; // 08:00 (30 min away)

        // 1. Indoors with clock -> exact 07:30 and 30 minutes
        roomItems = [nodes.item_clock];
        const exact = window.PromptBuilder.describeScheduleHorizon({
            name: 'Teacher', current_area: 'Classroom', schedule,
        });
        assertTrue(exact.includes('07:30') && exact.includes('30 minutes'), 'clock user gets exact time: ' + exact);

        // 2. Indoors without clock -> no 07:30 or 30 minutes
        roomItems = [];
        const vague = window.PromptBuilder.describeScheduleHorizon({
            name: 'Student', current_area: 'Classroom', schedule,
        });
        assertFalse(vague.includes('07:30'), 'clockless indoor student must not see 07:30: ' + vague);
        assertFalse(vague.includes('30 minutes'), 'clockless indoor student must not see 30 minutes: ' + vague);
        assertTrue(vague.includes('before long'), 'clockless indoor student gets soft horizon: ' + vague);

        // 3. Outdoors goblin -> natural sky band, never 07:30
        const goblin = window.PromptBuilder.describeScheduleHorizon({
            name: 'Snaggle', current_area: 'Courtyard', tags: ['goblin'], schedule,
        });
        assertTrue(goblin.includes('early morning'), 'outdoor goblin gets natural sky band: ' + goblin);
        assertFalse(goblin.includes('07:30'), 'goblin must not see 07:30: ' + goblin);
    } finally {
        window.worldState = prevWorldState;
    }
});
