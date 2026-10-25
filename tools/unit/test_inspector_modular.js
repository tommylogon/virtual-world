/**
 * test_inspector_modular.js - InspectorView base class, InspectorComponents,
 * and view adoption tests (task-902).
 */

function withInterpolatingLit(fn) {
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
    try {
        return fn();
    } finally {
        window.Lit.html = prevHtml;
    }
}

test('inspector modular: InspectorView lifecycle tracks nodeId, mounted, and _renderQueued without colliding with _deferRender', () => {
    const view = new InspectorView();
    assertEq(view.nodeId, null);
    assertEq(view.mounted, false);
    assertEq(view._renderQueued, false);

    view.show('area_tavern');
    assertEq(view.nodeId, 'area_tavern');
    assertEq(view.mounted, true);

    view._cancelRender();
    assertEq(view._renderQueued, false);

    assertTrue(typeof window.InspectorAgentView._deferRender === 'function', '_deferRender on agent-view remains a function');
    assertEq(window.InspectorAgentView._renderQueued, false, '_renderQueued on base class stays a boolean');
});

test('inspector modular: all 9 inspector view singletons extend InspectorView', () => {
    const views = [
        ['InspectorAgentView', window.InspectorAgentView],
        ['InspectorAreaView', window.InspectorAreaView],
        ['InspectorItemView', window.InspectorItemView],
        ['InspectorWayView', window.InspectorWayView],
        ['InspectorLore', window.InspectorLore],
        ['InspectorMemory', window.InspectorMemory],
        ['InspectorMindView', window.InspectorMindView],
        ['InspectorPaperdoll', window.InspectorPaperdoll],
        ['InspectorBehaviors', window.InspectorBehaviors],
    ];
    for (const [name, instance] of views) {
        assertTrue(instance instanceof InspectorView, `${name} should be an instance of InspectorView`);
    }
});

test('inspector modular: PropertyGridComponent separates text and number inputs', () => {
    withInterpolatingLit(() => {
        const htmlOut = String(InspectorComponents.PropertyGridComponent({
            fields: [
                { key: 'title', label: 'Title', type: 'text' },
                { key: 'weight', label: 'Weight', type: 'number' },
            ],
            values: { title: 'Tavern', weight: 5 },
            onChange: () => {},
        }));
        assertTrue(htmlOut.includes('type="text"'), 'text field renders type="text"');
        assertTrue(htmlOut.includes('type="number"'), 'number field renders type="number"');
    });
});

test('inspector modular: BreadcrumbComponent emits canonical .inspector-crumb classes', () => {
    const prevInspector = window.inspector;
    window.inspector = {
        _history: [
            { kind: 'node', id: 'area_1', label: 'Square' },
            { kind: 'node', id: 'item_1', label: 'Lantern' },
        ],
    };
    try {
        withInterpolatingLit(() => {
            const htmlOut = String(InspectorComponents.BreadcrumbComponent({
                onBack: () => {},
                onCrumbClick: () => {},
            }));
            assertTrue(htmlOut.includes('inspector-crumb-btn'), 'renders .inspector-crumb-btn for earlier trail entry');
            assertTrue(htmlOut.includes('inspector-crumb-label'), 'renders .inspector-crumb-label for current entry');
            assertTrue(htmlOut.includes('inspector-crumb-back'), 'renders .inspector-crumb-back when history > 1');
        });
    } finally {
        window.inspector = prevInspector;
    }
});

test('inspector modular: HeaderComponent and SectionComponent render header badge, close button, and section container', () => {
    withInterpolatingLit(() => {
        const hdr = String(InspectorComponents.HeaderComponent({
            title: 'World Lore',
            nodeType: '🌍 World',
            color: '#8a6e3b',
            onClose: () => {},
        }));
        assertTrue(hdr.includes('inspector-type-badge'), 'renders .inspector-type-badge');
        assertTrue(hdr.includes('World Lore'), 'renders header title');
        assertTrue(hdr.includes('✕'), 'renders close button when onClose is provided');

        const sec = String(InspectorComponents.SectionComponent({
            title: 'Entries',
            hint: '2 items',
            content: '<div>body</div>',
        }));
        assertTrue(sec.includes('inspector-section'), 'renders .inspector-section wrapper');
        assertTrue(sec.includes('<h3>Entries</h3>'), 'renders optional section title');
        assertTrue(sec.includes('section-hint'), 'renders optional section hint');
    });
});
