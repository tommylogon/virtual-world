/**
 * tools/unit/test_entity_editor.js
 *
 * task-673: Unit tests for EntityEditor frame: mount/unmount full-surface
 * editors alongside inspector panel.
 */
'use strict';

(() => {
    // Setup mock environment
    window.Lit = window.Lit || {
        html: (strings, ...values) => ({ strings, values }),
        render: (template, container) => {
            if (template === window.Lit.nothing) {
                if (container) container.textContent = '';
                return;
            }
            if (container) container.dataset.litRendered = '1';
        },
        nothing: Symbol('nothing'),
        unsafeHTML: (str) => str,
    };

    window.worldState = {
        data: { tick: 42 },
        players: {
            'Aria': { name: 'Aria', current_area: 'tavern', tags: ['bard'], node_id: 'player_Aria' },
        },
        areas: {
            'tavern': { name: 'The Prancing Pony', type: 'area', properties: {} },
        },
        graph: {
            nodes: {
                'char_aria': { id: 'char_aria', name: 'Aria', type: 'character' },
                'item_sword': { id: 'item_sword', name: 'Iron Sword', type: 'item', properties: { description: 'A sharp blade.' } },
                'tavern': { id: 'tavern', name: 'The Prancing Pony', type: 'area', properties: {} },
            },
        },
        getNode(id) {
            return this.graph.nodes[id] || null;
        },
        getInventory() {
            return [];
        },
        fetch: async () => {},
    };

    window.InspectorPanel = {
        renderCalls: 0,
        render(tmpl) {
            this.renderCalls++;
            const p = document.getElementById('inspector-panel');
            if (p) p.dataset.peekRendered = '1';
        },
    };

    window.InspectorAgentView = {
        showCalls: 0,
        lastTargetEl: null,
        showAgent(name, targetEl) {
            this.showCalls++;
            this.lastTargetEl = targetEl;
            if (targetEl) targetEl.dataset.agentViewMounted = name;
        },
    };

    window.InspectorItemView = {
        showCalls: 0,
        lastTargetEl: null,
        showItem(nodeId, node, targetEl) {
            this.showCalls++;
            this.lastTargetEl = targetEl;
            if (targetEl) targetEl.dataset.itemViewMounted = nodeId;
        },
    };

    window.InspectorAreaView = {
        showCalls: 0,
        lastTargetEl: null,
        showArea(nodeId, node, targetEl) {
            this.showCalls++;
            this.lastTargetEl = targetEl;
            if (targetEl) targetEl.dataset.areaViewMounted = nodeId;
        },
    };

    Object.assign(window.ApiClient, {
        updateNodeCalls: [],
        updateCharCalls: [],
        updateNode(id, payload) {
            this.updateNodeCalls.push({ id, payload });
            return Promise.resolve({ success: true });
        },
        updateCharacter(name, payload) {
            this.updateCharCalls.push({ name, payload });
            return Promise.resolve({ success: true });
        },
    });

    // Load EntityEditor module
    if (typeof __readFile === 'function') {
        eval(__readFile('static/js/inspector/entity-editor.js'));
    }

    const EntityEditor = window.EntityEditor;

    test('EntityEditor.mount mounts character without writing to inspector-panel', () => {
        assertTrue(typeof EntityEditor.mount === 'function', 'EntityEditor.mount exists');
        assertTrue(typeof EntityEditor.unmount === 'function', 'EntityEditor.unmount exists');

        const peekBefore = window.InspectorPanel.renderCalls;
        EntityEditor.mount('character', 'Aria');

        assertTrue(EntityEditor.isOpen(), 'EntityEditor is open');
        assertEq(window.InspectorPanel.renderCalls, peekBefore, 'inspector-panel was NOT written to');

        const container = document.getElementById('entity-editor');
        assertTrue(Boolean(container), '#entity-editor container exists');
        assertEq(container.style.display, 'flex', 'container is visible as flex');

        const badge = document.getElementById('entity-editor-kind-badge');
        assertEq(badge.textContent, '👤 Character', 'badge shows character icon and name');

        const nameInput = document.getElementById('entity-editor-name-input');
        assertEq(nameInput.value, 'Aria', 'header input displays character name');

        const idLabel = document.getElementById('entity-editor-node-id');
        assertEq(idLabel.textContent, 'char_aria', 'header displays character node ID');

        const status = document.getElementById('entity-editor-status');
        assertEq(status.textContent, '✔ Saved', 'status defaults to Saved');

        const bodyEl = document.getElementById('entity-editor-body');
        assertEq(bodyEl.dataset.agentViewMounted, 'Aria', 'agent-view was mounted into entity-editor-body');

        // Unmount
        EntityEditor.unmount();
        assertEq(EntityEditor.isOpen(), false, 'EntityEditor is closed');
        assertEq(container.style.display, 'none', 'container is hidden');
    });

    test('EntityEditor mounts item and area cleanly', () => {
        // Mount item
        EntityEditor.mount('item', 'item_sword');
        assertTrue(EntityEditor.isOpen(), 'item editor is open');
        const badgeItem = document.getElementById('entity-editor-kind-badge');
        assertEq(badgeItem.textContent, '📦 Item', 'badge shows item');
        const nameInputItem = document.getElementById('entity-editor-name-input');
        assertEq(nameInputItem.value, 'Iron Sword', 'displays item name');
        const bodyItem = document.getElementById('entity-editor-body');
        assertEq(bodyItem.dataset.itemViewMounted, 'item_sword', 'item-view mounted');
        EntityEditor.unmount();

        // Mount area
        EntityEditor.mount('area', 'tavern');
        assertTrue(EntityEditor.isOpen(), 'area editor is open');
        const badgeArea = document.getElementById('entity-editor-kind-badge');
        assertEq(badgeArea.textContent, '🏠 Area', 'badge shows area');
        const nameInputArea = document.getElementById('entity-editor-name-input');
        assertEq(nameInputArea.value, 'The Prancing Pony', 'displays area name');
        const bodyArea = document.getElementById('entity-editor-body');
        assertEq(bodyArea.dataset.areaViewMounted, 'tavern', 'area-view mounted');
        EntityEditor.unmount();
    });

    test('EntityEditor focus management traps and restores to opener', () => {
        const opener = document.createElement('button');
        opener.id = 'test-opener-btn';
        document.body.appendChild(opener);
        opener.focus();

        EntityEditor.mount('character', 'Aria', opener);

        const nameInput = document.getElementById('entity-editor-name-input');
        assertTrue(document.activeElement === nameInput, 'focus moves to header name input on open');

        EntityEditor.unmount();
        assertTrue(document.activeElement === opener, 'focus restores to opener element on close');
    });

    test('EntityEditor closes on Escape key and backdrop click', () => {
        const opener = document.createElement('button');
        opener.id = 'test-esc-opener';
        document.body.appendChild(opener);

        // Test Escape key
        EntityEditor.mount('item', 'item_sword', opener);
        assertTrue(EntityEditor.isOpen(), 'open before Esc');
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        assertEq(EntityEditor.isOpen(), false, 'closed after Esc key');
        assertTrue(document.activeElement === opener, 'focus restored after Esc key');

        // Test backdrop click
        EntityEditor.mount('item', 'item_sword', opener);
        assertTrue(EntityEditor.isOpen(), 'open before backdrop click');
        const backdrop = document.querySelector('.entity-editor-backdrop');
        assertTrue(Boolean(backdrop), 'backdrop element found');
        backdrop.dispatchEvent(new MouseEvent('click'));
        assertEq(EntityEditor.isOpen(), false, 'closed after backdrop click');
        assertTrue(document.activeElement === opener, 'focus restored after backdrop click');
    });

    test('EntityEditor in-flight indicator reflects active saves', () => {
        EntityEditor.mount('character', 'Aria');
        assertEq(EntityEditor.isInFlight(), false, 'idle by default');

        EntityEditor.setInFlight(true);
        assertTrue(EntityEditor.isInFlight(), 'in-flight set to true');
        const statusSaving = document.getElementById('entity-editor-status');
        assertEq(statusSaving.textContent, '⏳ Saving...', 'shows Saving text');
        assertTrue(statusSaving.classList.contains('saving'), 'has saving class');

        EntityEditor.setInFlight(false);
        assertEq(EntityEditor.isInFlight(), false, 'in-flight set to false');
        assertEq(statusSaving.textContent, '✔ Saved', 'shows Saved text');
        assertTrue(statusSaving.classList.contains('saved'), 'has saved class');

        EntityEditor.unmount();
    });

    test('Canvas double-click triggers EntityEditor.mount', () => {
        window.GraphNetwork = {
            revealItemsForNode: () => {},
            revealAreasForWay: () => {},
        };
        if (typeof __readFile === 'function') {
            eval(__readFile('static/js/graph/event-handlers.js'));
        }

        window.graphManager = {
            nodes: {
                get(id) {
                    return window.worldState.getNode(id);
                },
            },
        };

        const GEH = window.GraphEventHandlers;
        assertTrue(typeof GEH.onDoubleClick === 'function', 'GraphEventHandlers.onDoubleClick exists');

        // Double-click on character node
        GEH.onDoubleClick({ nodes: ['char_aria'] });
        assertTrue(EntityEditor.isOpen(), 'EntityEditor opened from double-click');
        const badge = document.getElementById('entity-editor-kind-badge');
        assertEq(badge.textContent, '👤 Character', 'correctly opened character editor');
        EntityEditor.unmount();

        // Double-click on item node
        GEH.onDoubleClick({ nodes: ['item_sword'] });
        assertTrue(EntityEditor.isOpen(), 'EntityEditor opened from double-click on item');
        assertEq(document.getElementById('entity-editor-kind-badge').textContent, '📦 Item');
        EntityEditor.unmount();

        // Single-click on character node does NOT open EntityEditor
        GEH.onClick({ nodes: ['char_aria'] });
        assertEq(EntityEditor.isOpen(), false, 'single-click leaves EntityEditor closed');
    });
    test('task-675: Character full-surface Bio tab renders 3 columns and sticky rail', () => {
        // Load agent-view for real
        window.reinitChoices = () => {};
        window.ui = { getAgentColor: () => '#bc8cff' };
        window.events = { getCharacterState: () => ({}), isAutonomous: () => false };
        window.InspectorComponents = {
            InspectorNodeHeader: () => ({}),
            InspectorDangerZone: () => ({}),
        };
        window.InspectorHelpers = {
            esc: (s) => String(s || ''),
            renderExpressionSection: () => '',
            graphGravityControl: () => '',
            renderAliasesSection: () => '',
        };

        if (typeof __readFile === 'function') {
            eval(__readFile('static/js/inspector/agent-view.js'));
        }

        const AV = window.InspectorAgentView;
        assertTrue(typeof AV._renderBioTab === 'function', '_renderBioTab exists on InspectorAgentView');

        const mockPlayer = {
            name: 'Aria',
            personality: 'Curious and bold',
            base_description: 'Tall with dark braids',
            description: 'Tall with dark braids, wearing travelling leathers',
            emotion: 'happy',
            tags: ['bard', 'traveler'],
            stats: { STR: 10, DEX: 14, CON: 12, INT: 13, WIS: 11, CHA: 16 },
            skills: { Performance: 15, Persuasion: 14 },
            traits: { charismatic: true, musical: true },
            crafting_known: ['healing_salve', 'torch'],
            recent_thoughts: ['Wonder what lies beyond the river', 'Need new strings'],
            interest_tags: ['lore', 'ballads'],
            fear_tags: ['drowning'],
            memories: [{ text: 'Heard the ballad of the lost king', importance: 8 }],
            relationships: { 'Barkeep': 5, 'Rival': -2 },
        };

        // 1. Contextual peek mode (isFullSurface = false): single-column layout
        const peekHtml = AV._renderBioTab('Aria', mockPlayer, {}, { name: 'Tavern' }, 'Aria', false, '#bc8cff', false);
        assertEq(peekHtml.includes('entity-editor-columns-3'), false, 'peek mode has no 3-column container');
        assertEq(peekHtml.includes('entity-editor-rail'), false, 'peek mode has no rail navigation');
        assertTrue(peekHtml.includes('Personality'), 'peek mode contains personality');

        // 2. Full surface mode (isFullSurface = true): 3 columns and sticky rail
        const fullHtml = AV._renderBioTab('Aria', mockPlayer, {}, { name: 'Tavern' }, 'Aria', false, '#bc8cff', true);
        assertTrue(fullHtml.includes('entity-editor-columns-3'), 'full surface has 3-column container');
        assertTrue(fullHtml.includes('entity-editor-rail'), 'full surface has section nav rail');
        assertTrue(fullHtml.includes('entity-editor-col-identity'), 'contains identity & persona column');
        assertTrue(fullHtml.includes('entity-editor-col-mechanics'), 'contains mechanics column');
        assertTrue(fullHtml.includes('entity-editor-col-knowledge'), 'contains knowledge column');

        // Verify sections inside columns
        assertTrue(fullHtml.includes('id="sec-personality"'), 'personality section present');
        assertTrue(fullHtml.includes('id="sec-appearance"'), 'appearance section present');
        assertTrue(fullHtml.includes('id="sec-emotion"'), 'emotion section present');
        assertTrue(fullHtml.includes('id="sec-tags"'), 'tags section present');
        assertTrue(fullHtml.includes('id="sec-vitals"'), 'vitals section present');
        assertTrue(fullHtml.includes('id="sec-stats-skills-traits"'), 'stats/skills/traits present');
        assertTrue(fullHtml.includes('id="sec-recipes"'), 'recipes section present');
        assertTrue(fullHtml.includes('id="sec-what-i-see"'), 'what-i-see section present');
        assertTrue(fullHtml.includes('id="sec-thoughts"'), 'latest thoughts section present');
        assertTrue(fullHtml.includes('id="sec-memories"'), 'memories section present');
        assertTrue(fullHtml.includes('id="sec-relationships"'), 'relationships section present in knowledge column');
    });

    test('task-675: EntityEditor header segmented control switches character tabs', () => {
        EntityEditor.mount('character', 'Aria');

        const tabsNav = document.getElementById('entity-editor-tabs');
        assertTrue(Boolean(tabsNav), '#entity-editor-tabs exists in header');
        assertEq(tabsNav.style.display, 'flex', 'tabs nav is visible for character');

        const tabButtons = tabsNav.querySelectorAll('.entity-editor-tab-btn');
        assertEq(tabButtons.length, 4, '4 segmented tabs rendered: Inventory, Bio, Images, Advanced');

        const tabNames = tabButtons.map(b => b.getAttribute('data-tab'));
        assertEq(tabNames, ['Inventory', 'Bio', 'Images', 'Advanced']);

        // Default active tab is Bio
        const bioBtn = tabButtons.find(b => b.getAttribute('data-tab') === 'Bio');
        assertTrue(bioBtn.classList.contains('active'), 'Bio tab is active by default');

        // Click Images tab
        const imagesBtn = tabButtons.find(b => b.getAttribute('data-tab') === 'Images');
        imagesBtn.dispatchEvent(new MouseEvent('click'));
        assertTrue(imagesBtn.classList.contains('active'), 'Images tab is now active');
        assertEq(bioBtn.classList.contains('active'), false, 'Bio tab is no longer active');

        EntityEditor.unmount();

        // Mounting item hides tabs
        EntityEditor.mount('item', 'item_sword');
        assertEq(tabsNav.style.display, 'none', 'tabs nav hidden for item');
        EntityEditor.unmount();
    });

    test('task-676: Area full-surface editor renders split properties/place view with mini-map', () => {
        const prevHtml = window.Lit.html;
        window.Lit.html = (strings, ...values) =>
            strings.reduce((acc, s, i) => {
                if (i >= values.length) return acc + s;
                const v = values[i];
                const rendered = Array.isArray(v)
                    ? v.join('')
                    : typeof v === 'function'
                        ? '[fn]'
                        : String(v ?? '');
                return acc + s + rendered;
            }, '');
        // Load area-view for real
        window.api = {
            updateNode: async () => {},
            getWorldScopes: async () => [],
        };
        window.events = {
            getAreaEvents: () => [
                { tick: 12, actor: 'Mikka', action: 'arrive', result: 'from Cooking Area' },
                { tick: 14, actor: 'Jake', action: 'examine', result: 'fire pit' },
            ],
            tickToTime: (t) => `tick ${t}`,
            setAreaFilter: () => {},
        };
        window.EventBus = {
            getActionIcon: () => '📍',
            getActionColor: () => '#58a6ff',
        };
        window.worldState.getItemsInArea = () => [
            { id: 'item_scrap', name: 'Scrap Pile', properties: { current_state: 'open' } },
        ];
        window.worldState.areas = {
            'Abandoned Farm': {
                name: 'Abandoned Farm',
                exits: {
                    'East Trail': { way_id: 'way_east', target: 'Camp Entrance', cardinal: 'E', state: 'locked' },
                    'North Bridge': { way_id: 'way_north', target: 'Bridge', cardinal: 'N', state: 'open' },
                },
            },
        };
        window.worldState.players = {
            'Jake': { name: 'Jake', current_area: 'Abandoned Farm' },
            'Mikka': { name: 'Mikka', current_area: 'Abandoned Farm' },
        };

        if (typeof __readFile === 'function') {
            eval(__readFile('static/js/inspector/area-view.js'));
        }

        const RV = window.InspectorAreaView;
        assertTrue(typeof RV.showArea === 'function', 'showArea exists on InspectorAreaView');

        const mockNode = {
            id: 'area_farm',
            name: 'Abandoned Farm',
            type: 'area',
            properties: {
                description: 'An overgrown farm, long abandoned.',
                environment: {
                    light: 80,
                    temperature: 27.6,
                    air: 'fresh',
                    smell: 'rot, straw, old food',
                    noise: 'quiet',
                    weather: 'clear',
                    wind: 'breeze',
                    humidity: 'dry',
                },
                tags: ['outdoor', 'abandoned', 'farm'],
            },
        };

        // 1. Full surface mode: renders .entity-editor-area-split with props and place columns
        const mockTarget = document.createElement('div');
        let renderedTemplate = null;
        const origLitRender = window.Lit.render;
        window.Lit.render = (tmpl, el) => {
            renderedTemplate = tmpl;
        };

        RV.showArea('area_farm', mockNode, mockTarget);

        assertTrue(Boolean(renderedTemplate), 'Lit.render called with template');
        const tmplStrings = typeof renderedTemplate === 'string' ? renderedTemplate : (renderedTemplate.strings || []).join(' ');
        assertTrue(tmplStrings.includes('entity-editor-area-split'), 'renders .entity-editor-area-split container');
        assertTrue(tmplStrings.includes('entity-editor-area-col-props'), 'renders left properties column');
        assertTrue(tmplStrings.includes('entity-editor-area-col-place'), 'renders right place column');
        assertTrue(tmplStrings.includes('entity-editor-minimap'), 'renders mini-map in place column');
        assertTrue(tmplStrings.includes('entity-editor-area-log'), 'renders scroll-locked area event log');

        // Check environment controls: 0 sliders / zero input[type=range]
        const envSectionTmpl = RV._renderEnvironmentSection(mockNode.properties.environment, 'area_farm');
        const envStrings = typeof envSectionTmpl === 'string' ? envSectionTmpl : (envSectionTmpl.strings || []).join(' ');
        assertEq(envStrings.includes('type="range"'), false, 'zero range sliders in environment controls');
        assertTrue(envStrings.includes('id="room-light"'), 'light control present');
        assertTrue(envStrings.includes('Temp °C'), 'temp control present');
        assertTrue(envStrings.includes('id="room-air"'), 'air control present');
        assertTrue(envStrings.includes('Smell'), 'smell control present');
        assertTrue(envStrings.includes('Noise'), 'noise control present');
        assertTrue(envStrings.includes('Weather'), 'weather control present');
        assertTrue(envStrings.includes('Wind'), 'wind control present');
        assertTrue(envStrings.includes('Humidity'), 'humidity control present');
        assertTrue(envStrings.includes('Presets'), 'preset control present');

        // 2. Peek mode (targetEl undefined): renders via InspectorPanel without split
        let peekTemplate = null;
        window.InspectorPanel.render = (tmpl) => {
            peekTemplate = tmpl;
        };

        RV.showArea('area_farm', mockNode, undefined);

        assertTrue(Boolean(peekTemplate), 'InspectorPanel.render called with peek template');
        const peekStrings = typeof peekTemplate === 'string' ? peekTemplate : (peekTemplate.strings || []).join(' ');
        assertEq(peekStrings.includes('entity-editor-area-split'), false, 'peek mode has no split container');
        assertTrue(peekStrings.includes('Description'), 'peek mode has description');
        assertTrue(peekStrings.includes('Exits'), 'peek mode has exits');

        window.Lit.render = origLitRender;
        window.Lit.html = prevHtml;
    });
})();
