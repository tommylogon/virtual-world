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

// ── placed areas (task-528) ───────────────────────────────────────────────

const PLACED = {
    area_placements: [{ id: 'area_hills', name: 'Northern Hills', x: 2, y: 1 }],
    unplaced_areas: [{ id: 'area_lake', name: 'Murk Lake' },
                     { id: 'area_river', name: 'Raven River' }],
};

test('areaAt finds the area on a cell, and areaMap keys them by cell', () => {
    assertEq(GM.areaAt(PLACED, 2, 1).id, 'area_hills', 'placed area');
    assertEq(GM.areaAt(PLACED, 0, 0), null, 'empty cell');
    assertEq(Object.keys(GM.areaMap(PLACED)), ['2,1'], 'cell keys');
    assertEq(GM.areaPlacementFor(PLACED, 'area_hills'), { id: 'area_hills', name: 'Northern Hills', x: 2, y: 1 }, 'by id');
    assertEq(GM.areaPlacementFor(PLACED, 'area_lake'), null, 'not placed here');
});

test('placeableAreas lists every area the picker offers, and never drops the picked one', () => {
    // task-541: the picker is grouped by scope, so the flat list is now the areas
    // on this grid plus every candidate — the already-placed one leads.
    assertEq(GM.placeableAreas(PLACED).map((a) => a.id),
        ['area_hills', 'area_lake', 'area_river'], 'placed first, then candidates');
    // A picked area that already sits on this map stays in the list (so it can
    // be moved), flagged with where it is.
    const picked = GM.placeableAreas(PLACED, 'area_hills');
    assertEq(picked.map((a) => a.id), ['area_hills', 'area_lake', 'area_river'], 'picked kept');
    assertEq(picked[0].placedHere, { x: 2, y: 1 }, 'placement known, and in the placed group');
    assertEq(GM.placeableAreas(PLACED, 'area_ghost').map((a) => a.id),
        ['area_hills', 'area_lake', 'area_river', 'area_ghost'], 'unknown id is still selectable');
});

test('the place helpers tolerate a payload with neither list', () => {
    assertEq(GM.areaMap({}), {}, 'no placements');
    assertEq(GM.areaAt(null, 3, 3), null, 'no payload');
    assertEq(GM.placeableAreas(undefined), [], 'no candidates');
    assertEq(GM.areaGroups({}, null), [], 'no groups');
    assertEq(GM.areaPlacementFor({}, 'x'), null, 'not placed');
});

test('gridForImageAspect makes the grid the picture (the match button)', () => {
    // The painter fits the image *into* the grid, so a different ratio leaves
    // empty bands. Matching the aspect keeps the width and derives the height.
    assertEq(GM.gridForImageAspect(20, 300, 100), { w: 20, h: 7, cells: 140, aspect: 3 },
        'a 3:1 picture on a 20-wide grid');
    assertEq(GM.gridForImageAspect(20, 100, 300), { w: 20, h: 60, cells: 1200, aspect: 1 / 3 },
        'a tall picture');
    // A very wide picture on a wide grid would ask for a fraction of a cell.
    assertEq(GM.gridForImageAspect(400, 4000, 100).h, 10, 'height never below 1');
    assertEq(GM.gridForImageAspect(20, 0, 0), null, 'no readable image → no grid');
    assertEq(GM.gridForImageAspect(20, null, null), null, 'null size → no grid');
    // The cell count stays sane, so the compiler cannot be asked to mint a
    // quarter of a million cells from a mistyped width.
    const wide = GM.gridForImageAspect(400, 100, 40000);
    assertTrue(wide.cells <= 20000, `cells capped (${wide.cells})`);
});

test('strandedCount says what a shrink would prune', () => {
    // `▦ match` shrinks the grid, and `ensure_grid` prunes out-of-bounds paint
    // and placements — so the count is shown and confirmed before that happens.
    const payload = {
        layers: { biome: { '0,0': 'hills', '19,9': 'hills' }, road: { '20,0': 'road' } },
        area_placements: [{ id: 'a1', x: 1, y: 1 }, { id: 'a2', x: 30, y: 2 }],
        placements: [{ id: 'child', x: 3, y: 3 }, { id: 'child2', x: 0, y: 40 }],
    };
    // Shrinking to 10x10: (19,9) and (20,0) both fall outside, as do a2 and child2.
    assertEq(GM.strandedCount(payload, 10, 10), 4, 'four things would be pruned');
    assertEq(GM.strandedCount(payload, 40, 50), 0, 'growing strands nothing');
    // 20x10 keeps the cell at (19,9) — the edge is inclusive — and prunes the rest.
    assertEq(GM.strandedCount(payload, 20, 10), 3, 'exactly on the edge survives');
    assertEq(GM.strandedCount(null, 10, 10), 0, 'no payload');
    assertEq(GM.strandedCount(payload, 0, 0), 0, 'no grid');
});

test('areaGroups keeps a child scope out of the parent map picker (task-541)', () => {
    // Painting the world map: the camp's rooms are members of the camp, so they
    // must not read as this map's areas — only as an explicit "elsewhere" group.
    const payload = {
        scope: { id: 'world', name: 'World' },
        area_placements: [{ id: 'area_gate', name: 'The Gate', x: 4, y: 4 }],
        unplaced_areas: [
            { id: 'area_hall', name: 'Great Hall', scope_id: 'world', scope_name: 'World' },
            { id: 'area_tent', name: 'Tent', scope_id: 'goblin_camp', scope_name: 'Goblin Camp' },
            { id: 'area_pit', name: 'Sewer Pit', scope_id: 'goblin_camp', scope_name: 'Goblin Camp' },
            { id: 'area_loose', name: 'Wanderer Camp', scope_id: null, scope_name: null },
        ],
    };
    const groups = GM.areaGroups(payload, null);
    const byKey = {};
    groups.forEach((g) => { byKey[g.key] = g.areas.map((a) => a.id); });
    assertEq(Object.keys(byKey), ['placed', 'mine', 'elsewhere'], 'three groups, in order');
    assertEq(byKey.placed, ['area_gate'], 'already on this grid');
    // Free-floating areas count as this scope's: they belong to nobody.
    assertEq(byKey.mine, ['area_hall', 'area_loose'], 'this scope + unowned');
    assertEq(byKey.elsewhere, ['area_tent', 'area_pit'], 'the camp belongs elsewhere');
    assertEq(groups[2].areas[0].scope_name, 'Goblin Camp', 'the other scope is named');

    // On the camp's own map they are ordinary candidates. The unowned area is
    // still offered here: it belongs to nobody, so any map may claim it.
    const camp = GM.areaGroups({ ...payload, scope: { id: 'goblin_camp' } }, null);
    const campKeys = camp.reduce((acc, g) => { acc[g.key] = g.areas.map((a) => a.id); return acc; }, {});
    assertEq(campKeys.mine, ['area_tent', 'area_pit', 'area_loose'], "the camp's rooms + unowned");
    assertEq(campKeys.elsewhere, ['area_hall'], 'the world map hall is elsewhere');

    // An area on this grid is never listed twice, even if the server also offers it.
    const dup = GM.areaGroups({
        scope: { id: 'world' },
        area_placements: [{ id: 'area_hall', name: 'Great Hall', x: 1, y: 1 }],
        unplaced_areas: [{ id: 'area_hall', name: 'Great Hall', scope_id: 'world' }],
    }, null);
    assertEq(dup.flatMap((g) => g.areas.map((a) => a.id)), ['area_hall'], 'listed once');
});

test('cellInfo reports everything on a cell (task-540)', () => {
    const payload = {
        scope: { id: 'camp' },
        layers: { biome: { '2,1': 'sparse_forest' }, road: { '2,1': 'road' },
                  floor: { '2,1': '3' } },
        placements: [{ id: 'deep_woods', name: 'Deep Woods', kind: 'scope' }],
        feature: { '2,1': 'deep_woods' },
        area_placements: [{ id: 'area_pit', name: 'Sewer Pit', x: 2, y: 1 }],
    };
    const info = GM.cellInfo(payload, 2, 1);
    assertEq(info.key, '2,1', 'cell key');
    assertEq(info.biome, 'sparse_forest', 'biome layer');
    assertEq(info.road, 'road', 'road layer');
    assertEq(info.floor, 3, 'floor layer is a numeric storey');
    assertEq(info.area.name, 'Sewer Pit', 'placed area');
    // The feature layer is {cellKey: child_id}; the readable name comes from the
    // scope's own placement card.
    assertEq(info.child, { id: 'deep_woods', name: 'Deep Woods', kind: 'scope' }, 'child scope');
    assertEq(info.painted, true, 'painted');
    assertEq(info.empty, false, 'not empty');

    // An empty cell says so, rather than printing three blank fields.
    const bare = GM.cellInfo({ layers: {}, placements: [], area_placements: [] }, 0, 0);
    assertEq(bare, { x: 0, y: 0, key: '0,0', biome: null, road: null, floor: null,
                     area: null, child: null, painted: false, empty: true }, 'bare cell');

    // A feature id with no card (a scope that was deleted) still names something.
    const orphan = GM.cellInfo({ layers: {}, feature: { '1,1': 'gone' },
                                 placements: [], area_placements: [] }, 1, 1);
    assertEq(orphan.child, { id: 'gone', name: 'gone', kind: null }, 'orphan child');
});

test('the floor layer is a storey index, unbounded and whole', () => {
    // 0 ground, 1 up, -1 down, and as far as the author wants: three stacked
    // rooms, a lake bottom, an 80-storey tower, a hole to hell at -900.
    assertEq(GM.PAINT_LAYERS, ['biome', 'road', 'floor'], 'layer list');
    assertEq(GM.floorNumber('3'), 3, 'above');
    assertEq(GM.floorNumber('-900'), -900, 'far below');
    assertEq(GM.floorNumber('80'), 80, 'far above');
    assertEq(GM.floorNumber('2.4'), 2, 'rounded to a whole storey');
    assertEq(GM.floorNumber(0), 0, 'ground is a real painted value');
    assertEq(GM.floorNumber(''), null, 'unpainted');
    assertEq(GM.floorNumber(null), null, 'unpainted');
    assertEq(GM.floorNumber('dirt'), null, 'a material is not a storey');

    // 0 must survive as 0 — a storey of ground is painted, not absent.
    const ground = GM.cellInfo({ layers: { floor: { '4,4': '0' } } }, 4, 4);
    assertEq(ground.floor, 0, 'ground storey');
    assertEq(ground.painted, true, 'a painted ground storey is still painted');
    assertEq(ground.empty, false, 'not an empty cell');

    assertEq(GM.floorLabel(0), 'ground (0)', 'ground reads as ground');
    assertEq(GM.floorLabel(3), 'floor 3', 'above');
    assertEq(GM.floorLabel(-3), '3 below ground (-3)', 'below');
    assertEq(GM.floorLabel(null), '—', 'unpainted reads as a dash');

    // The colour is a tint, not a value: any far-off storey must not blow up.
    ['-900', '80', '0'].forEach((v) => assertTrue(
        /^hsl\(/.test(GM.layerColor('floor', v)), `floor colour for ${v}`));
});

test('estimateCompile drops cells a hand-placed area owns (task-528)', () => {
    // Two painted cells, one of them occupied: generate mints one area, and the
    // estimate must not promise two.
    const payload = {
        layers: { biome: { '5,3': 'sparse_forest', '6,3': 'dense_forest' } },
        area_placements: [{ id: 'area_bathroom', name: 'Bathroom', x: 5, y: 3 }],
    };
    const est = GM.estimateCompile(payload, false);
    assertEq(est.areas, 1, 'one compiled area');
    assertEq(est.ways, 0, 'the lone compiled cell has no neighbour left to link');
    // Merged, the same answer: the occupied cell never enters a region.
    assertEq(GM.estimateCompile(payload, true).areas, 1, 'merge too');

    // Every painted cell taken → nothing to compile, and it says so rather than
    // promising an area that cannot be minted.
    const all = {
        layers: { biome: { '5,3': 'sparse_forest' } },
        area_placements: [{ id: 'a', name: 'A', x: 5, y: 3 }],
    };
    assertEq(GM.estimateCompile(all, false).areas, 0, 'no cells left');
});

test('estimateCompile counts road cells as places, and the road as identity (task-496)', () => {
    // A road painted over the forest line: three cells, all of them places.
    // Without merge that is 3 areas + 2 ways (a 3-cell run, 8-neighbour).
    const p = {
        layers: {
            biome: { '0,0': 'sparse_forest', '1,0': 'sparse_forest', '2,0': 'sparse_forest' },
            road: { '1,0': 'road' },
        },
    };
    const flat = GM.estimateCompile(p, false);
    assertEq(flat.areas, 3, 'the road cell is a place, not a gap in the forest');
    assertEq(flat.ways, 2, 'one way per adjacent pair along the run');

    // Merged, the road cell stays its own place: the road *is* the cell's
    // identity, so it never merges into forest. The forest is cut in two by the
    // road, and the stubs are two cells apart, so 8-neighbour merging cannot join
    // them either — two forest regions plus the road.
    const merged = GM.estimateCompile(p, true);
    assertEq(merged.areas, 3, 'two forest stubs + the road region');
    assertEq(merged.ways, 2, 'each forest stub touches the road once');

    // Three distinct identities in a row: forest, road, hills — three places.
    const beside = {
        layers: {
            biome: { '0,0': 'sparse_forest', '2,0': 'hills' },
            road: { '1,0': 'road' },
        },
    };
    assertEq(GM.estimateCompile(beside, true).areas, 3, 'forest, road and hills are three places');

    // A run of road merges with itself into one road area.
    const run = {
        layers: {
            biome: { '0,0': 'hills', '1,0': 'hills', '2,0': 'hills' },
            road: { '0,0': 'road', '1,0': 'road', '2,0': 'road' },
        },
    };
    assertEq(GM.estimateCompile(run, true).areas, 1, 'a whole road run is one area');
    assertEq(GM.estimateCompile(run, false).areas, 3, 'one area per cell without merge');

    // Road-only cells compile at all: a road painted with no biome under it is
    // still a place, and two of them make a way.
    const only = { layers: { road: { '4,4': 'road', '5,4': 'road' } } };
    assertEq(GM.estimateCompile(only, false).areas, 2, 'road-only cells are places');
    assertEq(GM.estimateCompile(only, false).ways, 1, 'and they are joined');
    assertEq(GM.estimateCompile(only, true).areas, 1, 'and they merge as one road');

    // A hand-placed area still wins over a road painted on its cell.
    const taken = {
        layers: { road: { '0,0': 'road', '1,0': 'road' } },
        area_placements: [{ id: 'area_gate', name: 'The Gate', x: 0, y: 0 }],
    };
    assertEq(GM.estimateCompile(taken, false).areas, 1, 'the occupied cell is skipped');
    assertEq(GM.estimateCompile(taken, true).areas, 1, 'merge too');
});

