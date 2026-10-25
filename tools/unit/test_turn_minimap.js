/**
 * Unit tests for TurnMinimap (task-677).
 *
 * Verifies that TurnMinimap renders visited cells, current cell marker,
 * scope selector, and empty-state messaging without inventing state.
 */
'use strict';

test('TurnMinimap exports fetchMap, render, and mount', () => {
    const TM = window.TurnMinimap;
    assertTrue(!!TM, 'TurnMinimap exists on window');
    assertEq(typeof TM.fetchMap, 'function', 'fetchMap is a function');
    assertEq(typeof TM.render, 'function', 'render is a function');
    assertEq(typeof TM.mount, 'function', 'mount is a function');
});

test('TurnMinimap.render renders empty state when no areas visited', () => {
    const TM = window.TurnMinimap;
    const host = {
        children: [],
        appendChild(c) { this.children.push(c); return c; },
        insertBefore(c) { this.children.unshift(c); return c; },
    };

    const emptyPayload = {
        name: 'Gribba',
        current_area: 'camp_entrance',
        areas: [],
        scopes: [],
        sightline_areas: [],
        known_areas: [],
    };

    TM.render(host, emptyPayload);

    assertTrue(host.children.length > 0, 'panel was inserted into host');
    const panel = host.children[0];
    assertEq(panel.id, 'htc-map', 'panel host id is htc-map');
    const emptyNotice = panel.children.find(c => c.className === 'tmn-empty');
    assertTrue(!!emptyNotice, 'tmn-empty notice rendered');
    assertEq(emptyNotice.textContent, 'No map yet - this character has not been anywhere.', 'empty text matches');
});

test('TurnMinimap.render populates scope selector and grid when areas exist', () => {
    const TM = window.TurnMinimap;
    const host = {
        children: [],
        appendChild(c) { this.children.push(c); return c; },
        insertBefore(c) { this.children.unshift(c); return c; },
    };

    const payload = {
        name: 'Gribba',
        current_area: 'camp_gate',
        areas: [
            {
                id: 'camp_gate',
                name: 'Camp Gate',
                cell: { x: 5, y: 10 },
                world_scope_id: 'goblin_camp',
                visited: true,
                last_seen_tick: 42,
                items: ['spear'],
                characters: [],
                ways: [
                    {
                        way_id: 'way_gate',
                        direction: 'north',
                        name: 'Heavy Gate',
                        state: 'closed',
                        real_state: 'closed',
                        solid: true,
                        way_blocked: true,
                    }
                ],
            },
            {
                id: 'watchtower',
                name: 'Watchtower',
                cell: { x: 5, y: 9 },
                world_scope_id: 'goblin_camp',
                visited: true,
                last_seen_tick: 30,
                items: [],
                characters: [],
                ways: [],
            }
        ],
        scopes: [
            { id: 'goblin_camp', name: 'Goblin Camp', visited_cells: 2 }
        ],
        sightline_areas: [],
        known_areas: ['camp_gate', 'watchtower'],
    };

    TM.render(host, payload);

    const panel = host.children[0];
    assertTrue(!!panel, 'panel mounted');
    assertEq(panel.id, 'htc-map', 'panel id');

    // Head section
    const head = panel.children.find(c => c.className === 'tmn-head');
    assertTrue(!!head, 'head section exists');

    const select = head.children.find(c => c.children && c.children.some(opt => opt.value === 'goblin_camp'));
    assertTrue(!!select, 'scope select dropdown exists');
    const opt = select.children[0];
    assertEq(opt.value, 'goblin_camp', 'option value is goblin_camp');
    assertEq(opt.textContent, 'Goblin Camp (2)', 'option text includes cell count');

    // Grid section
    const grid = panel.children.find(c => c.className === 'tmn-grid');
    assertTrue(!!grid, 'grid container exists');

    // Foot legend section
    const foot = panel.children.find(c => c.className === 'tmn-foot');
    assertTrue(!!foot, 'legend foot exists');
});
