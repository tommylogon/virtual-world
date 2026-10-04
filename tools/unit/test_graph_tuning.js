/**
 * tools/unit/test_graph_tuning.js — the apply path for graph physics settings.
 *
 * GraphNetwork.applyGraphSettings() is the one writer of "physics settings
 * changed". It has two paths: the default tunes the graph as it is on screen
 * (setOptions + startSimulation — no refetch, no reseed, no camera move; the
 * old unconditional rebuild re-fit the camera ~1s after every slider tick,
 * which the user read as the graph reloading under them), and `rebuild`
 * re-derives the layout from data for Levels/Free switches.
 */
'use strict';

const NM_SRC = __readFile('static/js/graph/network-manager.ts');

function fnSource(startMarker, endMarker) {
    const start = NM_SRC.indexOf(startMarker);
    assertTrue(start !== -1, `${startMarker} exists`);
    const end = NM_SRC.indexOf(endMarker, start);
    assertTrue(end !== -1, `${endMarker} found after ${startMarker}`);
    return NM_SRC.slice(start, end);
}

test('applyGraphSettings tunes in place by default: no refetch, no signature blanking', () => {
    const src = fnSource('applyGraphSettings(rebuild = false)', 'async loadGraphData() {');
    // Everything before the refetch IS the in-place path: setOptions + wake the
    // solver + the opt-in `if (!rebuild)` block. The refetch is the first line of
    // the rebuild branch, so this slice excludes it by construction.
    const defaultPath = src.slice(0, src.indexOf('GraphNetwork.loadGraphData()'));
    assertFalse(defaultPath.includes("_lastSig = ''"), 'does not blank the load signature');
    assertFalse(defaultPath.includes('loadGraphData'), 'does not refetch the dataset');
    assertTrue(defaultPath.includes('startSimulation()'), 'wakes the frozen solver');
});

test('the rebuild path is opt-in and still refetches, reseeds and restabilizes', () => {
    const src = fnSource('applyGraphSettings(rebuild = false)', 'async loadGraphData() {');
    const rebuildBranch = src.slice(src.indexOf('if (!rebuild)'));
    assertTrue(rebuildBranch.includes('loadGraphData()'), 'rebuild refetches');
    assertTrue(rebuildBranch.includes('reseed()'), 'rebuild reseeds the ring caches');
    assertTrue(rebuildBranch.includes('stabilize(200)'), 'rebuild restabilizes');
});

test('settings handlers call the in-place path: no rebuild argument', () => {
    const html = __readFile('templates/index.html');
    const tab = html.slice(html.indexOf('id="tab-graph"'), html.indexOf('id="tab-embedding"'));
    const calls = [...tab.matchAll(/GraphNetwork\.applyGraphSettings\(([^)]*)\)/g)].map(m => m[1].trim());
    assertEq(calls.length, 14, 'modal Graph-tab handlers');
    assertTrue(calls.every(c => c === ''), 'every settings handler uses the default in-place path');
});

test('the Levels/Free switch opts into the rebuild', () => {
    const src = fnSource('toggleLayoutMode()', '    _syncLayoutButton() {');
    assertTrue(src.includes('applyGraphSettings(true)'), 'mode switch passes rebuild');
});

// ─── Node size (graphNodeScale) ──────────────────────────────────────────────

test('node size scales the drawn shapes, the guard radii, and nothing else', () => {
    const nm = __readFile('static/js/graph/network-manager.ts');
    assertTrue(nm.includes('nodeSizeScale()'), 'network-manager declares nodeSizeScale');
    // The four group definitions are one line each; slice across all of them.
    const groupsBlock = nm.slice(nm.indexOf('area: { color:'), nm.indexOf('mapCompact()'));
    // area card margins (4) + item, way, character sizes (3) = 7 scaled sites.
    const sizeHits = groupsBlock.match(/GraphNetwork\.nodeSizeScale\(\)/g) || [];
    assertEq(sizeHits.length, 7, 'scaled size/margin sites in the groups block');
    // Fonts are NOT scaled: the exact font-size expressions are untouched, so
    // labels keep a readable size while shapes grow under the knob.
    assertTrue(groupsBlock.includes('size: 14 * GraphNetwork.mapSizeScale() }'), 'area/character font stays unscaled');
    assertTrue(groupsBlock.includes('size: 12 * GraphNetwork.mapSizeScale() }'), 'item font stays unscaled');
    // The image-node branch and the compact dot scale too.
    assertTrue(nm.includes('|| 24)\n                * GraphNetwork.nodeSizeScale()'), 'image node size scaled');
    // The overlap guard grants bigger nodes more room. The needle starts at the
    // IMPLEMENTATION — the interface declares radiusOf before the body.
    const sep = __readFile('static/js/graph/separation.ts');
    const radiusImpl = sep.indexOf('radiusOf(node', sep.indexOf('spec() {'));
    const radius = sep.slice(radiusImpl, sep.indexOf('/** Areas and ways are the world'));
    assertTrue(radius.includes('graphNodeScale'), 'separation radiusOf reads graphNodeScale');
});

test('the overlap guard strength knob the UI now exposes is the one the engine reads', () => {
    const sep = __readFile('static/js/graph/separation.ts');
    const spec = sep.slice(sep.indexOf('spec() {'), sep.indexOf('radiusOf(node', sep.indexOf('spec() {')));
    assertTrue(spec.includes('graphRepelStrength'), 'spec() reads graphRepelStrength');
    const html = __readFile('templates/index.html');
    assertTrue(html.includes("id=\"graph-repel-strength\""), 'the modal exposes it');
    assertTrue(html.includes("config.graphRepelStrength="), 'the modal writes it');
});

test('the in-place path re-derives what lives outside the solver options', () => {
    // Measured live: dragging Contents length moved attachment distances 0%
    // until this existed — per-edge lengths are stamped in the dataset, and the
    // overlap guard only ran inside apply() (a full layout re-derivation).
    const src = fnSource('applyGraphSettings(rebuild = false)', 'async loadGraphData() {');
    // The re-derivation lives INSIDE the `if (!rebuild) { … return; }` block.
    const blockStart = src.indexOf('if (!rebuild)');
    const defaultPath = src.slice(blockStart, src.indexOf('return;', blockStart) + 12);
    assertTrue(defaultPath.includes('refreshEdgeLengths'), 'restamps per-edge lengths');
    assertTrue(defaultPath.includes('resolveSeparation'), 're-runs the overlap guard');
    assertTrue(defaultPath.includes('_lastArrangement'), 'only re-derives when an arrangement knob moved');
    const nm = __readFile('static/js/graph/network-manager.ts');
    assertTrue(nm.includes('refreshEdgeLengths(): number'), 'refreshEdgeLengths is implemented');
    const rl = __readFile('static/js/graph/relative-layout.ts');
    const impl = rl.indexOf('resolveSeparation(): number {');
    assertTrue(impl !== -1, 'relative-layout implements resolveSeparation');
    const body = rl.slice(impl, impl + 1200);
    assertTrue(body.includes('spec.targets'), 'pull targets come from the parents map');
});

test('the dead global edge-length knob is gone from both surfaces', () => {
    const spec = GraphToolbar.TUNING_GROUPS.flatMap(g => g.fields).map(f => f.key);
    assertFalse(spec.includes('graphSpringLength'), 'not in the Tune popover');
    const html = __readFile('templates/index.html');
    const tab = html.slice(html.indexOf('id="tab-graph"'), html.indexOf('id="tab-embedding"'));
    assertFalse(tab.includes('id="graph-spring-length"'), 'not in the modal');
    // It stays an engine fallback (rare edges carry no length of their own).
    const nm = __readFile('static/js/graph/network-manager.ts');
    assertTrue(nm.includes('graphSpringLength'), 'config key still drives the solver fallback');
});
