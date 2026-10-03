/**
 * Unit tests for the sprite-sheet grid geometry (task-678).
 *
 * Covers the pure half in static/js/inspector/sprite-sheet-geometry.js — the
 * frame-plus-dividers model, its drag/edit operations, and whitespace
 * auto-detection. The canvas half cannot run in this Node sandbox.
 */
'use strict';
const G = window.SpriteSheetGeometry;
const OLD = window.SpriteSheet;

const gsum = (arr, f) => arr.reduce((a, x) => a + f(x), 0);
const gkey = c => `${c.row},${c.col},${c.x},${c.y},${c.w},${c.h}`;

// ── the load-bearing regression: the new model reproduces the old grid ──

test('cellsFromCuts(cutsFromGrid) is identical to computeCells for every shape', () => {
    // The change from a rows×cols count to a frame+dividers is only safe if the
    // even case is bit-identical, not merely similar. These are the shapes the
    // old `computeCells` tests pinned, plus odd sizes where rounding differs.
    const shapes = [
        [1536, 1024, 3, 4], [400, 300, 3, 4], [100, 100, 3, 3],
        [101, 97, 7, 5], [7, 3, 3, 7], [1920, 1080, 1, 1], [255, 255, 16, 16],
    ];
    shapes.forEach(([w, h, r, c]) => {
        assertEq(
            G.cellsFromCuts(G.cutsFromGrid(w, h, r, c)).map(gkey).join('|'),
            OLD.computeCells(w, h, r, c, {}).map(gkey).join('|'),
            `${w}x${h} ${r}x${c} identical`);
    });
});

test('cellsFromCuts applies labelTrim identically to computeCells', () => {
    const cuts = G.cutsFromGrid(400, 300, 3, 4);
    assertEq(
        G.cellsFromCuts(cuts, 0.1).map(gkey).join('|'),
        OLD.computeCells(400, 300, 3, 4, { labelTrim: 0.1 }).map(gkey).join('|'),
        'labelTrim matches');
});

test('evenBoundaries land exactly on both ends so cells cover with no gap', () => {
    assertEq(G.evenBoundaries(0, 1536, 4).join(','), '0,384,768,1152,1536', 'even span');
    assertEq(G.evenBoundaries(0, 100, 3).pop(), 100, 'last boundary is the end');
    // Independent rounding must not repeat on a span too small to hold the cells.
    assertEq(G.evenBoundaries(0, 5, 8).join(','), '0,1,2,3,4,5', 'deduped, still ends at 5');
});

// ── what the old count-based model could not express ──

test('a frame excludes a title banner without wasting a cell', () => {
    // 90px banner, then a 4x3 block. The old grid could only start at y=0.
    const cuts = { x0: 0, y0: 90, x1: 800, y1: 590, colCuts: [200, 400, 600], rowCuts: [256, 423] };
    const cells = G.cellsFromCuts(cuts);
    assertEq(cells.length, 12, '12 cells, none of them the banner');
    assertEq(cells[0].y, 90, 'first cell starts below the banner');
    assertTrue(cells.every(c => c.y >= 90), 'no cell reaches into the banner');
});

test('uneven dividers give mixed panel sizes in one grid', () => {
    // One 500px full-body panel beside two 250px detail panels.
    const cuts = { x0: 0, y0: 0, x1: 1000, y1: 400, colCuts: [500], rowCuts: [] };
    const cells = G.cellsFromCuts(cuts);
    assertEq(cells.length, 2, 'two panels');
    assertEq(cells[0].w, 500, 'wide panel');
    assertEq(cells[1].w, 500, 'second panel');
    const rows = G.cellsFromCuts({ x0: 0, y0: 0, x1: 1000, y1: 900, colCuts: [], rowCuts: [600, 750] });
    assertEq(rows.map(c => c.h).join(','), '600,150,150', 'rows of differing heights');
});

test('cellsFromCuts reads in order and covers the frame exactly', () => {
    const cuts = { x0: 10, y0: 20, x1: 310, y1: 220, colCuts: [100, 200], rowCuts: [100] };
    const cells = G.cellsFromCuts(cuts);
    assertEq(cells.length, 6, '3x2');
    assertEq(gkey(cells[0]), '0,0,10,20,90,80', 'first cell top-left');
    assertEq(gsum(cells.filter(c => c.row === 0), c => c.w), 300, 'row covers width exactly');
    assertEq(gsum(cells.filter(c => c.col === 0), c => c.h), 200, 'col covers height exactly');
    assertEq(cells[5].x + cells[5].w, 310, 'last col ends on the frame');
});

// ── the drag / edit operations ──

test('moveDivider clamps between neighbours so a line cannot be dragged through', () => {
    const cuts = { x0: 0, y0: 0, x1: 900, y1: 300, colCuts: [300, 600], rowCuts: [] };
    const m = G.MIN_CELL_PX;
    // Drag the middle divider far left: stops one minCell past its neighbour.
    assertEq(G.moveDivider(cuts, 'x', 0, -500).colCuts[0], 0 + m, 'clamped to neighbour');
    // Far right: stops one minCell short of the next.
    assertEq(G.moveDivider(cuts, 'x', 0, 5000).colCuts[0], 600 - m, 'clamped to next');
    // The ends are bounded by the frame instead of a neighbour.
    assertEq(G.moveDivider(cuts, 'x', 1, 9999).colCuts[1], 900 - m, 'last divider stops at frame');
    assertEq(G.moveDivider(cuts, 'x', 1, -999).colCuts[1], 300 + m, 'last divider stops at neighbour');
    // Vertical is independent of horizontal.
    const v = G.moveDivider(cuts, 'y', 0, 150);
    assertEq(v.rowCuts, [], 'no row dividers to move');
    assertEq(v.colCuts, cuts.colCuts, 'cols untouched');
});

test('moveDivider rejects an out-of-range index and never mutates', () => {
    const cuts = { x0: 0, y0: 0, x1: 300, y1: 100, colCuts: [150], rowCuts: [] };
    assertEq(G.moveDivider(cuts, 'x', 5, 100), cuts, 'index past the end is a no-op');
    assertEq(G.moveDivider(cuts, 'x', -1, 100), cuts, 'negative index is a no-op');
    G.moveDivider(cuts, 'x', 0, 40);
    assertEq(cuts.colCuts[0], 150, 'input untouched');
});

test('recountCuts keeps the frame and the divider count the inputs asked for', () => {
    const cuts = { x0: 100, y0: 90, x1: 700, y1: 490, colCuts: [333], rowCuts: [] };
    const more = G.recountCuts(cuts, 3, 4);
    assertEq(more.x0, 100, 'frame left preserved');
    assertEq(more.y0, 90, 'frame top preserved — the banner stays excluded');
    assertEq(more.x1, 700, 'frame right preserved');
    assertEq(more.y1, 490, 'frame bottom preserved');
    assertEq(more.colCuts.length, 4 - 1, '4 columns -> 3 dividers');
    assertEq(more.rowCuts.length, 3 - 1, '3 rows -> 2 dividers');
    assertEq(G.cellsFromCuts(more).length, 12, '12 cells');
    // Fewer lines than before must shed dividers, not leave a crowded grid.
    assertEq(G.recountCuts(more, 1, 2).colCuts.length, 1, '2 columns -> 1 divider');
});

test('clampCuts sorts, dedupes and drops dividers too close to a frame edge', () => {
    const m = G.MIN_CELL_PX;
    const out = G.clampCuts({ x0: 0, y0: 0, x1: 100, y1: 100,
        colCuts: [90, 10, 50, 50, 3, -5, 200], rowCuts: [40] }, 100, 100);
    // 3 is 3px from the frame edge (below minCell) so it goes; 10 and 90 are each
    // 10px from an edge, which is legal, so both stay.
    assertEq(out.colCuts.join(','), '10,50,90', 'sorted, deduped, illegal ones dropped');
    assertEq(out.rowCuts.join(','), '40', 'valid divider kept');
    // A frame too small to honour minCell is widened, not inverted.
    const tiny = G.clampCuts({ x0: 50, y0: 50, x1: 50, y1: 50, colCuts: [], rowCuts: [] }, 100, 100);
    assertTrue(tiny.x1 > tiny.x0, 'x1 pushed out');
    assertTrue(tiny.y1 > tiny.y0, 'y1 pushed out');
});

test('addDivider inserts in order and removeDivider takes one out', () => {
    let cuts = { x0: 0, y0: 0, x1: 900, y1: 300, colCuts: [300], rowCuts: [] };
    cuts = G.addDivider(cuts, 'x', 600);
    assertEq(cuts.colCuts.join(','), '300,600', 'appended in order');
    cuts = G.addDivider(cuts, 'x', 100);
    assertEq(cuts.colCuts.join(','), '100,300,600', 'prepended in order');
    cuts = G.addDivider(cuts, 'y', 150);
    assertEq(cuts.rowCuts.join(','), '150', 'axes independent');
    cuts = G.removeDivider(cuts, 'x', 1);
    assertEq(cuts.colCuts.join(','), '100,600', 'middle removed');
    assertEq(G.removeDivider(cuts, 'x', 9), cuts, 'bad index is a no-op');
});

test('hitDivider resolves to the nearest line within tolerance', () => {
    const cuts = { x0: 0, y0: 0, x1: 1000, y1: 300, colCuts: [300, 600], rowCuts: [] };
    assertEq(G.hitDivider(cuts, 'x', 298, 10), 0, 'near line 0');
    assertEq(G.hitDivider(cuts, 'x', 590, 20), 1, 'near line 1');
    assertEq(G.hitDivider(cuts, 'x', 450, 10), -1, 'dead zone between lines');
    assertEq(G.hitDivider(cuts, 'y', 100, 10), -1, 'no row dividers to hit');
});

// ── whitespace auto-detection ──

test('guttersFromProfile returns run centres and ignores margins and noise', () => {
    // blank margin, ink, gutter, ink, thin noise gap, ink, blank margin
    const p = [0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0];
    assertEq(G.guttersFromProfile(p, { minRun: 3 }).join(','), '5.5', 'one real gutter at the run centre');
    // Thin runs are noise, not gutters.
    assertEq(G.guttersFromProfile([1, 1, 0, 1, 1], { minRun: 3 }).join(','), '', '2px gap ignored');
    // All blank -> no gutters (caller falls back to an even grid).
    assertEq(G.guttersFromProfile([0, 0, 0], { minRun: 3 }).join(','), '', 'blank sheet');
    assertEq(G.guttersFromProfile([], {}).join(','), '', 'empty profile');
});

test('guttersFromProfile separates a caption gutter from the panel it sits under', () => {
    // 3 rows of art with a caption band and a gutter under each, plus a banner band.
    const p = [];
    for (let r = 0; r < 3; r++) { for (let i = 0; i < 40; i++) p.push(1); for (let i = 0; i < 8; i++) p.push(0); }
    assertEq(G.guttersFromProfile(p, { minRun: 4 }).length, 2, 'two gutters between three rows');
});

test('cutsFromProfiles scales SAMPLE indices back into source pixels', () => {
    // A 100-sample profile describing a 1000px sheet: every detected position must
    // land 10x further along. profileRects caps the long edge at 400px, so using
    // the raw index would put every cut at 1/2.5th of where it belongs on a real
    // reference sheet — the failure this test exists to catch.
    const rowP = new Array(100).fill(1);
    const colP = new Array(100).fill(1);
    for (let i = 0; i < 10; i++) { rowP[i] = 0; colP[i] = 0; }          // top/left margin
    for (let i = 90; i < 100; i++) { rowP[i] = 0; colP[i] = 0; }        // bottom/right margin
    for (let i = 48; i < 52; i++) { rowP[i] = 0; colP[i] = 0; }        // one central gutter
    const cuts = G.cutsFromProfiles(rowP, colP, 1000, 1000, { minRun: 3 });
    assertEq(cuts.x0, 100, 'left margin scaled to px');
    assertEq(cuts.y0, 100, 'top margin scaled to px');
    assertEq(cuts.x1, 900, 'right margin scaled to px');
    assertEq(cuts.y1, 900, 'bottom margin scaled to px');
    assertEq(cuts.colCuts.join(','), '500', 'central column gutter scaled to px');
    assertEq(cuts.rowCuts.join(','), '500', 'central row gutter scaled to px');
    assertEq(G.cellsFromCuts(cuts).length, 4, '4 quadrants');
    // A 1:1 profile (small sheet, no downsampling) must be unaffected. The content
    // box has to clear MIN_CELL_PX or the frame is legitimately rejected as too
    // small and the whole sheet is used instead.
    const flat = [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0];
    const tiny = G.cutsFromProfiles(flat, flat, 20, 20, { minRun: 1 });
    assertEq(`${tiny.x0},${tiny.y0},${tiny.x1},${tiny.y1}`, '2,2,18,18', '1:1 unchanged');
});

test('cutsFromProfiles degrades to a 1x1 whole sheet when there is no content', () => {
    const blank = new Array(50).fill(0);
    const cuts = G.cutsFromProfiles(blank, blank, 400, 400, { minRun: 3 });
    assertEq(cuts.x0, 0, 'no collapse to nothing');
    assertEq(cuts.x1, 400, 'whole width kept');
    assertEq(cuts.colCuts.length, 0, 'no invented dividers');
    assertEq(cuts.rowCuts.length, 0, 'no invented dividers');
});