/**
 * Unit tests for the WorldPainter grid view-model (task-495).
 *
 * Loads `static/js/worldpainter/grid-model.js` in the run.cjs sandbox; no DOM.
 */

const GM = window.VW.gridModel;

const PAYLOAD = {
    grid: { w: 3, h: 2, cell_scale: 1 },
    mode: 'world',
    layers: { biome: { '0,0': 'sparse_forest', '2,1': 'ocean' }, road: { '1,0': 'road' } },
    placements: [{ id: 'v1', name: 'Village', kind: 'settlement', x: 1, y: 1, placed: true }],
    feature: { '1,1': 'v1' },
    children: [
        { id: 'v1', name: 'Village', placed: true },
        { id: 'v2', name: 'Hamlet', placed: false },
    ],
};

test('cellKey and parseCellKey round-trip', () => {
    assertEq(GM.cellKey(2, 5), '2,5', 'key');
    assertEq(GM.parseCellKey('2,5'), { x: 2, y: 5 }, 'parse');
    assertEq(GM.parseCellKey('nope'), null, 'bad parse');
    assertEq(GM.parseCellKey('1,2,3'), null, 'extra parts');
});

test('cellId is stable and namespaced by scope', () => {
    assertEq(GM.cellId('the_pines', 1, 2), 'the_pines:1,2', 'cellId');
});

test('nextMode walks world -> town -> interior and saturates', () => {
    assertEq(GM.nextMode('world'), 'town', 'world');
    assertEq(GM.nextMode('town'), 'interior', 'town');
    assertEq(GM.nextMode('interior'), 'interior', 'interior');
    assertEq(GM.nextMode(undefined), 'world', 'unknown defaults to world');
});

test('layerColor is deterministic and lightens empty values to null', () => {
    assertEq(GM.layerColor('biome', 'sparse_forest'), GM.BIOME_COLORS.sparse_forest, 'known biome');
    assertEq(GM.layerColor('biome', 'sparse_forest'), GM.layerColor('biome', 'sparse_forest'), 'stable');
    assertEq(GM.layerColor('road', 'road'), GM.ROAD_COLORS.road, 'known road');
    assertEq(GM.layerColor('biome', null), null, 'null value');
    assertTrue(/^hsl\(/.test(GM.layerColor('biome', 'unknown_biome')), 'hash colour fallback');
});

test('cellValue and featureAt read the payload safely', () => {
    assertEq(GM.cellValue(PAYLOAD, 'biome', 0, 0), 'sparse_forest', 'biome');
    assertEq(GM.cellValue(PAYLOAD, 'biome', 9, 9), undefined, 'out of layer');
    assertEq(GM.featureAt(PAYLOAD, 1, 1), 'v1', 'feature');
    assertEq(GM.featureAt(PAYLOAD, 0, 0), null, 'no feature');
    assertEq(GM.placementFor(PAYLOAD, 'v1').name, 'Village', 'placement lookup');
    assertEq(GM.placementFor(PAYLOAD, 'ghost'), null, 'missing placement');
});

test('buildRows sizes the grid y-major and carries paint + feature', () => {
    const rows = GM.buildRows(PAYLOAD);
    assertEq(rows.length, 2, 'row count');
    assertEq(rows[0].length, 3, 'col count');
    assertEq(rows[0][0].color, GM.BIOME_COLORS.sparse_forest, 'biome colour on cell');
    assertEq(rows[0][1].road, 'road', 'road value');
    assertEq(rows[1][1].feature, 'v1', 'feature marker');
    assertEq(rows[0][0].key, '0,0', 'cell key');
});

test('buildRows returns [] without a grid', () => {
    assertEq(GM.buildRows({ grid: null }), [], 'no grid');
    assertEq(GM.buildRows({}), [], 'no payload grid');
});

test('featureMap keys placements by cell', () => {
    const map = GM.featureMap(PAYLOAD);
    assertEq(map['1,1'].id, 'v1', 'placement in map');
});

test('pruneGrid counts what a shrink would drop', () => {
    assertEq(GM.pruneGrid(PAYLOAD, 3, 2), { paintKept: 3, placementsKept: 1 }, 'no shrink');
    assertEq(GM.pruneGrid(PAYLOAD, 1, 1), { paintKept: 1, placementsKept: 0 }, 'shrink drops');
});

test('childrenAvailable excludes placed features', () => {
    assertEq(GM.childrenAvailable(PAYLOAD).map((c) => c.id), ['v2'], 'only unplaced');
});

test('lineCells is an inclusive Bresenham line', () => {
    assertEq(GM.lineCells({ x: 0, y: 0 }, { x: 3, y: 0 }).length, 4, 'horizontal');
    assertEq(GM.lineCells({ x: 2, y: 2 }, { x: 2, y: 5 }).length, 4, 'vertical');
    assertEq(GM.lineCells({ x: 0, y: 0 }, { x: 2, y: 2 }).length, 3, 'diagonal');
    assertEq(GM.lineCells({ x: 1, y: 1 }, { x: 1, y: 1 }), [{ x: 1, y: 1 }], 'single cell');
    // Endpoints are exact.
    const line = GM.lineCells({ x: 0, y: 0 }, { x: 4, y: 2 });
    assertEq(line[0], { x: 0, y: 0 }, 'starts at a');
    assertEq(line[line.length - 1], { x: 4, y: 2 }, 'ends at b');
});

test('routeCells chains waypoints and de-duplicates joints', () => {
    const cells = GM.routeCells([{ x: 0, y: 0 }, { x: 2, y: 0 }, { x: 2, y: 2 }]);
    // 3 + 3 cells, minus the shared (2,0) joint counted once.
    assertEq(cells.length, 5, 'chain length');
    assertEq(cells[0], { x: 0, y: 0 }, 'first');
    assertEq(cells[cells.length - 1], { x: 2, y: 2 }, 'last');
    const keys = new Set(cells.map((c) => GM.cellKey(c.x, c.y)));
    assertEq(keys.size, 5, 'no duplicates');
});

test('estimateCompile counts areas and ways, with and without region merge', () => {
    const p = {
        grid: { w: 2, h: 2 },
        layers: { biome: { '0,0': 'sparse_forest', '1,0': 'sparse_forest',
                           '0,1': 'hills', '1,1': 'hills' } },
    };
    const flat = GM.estimateCompile(p, false);
    assertEq(flat.areas, 4, 'one area per painted cell');
    assertEq(flat.ways, 4, 'every adjacent pair is a way');
    const merged = GM.estimateCompile(p, true);
    assertEq(merged.areas, 2, 'one area per same-biome region');
    assertEq(merged.ways, 1, 'one passage per adjacent region pair');
    assertEq(GM.estimateCompile({ grid: { w: 1, h: 1 }, layers: {} }).total, 0, 'empty');
});

test('routeStats turns cells into turns and game hours (1 cell = 1 turn)', () => {
    assertEq(GM.routeStats(240).turns, 240, 'turns');
    assertTrue(GM.routeStats(240).label.indexOf('4 h 00 m') >= 0, '240 cells = 4 h');
    assertEq(GM.routeStats(240).hours, 4, 'hours');
    assertTrue(GM.routeStats(90).label.indexOf('1 h 30 m') >= 0, '90 cells = 1 h 30 m');
    assertTrue(GM.routeStats(45).label.indexOf('45 turns') >= 0, 'under an hour shows turns');
});
