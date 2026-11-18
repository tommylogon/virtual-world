/**
 * tools/unit/test_throw_action.js
 *
 * task-953: JS unit tests for ActionNormalizer, PlanGrounding, and
 * PromptBuilder.buildAvailableActionsBlock with cross-area `throw` / `toss`.
 */

test('ActionNormalizer normalizes throw and toss with prepositions', () => {
    const an = window.ActionNormalizer;
    assertEq(an.normalizeStructuredAction({ action: 'throw', item: 'knife', target: 'fence', relation: 'over' }), 'throw knife over fence');
    assertEq(an.normalizeStructuredAction({ action: 'throw', item: 'key', target: 'yard' }), 'throw key to yard');
    assertEq(an.normalizeStructuredAction({ action: 'toss', item: 'coin', target: 'north' }), 'throw coin to north');
});

test('PlanGrounding grounds throw on carried items and exits', () => {
    const pg = window.PlanGrounding;
    const state = {
        active_player: 'Hero',
        players: {
            Hero: { name: 'Hero', current_area: 'Origin Room', inventory: ['Knife'], known: ['Yard'] },
        },
        areas: {
            'Origin Room': {
                exits: {
                    north: { direction: 'north', way_id: 'way_fence', to: 'Yard', state: 'closed', prevent_close: true },
                },
                items: [{ name: 'Crate', actions: ['examine'] }],
            },
        },
        players_in_area: [],
    };
    const facts = pg.collectFacts('Hero', state, state.players.Hero, 'Origin Room');

    const ok = pg.groundStep({ action: 'throw', item: 'Knife', target: 'north' }, facts, 'Origin Room');
    assertEq(ok, null, 'throw carried item toward exit grounds cleanly');

    const okArea = pg.groundStep({ action: 'throw', item: 'Knife', target: 'Yard' }, facts, 'Origin Room');
    assertEq(okArea, null, 'throw carried item toward connected area grounds cleanly');

    const notCarried = pg.groundStep({ action: 'throw', item: 'Crate', target: 'north' }, facts, 'Origin Room');
    assertTrue(notCarried && notCarried.includes('not carrying'), 'rejects throwing uncarried item');

    const badTarget = pg.groundStep({ action: 'throw', item: 'Knife', target: 'Volcano' }, facts, 'Origin Room');
    assertTrue(badTarget && badTarget.includes('no path or target'), 'rejects throwing toward unknown target');
});

test('contextual-actions advertises throw when carrying items with visible exits', () => {
    const prevWorldState = window.worldState;
    try {
        const stateBase = {
            active_player: 'Hero',
            current_area: 'Origin Room',
            players: {
                Hero: { name: 'Hero', current_area: 'Origin Room', vitals: {}, conditions: {}, traits: {} },
            },
            players_in_area: [],
        };
        const nodes = {
            area_origin: { id: 'area_origin', type: 'area', name: 'Origin Room', properties: {} },
            way_fence: { id: 'way_fence', type: 'way', name: 'fence', properties: { current_state: 'open' } },
            player_Hero: { id: 'player_Hero', type: 'character', name: 'Hero', properties: {} },
            item_knife: { id: 'item_knife', type: 'item', name: 'Knife', properties: { actions: ['take', 'drop'] } },
        };
        const edges = [
            { source: 'item_knife', target: 'player_Hero', type: 'carrying', properties: {} },
        ];
        window.worldState = {
            data: stateBase,
            graph: { nodes: Object.values(nodes), edges },
            getNode: (id) => nodes[id] || null,
            hasMet: () => true,
            getItemsInArea: () => [],
            isHiddenArea: () => false,
            findPlayerNodeId: (n) => (n === 'Hero' ? 'player_Hero' : null),
        };
        const currentArea = {
            name: 'Origin Room',
            ambient_light: 60,
            exits: { north: { way_id: 'way_fence', to: 'Yard', state: 'open' } },
            items: [],
        };
        const block = window.PromptBuilder.buildAvailableActionsBlock(
            stateBase,
            'Hero',
            stateBase.players.Hero,
            currentArea
        );
        assertTrue(block.includes('throw <item> to/over <way>'), 'available actions advertises throw');
    } finally {
        window.worldState = prevWorldState;
    }
});
