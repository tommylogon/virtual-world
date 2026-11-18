/**
 * Unit tests for WorldPainter origin-anchored scaling and 4-way margin expansion (task-931).
 */

(() => {
const GM = window.VW.gridModel;

test('gridHandlePoints returns all 8 border and corner handles', () => {
    const pts = GM.gridHandlePoints(10, 8);
    assertEq(pts.nw, { x: 0, y: 0 }, 'nw');
    assertEq(pts.n, { x: 5, y: 0 }, 'n');
    assertEq(pts.ne, { x: 10, y: 0 }, 'ne');
    assertEq(pts.w, { x: 0, y: 4 }, 'w');
    assertEq(pts.e, { x: 10, y: 4 }, 'e');
    assertEq(pts.sw, { x: 0, y: 8 }, 'sw');
    assertEq(pts.s, { x: 5, y: 8 }, 's');
    assertEq(pts.se, { x: 10, y: 8 }, 'se');
});

test('gridHandleDragMargins computes West and North expansions with positive offsets', () => {
    const westExpand = GM.gridHandleDragMargins(10, 6, 'w', { x: -3.2, y: 3 });
    assertEq(westExpand, { w: 13, h: 6, offsetX: 3, offsetY: 0 }, 'west drag -3 adds 3 cols and shifts +3');

    const northExpand = GM.gridHandleDragMargins(10, 6, 'n', { x: 5, y: -2.4 });
    assertEq(northExpand, { w: 10, h: 8, offsetX: 0, offsetY: 2 }, 'north drag -2 adds 2 rows and shifts +2');

    const nwExpand = GM.gridHandleDragMargins(10, 6, 'nw', { x: -2, y: -4 });
    assertEq(nwExpand, { w: 12, h: 10, offsetX: 2, offsetY: 4 }, 'nw drag expands both');

    const westShrink = GM.gridHandleDragMargins(10, 6, 'w', { x: 2, y: 3 });
    assertEq(westShrink, { w: 8, h: 6, offsetX: -2, offsetY: 0 }, 'west drag +2 shrinks by 2 and shifts -2');

    const clamped = GM.gridHandleDragMargins(10, 6, 'nw', { x: 20, y: 20 });
    assertEq(clamped, { w: 1, h: 1, offsetX: -9, offsetY: -5 }, 'clamped to 1x1 minimum');
});

test('scaleGridWithAnchor scales placed areas, features, names, and layers around anchor', () => {
    const payload = {
        grid: { w: 10, h: 10 },
        layers: {
            biome: { '5,5': 'plains', '7,5': 'sparse_forest', '3,4': 'river' },
            floor: { '5,5': 1 },
        },
        names: { '7,5': 'East Woods' },
        placements: [{ id: 'town_1', x: 3, y: 5 }],
        area_placements: [{ id: 'house', x: 5, y: 5 }, { id: 'barn', x: 6, y: 7 }],
    };

    const scaled = GM.scaleGridWithAnchor(payload, { x: 5, y: 5 }, 2);
    assertEq(scaled.grid, { w: 20, h: 20 }, 'grid dims doubled');
    assertEq(scaled.layers.biome['5,5'], 'plains', 'anchor cell stays at (5,5)');
    assertEq(scaled.layers.biome['9,5'], 'sparse_forest', '(7,5) -> 5 + (7-5)*2 = (9,5)');
    assertEq(scaled.layers.biome['1,3'], 'river', '(3,4) -> (1,3)');
    assertEq(scaled.layers.floor['5,5'], 1, 'floor at anchor preserved');
    assertEq(scaled.names['9,5'], 'East Woods', 'name re-indexed');
    assertEq(scaled.placements, [{ id: 'town_1', x: 1, y: 5 }], 'feature placement scaled');
    assertEq(scaled.area_placements, [
        { id: 'house', x: 5, y: 5 },
        { id: 'barn', x: 7, y: 9 },
    ], 'area placements scaled relative to anchor');
});

test('expandGridMargins shifts cell coordinates by west and north margins', () => {
    const payload = {
        grid: { w: 6, h: 5 },
        layers: { biome: { '0,0': 'plains', '5,4': 'hills' } },
        names: { '0,0': 'Origin' },
        placements: [{ id: 'c1', x: 2, y: 1 }],
        area_placements: [{ id: 'a1', x: 1, y: 3 }],
        reference: { rect: { x: 0, y: 0, w: 6, h: 5 } },
    };

    const expanded = GM.expandGridMargins(payload, { north: 2, south: 1, east: 4, west: 3 });
    assertEq(expanded.grid, { w: 13, h: 8 }, '6+4+3=13, 5+2+1=8');
    assertEq(expanded.layers.biome, { '3,2': 'plains', '8,6': 'hills' }, 'layers shifted by (+3,+2)');
    assertEq(expanded.names, { '3,2': 'Origin' }, 'names shifted by (+3,+2)');
    assertEq(expanded.placements, [{ id: 'c1', x: 5, y: 3 }], 'placements shifted by (+3,+2)');
    assertEq(expanded.area_placements, [{ id: 'a1', x: 4, y: 5 }], 'area_placements shifted by (+3,+2)');
    assertEq(expanded.reference.rect, { x: 3, y: 2, w: 6, h: 5 }, 'reference rect shifted by (+3,+2)');
});

test('WorldPainterPalette.areaBar groups areas into optgroups and shows placed coordinates (bug-572)', () => {
    (0, eval)(window.__readFile('static/js/worldpainter/editor-palette.js'));
    const WPP = window.WorldPainterPalette;

    function makeEl(tag, style, text) {
        const attrs = {};
        const listeners = {};
        return {
            tagName: String(tag).toUpperCase(),
            style: style || '',
            textContent: text != null ? String(text) : '',
            value: '',
            label: '',
            selected: false,
            children: [],
            setAttribute(k, v) { attrs[k] = String(v); },
            getAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; },
            appendChild(child) { this.children.push(child); return child; },
            addEventListener(type, fn) { listeners[type] = fn; },
            trigger(type) { if (listeners[type]) listeners[type](); },
        };
    }

    const payload = {
        scope: { id: 'outdoor', name: 'Outdoor Grounds' },
        area_placements: [
            { id: 'a_stream', name: 'Frozen Stream Crossing', x: 44, y: 14 },
            { id: 'a_gate', name: 'Iron Gate', x: 12, y: 30 },
        ],
        unplaced_areas: [
            { id: 'a_ridge', name: 'Windy Ridge', scope_id: 'outdoor', scope_name: 'Outdoor Grounds' },
            { id: 'a_clearing', name: 'Pine Clearing', scope_id: null, scope_name: null },
            { id: 'a_foyer', name: 'Manor Foyer', scope_id: 'manor', scope_name: 'Valerious Manor' },
        ],
    };

    let renderCount = 0;
    const unplacedIds = [];
    const ctx = {
        state: { selectedArea: 'a_stream' },
        GM: () => GM,
        el: (tag, style, text) => makeEl(tag, style, text),
        btn: (label, onClick, style, title) => {
            const b = makeEl('button', style, label);
            b.title = title || '';
            b.addEventListener('click', onClick);
            return b;
        },
        render: () => { renderCount += 1; },
        unplaceArea: (id) => { unplacedIds.push(id); },
        promoteArea: () => {},
    };

    const bar = WPP.areaBar(ctx, payload);
    const sel = bar.children.find((c) => c.getAttribute && c.getAttribute('data-role') === 'wp-area');
    assertTrue(!!sel, 'wp-area select rendered');

    const optgroups = sel.children.filter((c) => c.tagName === 'OPTGROUP');
    assertEq(optgroups.length, 3, 'three optgroups rendered');
    assertEq(optgroups[0].label, 'On this grid (2)', 'placed optgroup label');
    assertEq(optgroups[1].label, 'This scope, not placed (2)', 'mine optgroup label');
    assertEq(optgroups[2].label, 'Elsewhere in the world - picking one moves it here', 'elsewhere optgroup label');

    const placedOpts = optgroups[0].children.map((o) => ({ value: o.value, text: o.textContent, selected: o.selected }));
    assertEq(placedOpts, [
        { value: 'a_stream', text: 'Frozen Stream Crossing (44,14)', selected: true },
        { value: 'a_gate', text: 'Iron Gate (12,30)', selected: false },
    ], 'placed options include cell coordinates and preserve selection');

    const mineOpts = optgroups[1].children.map((o) => ({ value: o.value, text: o.textContent }));
    assertEq(mineOpts, [
        { value: 'a_ridge', text: 'Windy Ridge' },
        { value: 'a_clearing', text: 'Pine Clearing' },
    ], 'unplaced scope areas grouped together without coordinates');

    const elsewhereOpts = optgroups[2].children.map((o) => ({ value: o.value, text: o.textContent }));
    assertEq(elsewhereOpts, [
        { value: 'a_foyer', text: 'Manor Foyer' },
    ], 'external scope areas grouped under Elsewhere');

    // Verify toolbar readout and unplace action for selected placed area
    const texts = bar.children.map((c) => c.textContent);
    assertTrue(texts.includes('on (44,14)'), 'toolbar shows placed area coordinates');
    const takeOffBtn = bar.children.find((c) => c.tagName === 'BUTTON' && c.textContent === 'Take off map');
    assertTrue(!!takeOffBtn, 'Take off map button rendered for placed area');
    takeOffBtn.trigger('click');
    assertEq(unplacedIds, ['a_stream'], 'Take off map triggers unplaceArea');

    // Verify selecting an unplaced area updates state and shows placement prompt
    sel.value = 'a_ridge';
    sel.trigger('change');
    assertEq(ctx.state.selectedArea, 'a_ridge', 'change event updates selectedArea');
    assertEq(renderCount, 1, 'change event triggers render');

    const barUnplaced = WPP.areaBar(ctx, payload);
    assertTrue(barUnplaced.children.some((c) => c.textContent === 'Click a cell to place this area'),
        'unplaced selection prompts author to click a cell');
});
})();
