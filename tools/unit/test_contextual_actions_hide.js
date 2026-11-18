/**
 * Unit tests for contextual-actions hide and unhide surfacing (task-958).
 */
'use strict';

test('contextual-actions surfaces hide when hideable cover or threat exists and unhide when hidden', () => {
    const prevWorldState = window.worldState;
    try {
        const stateBase = {
            current_area: 'Storage',
            players_in_area: [{ name: 'Hero' }],
            players: {
                Hero: { name: 'Hero', vitals: { Hunger: 10 }, equipped: {}, hidden: false, state: 'normal' },
            },
        };

        const nodes = {
            area_storage: { id: 'area_storage', type: 'area', name: 'Storage', properties: {} },
            player_Hero: { id: 'player_Hero', type: 'character', name: 'Hero', properties: {} },
            item_crate: { id: 'item_crate', type: 'item', name: 'Wooden Crate', properties: { tags: ['hideable'] } },
        };
        const edges = [
            { source: 'item_crate', target: 'area_storage', type: 'in', properties: {} },
        ];

        window.worldState = {
            data: stateBase,
            graph: { nodes: Object.values(nodes), edges },
            getNode: (id) => nodes[id] || null,
            getNodeByIdentifier: (name) => (name === 'Storage' ? nodes.area_storage : null),
            hasMet: () => true,
            getItemsInArea: () => [nodes.item_crate],
            isHiddenArea: () => false,
            findPlayerNodeId: () => 'player_Hero',
        };

        // 1. Hideable cover present: surfaces hide with the cover label
        const withCover = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase,
            'Hero',
            stateBase.players.Hero,
            { name: 'Storage', exits: {} }
        );
        assertTrue(
            withCover.includes('hide  -  hide in/behind/under Wooden Crate'),
            'hide surfaced when hideable cover is in area, got: ' + withCover
        );
        assertFalse(
            withCover.includes('unhide  -  '),
            'unhide not surfaced when Hero is not hidden'
        );

        // 2. No cover and no threat: hide not surfaced
        window.worldState.getItemsInArea = () => [];
        window.worldState.graph.edges = [];
        const calmNoCover = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase,
            'Hero',
            stateBase.players.Hero,
            { name: 'Storage', exits: {} }
        );
        assertFalse(
            calmNoCover.includes('hide  -  '),
            'hide not surfaced in calm room without cover'
        );

        // 3. Threat/danger present without cover: surfaces hide in cover or shadows
        stateBase.players.Hero.conditions = { frightened: [{ source: 'Slasher' }] };
        const underThreat = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase,
            'Hero',
            stateBase.players.Hero,
            { name: 'Storage', exits: {} }
        );
        assertTrue(
            underThreat.includes('hide  -  hide in cover or shadows'),
            'hide surfaced when frightened/threatened, got: ' + underThreat
        );

        // 4. When player.hidden is true: surfaces unhide instead of hide
        stateBase.players.Hero.hidden = true;
        const whileHidden = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase,
            'Hero',
            stateBase.players.Hero,
            { name: 'Storage', exits: {} }
        );
        assertTrue(
            whileHidden.includes('unhide  -  step out of hiding'),
            'unhide surfaced when player.hidden is true, got: ' + whileHidden
        );
        assertFalse(
            whileHidden.includes('\nhide  -  '),
            'hide not surfaced when already hidden'
        );

        // 5. When player.state is stealthed: surfaces unhide
        stateBase.players.Hero.hidden = false;
        stateBase.players.Hero.state = 'stealthed';
        const whileStealthed = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase,
            'Hero',
            stateBase.players.Hero,
            { name: 'Storage', exits: {} }
        );
        assertTrue(
            whileStealthed.includes('unhide  -  step out of hiding'),
            'unhide surfaced when player.state is stealthed'
        );
    } finally {
        window.worldState = prevWorldState;
    }
});
