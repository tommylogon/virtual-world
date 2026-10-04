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
    // The default path is everything BEFORE the opt-in branch; the rebuild
    // branch legitimately refetches, so scope the assertions to the default.
    const defaultPath = src.slice(0, src.indexOf('if (!rebuild)'));
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
    assertEq(calls.length, 13, 'modal Graph-tab handlers');
    assertTrue(calls.every(c => c === ''), 'every settings handler uses the default in-place path');
});

test('the Levels/Free switch opts into the rebuild', () => {
    const src = fnSource('toggleLayoutMode()', '    _syncLayoutButton() {');
    assertTrue(src.includes('applyGraphSettings(true)'), 'mode switch passes rebuild');
});
