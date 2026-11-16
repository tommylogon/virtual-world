/**
 * Unit tests for task-712: scope subgraph fetch error handling and fallback.
 */
'use strict';

test('ApiClient.getScopeSubgraph attaches HTTP status code to thrown error', async () => {
    const originalFetch = window.fetch;
    try {
        window.fetch = async () => ({
            ok: false,
            status: 503,
            statusText: 'SERVICE UNAVAILABLE',
            json: async () => ({ error: 'Database locked' })
        });

        let thrown = null;
        try {
            await window.ApiClient.getScopeSubgraph('goblin_camp');
        } catch (err) {
            thrown = err;
        }

        assertTrue(thrown !== null, 'throws on non-ok response');
        assertEq(thrown.status, 503, 'attaches status code 503 to error object');
        assertTrue(thrown.message.includes('503'), 'message includes status code');
    } finally {
        window.fetch = originalFetch;
    }
});

test('GraphNetwork.loadGraphData preserves scope filter and picker on 5xx transient failure', async () => {
    if (!window.GraphProjector) {
        const srcProj = window.__readFile('static/js/graph/projector.js');
        (new Function(srcProj)).call(window);
    }
    if (!window.GraphNetwork) {
        const src = window.__readFile('static/js/graph/network-manager.js');
        (new Function(src)).call(window);
    }

    const selectEl = { id: 'graph-scope-filter', value: 'goblin_camp' };
    const prevGetElementById = window.document.getElementById;
    window.document.getElementById = (id) => {
        if (id === 'graph-scope-filter') return selectEl;
        return null;
    };

    let toastMessage = null;
    const prevToast = window.toastError;
    window.toastError = (msg) => { toastMessage = msg; };

    let wholeWorldFetched = false;
    const origGetScope = window.ApiClient.getScopeSubgraph;
    const origGetNodes = window.ApiClient.getGraphNodes;
    const origGetEdges = window.ApiClient.getGraphEdges;

    window.ApiClient.getScopeSubgraph = async () => {
        const err = new Error('scope subgraph failed: 503');
        err.status = 503;
        throw err;
    };
    window.ApiClient.getGraphNodes = async () => {
        wholeWorldFetched = true;
        return {};
    };
    window.ApiClient.getGraphEdges = async () => [];

    const prevGraphManager = window.graphManager;
    window.graphManager = {
        network: {},
        _scopeFilter: 'goblin_camp',
        _persistScopeFilter: () => {},
        nodes: new Map(),
        _revealedItemIds: new Map(),
        _revealedAreaIds: new Set(),
    };

    try {
        await window.GraphNetwork.loadGraphData();

        assertEq(window.graphManager._scopeFilter, 'goblin_camp', 'scopeFilter preserved on 503');
        assertEq(selectEl.value, 'goblin_camp', 'select value preserved on 503');
        assertFalse(wholeWorldFetched, 'does not fetch whole world on transient error');
        assertTrue(toastMessage !== null && toastMessage.includes('goblin_camp'), 'surfaces error toast with scope name');
    } finally {
        window.document.getElementById = prevGetElementById;
        window.toastError = prevToast;
        window.ApiClient.getScopeSubgraph = origGetScope;
        window.ApiClient.getGraphNodes = origGetNodes;
        window.ApiClient.getGraphEdges = origGetEdges;
        window.graphManager = prevGraphManager;
    }
});

test('GraphNetwork.loadGraphData resets scope filter and falls back to whole world on 404', async () => {
    if (!window.GraphProjector) {
        const srcProj = window.__readFile('static/js/graph/projector.js');
        (new Function(srcProj)).call(window);
    }
    if (!window.GraphNetwork) {
        const src = window.__readFile('static/js/graph/network-manager.js');
        (new Function(src)).call(window);
    }

    const selectEl = { id: 'graph-scope-filter', value: 'deleted_scope' };
    const prevGetElementById = window.document.getElementById;
    window.document.getElementById = (id) => {
        if (id === 'graph-scope-filter') return selectEl;
        return null;
    };

    let toastMessage = null;
    const prevToast = window.toastError;
    window.toastError = (msg) => { toastMessage = msg; };

    let persisted = false;
    let wholeWorldNodesFetched = false;
    let wholeWorldEdgesFetched = false;

    const origGetScope = window.ApiClient.getScopeSubgraph;
    const origGetNodes = window.ApiClient.getGraphNodes;
    const origGetEdges = window.ApiClient.getGraphEdges;

    window.ApiClient.getScopeSubgraph = async () => {
        const err = new Error('scope subgraph failed: 404');
        err.status = 404;
        throw err;
    };
    window.ApiClient.getGraphNodes = async () => {
        wholeWorldNodesFetched = true;
        return { node1: { id: 'node1', type: 'area', label: 'Area 1' } };
    };
    window.ApiClient.getGraphEdges = async () => {
        wholeWorldEdgesFetched = true;
        return [];
    };

    const prevGraphManager = window.graphManager;
    window.graphManager = {
        network: {
            getPositions: () => ({}),
            setData: () => {},
            redraw: () => {},
            body: { data: { nodes: { get: () => [], forEach: () => {}, update: () => {} } } }
        },
        activeLayout: () => 'free',
        refreshFloorOptions: () => {},
        _renderCurrentView: () => {},
        _scopeFilter: 'deleted_scope',
        _persistScopeFilter: () => { persisted = true; },
        nodes: { clear: () => {}, set: () => {}, get: () => null, forEach: () => {} },
        _revealedItemIds: new Map(),
        _revealedAreaIds: new Set(),
    };

    try {
        await window.GraphNetwork.loadGraphData();

        assertEq(window.graphManager._scopeFilter, null, 'scopeFilter reset to null on 404');
        assertEq(selectEl.value, '', 'select value cleared to empty on 404');
        assertTrue(persisted, '_persistScopeFilter called to persist reset');
        assertTrue(wholeWorldNodesFetched, 'fetches whole world nodes on 404');
        assertTrue(wholeWorldEdgesFetched, 'fetches whole world edges on 404');
        assertTrue(toastMessage !== null && toastMessage.includes('deleted_scope') && toastMessage.includes('Whole world'), 'surfaces explanatory fallback toast');
    } finally {
        window.document.getElementById = prevGetElementById;
        window.toastError = prevToast;
        window.ApiClient.getScopeSubgraph = origGetScope;
        window.ApiClient.getGraphNodes = origGetNodes;
        window.ApiClient.getGraphEdges = origGetEdges;
        window.graphManager = prevGraphManager;
    }
});
