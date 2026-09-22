/**
 * Unit tests for graph-export.js pure helpers (crop mapping, size clamp,
 * view-scale mapping). The DOM/vis render path is not reachable here.
 */

test('graph-export cropSource maps a normalised crop onto source pixels', () => {
    const g = window.GraphExport._internals;
    assertEq(g._cropSource({ x: 0.5, y: 0.25, w: 0.5, h: 0.5 }, 200, 100),
        { sx: 100, sy: 25, sw: 100, sh: 50 }, 'half crop of 200x100');
});

test('graph-export cropSource defaults to the full image', () => {
    const g = window.GraphExport._internals;
    assertEq(g._cropSource(null, 80, 40), { sx: 0, sy: 0, sw: 80, sh: 40 }, 'no crop');
});

test('graph-export clampExportSize leaves sizes under the cap alone', () => {
    const g = window.GraphExport._internals;
    assertEq(g._clampExportSize(800, 600, 2, 8192, 1),
        { width: 1600, height: 1200, factor: 1, clamped: false }, '2x under cap');
});

test('graph-export clampExportSize shrinks uniformly to the backing cap', () => {
    const g = window.GraphExport._internals;
    const sized = g._clampExportSize(800, 600, 2, 1000, 1);
    assertTrue(sized.clamped, 'reports clamped');
    assertTrue(sized.width <= 1000 && sized.height <= 1000, 'within cap');
    assertTrue(Math.abs(sized.width / sized.height - 800 / 600) < 0.02, 'aspect preserved');
});

test('graph-export clampExportSize accounts for devicePixelRatio', () => {
    const g = window.GraphExport._internals;
    const sized = g._clampExportSize(800, 600, 2, 1000, 2);
    assertTrue(sized.width <= 500 && sized.height <= 500, 'cap is in backing pixels');
});

test('graph-export scaledView preserves the field of view', () => {
    const g = window.GraphExport._internals;
    assertEq(g._scaledView(0.5, 800, 1600), 1, 'doubling width doubles scale');
    assertEq(g._scaledView(0.5, 0, 1600), 0.5, 'no base width keeps scale');
});
