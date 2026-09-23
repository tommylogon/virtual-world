/**
 * Unit tests for graph-tooltips.js pure helpers (buildTooltip /
 * buildTooltipHtml / _envInfo / _lightLabel / _envLines).
 *
 * The tippy/DOM binding path is out of scope here; we only exercise the
 * content-building functions, which are the ones carrying the new
 * environment / weight / state data.
 */

function _resetWorld(areas, players) {
    window.worldState = { areas: areas || {}, players: players || {} };
}

test('graph-tooltips _lightLabel numeric thresholds', () => {
    assertEq(window.GraphTooltips._lightLabel(10), 'Pitch Black', 'very dark');
    assertEq(window.GraphTooltips._lightLabel(25), 'Dim', 'dim');
    assertEq(window.GraphTooltips._lightLabel(60), 'Normal', 'normal');
    assertEq(window.GraphTooltips._lightLabel(85), 'Bright', 'bright');
    assertEq(window.GraphTooltips._lightLabel(100), 'Blinding', 'blinding');
    assertEq(window.GraphTooltips._lightLabel(null), null, 'null -> null');
});

test('graph-tooltips _lightLabel normalizes env enum strings', () => {
    assertEq(window.GraphTooltips._lightLabel('dim'), 'Dim', 'dim string');
    assertEq(window.GraphTooltips._lightLabel('pitch_black'), 'Pitch black', 'underscored');
    assertEq(window.GraphTooltips._lightLabel('BLINDING'), 'Blinding', 'uppercased');
});

test('graph-tooltips _envInfo prefers node environment over worldState', () => {
    _resetWorld({ Tavern: { environment: { temperature: 5, air: 'smoky' } } }, {});
    const node = { type: 'area', name: 'Tavern', properties: { environment: { temperature: 22, air: 'fresh' } } };
    const info = window.GraphTooltips._envInfo(node);
    assertEq(info.temp, 22, 'node temp wins');
    assertEq(info.air, 'fresh', 'node air wins');
    assertEq(info.hasAny, true, 'has env');
});

test('graph-tooltips _envInfo falls back to worldState area environment', () => {
    _resetWorld({ Tavern: { environment: { temperature: 18, light: 'dim', air: 'stale' } } }, {});
    const node = { type: 'area', name: 'Tavern', properties: {} };
    const info = window.GraphTooltips._envInfo(node);
    assertEq(info.temp, 18, 'fallback temp');
    assertEq(info.light, 'dim', 'fallback light');
    assertEq(info.air, 'stale', 'fallback air');
    assertEq(info.hasAny, true, 'has env');
});

test('graph-tooltips _envInfo reports empty when no env present', () => {
    _resetWorld({ Tavern: {} }, {});
    const node = { type: 'area', name: 'Tavern', properties: {} };
    const info = window.GraphTooltips._envInfo(node);
    assertFalse(info.hasAny, 'no env -> hasAny false');
});

test('graph-tooltips area text tooltip includes environment data', () => {
    _resetWorld({ Tavern: { environment: { temperature: 21, light: 'dim', air: 'fresh' } } }, {});
    const node = { id: 'area_tavern', name: 'Tavern', type: 'area', properties: {} };
    const tip = window.GraphTooltips.buildTooltip(node);
    assertTrue(tip.includes('🌡️ Temp 21°C'), 'temperature present');
    assertTrue(tip.includes('💡 Light dim'), 'light present');
    assertTrue(tip.includes('🌬️ Air fresh'), 'air present');
});

test('graph-tooltips area html tooltip includes environment rows', () => {
    _resetWorld({ Tavern: { environment: { temperature: 21.4, light: 20, air: 'toxic', noise: 'windy' } } }, {});
    const node = { id: 'area_tavern', name: 'Tavern', type: 'area', properties: {} };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertTrue(html.includes('🌡️ Temp: <b>21.4°C</b>'), 'temp row html (rounded to 1dp)');
    assertTrue(html.includes('💡 Light: <b>Pitch Black (20)</b>'), 'light row with number');
    assertTrue(html.includes('🌬️ Air: <b>toxic</b>'), 'air row html');
    assertTrue(html.includes('🔊 Noise: <b>windy</b>'), 'noise row html');
});

test('graph-tooltips area tooltip omits env section when empty', () => {
    _resetWorld({ Tavern: {} }, {});
    const node = { id: 'area_tavern', name: 'Tavern', type: 'area', properties: { tags: [] } };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertFalse(html.includes('🌡️'), 'no temp row');
    assertFalse(html.includes('💡 Light'), 'no light row');
});

test('graph-tooltips item text tooltip includes weight and equip slots', () => {
    _resetWorld({}, {});
    const node = { id: 'item_sword', name: 'Sword', type: 'item', properties: { weight: 5, equip_slots: ['hand_left', 'hand_right'], tags: ['weapon'] } };
    const tip = window.GraphTooltips.buildTooltip(node);
    assertTrue(tip.includes('⚖️ Weight 5'), 'weight present');
    assertTrue(tip.includes('🎯 Equip slots hand_left, hand_right'), 'slots present');
    assertTrue(tip.includes('🏷️ weapon'), 'tags present');
});

test('graph-tooltips item html tooltip includes weight and equip slots', () => {
    _resetWorld({}, {});
    const node = { id: 'item_helm', name: 'Helm', type: 'item', properties: { weight: 3, equip_slots: ['head'], tags: ['armor','clothing'] } };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertTrue(html.includes('⚖️ Weight: 3'), 'weight row');
    assertTrue(html.includes('🎯 Equip slots: head'), 'slots row');
});

test('graph-tooltips item tooltip omits weight/equip when absent', () => {
    _resetWorld({}, {});
    const node = { id: 'item_note', name: 'Note', type: 'item', properties: {} };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertFalse(html.includes('⚖️'), 'no weight row');
    assertFalse(html.includes('🎯 Equip slots'), 'no slots row');
});

test('graph-tooltips character tooltip includes state and vitals', () => {
    _resetWorld({}, { Alice: { state: 'unconscious', current_area: 'Tavern', vitals: { HP: 8, Max_HP: 10, Energy: 42 } } });
    const node = { id: 'char_alice', name: 'Alice', type: 'character', properties: {} };
    const tip = window.GraphTooltips.buildTooltip(node);
    assertTrue(tip.includes('📍 Tavern'), 'area present');
    assertTrue(tip.includes('❤️ HP 8'), 'hp present');
    assertTrue(tip.includes('⚡ Energy 42'), 'energy present');
    assertTrue(tip.includes('🎭 State unconscious'), 'state present');
});

test('graph-tooltips character html tooltip includes state', () => {
    _resetWorld({}, { Alice: { state: 'sleeping', current_area: 'Tavern', vitals: { HP: 10, Max_HP: 10, Energy: 5 } } });
    const node = { id: 'char_alice', name: 'Alice', type: 'character', properties: {} };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertTrue(html.includes('🎭 State: sleeping'), 'state row html');
    assertTrue(html.includes('❤️ HP: 10'), 'hp row html');
});

test('graph-tooltips area html tooltip escapes free-text environment values', () => {
    _resetWorld({ Tavern: { environment: { temperature: 21, smell: '<script>alert(1)</script>' } } }, {});
    const node = { id: 'area_tavern', name: 'Tavern', type: 'area', properties: {} };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertFalse(html.includes('<script>'), 'raw script tag must not appear');
    assertTrue(html.includes('&lt;script&gt;'), 'script tag escaped');
});

test('graph-tooltips area html tooltip renders humidity', () => {
    _resetWorld({ Tavern: { environment: { humidity: 'wet' } } }, {});
    const node = { id: 'area_tavern', name: 'Tavern', type: 'area', properties: {} };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertTrue(html.includes('💧 Humidity: <b>wet</b>'), 'humidity row');
});

test('graph-tooltips _envInfo merges partial node env over area env', () => {
    _resetWorld({ Tavern: { environment: { temperature: 18, air: 'stale' } } }, {});
    const node = { id: 'area_tavern', name: 'Tavern', type: 'area', properties: { environment: { light: 'dim' } } };
    const info = window.GraphTooltips._envInfo(node);
    assertEq(info.light, 'dim', 'node light wins');
    assertEq(info.temp, 18, 'area temp kept when node omits it');
    assertEq(info.air, 'stale', 'area air kept when node omits it');
});

test('graph-tooltips item html tooltip renders a zero weight', () => {
    _resetWorld({}, {});
    const node = { id: 'item_feather', name: 'Feather', type: 'item', properties: { weight: 0 } };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertTrue(html.includes('⚖️ Weight: 0'), 'zero weight must not render blank');
});

test('graph-tooltips way tooltip shows state and to/from areas', () => {
    const esc = window.GraphTooltips._escHtml;
    window.WayAuthoring = {
        getWayAreaPair: (id) => ({ from: 'Tavern', to: 'Cellar' }),
        enhanceWayNodeTooltip: (nodeData, baseHtml) => {
            const pair = window.WayAuthoring.getWayAreaPair(nodeData.id);
            let extra = '';
            if (pair.from || pair.to) {
                extra += `<div style="margin:2px 0;">📍 ${esc(pair.from || '?')} ↔ ${esc(pair.to || '?')}</div>`;
            }
            const tags = nodeData.properties?.tags || [];
            if (tags.length) extra += `<div style="margin:2px 0;">🏷️ ${esc(tags.join(', '))}</div>`;
            if (!extra) return baseHtml;
            const insertAt = baseHtml.lastIndexOf('</div>');
            if (insertAt === -1) return baseHtml + extra;
            return baseHtml.slice(0, insertAt) + extra + baseHtml.slice(insertAt);
        },
    };
    _resetWorld({}, {});
    const node = { id: 'way_door', name: 'Door', type: 'way', properties: { current_state: 'locked', one_way: true } };
    const html = window.GraphTooltips.buildTooltipHtml(node);
    assertTrue(html.includes('🚪 State: locked'), 'state row');
    assertTrue(html.includes('➡️ One-way (blue border)'), 'one-way row');
    assertTrue(html.includes('📍 Tavern ↔ Cellar'), 'area pair row');
    delete window.WayAuthoring;
});
