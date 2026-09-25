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
    assertEq(flat.ways, 6, 'every adjacent pair (orthogonal or diagonal) is a way');
    const merged = GM.estimateCompile(p, true);
    assertEq(merged.areas, 2, 'one area per same-biome region');
    assertEq(merged.ways, 1, 'one passage per adjacent region pair');
    assertEq(GM.estimateCompile({ grid: { w: 1, h: 1 }, layers: {} }).total, 0, 'empty');
    assertEq(flat.isolated, 0, 'a fully connected 2x2 has no islands');
});

test('estimateCompile connects diagonal neighbours and links true islands', () => {
    // 8-neighbour: a diagonal-only pair is connected.
    const diag = {
        grid: { w: 3, h: 3 },
        layers: { biome: { '0,0': 'dense_forest', '1,1': 'hills' } },
    };
    const flat = GM.estimateCompile(diag, false);
    assertEq(flat.ways, 1, 'a diagonal pair shares a way');
    assertEq(flat.isolated, 0, 'diagonal neighbours are not islands');
    assertEq(flat.links, 0, 'a connected pair needs no link');
    const merged = GM.estimateCompile(diag, true);
    assertEq(merged.ways, 1, 'the two regions are joined diagonally');
    assertEq(merged.isolated, 0, 'merged diagonal regions are not islands');

    // A cell touching nothing is counted as an island and gets one link way.
    const far = {
        grid: { w: 5, h: 5 },
        layers: { biome: { '0,0': 'dense_forest', '4,4': 'lake' } },
    };
    assertEq(GM.estimateCompile(far, false).isolated, 2, 'distant cells have no neighbour');
    assertEq(GM.estimateCompile(far, false).links, 1, 'the two components need one link');
    assertEq(GM.estimateCompile(far, false).ways, 1, 'the link is the only way');
    const farMerged = GM.estimateCompile(far, true);
    assertEq(farMerged.isolated, 2, 'orphan regions too');
    assertEq(farMerged.links, 1, 'and they link once');
});

test('routeStats turns cells into turns and game hours (1 cell = 1 turn)', () => {
    assertEq(GM.routeStats(240).turns, 240, 'turns');
    assertTrue(GM.routeStats(240).label.indexOf('4 h 00 m') >= 0, '240 cells = 4 h');
    assertEq(GM.routeStats(240).hours, 4, 'hours');
    assertTrue(GM.routeStats(90).label.indexOf('1 h 30 m') >= 0, '90 cells = 1 h 30 m');
    assertTrue(GM.routeStats(45).label.indexOf('45 turns') >= 0, 'under an hour shows turns');
});

test('fitReferenceRect contains the image in the grid, centred (cell units)', () => {
    // 100x50 image into a 20x20 grid: width-bound, centred vertically.
    assertEq(GM.fitReferenceRect(20, 20, 100, 50), { x: 0, y: 5, w: 20, h: 10 });
    // 50x100 image into a 20x20 grid: height-bound, centred horizontally.
    assertEq(GM.fitReferenceRect(20, 20, 50, 100), { x: 5, y: 0, w: 10, h: 20 });
    // Without image dims it fills the grid.
    assertEq(GM.fitReferenceRect(8, 4, 0, 0), { x: 0, y: 0, w: 8, h: 4 });
});

test('referenceHandleDrag: corners resize, edges crop', () => {
    const rect = { x: 0, y: 0, w: 10, h: 10 };
    const whole = { x: 0, y: 0, w: 1, h: 1 };

    // Corner resize keeps the crop (scales the whole picture).
    const grown = GM.referenceHandleDrag(rect, whole, 'se', 12, 14);
    assertEq(grown.rect, { x: 0, y: 0, w: 12, h: 14 }, 'se grows w/h');
    assertEq(grown.crop, whole, 'crop unchanged on resize');

    // Left edge drag to the right to x=2 cuts the left 20% (crop 0 -> 0.2, w 1 -> 0.8).
    const cut = GM.referenceHandleDrag(rect, whole, 'w', 2, 5);
    assertEq(cut.rect, { x: 2, y: 0, w: 8, h: 10 }, 'rect left edge follows the pointer');
    assertEq(cut.crop.x, 0.2, 'crop x advances');
    assertEq(Math.round(cut.crop.w * 100) / 100, 0.8, 'crop w shrinks');

    // Top edge drag down to y=5 cuts the top half.
    const top = GM.referenceHandleDrag(rect, whole, 'n', 5, 5);
    assertEq(top.crop.y, 0.5, 'crop y advances');
    assertEq(Math.round(top.crop.h * 100) / 100, 0.5, 'crop h shrinks');

    // Clamped: dragging an edge almost onto the far edge keeps a positive window.
    const tiny = GM.referenceHandleDrag(rect, whole, 'e', -50, 5);
    assertTrue(tiny.rect.w > 0 && tiny.crop.w > 0, 'never collapses to zero');
});

test('referenceHandlePoints puts corners on the rect and edges mid-span', () => {
    const pts = GM.referenceHandlePoints({ x: 1, y: 2, w: 4, h: 6 });
    assertEq(pts.nw, { x: 1, y: 2 }, 'nw');
    assertEq(pts.se, { x: 5, y: 8 }, 'se');
    assertEq(pts.n, { x: 3, y: 2 }, 'n edge midpoint');
    assertEq(pts.e, { x: 5, y: 5 }, 'e edge midpoint');
});
