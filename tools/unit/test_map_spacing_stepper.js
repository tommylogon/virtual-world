/**
 * tools/unit/test_map_spacing_stepper.js
 *
 * bug-574: Unit tests for direct numeric typing, clamping, Auto (A)
 * disengagement, invalid-input rejection, and stepper button updates on
 * #map-spacing and #edge-label-size.
 */

(() => {
    function makeInput(id, initialValue) {
        const listeners = {};
        const attrs = {};
        return {
            id,
            tagName: 'INPUT',
            type: 'number',
            value: String(initialValue),
            textContent: '',
            title: '',
            dataset: {},
            blurred: false,
            addEventListener(type, fn) {
                (listeners[type] = listeners[type] || []).push(fn);
            },
            dispatch(type, extra) {
                const ev = Object.assign({
                    type,
                    preventDefault() { ev.defaultPrevented = true; },
                    stopPropagation() {},
                }, extra || {});
                for (const fn of (listeners[type] || [])) fn(ev);
                return ev;
            },
            blur() { this.blurred = true; },
            setAttribute(k, v) { attrs[k] = String(v); },
            getAttribute(k) { return attrs[k] ?? null; },
        };
    }

    function makeAutoBtn() {
        const attrs = { 'aria-pressed': 'true' };
        return {
            id: 'map-spacing-auto',
            tagName: 'BUTTON',
            title: '',
            setAttribute(k, v) { attrs[k] = String(v); },
            getAttribute(k) { return attrs[k] ?? null; },
        };
    }

    function loadGraphManagerHarness() {
        const mapInput = makeInput('map-spacing', '240');
        const edgeInput = makeInput('edge-label-size', '8');
        const autoBtn = makeAutoBtn();
        const elements = {
            'map-spacing': mapInput,
            'edge-label-size': edgeInput,
            'map-spacing-auto': autoBtn,
        };

        globalThis.document = {
            getElementById(id) { return elements[id] || null; },
        };
        globalThis.localStorage = {
            getItem() { return null; },
            setItem() {},
        };
        globalThis.config = {
            graphMapSpacing: 240,
            graphMapSpacingAuto: true,
            graphLayoutMode: 'map',
            graphCardinalLayout: true,
        };
        globalThis.storage = {
            calls: [],
            setConfig(k, v) { this.calls.push([k, v]); },
        };
        globalThis.window = {
            Lit: { html: () => '' },
            GraphNetwork: { applyGraphSettings() {} },
        };
        globalThis.GraphNetwork = globalThis.window.GraphNetwork;

        if (typeof globalThis.GraphManagerImpl === 'undefined' && typeof __readFile === 'function') {
            const src = __readFile('static/js/graph-manager.js');
            (0, eval)(src + '\nglobalThis.GraphManagerImpl = GraphManagerImpl;');
        }

        const gm = new globalThis.GraphManagerImpl();
        let loadCalls = 0;
        gm.loadGraphData = async () => { loadCalls += 1; };
        gm._syncMapSpacingButton();
        gm._syncEdgeLabelSizeInput();
        gm._bindStepperInputs();

        return {
            gm,
            mapInput,
            edgeInput,
            autoBtn,
            getLoadCalls: () => loadCalls,
            resetLoadCalls: () => { loadCalls = 0; },
        };
    }

    test('templates/index.html renders #map-spacing and #edge-label-size as editable number inputs', () => {
        const html = __readFile('templates/index.html');
        assertTrue(html.includes('<input type="number" id="edge-label-size" class="stepper-input"'), 'edge-label-size is a number input');
        assertTrue(html.includes('<input type="number" id="map-spacing" class="stepper-input"'), 'map-spacing is a number input');
        assertTrue(html.includes('id="map-spacing-auto"'), 'Auto (A) button preserved');
        assertTrue(html.includes('graphManager.setMapSpacing(-20)'), 'map-spacing - button preserved');
        assertTrue(html.includes('graphManager.setMapSpacing(20)'), 'map-spacing + button preserved');
        assertTrue(html.includes('graphManager.setEdgeLabelSize(-1)'), 'edge-label-size - button preserved');
        assertTrue(html.includes('graphManager.setEdgeLabelSize(1)'), 'edge-label-size + button preserved');
    });

    test('direct numeric entry on #map-spacing updates spacing, disengages Auto, and reloads on Enter and change', () => {
        const h = loadGraphManagerHarness();
        assertEq(h.autoBtn.getAttribute('aria-pressed'), 'true', 'starts in auto mode');

        h.mapInput.value = '320';
        const ev = h.mapInput.dispatch('keydown', { key: 'Enter' });
        assertTrue(ev.defaultPrevented, 'Enter prevents default');
        assertTrue(h.mapInput.blurred, 'Enter blurs input');
        assertEq(globalThis.config.graphMapSpacing, 320, 'config updated to 320');
        assertEq(globalThis.config.graphMapSpacingAuto, false, 'config auto flag disengaged');
        assertEq(h.gm._mapSpacingAuto, false, 'manager auto flag disengaged');
        assertEq(h.autoBtn.getAttribute('aria-pressed'), 'false', 'A button aria-pressed is false');
        assertEq(h.mapInput.value, '320', 'input value reflects 320');
        assertEq(h.getLoadCalls(), 1, 'loadGraphData called once');

        h.resetLoadCalls();
        h.mapInput.value = '480';
        h.mapInput.dispatch('change');
        assertEq(globalThis.config.graphMapSpacing, 480, 'change event updates config to 480');
        assertEq(h.mapInput.value, '480', 'input value reflects 480');
        assertEq(h.getLoadCalls(), 1, 'loadGraphData called on change');
    });

    test('#map-spacing clamps out-of-range numbers and rounds decimals', () => {
        const h = loadGraphManagerHarness();

        h.mapInput.value = '5';
        h.mapInput.dispatch('change');
        assertEq(globalThis.config.graphMapSpacing, 20, 'clamps below min to 20');
        assertEq(h.mapInput.value, '20', 'input displays clamped 20');

        h.mapInput.value = '2500';
        h.mapInput.dispatch('change');
        assertEq(globalThis.config.graphMapSpacing, 1000, 'clamps above max to 1000');
        assertEq(h.mapInput.value, '1000', 'input displays clamped 1000');

        h.mapInput.value = '123.6';
        h.mapInput.dispatch('change');
        assertEq(globalThis.config.graphMapSpacing, 124, 'rounds decimal to nearest integer');
        assertEq(h.mapInput.value, '124', 'input displays rounded 124');
    });

    test('#map-spacing rejects invalid non-numeric input gracefully without disengaging Auto', () => {
        const h = loadGraphManagerHarness();

        for (const bad of ['', '   ', 'abc', '320px']) {
            h.mapInput.value = bad;
            const ok = h.gm.commitMapSpacingInput(h.mapInput.value);
            assertFalse(ok, `rejects "${bad}"`);
            assertEq(h.mapInput.value, '240', `restores previous value for "${bad}"`);
        }
        assertEq(h.gm._mapSpacingAuto, true, 'Auto remains engaged');
        assertEq(h.autoBtn.getAttribute('aria-pressed'), 'true', 'A button remains pressed');
        assertEq(h.getLoadCalls(), 0, 'loadGraphData not called on invalid input');
    });

    test('#map-spacing - and + stepper buttons adjust spacing by delta and disengage Auto', () => {
        const h = loadGraphManagerHarness();
        h.gm.setMapSpacing(-20);
        assertEq(globalThis.config.graphMapSpacing, 220, 'decrements by 20');
        assertEq(h.mapInput.value, '220', 'input reflects 220');
        assertEq(h.autoBtn.getAttribute('aria-pressed'), 'false', 'disengages Auto');

        h.gm.setMapSpacing(20);
        assertEq(globalThis.config.graphMapSpacing, 240, 'increments by 20');
        assertEq(h.mapInput.value, '240', 'input reflects 240');
    });

    test('#edge-label-size supports direct typing, clamping, invalid rejection, and stepper buttons', () => {
        const h = loadGraphManagerHarness();
        assertEq(h.edgeInput.value, '8', 'initial edge label size is 8');

        h.edgeInput.value = '12';
        h.edgeInput.dispatch('keydown', { key: 'Enter' });
        assertEq(h.gm._edgeLabelSize, 12, 'Enter sets edge label size to 12');
        assertEq(h.edgeInput.value, '12', 'input reflects 12');
        assertEq(h.getLoadCalls(), 1, 'loadGraphData called');

        h.resetLoadCalls();
        h.edgeInput.value = '1';
        h.edgeInput.dispatch('change');
        assertEq(h.gm._edgeLabelSize, 4, 'clamps below 4 to 4');
        assertEq(h.edgeInput.value, '4', 'input reflects 4');

        h.edgeInput.value = '99';
        h.edgeInput.dispatch('change');
        assertEq(h.gm._edgeLabelSize, 20, 'clamps above 20 to 20');
        assertEq(h.edgeInput.value, '20', 'input reflects 20');

        h.resetLoadCalls();
        h.edgeInput.value = 'nope';
        assertFalse(h.gm.commitEdgeLabelSizeInput(h.edgeInput.value), 'rejects non-numeric');
        assertEq(h.edgeInput.value, '20', 'restores 20');
        assertEq(h.getLoadCalls(), 0, 'does not reload on invalid input');

        h.gm.setEdgeLabelSize(-1);
        assertEq(h.gm._edgeLabelSize, 19, 'stepper - decrements to 19');
        assertEq(h.edgeInput.value, '19', 'input reflects 19');

        h.gm.setEdgeLabelSize(1);
        assertEq(h.gm._edgeLabelSize, 20, 'stepper + increments to 20');
        assertEq(h.edgeInput.value, '20', 'input reflects 20');
    });
})();
