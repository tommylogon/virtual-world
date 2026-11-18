/**
 * Unit tests for contextual-actions disarm surfacing (task-959).
 */
'use strict';

test('contextual-actions surfaces disarm only when another present character visibly holds a hand item', () => {
    const prevWorldState = window.worldState;
    try {
        const stateBase = {
            current_area: 'Yard',
            players_in_area: [{ name: 'Hero' }, { name: 'Raider' }],
            players: {
                Hero: { name: 'Hero', vitals: { Hunger: 20 }, equipped: {} },
                Raider: { name: 'Raider', state: 'idle', equipped: { hand_right: ['item_knife'] } },
            },
        };

        const nodes = {
            area_yard: { id: 'area_yard', type: 'area', name: 'Yard', properties: {} },
            player_Hero: { id: 'player_Hero', type: 'character', name: 'Hero', properties: {} },
            player_Raider: { id: 'player_Raider', type: 'character', name: 'Raider', properties: {} },
            item_knife: { id: 'item_knife', type: 'item', name: 'Rusty Knife', properties: { actions: ['examine', 'take'] } },
        };
        const edges = [
            { source: 'item_knife', target: 'player_Raider', type: 'equipped', properties: { slot: 'hand_right' } },
        ];

        window.worldState = {
            data: stateBase,
            graph: { nodes: Object.values(nodes), edges },
            getNode: (id) => nodes[id] || null,
            hasMet: () => true,
            getItemsInArea: () => [],
            isHiddenArea: () => false,
            findPlayerNodeId: (n) => (n === 'Hero' ? 'player_Hero' : 'player_Raider'),
        };

        const withWeapon = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase,
            'Hero',
            stateBase.players.Hero,
            { name: 'Yard', exits: {} }
        );
        assertTrue(
            withWeapon.includes('disarm  -  wrest a held item from'),
            'disarm surfaced when Raider holds Rusty Knife, got: ' + withWeapon
        );

        // Unarmed Raider: disarm should not be surfaced
        stateBase.players.Raider.equipped = {};
        window.worldState.graph.edges = [];
        const unarmed = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase,
            'Hero',
            stateBase.players.Hero,
            { name: 'Yard', exits: {} }
        );
        assertFalse(
            unarmed.includes('disarm  -  '),
            'disarm not surfaced when Raider holds nothing in hand'
        );
    } finally {
        window.worldState = prevWorldState;
    }
});
