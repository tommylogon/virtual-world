/**
 * tools/unit/test_agent_view_tags.js
 *
 * bug-579: Verify Character Inspector Bio tab renders a sanitized
 * tag-multiselect-agent-* container ID and mounts TagMultiselect for
 * characters with multi-word names (e.g. "kayla jenkins", "jake halloway")
 * in both compact and full-surface Bio tab layouts.
 */

const AV = window.InspectorAgentView;

function createMockPanel() {
    let renderedHtml = '';
    const mountedIds = new Set();
    const containerById = {};

    function syncHtml(html) {
        renderedHtml = String(html || '');
        const idMatches = renderedHtml.matchAll(/id="([^"]+)"/g);
        mountedIds.clear();
        for (const m of idMatches) {
            mountedIds.add(m[1]);
        }
    }

    function querySelector(selector) {
        if (typeof selector !== 'string') return null;
        // Simulate real CSS selector validation: unescaped spaces in an ID
        // selector (like #tag-multiselect-agent-kayla jenkins) are invalid /
        // treated as descendant combinator and never match the element.
        if (/^#[^\s]+$/.test(selector)) {
            const id = selector.slice(1);
            if (mountedIds.has(id)) {
                if (!containerById[id]) {
                    containerById[id] = { id, dataset: {} };
                }
                return containerById[id];
            }
        }
        return null;
    }

    return {
        syncHtml,
        querySelector,
        getHtml: () => renderedHtml,
    };
}

function setupShowAgentMocks(agentName, playerData, mockPanel) {
    const savedGlobals = {
        worldState: window.worldState,
        ui: window.ui,
        events: window.events,
        Lit: window.Lit,
        InspectorPanel: window.InspectorPanel,
        InspectorComponents: window.InspectorComponents,
        TagMultiselect: globalThis.TagMultiselect,
        ApiClient: globalThis.ApiClient,
        reinitChoices: globalThis.reinitChoices,
        tippy: globalThis.tippy,
        docGetElementById: document.getElementById,
        docQuerySelector: document.querySelector,
    };

    const updateCalls = [];
    const tagMounts = [];

    window.worldState = {
        data: { tick: 1 },
        tick: 1,
        players: { [agentName]: playerData },
        areas: { tavern: { name: 'Tavern' } },
        graph: { nodes: {} },
        getNode: () => null,
        getInventory: () => [],
        fetch: () => Promise.resolve(),
    };
    window.ui = { getAgentColor: () => '#bc8cff' };
    window.events = {
        getCharacterState: () => ({}),
        isAutonomous: () => false,
        getControlMode: () => 'autonomous',
    };
    window.Lit = {
        nothing: '',
        unsafeHTML: (s) => s,
        html: (strings, ...values) => {
            let out = '';
            for (let i = 0; i < strings.length; i++) {
                out += strings[i] + (i < values.length ? String(values[i] ?? '') : '');
            }
            return out;
        },
        render: (tmpl, target) => {
            mockPanel.syncHtml(tmpl);
            if (target && typeof target._setHtml === 'function') {
                target._setHtml(String(tmpl || ''));
            }
        },
    };
    window.InspectorPanel = {
        render: (tmpl) => {
            mockPanel.syncHtml(tmpl);
        },
    };
    window.InspectorComponents = {
        InspectorNodeHeader: () => '',
        InspectorDangerZone: () => '',
    };
    globalThis.TagMultiselect = function(container, opts) {
        tagMounts.push({ container, opts });
    };
    globalThis.ApiClient = {
        updateCharacter: (name, payload) => {
            updateCalls.push({ name, payload });
            return Promise.resolve({});
        },
    };
    globalThis.reinitChoices = () => {};
    globalThis.tippy = undefined;
    document.getElementById = (id) => {
        if (id === 'inspector-panel') {
            return {
                id: 'inspector-panel',
                querySelector: mockPanel.querySelector,
                querySelectorAll: () => [],
            };
        }
        return null;
    };
    document.querySelector = mockPanel.querySelector;

    return {
        tagMounts,
        updateCalls,
        restore: () => {
            window.worldState = savedGlobals.worldState;
            window.ui = savedGlobals.ui;
            window.events = savedGlobals.events;
            window.Lit = savedGlobals.Lit;
            window.InspectorPanel = savedGlobals.InspectorPanel;
            window.InspectorComponents = savedGlobals.InspectorComponents;
            globalThis.TagMultiselect = savedGlobals.TagMultiselect;
            globalThis.ApiClient = savedGlobals.ApiClient;
            globalThis.reinitChoices = savedGlobals.reinitChoices;
            globalThis.tippy = savedGlobals.tippy;
            document.getElementById = savedGlobals.docGetElementById;
            document.querySelector = savedGlobals.docQuerySelector;
        },
    };
}

test('bug-579: _renderBioTab sanitizes tagMountId for multi-word names in both layouts', () => {
    assertTrue(!!AV, 'InspectorAgentView is defined');
    const savedWs = window.worldState;
    window.worldState = window.worldState || {};
    window.worldState.getNode = window.worldState.getNode || (() => null);

    try {
        const player = { name: 'kayla jenkins', tags: ['scholar'], stats: {} };
        const compactHtml = AV._renderBioTab('kayla jenkins', player, {}, null, 'kayla jenkins', false, '#bc8cff', false);
        assertTrue(
            compactHtml.includes('id="tag-multiselect-agent-kayla_jenkins"'),
            'compact Bio tab renders sanitized tag-multiselect-agent-kayla_jenkins ID'
        );

        const fullHtml = AV._renderBioTab('kayla jenkins', player, {}, null, 'kayla jenkins', false, '#bc8cff', true);
        assertTrue(
            fullHtml.includes('id="tag-multiselect-agent-kayla_jenkins"'),
            'full-surface Bio tab renders sanitized tag-multiselect-agent-kayla_jenkins ID'
        );
    } finally {
        window.worldState = savedWs;
    }
});

test('bug-579: showAgent mounts TagMultiselect for kayla jenkins in compact mode and wires onChange', () => {
    const mockPanel = createMockPanel();
    const player = {
        name: 'kayla jenkins',
        current_area: 'tavern',
        tags: ['merchant', 'friendly'],
        stats: {},
    };
    const env = setupShowAgentMocks('kayla jenkins', player, mockPanel);
    try {
        AV.showAgent('kayla jenkins');
        assertEq(env.tagMounts.length, 1, 'TagMultiselect mounted once for kayla jenkins');
        assertEq(
            env.tagMounts[0].container.id,
            'tag-multiselect-agent-kayla_jenkins',
            'mounted into sanitized container ID'
        );
        assertEq(env.tagMounts[0].opts.appliesTo, 'characters', 'appliesTo characters');
        assertEq(env.tagMounts[0].opts.tags.join(','), 'merchant,friendly', 'initial tags passed');

        env.tagMounts[0].opts.onChange(['merchant', 'ally']);
        assertEq(env.updateCalls.length, 1, 'onChange invokes ApiClient.updateCharacter');
        assertEq(env.updateCalls[0].name, 'kayla jenkins', 'updateCharacter receives unescaped agentName');
        assertEq(env.updateCalls[0].payload.tags.join(','), 'merchant,ally', 'updateCharacter receives updated tags');
    } finally {
        env.restore();
    }
});

test('bug-579: showAgent mounts TagMultiselect for multi-word names in full-surface targetEl mode', () => {
    const mockPanel = createMockPanel();
    const player = {
        name: 'jake halloway',
        current_area: 'tavern',
        tags: ['guard'],
        stats: {},
    };
    const env = setupShowAgentMocks('jake halloway', player, mockPanel);
    const targetEl = {
        querySelector: mockPanel.querySelector,
        querySelectorAll: () => [],
        _setHtml: () => {},
    };
    try {
        AV.showAgent('jake halloway', targetEl);
        assertEq(env.tagMounts.length, 1, 'TagMultiselect mounted once for jake halloway in targetEl');
        assertEq(
            env.tagMounts[0].container.id,
            'tag-multiselect-agent-jake_halloway',
            'mounted into sanitized container ID in full-surface mode'
        );
    } finally {
        env.restore();
    }
});
