/**
 * Unit tests for the graph background's pure logic (task-451, bug-39).
 *
 * These cover exactly the parts that were previously only verifiable by hand in a
 * browser: the legacy-block migration, the "is there a background at all?"
 * predicate that bug-39 turned on, hit sorting, snapping, and the screen→graph
 * conversion that alt-click cycling depends on.
 */
'use strict';
const GB = window.GraphBackground;

const LAYER = {
    id: 'bg-one',
    label: 'Ground floor',
    image: '/static/images/backgrounds/floor-1.png',
    rect: { x: 0, y: 0, width: 100, height: 80 },
    rotation: 0,
    crop: { x: 0, y: 0, w: 1, h: 1 },
    opacity: 0.5,
    locked: false,
    visible: true,
};

test('legacy single-image block migrates to a one-layer list', () => {
    const block = GB._internals._normalizeBlock({
        image: '/static/images/backgrounds/old.png',
        rect: { x: -10, y: -20, width: 200, height: 100 },
        rotation: 15,
        crop: { x: 0.1, y: 0, w: 0.8, h: 1 },
        opacity: 0.4,
        locked: true,                 // old meaning: the NODE-LAYOUT freeze
        positions: { area_a: { x: 1, y: 2 } },
    });
    assertEq(block.layers.length, 1, 'one layer');
    assertEq(block.layers[0].imagePath, '/static/images/backgrounds/old.png', 'path kept');
    assertEq(block.layers[0].rect.width, 200, 'rect kept');
    assertEq(block.layers[0].rotation, 15, 'rotation kept');
    assertEq(block.layers[0].opacity, 0.4, 'opacity kept');
    assertFalse(block.layers[0].locked, 'a layer starts unlocked');
    assertTrue(block.layoutLocked, 'legacy locked became layoutLocked');
    assertEq(block.positions, { area_a: { x: 1, y: 2 } }, 'positions kept');
});

test('migration ignores nonsense and keeps a data URL local', () => {
    assertEq(GB._internals._normalizeBlock(null), null, 'null block');
    assertEq(GB._internals._normalizeBlock({}).layers.length, 0, 'empty block');
    // A record with neither an image nor a rect is not a layer.
    assertEq(GB._internals._normalizeBlock({ image: 'x' }).layers.length, 0, 'image without rect');
    assertEq(GB._internals._normalizeBlock({ rect: LAYER.rect }).layers.length, 0, 'rect without image');
    const dataUrl = GB._internals._normalizeLayer({ id: 'd', image: 'data:image/png;base64,AAAA', rect: LAYER.rect });
    assertEq(dataUrl.imagePath, null, 'data URLs have no server path');
    assertEq(dataUrl.imageSrc, 'data:image/png;base64,AAAA', 'source preserved');
});

test('the list form normalizes per-layer fields and filters junk', () => {
    const block = GB._internals._normalizeBlock({
        layers: [1, null, 'x', LAYER, { id: 'broken' }],
        positions: 'nope',
        layoutLocked: 'yes',
    });
    assertEq(block.layers.map(l => l.id), ['bg-one'], 'only real layers survive');
    assertEq(block.layers[0].visible, true, 'visible defaults to true');
    assertEq(block.positions, {}, 'non-object positions become {}');
    assertTrue(block.layoutLocked, 'truthy layoutLocked');
    // opacity 0 and visible:false must not be swallowed by falsy checks.
    const zero = GB._internals._normalizeBlock({ layers: [{ ...LAYER, opacity: 0, visible: false }] });
    assertEq(zero.layers[0].opacity, 0, 'opacity 0 survives');
    assertEq(zero.layers[0].visible, false, 'visible:false survives');
});

test('bug-39: "no background" is distinguishable from "a background with nothing in it"', () => {
    const has = GB._internals._hasBackground;
    assertFalse(has({}), 'empty block is not a background');
    assertFalse(has({ layers: [] }), 'empty list is not a background');
    assertFalse(has({ layers: [{ id: 'x', image: null, rect: null }] }), 'imageless layers are not a background');
    assertFalse(has(null), 'null is not a background');
    assertTrue(has({ layers: [LAYER] }), 'a real layer is a background');
    assertTrue(has({ layers: [], positions: { area_a: { x: 0, y: 0 } } }), 'positions alone count');
    assertTrue(has({ layers: [], layoutLocked: true }), 'a lock alone counts');
    // The legacy shape has to count too, or migration never runs.
    assertTrue(has({ image: '/static/images/backgrounds/old.png', rect: LAYER.rect }), 'legacy single image counts');
});

test('hit sorting returns the topmost layer first', () => {
    const state = GB._state;
    const saved = state.layers;
    try {
        state.layers = [
            { ...LAYER, id: 'under', rect: { x: 0, y: 0, width: 100, height: 100 } },
            { ...LAYER, id: 'over', rect: { x: 0, y: 0, width: 100, height: 100 } },
        ];
        assertEq(GB._internals._layersAt(50, 50).map(l => l.id), ['over', 'under'], 'later layers are on top');
        assertEq(GB._internals._layersAt(500, 500).length, 0, 'a point outside every layer hits nothing');
        state.layers[0].visible = false;
        assertEq(GB._internals._layersAt(50, 50).map(l => l.id), ['over'], 'hidden layers are skipped');
    } finally {
        state.layers = saved;
    }
});

test('point-in-layer accounts for rotation', () => {
    const inLayer = GB._internals._pointInLayer;
    const square = { rect: { x: 0, y: 0, width: 100, height: 100 }, rotation: 45 };
    assertTrue(inLayer(square, 50, 50), 'centre is inside');
    assertTrue(inLayer(square, 50, 90), 'the rotated square reaches further down the middle');
    // A corner of the axis-aligned box falls outside the diamond.
    assertFalse(inLayer(square, 4, 4), 'a corner is outside once rotated 45°');
    assertTrue(inLayer({ rect: { x: 0, y: 0, width: 100, height: 100 }, rotation: 0 }, 4, 4), 'inside when unrotated');
});

test('snapping pulls an edge onto a neighbour and leaves distant rects alone', () => {
    const state = GB._state;
    const saved = state.layers;
    try {
        state.layers = [{ ...LAYER, id: 'anchor', rect: { x: 0, y: 0, width: 100, height: 100 } }];
        const moving = { id: 'moving' };
        const near = GB._internals._snapRect({ x: 102, y: 0, width: 50, height: 50 }, moving);
        assertEq(near.x, 100, 'left edge snapped to the anchor right edge');
        assertEq(near.y, 0, 'y already aligned');
        const far = GB._internals._snapRect({ x: 400, y: 400, width: 50, height: 50 }, moving);
        assertEq(far.x, 400, 'out of tolerance is untouched');
        assertEq(far.y, 400, 'out of tolerance is untouched (y)');
        // The layer being dragged must not snap to itself.
        const self = GB._internals._snapRect({ x: 100, y: 0, width: 100, height: 100 }, state.layers[0]);
        assertEq(self.x, 100, 'a layer never snaps to itself');
    } finally {
        state.layers = saved;
    }
});

test('screen→graph conversion inverts the transform the layers are drawn with', () => {
    // A 400x300 graph area at (100,50) on screen, scaled 2x, centred on graph (10,20).
    window.document = {
        getElementById: () => ({ getBoundingClientRect: () => ({ left: 100, top: 50, width: 400, height: 300 }) }),
    };
    window.graphManager = { network: { getScale: () => 2, getViewPosition: () => ({ x: 10, y: 20 }) } };
    const point = GB._internals._clientToGraph(340, 240);
    assertEq(point.x, 30, 'x maps back');
    assertEq(point.y, 40, 'y maps back');
    // The container centre maps to the view position.
    const centre = GB._internals._clientToGraph(100 + 200, 50 + 150);
    assertEq(centre.x, 10, 'centre x is the view position');
    assertEq(centre.y, 20, 'centre y is the view position');
});

/* ─────────────────────────────────────────────────────────────────────────
 * The silent-failure contract.
 *
 * Commit 6fd774b8 ("feat(config): add combat damage reduction mode…") deleted
 * refreshForScope / reconcileAllForGapChange / _reconcileReferenceArt from this
 * module. All four call sites were written as
 * `window.GraphBackground && typeof window.GraphBackground.<name> === 'function'`,
 * which is **indistinguishable from "the module has not loaded yet"** — so a
 * deleted function and an unloaded module looked the same, and scope switches and
 * pitch changes stopped re-deriving the background art with nothing logged, no
 * test red, no type error (the ambient declaration was `any`).
 *
 * Two guards, because either alone has a hole: the runtime check below fails if
 * a method goes missing, and the source check fails if the `typeof … === 'function'`
 * wrapper is put back — which is what would hide the next deletion.
 * ───────────────────────────────────────────────────────────────────────── */

const CROSS_MODULE_CALLERS = {
    'static/js/graph-manager.js': ['refreshForScope', 'reconcileAllForGapChange', 'fitToPaintedGrid'],
    'static/js/graph/network-manager.js': ['reconcileAllForGapChange'],
};

test('every cross-module member the graph view calls is actually exported', () => {
    const surface = {
        init: typeof GB.init,
        showCanvasMenu: typeof GB.showCanvasMenu,
        fitToPaintedGrid: typeof GB.fitToPaintedGrid,
        refreshForScope: typeof GB.refreshForScope,
        reconcileAllForGapChange: typeof GB.reconcileAllForGapChange,
        getExportLayers: typeof GB.getExportLayers,
    };
    for (const [name, kind] of Object.entries(surface)) {
        assertEq(kind, 'function', `GraphBackground.${name} is exported`);
    }
});

test('the exported reconcile functions re-derive for the loaded scope, once per grid', async () => {
    // Not "does it exist": a stub that resolves without doing anything passes an
    // existence check and fails the user. Prove the mechanism instead — a scope
    // switch asks for that scope's grid, records the grid it derived for, and a
    // second call for the same grid costs no request (the signature cache that
    // keeps the frequent `state:updated` from refetching per paint stroke).
    //
    // `async`, so the `finally` runs after the awaited work: a returned promise
    // would restore the stubs while the reconcile was still in flight.
    const state = GB._state;
    const savedManager = window.graphManager;
    const savedApi = window.ApiClient;
    const savedLayers = state.layers;
    const savedSignature = state._reconciledFor;
    const savedDocument = window.document;
    // An earlier test replaces `window.document` with a two-method stub, so give
    // this one a canvas-capable `document`: the reconcile ends in `_render`, and
    // a missing `createElement` would fail the test for the wrong reason.
    const el = () => ({
        style: {}, dataset: {}, children: [], className: '', id: '',
        classList: { add() {}, remove() {} },
        getContext: () => new Proxy({}, { get: (t, k) => (k === 'measureText' ? () => ({ width: 0 }) : () => undefined) }),
        appendChild(c) { return c; }, insertBefore(c) { return c; },
        removeChild() {}, remove() {}, setAttribute() {}, getAttribute: () => null,
        addEventListener() {}, removeEventListener() {},
        getBoundingClientRect: () => ({ left: 0, top: 0, width: 0, height: 0 }),
    });
    window.document = Object.assign({}, savedDocument || {}, {
        createElement: el,
        getElementById: () => el(),
    });
    let fetches = 0;
    const payload = gridPayload('zone', 20, 10);
    const layer = imageLayer('zone', payload.reference.image);
    layer.rect = { x: 1, y: 2, width: 3, height: 4 };      // stale px from an older pitch
    state.layers = [layer];
    window.graphManager = { _scopeFilter: 'zone', _scopeOffsets: {} };
    window.ApiClient = { getWorldGrid: () => { fetches++; return Promise.resolve(payload); } };
    try {
        await GB._internals._reconcileReferenceArt();
        assertEq(fetches, 1, 'the world-refetch path fetched that scope\'s grid once');
        assertTrue(typeof state._reconciledFor === 'string' && state._reconciledFor.startsWith('zone|'),
            'the derived signature names the scope and its pitch');
        assertEq(layer.rect.width, 800, 'the stale px rect was re-derived from the cells');

        // `state:updated` fires on every world fetch — after every paint stroke and
        // every node edit — so the signature has to short-circuit a fetch when the
        // grid has not actually moved. This is what that cache buys.
        await GB._internals._reconcileReferenceArt();
        assertEq(fetches, 1, 'the same grid is not refetched — the signature short-circuits');

        // A moved zone is a different grid, so it must be re-derived again.
        window.graphManager._scopeOffsets = { zone: { x: 5, y: 0 } };
        await GB._internals._reconcileReferenceArt();
        assertEq(fetches, 2, 'a zone move re-derives');
        assertEq(layer.rect.x, -20 + 5 * 40, 'the art followed the new zone offset');

        // A scope switch cannot trust the previous signature, so refreshForScope
        // clears it and refetches — deliberately, and unlike the refetch path.
        state._reconciledFor = null;
        await GB.refreshForScope();
        assertEq(fetches, 3, 'a scope switch re-derives even though nothing changed yet');

        // No scope filter = the whole-world view, where there is no single grid:
        // the ordinary reconcile must decline rather than guess.
        window.graphManager._scopeFilter = null;
        state._reconciledFor = null;
        const before = fetches;
        await GB.refreshForScope();
        assertEq(fetches, before, 'the whole-world view fetches nothing');
        assertEq(state._reconciledFor, null, 'and records no signature');
    } finally {
        window.graphManager = savedManager;
        window.ApiClient = savedApi;
        window.document = savedDocument;
        state.layers = savedLayers;
        state._reconciledFor = savedSignature;
    }
});

test('no call site guards a cross-module call with typeof … === \'function\'', () => {
    for (const [path, members] of Object.entries(CROSS_MODULE_CALLERS)) {
        const src = window.__readFile(path);
        for (const member of members) {
            // Any `typeof … <member> === 'function'` / `&& <member>` existence
            // probe around these names is the pattern that hid the deletion.
            const probes = [
                new RegExp(`typeof\\s+(?:window\\.)?(?:GraphBackground\\.)?${member}\\s*===?\\s*'function'`),
                new RegExp(`GraphBackground!?\\.?${member}\\s*\\?`),
                new RegExp(`GraphBackground!?\\.?${member}\\s*&&`),
                new RegExp(`GraphBackground!?\\.?${member}\\s*\\)`),      // `&& X.m())`
            ];
            for (const re of probes) {
                assertFalse(re.test(src), `${path} must not existence-probe GraphBackground.${member} (${re})`);
            }
            // …and it must actually call it.
            assertTrue(src.includes(member), `${path} calls GraphBackground.${member}`);
        }
    }
});

test('the ambient declaration is not `any`, so a deletion is a compile error', () => {
    const src = window.__readFile('static/js/types/globals.d.ts');
    assertFalse(/^declare const GraphBackground: any;/m.test(src),
        'GraphBackground is `any`, which is why tsc could not see the deletion');
    // …and every member the callers use must be required, not optional (`?`),
    // because an optional member is exactly the "might not exist" contract that
    // produced the silent no-op.
    const block = src.slice(src.indexOf('declare const GraphBackground: {'));
    for (const member of ['refreshForScope', 'reconcileAllForGapChange', 'fitToPaintedGrid']) {
        assertTrue(new RegExp(`\\b${member}\\s*\\(`).test(block.slice(0, block.indexOf('};'))),
            `${member} is declared on GraphBackground`);
    }
    assertFalse(/\?\s*\(/.test(block.slice(0, block.indexOf('};'))), 'no member is declared optional');
});

test('paintedGridRect maps a painted scope grid to graph space', () => {
    const rect = GB._internals.paintedGridRect;
    assertEq(rect(null), null, 'no grid');
    assertEq(rect({}), null, 'empty grid');
    assertEq(rect({ w: 0, h: 4 }), null, 'zero width');
    assertEq(rect({ w: 4, h: 0 }), null, 'zero height');
    // Default spacing: the Map layout's scale (GRID_SCALE 1) = 40px per cell,
    // half a cell offset so cell 0's area is at the origin.
    assertEq(rect({ w: 8, h: 4 }), { x: -20, y: -20, width: 320, height: 160 }, 'map spacing');
    assertEq(rect({ w: 8, h: 4 }, 1), { x: -20, y: -20, width: 320, height: 160 }, 'engine units');
    // An explicit override scales with the spacing (3.5 → 140px/cell).
    assertEq(rect({ w: 8, h: 4 }, 3.5), { x: -70, y: -70, width: 1120, height: 560 }, 'override');
    const wide = rect({ w: 8, h: 4 }, 1);
    assertEq(wide.x + wide.width, 300, 'right edge is half a cell past the last column');
    assertEq(wide.y + wide.height, 140, 'bottom edge is half a cell past the last row');
});

/* ─────────────────────────────────────────────────────────────────────────
 * bug-52 / task-526 / bug-51: the art is DERIVED from a scope's cells, and
 * three functions that re-derive it (`refreshForScope`, `reconcileAllForGapChange`,
 * `_reconcileReferenceArt`) were deleted by commit 6fd774b8 while their guarded
 * call sites stayed — silent no-ops. `GraphManager.setScopeFilter` and
 * `setMapSpacing` therefore stopped moving the background art, and the zone drag
 * stopped re-deriving the dragged zone's own picture. These pin the derivation
 * itself, so a repeat cannot be silent: the art has to fit the same cells the
 * layout puts the areas on.
 * ───────────────────────────────────────────────────────────────────────── */

/** A scope whose reference has no stored rect → the derived answer is the
 *  whole-grid contain fit, which is every reference in `kraktooth_goblin_camp`. */
function gridPayload(scopeId, w, h) {
    return { scope: { id: scopeId }, grid: { w, h }, reference: { image: `/static/images/backgrounds/${scopeId}.png`, opacity: 1 } };
}

/** The `gridRect` a caller derives from a payload before laying the art out. */
function gridRectOf(payload) {
    return GB._internals.paintedGridRect(payload.grid);
}

function withPitch(pitch, fn) {
    const had = Object.prototype.hasOwnProperty.call(window, 'config');
    const before = window.config;
    window.config = Object.assign({}, window.config || {}, { graphMapSpacing: pitch });
    try { return fn(); } finally {
        if (had) window.config = before; else delete window.config;
    }
}

function withManager(manager, fn) {
    const before = window.graphManager;
    window.graphManager = manager;
    try { return fn(); } finally { window.graphManager = before; }
}

/** A layer whose picture is 4:1, so a 20x10 grid (2:1) letterboxes it — which is
 *  the real case: every `kraktooth_goblin_camp` reference is ~2.98 against a
 *  2.0 grid, so the drawn band covers the middle rows and not the whole grid. */
function imageLayer(label, src) {
    return {
        id: label, label, imagePath: src, imageSrc: src,
        image: { width: 800, height: 200 },
        rect: null, rotation: 0, crop: { x: 0, y: 0, w: 1, h: 1 },
        opacity: 1, locked: false, visible: true,
    };
}

/** What every caller derives before laying the art out: the grid rect moved by
 *  the zone's map offset (task-523), at the current pitch. */
function placedRectOf(payload, offset, pitch) {
    const rect = GB._internals.paintedGridRect(payload.grid, pitch / 40);
    return {
        x: rect.x + offset.x * pitch,
        y: rect.y + offset.y * pitch,
        width: rect.width,
        height: rect.height,
    };
}

test('the art rect is derived from the scope\'s cells, so it tracks the map pitch', () => {
    const payload = gridPayload('zone', 20, 10);
    const src = payload.reference.image;
    const layer = imageLayer('zone', src);
    // 20x10 cells at 40px = 800x400; the 4:1 picture is letterboxed to an 800x200
    // band centred in it, exactly as the painter shows it.
    withPitch(40, () => GB._internals._applyReferenceLayout(layer, payload, placedRectOf(payload, { x: 0, y: 0 }, 40), 'zone'));
    assertEq(layer.rect, { x: -20, y: 80, width: 800, height: 200 }, 'pitch 40');

    // Same cells, pitch 160: every dimension scales by exactly 4. This is the
    // property `reconcileAllForGapChange` exists to maintain, and the reason a
    // px rect goes stale the moment the pitch moves.
    const wide = imageLayer('zone', src);
    withPitch(160, () => GB._internals._applyReferenceLayout(wide, payload, placedRectOf(payload, { x: 0, y: 0 }, 160), 'zone'));
    assertEq(wide.rect, { x: -80, y: 320, width: 3200, height: 800 }, 'pitch 160');
});

test('the derived art rect is the same frame the Map layout puts the areas in', () => {
    const payload = gridPayload('zone', 20, 10);
    const src = payload.reference.image;
    const layer = imageLayer('zone', src);
    // A zone moved by the painter's zone drag (task-523).
    const offsets = { zone: { x: -4, y: 13 } };
    withPitch(40, () => withManager({ _scopeOffsets: offsets }, () => {
        GB._internals._applyReferenceLayout(layer, payload, placedRectOf(payload, offsets.zone, 40), 'zone');
    }));

    // Every area of that scope, laid out by the real engine helper.
    const u = window.GraphLayoutEngine.mapSpacing();
    const inside = (cx, cy) => {
        const node = { type: 'area', properties: { world_scope_id: 'zone', x: cx * 40, y: cy * 40 } };
        const placed = window.GraphLayoutEngine.scopedGridPosition(node.properties, node, offsets);
        assertEq(placed.x, cx * u + offsets.zone.x * u, `cell ${cx} x is cell*pitch + offset`);
        assertEq(placed.y, cy * u + offsets.zone.y * u, `cell ${cy} y is cell*pitch + offset`);
        return placed.x >= layer.rect.x && placed.x <= layer.rect.x + layer.rect.width
            && placed.y >= layer.rect.y && placed.y <= layer.rect.y + layer.rect.height;
    };
    // The picture has to cover the cells it was drawn over — this is the whole
    // complaint ("the bg images do not follow the scope zones"). Measured on the
    // real world before the fix: 0 of 463 painted areas inside the derived rect.
    assertTrue(inside(1, 4), 'a mid-grid cell is under the art');
    assertTrue(inside(10, 5), 'a centre cell is under the art');
    assertTrue(inside(18, 7), 'the last column is under the art');
    // The letterbox is honest, not a full-grid cover: rows outside the picture's
    // band sit above and below it, which is what the painter shows too.
    assertFalse(inside(0, 0), 'a cell above the letterbox band is not under the art');
    assertFalse(inside(19, 9), 'a cell below the letterbox band is not under the art');
});

test('a reference with its own stored cell rect wins over the whole-grid fit', () => {
    const payload = gridPayload('zone', 20, 10);
    payload.reference.rect = { x: 2, y: 3, w: 6, h: 4 };
    const layer = imageLayer('zone', payload.reference.image);
    withPitch(40, () => GB._internals._applyReferenceLayout(layer, payload, gridRectOf(payload), 'zone'));
    assertEq(layer.rect, { x: 80, y: 120, width: 240, height: 160 }, 'stored rect in cells x pitch');
});

test('the crop window is copied so both views show the same part of the picture', () => {
    const payload = gridPayload('zone', 20, 10);
    payload.reference.crop = { x: 2, y: 0, w: 0.5, h: 1 };
    const layer = imageLayer('zone', payload.reference.image);
    withPitch(40, () => GB._internals._applyReferenceLayout(layer, payload, gridRectOf(payload), 'zone'));
    assertEq(layer.crop, { x: 2, y: 0, w: 0.5, h: 1 }, 'crop carried over');
    const bare = imageLayer('zone', payload.reference.image);
    withPitch(40, () => GB._internals._applyReferenceLayout(bare, { grid: payload.grid, reference: { image: payload.reference.image } }, gridRectOf(payload), 'zone'));
    assertEq(bare.crop, { x: 0, y: 0, w: 1, h: 1 }, 'a reference with no crop resets to the whole picture');
});

test('_referenceLayerFor finds a scope by its reference image, not by what is active', () => {
    const a = gridPayload('alpha', 8, 8);
    const b = gridPayload('beta', 8, 8);
    const state = GB._state;
    const saved = state.layers, savedActive = state.activeId;
    try {
        state.layers = [imageLayer('alpha', a.reference.image), imageLayer('beta', b.reference.image)];
        state.activeId = 'alpha';
        assertEq(GB._internals._referenceLayerFor('beta', b).label, 'beta',
            "the active layer is a UI selection and says nothing about which zone is being dragged");
        assertEq(GB._internals._referenceLayerFor('gamma', { grid: { w: 8, h: 8 }, reference: null }), null,
            'a scope with no reference has no art');
    } finally { state.layers = saved; state.activeId = savedActive; }
});

test('a zone drag re-derives the dragged zone\'s own art and leaves the others alone', () => {
    const a = gridPayload('alpha', 8, 8);
    const b = gridPayload('beta', 8, 8);
    const state = GB._state;
    const saved = state.layers, savedActive = state.activeId;
    try {
        const layerA = imageLayer('alpha', a.reference.image);
        const layerB = imageLayer('beta', b.reference.image);
        state.layers = [layerA, layerB];
        state.activeId = 'alpha';                       // the user selected the OTHER zone's map
        // Both grids cached, as a completed drag would have them.
        GB._internals._cacheGrid('alpha', a);
        GB._internals._cacheGrid('beta', b);
        withPitch(40, () => withManager({ _scopeOffsets: { alpha: { x: 0, y: 0 }, beta: { x: 9, y: 0 } } }, () => {
            assertTrue(GB._internals._reapplyZoneArt('beta'), 'the dragged zone reports a re-apply');
            assertFalse(GB._internals._reapplyZoneArt('nowhere'), 'an uncached scope is a no-op');
        }));
        // beta sits 9 cells right of its grid; alpha did not move.
        assertEq(layerB.rect.x, -20 + 9 * 40, 'the dragged zone art followed the offset');
        assertEq(layerA.rect, null, "the active-but-untouched zone's art was not nudged");
        assertEq(GB._internals._cachedGrid('beta').grid, { w: 8, h: 8 }, 'the grid payload is cached for the drag');
        GB._internals._cacheGrid('beta', null);
    } finally { state.layers = saved; state.activeId = savedActive; }
});

test('_allNodePositions reads hidden nodes too — getPositions() drops them', () => {
    const network = {
        // Items and triggers are hidden by default, so a saved layout used to
        // lose exactly those (task-617).
        getPositions: () => ({ visible_a: { x: 1, y: 2 } }),
        body: {
            nodes: { visible_a: { x: 1, y: 2 }, hidden_b: { x: 3, y: 4 } },
            data: { nodes: { getIds: () => ['visible_a', 'hidden_b'] } },
        },
    };
    assertEq(GB._internals._allNodePositions(network), { visible_a: { x: 1, y: 2 }, hidden_b: { x: 3, y: 4 } },
        'the hidden node is included');
    // A stale body entry (left behind by a rebuild) is dropped.
    const stale = { getPositions: () => ({ live: { x: 9, y: 9 } }), body: { nodes: { gone: { x: 0, y: 0 } }, data: { nodes: { getIds: () => ['live'] } } } };
    assertEq(GB._internals._allNodePositions(stale), { live: { x: 9, y: 9 } }, 'stale body entries are filtered');
    // A body with nothing placed in it falls back to getPositions rather than
    // reporting "no positions" and silently persisting nothing.
    assertEq(GB._internals._allNodePositions({ getPositions: () => ({ live: { x: 9, y: 9 } }), body: { nodes: {} } }),
        { live: { x: 9, y: 9 } }, 'an empty body falls back to getPositions');
    assertEq(GB._internals._allNodePositions(null), {}, 'no network, no positions');
});

test('saving the layout to the world leaves a painted area on its own cell', () => {
    // The regression that corrupted a whole world: persistPositionsToWorld wrote
    // every node's CANVAS position into properties.x/y, including painted areas,
    // whose x/y are the compiler's `cell * 40`. The Map layout then scaled those
    // pixels by the pitch again (8.25x at pitch 330) and re-added the zone
    // offset, so the areas walked off their own background art — measured at
    // 0 of 463 painted areas inside the derived image rect.
    const painted = { type: 'area', properties: { cell: { x: 7, y: 6 }, x: 280, y: 240, world_scope_id: 'zone' } };
    const dragged = { type: 'area', properties: { x: 11, y: 13 } };        // hand-placed: canvas px, keep them
    const item = { type: 'item', properties: { x: 5, y: 6 } };
    let captured = null;
    const manager = {
        _graphNodesObj: { painted_area: painted, dragged_area: dragged, item_thing: item },
        network: {
            getPositions: () => ({ painted_area: { x: 969, y: 6423 } }),   // what getPositions() alone would save
            body: {
                nodes: {
                    painted_area: { x: 969, y: 6423 },
                    dragged_area: { x: 11, y: 13 },
                    item_thing: { x: 5, y: 6 },
                },
                data: { nodes: { getIds: () => ['painted_area', 'dragged_area', 'item_thing'] } },
            },
        },
    };
    const beforeApi = window.ApiClient;
    window.ApiClient = { batchGraph: (ops) => { captured = ops; return {}; } };
    try {
        const result = withManager(manager, () => GB.persistPositionsToWorld());
        // The function is async; drive it to completion here.
        return result.then((res) => {
            assertEq(res.skipped, 1, 'the painted area was skipped');
            assertEq(res.saved, 2, 'the hand-placed area and the item were saved');
            const ids = captured.map((op) => op.payload.node_id).sort();
            assertEq(ids, ['dragged_area', 'item_thing'], 'no op targets the painted area');
            const op = captured.find((o) => o.payload.node_id === 'dragged_area');
            assertEq(op.payload.patch.properties, { x: 11, y: 13 }, 'a hand-placed position is saved verbatim');
        });
    } finally {
        window.ApiClient = beforeApi;
    }
});
