"use strict";
/**
 * @module worldpainter/editor-palette - WorldPainter floating tile palette and categories
 * @contributes tile palette dock, category rail, search filter, and tile detail panel
 * @powers WorldPainter tile browsing and paint selection (task-880)
 * @relates static/js/worldpainter/editor.js; static/js/worldpainter/grid-model.js
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(function () {
    'use strict';
    const STRUCTURE_NOTES = {
        solid: 'solid - nothing passes it',
        see_through: 'you can see through it, not walk through it',
        passable: 'a threshold - you go through it',
    };
    const _layerOptionsCache = new Map();
    const _paletteSectionsCache = new Map();
    function _clearPaletteMemos() {
        _layerOptionsCache.clear();
        _paletteSectionsCache.clear();
    }
    function _layerOptions(ctx, layer) {
        const cached = _layerOptionsCache.get(layer);
        if (cached)
            return cached;
        const vocab = ctx.state.vocab || {};
        let res = [];
        if (layer === 'biome')
            res = (vocab.b || vocab.biomes || []).slice();
        else if (layer === 'road')
            res = (vocab.f || vocab.features || []).slice();
        else if (layer === 'climate') {
            res = ctx.GM().CLIMATE_IDS.map((id) => {
                const c = ctx.GM().CLIMATES[id] || {};
                return {
                    id,
                    name: `${c.label} (${c.base}°C)`,
                    tags: ['climate'],
                };
            });
        }
        if (ctx.state.vocab)
            _layerOptionsCache.set(layer, res);
        return res;
    }
    function _climateLegend(ctx) {
        if (ctx.state.layer !== 'climate')
            return null;
        const box = ctx.el('div', 'display:flex;gap:6px;align-items:center;flex-wrap:wrap;' +
            'padding:4px 8px;margin-bottom:6px;border:1px solid var(--border,#3a3a44);' +
            'border-radius:6px;font-size:11px;');
        box.setAttribute('data-role', 'wp-climate-legend');
        box.appendChild(ctx.el('span', 'color:var(--text-muted,#999);', 'compiles to base_temperature:'));
        ctx.GM().CLIMATE_IDS.forEach((id) => {
            const c = ctx.GM().CLIMATES[id] || {};
            const chip = ctx.el('span', 'display:inline-flex;align-items:center;gap:4px;padding:1px 6px;'
                + 'border-radius:9px;border:1px solid var(--border,#3a3a44);', c.label);
            const swatch = ctx.el('span', 'display:inline-block;width:9px;height:9px;border-radius:2px;', '');
            swatch.style.background = c.color;
            chip.insertBefore(swatch, chip.firstChild);
            chip.title = `${c.label}: ${c.base}°C base, plus the day's curve`;
            box.appendChild(chip);
        });
        box.appendChild(ctx.el('span', 'color:var(--text-muted,#777);', '· unpainted is Temperate'));
        box.title = 'A region takes the majority climate of its cells, and a '
            + 'climate boundary never splits an area. Only world scopes compile '
            + 'a climate; a town or interior keeps its own air.';
        return box;
    }
    function _paletteSections(ctx, layer) {
        const p = ctx.state.payload;
        const mode = p ? (p.mode || (p.scope && p.scope.mode) || '') : '';
        const memoKey = `${layer}:${mode}`;
        const cached = _paletteSectionsCache.get(memoKey);
        if (cached)
            return cached;
        const all = ctx.GM().paletteSections(layer, _layerOptions(ctx, layer));
        const filtered = ctx.GM().paletteForMode(all, mode || null);
        if (ctx.state.vocab)
            _paletteSectionsCache.set(memoKey, filtered);
        return filtered;
    }
    function _defaultValueForLayer(ctx, layer) {
        if (layer === 'floor')
            return '1';
        const options = _layerOptions(ctx, layer);
        if (!options.length)
            return '';
        const preferred = { biome: 'sparse_forest', road: 'road' }[layer];
        if (preferred && options.some((o) => o.id === preferred))
            return preferred;
        return options[0].id || '';
    }
    function _valueControl(ctx) {
        const options = _layerOptions(ctx, ctx.state.layer);
        if (ctx.state.layer === 'floor' || !options.length) {
            const wrap = ctx.el('div', 'display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap;');
            const input = ctx.el('input', 'width:90px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            input.setAttribute('data-role', 'wp-value');
            input.value = ctx.state.value;
            input.placeholder = ctx.state.layer === 'floor' ? '+1 / -1' : 'value';
            input.title = ctx.state.layer === 'floor'
                ? 'Storey: 0 is ground, 1 is one up, -1 one down. Unbounded - 3 for a '
                    + 'room three storeys up, 80 for a tower, -900 for a hole.'
                : `Value painted on the ${ctx.state.layer} layer.`;
            input.addEventListener('input', () => { ctx.state.value = input.value; });
            wrap.appendChild(input);
            if (ctx.state.layer === 'floor' && ctx.state.payload && ctx.state.payload.grid) {
                const btnImport = ctx.btn('📥 Import heightmap…', () => {
                    const wpDialogs = window.WorldPainterDialogs;
                    if (wpDialogs) {
                        wpDialogs.openHeightmapImportDialog(ctx.dialogCtx(), ctx.state.payload);
                    }
                }, 'font-size:11px;padding:2px 6px;', 'Import greyscale heightmap PNG into the floor layer (task-877)');
                btnImport.setAttribute('data-role', 'wp-heightmap-import');
                wrap.appendChild(btnImport);
                const btnExport = ctx.btn('📤 Export heightmap…', () => {
                    const wpDialogs = window.WorldPainterDialogs;
                    if (wpDialogs) {
                        wpDialogs.openHeightmapExportDialog(ctx.dialogCtx(), ctx.state.payload);
                    }
                }, 'font-size:11px;padding:2px 6px;', 'Export floor layer as greyscale PNG (task-877)');
                btnExport.setAttribute('data-role', 'wp-heightmap-export');
                wrap.appendChild(btnExport);
            }
            return wrap;
        }
        const sections = _paletteSections(ctx, ctx.state.layer);
        const all = ctx.GM().flattenPalette(sections);
        const ids = all.map((t) => t.id);
        if (ids.indexOf(ctx.state.value) < 0)
            ctx.state.value = ids[0] || '';
        const wrap = ctx.el('div', 'display:flex;gap:6px;align-items:center;flex-wrap:wrap;');
        const swatch = ctx.el('span', 'display:inline-block;width:14px;height:14px;' +
            'border-radius:3px;border:1px solid #555;flex:0 0 auto;');
        swatch.setAttribute('data-role', 'wp-value-swatch');
        wrap.appendChild(swatch);
        const pick = ctx.btn('', () => { ctx.state.paletteOpen = !ctx.state.paletteOpen; ctx.saveScopePrefs(); ctx.softRender(); }, 'min-width:150px;text-align:left;', 'Open the palette to choose what this layer paints (task-759).');
        pick.setAttribute('data-role', 'wp-value');
        wrap.appendChild(pick);
        const detail = ctx.el('div', 'font-size:11px;color:var(--text-muted,#999);' +
            'line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px;');
        detail.setAttribute('data-role', 'wp-value-detail');
        const tile = ctx.GM().paletteTile(sections, ctx.state.value);
        const text = tile ? ctx.GM().tileDetail(ctx.state.layer, tile.rec) : '';
        pick.textContent = (tile ? tile.name : '(no tiles)') + '  ▾';
        detail.textContent = text;
        detail.title = text;
        swatch.style.background = ctx.GM().layerColor(ctx.state.layer, ctx.state.value) || 'transparent';
        swatch.title = tile ? tile.name : '';
        wrap.appendChild(detail);
        return wrap;
    }
    function _palettePanel(ctx) {
        const layer = ctx.state.layer;
        if (layer === 'floor')
            return null;
        const sections = _paletteSections(ctx, layer);
        if (!sections.length)
            return null;
        const wrap = ctx.el('div', 'border:1px solid var(--border,#3a3a44);border-radius:8px;' +
            'padding:8px;background:var(--bg-card,#23232b);width:320px;flex:0 0 320px;' +
            'display:flex;flex-direction:column;gap:6px;max-height:560px;overflow:hidden;');
        wrap.setAttribute('data-role', 'wp-palette');
        const head = ctx.el('div', 'display:flex;align-items:center;gap:6px;');
        head.appendChild(ctx.el('span', 'font-weight:600;font-size:13px;', 'Palette'));
        head.appendChild(ctx.el('div', 'flex:1;'));
        head.appendChild(ctx.btn('✕', () => { ctx.state.paletteOpen = false; ctx.saveScopePrefs(); ctx.softRender(); }, 'padding:2px 8px;', 'Close the palette dock'));
        wrap.appendChild(head);
        const subHint = ctx.el('div', 'font-size:11px;color:var(--text-muted,#999);line-height:1.2;', 'hover to preview · click to paint');
        wrap.appendChild(subHint);
        const search = ctx.el('input', 'width:100%;box-sizing:border-box;padding:3px 6px;border-radius:5px;' +
            'border:1px solid var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
        search.type = 'search';
        search.placeholder = 'Search tiles by name or id…';
        search.value = ctx.state.paletteQuery;
        search.setAttribute('data-role', 'wp-palette-search');
        search.setAttribute('aria-label', 'Search palette tiles by name or id');
        wrap.appendChild(search);
        const rail = ctx.el('div', 'display:flex;gap:4px;flex-wrap:wrap;max-height:90px;overflow-y:auto;padding-bottom:2px;');
        rail.setAttribute('data-role', 'wp-palette-rail');
        wrap.appendChild(rail);
        const grid = ctx.el('div', 'display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));' +
            'gap:4px;flex:1 1 auto;overflow-y:auto;padding:2px;min-height:120px;');
        grid.setAttribute('data-role', 'wp-palette-grid');
        wrap.appendChild(grid);
        const detailBox = ctx.el('div', 'font-size:11px;color:var(--text-muted,#999);line-height:1.45;' +
            'border-top:1px solid var(--border,#333);padding-top:6px;min-height:50px;flex:0 0 auto;');
        detailBox.setAttribute('data-role', 'wp-palette-detail');
        wrap.appendChild(detailBox);
        const showDetail = (t) => {
            detailBox.textContent = '';
            detailBox.appendChild(ctx.el('div', 'font-weight:600;color:var(--text,#ddd);', t.name));
            ctx.GM().detailRows(layer, t.rec).forEach((r) => {
                detailBox.appendChild(ctx.el('div', null, r.label + ': ' + r.value));
            });
        };
        const build = () => {
            const filtered = ctx.GM().filterPalette(sections, ctx.state.paletteQuery);
            rail.textContent = '';
            if (!ctx.state.paletteQuery && filtered.length) {
                if (!filtered.some((s) => s.id === ctx.state.paletteCategory)) {
                    ctx.state.paletteCategory = filtered[0].id;
                }
                filtered.forEach((s) => {
                    const active = s.id === ctx.state.paletteCategory;
                    const b = ctx.btn(s.label, () => { ctx.state.paletteCategory = s.id; build(); }, 'padding:2px 8px;font-size:11px;' +
                        (active ? 'background:#2d4a6b;color:#cfe;' : ''), `${s.label} (${s.tiles.length})`);
                    b.setAttribute('data-role', 'wp-palette-cat');
                    b.setAttribute('data-cat', s.id);
                    rail.appendChild(b);
                });
            }
            const tiles = ctx.state.paletteQuery
                ? ctx.GM().flattenPalette(filtered)
                : ((filtered.find((s) => s.id === ctx.state.paletteCategory) || filtered[0]) || { tiles: [] }).tiles;
            grid.textContent = '';
            tiles.forEach((t) => {
                const selected = t.id === ctx.state.value;
                const b = ctx.el('button', 'display:flex;align-items:center;gap:6px;text-align:left;' +
                    'cursor:pointer;border:1px solid ' + (selected ? '#5a8fd0' : 'var(--border,#3a3a44)') +
                    ';border-radius:6px;padding:4px 6px;font-size:11px;' +
                    'background:' + (selected ? '#2d4a6b' : 'var(--bg-card,#2a2a32)') + ';color:var(--text,#ddd);');
                b.setAttribute('data-role', 'wp-palette-tile');
                b.setAttribute('data-id', t.id);
                const sw = ctx.el('span', 'display:inline-block;width:12px;height:12px;border-radius:3px;' +
                    'border:1px solid #555;flex:0 0 auto;');
                sw.style.background = ctx.GM().layerColor(layer, t.id) || 'transparent';
                b.appendChild(sw);
                b.appendChild(ctx.el('span', null, t.name));
                b.addEventListener('mouseenter', () => showDetail(t));
                b.addEventListener('focus', () => showDetail(t));
                b.addEventListener('click', (ev) => {
                    ctx.state.value = t.id;
                    ctx.pushRecent(layer, ctx.state.value);
                    ctx.saveScopePrefs();
                    ev.currentTarget.blur();
                    ctx.softRender();
                });
                grid.appendChild(b);
            });
            if (tiles.length) {
                showDetail(tiles.find((t) => t.id === ctx.state.value) || tiles[0]);
            }
            else {
                detailBox.textContent = 'No tile matches that search.';
            }
        };
        search.addEventListener('input', () => { ctx.state.paletteQuery = search.value; build(); });
        search.addEventListener('keydown', (ev) => {
            if (ev.key === 'Escape') {
                ctx.state.paletteOpen = false;
                ctx.saveScopePrefs();
                ctx.softRender();
            }
        });
        build();
        return wrap;
    }
    function _cellPanel(ctx, p) {
        const at = ctx.state.inspected;
        if (!at || !p.scope.has_grid)
            return null;
        const info = ctx.GM().cellInfo(p, at.x, at.y, ctx.state.vocab);
        const wrap = ctx.el('div', 'border:1px solid var(--border,#3a3a44);border-radius:8px;' +
            'padding:8px;margin-bottom:10px;font-size:12px;flex-shrink:0;position:relative;z-index:2;');
        wrap.setAttribute('data-role', 'wp-cellpanel');
        const head = ctx.el('div', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;');
        head.appendChild(ctx.el('strong', null, `Cell (${info.x},${info.y})`));
        head.appendChild(ctx.el('span', 'color:var(--text-muted,#999);', info.empty ? 'nothing on this cell' : 'what is on this cell'));
        head.appendChild(ctx.btn('✕', () => { ctx.state.inspected = null; ctx.softRender(); }, 'margin-left:auto;padding:1px 7px;', 'Close the cell panel'));
        wrap.appendChild(head);
        const rows = ctx.el('div', 'display:flex;flex-direction:column;gap:2px;margin-top:6px;');
        const row = (label, value) => {
            const r = ctx.el('div', 'display:flex;gap:6px;align-items:baseline;');
            r.appendChild(ctx.el('span', 'color:var(--text-muted,#999);min-width:78px;', label));
            r.appendChild(ctx.el('span', null, value));
            rows.appendChild(r);
        };
        row('biome', info.biome ? String(info.biome).replace(/_/g, ' ') : '-');
        row('road', info.road ? String(info.road).replace(/_/g, ' ') : '-');
        row('floor', ctx.GM().floorLabel(info.floor));
        row('structure', info.kind
            ? `not a place - ${STRUCTURE_NOTES[info.kind] || info.kind}`
            : '-');
        row('enter', info.enter || '-');
        row('area', info.area ? `${info.area.name} (${info.area.id})` : '-');
        row('sub-zone', info.child ? `${info.child.name || info.child.id} (${info.child.id})` : '-');
        const neighbours = ctx.GM().cellNeighbours(p, at.x, at.y, ctx.state.vocab);
        const label = (n) => {
            if (n == null)
                return 'map edge';
            const noun = String(n.road || n.biome || '').replace(/_/g, ' ');
            const solid = n.kind && n.kind !== 'place' ? ` (${n.kind})` : '';
            const what = noun ? `${noun}${solid}` : 'empty';
            return n.name ? `${what} "${n.name}"` : what;
        };
        row('exits', ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            .map((d) => `${d}: ${label(neighbours[d])}`).join(' · '));
        wrap.appendChild(rows);
        const nameRow = ctx.el('div', 'display:flex;gap:6px;align-items:center;margin-top:6px;');
        nameRow.appendChild(ctx.el('span', 'color:var(--text-muted,#999);min-width:78px;', 'name'));
        const nameInput = ctx.el('input', 'flex:1;min-width:0;padding:2px 6px;border-radius:5px;' +
            'border:1px solid var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
        nameInput.value = info.name || '';
        nameInput.placeholder = 'unnamed - compiles to a coordinate';
        nameInput.title = 'The name this place compiles to. Needed for a town: a building is not addressable until it has one.';
        nameInput.addEventListener('change', () => {
            ctx.setCellName(p, info.x, info.y, nameInput.value);
        });
        nameInput.addEventListener('keydown', (ev) => { if (ev.key === 'Enter')
            nameInput.blur(); });
        nameRow.appendChild(nameInput);
        wrap.appendChild(nameRow);
        const actions = ctx.el('div', 'display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;');
        if (info.area) {
            actions.appendChild(ctx.btn(`📍 Move ${info.area.name}`, () => {
                ctx.state.tool = 'area';
                ctx.state.selectedArea = info.area.id;
                ctx.render();
            }, '', 'Switch to the Area tool with this area picked, then click its new cell'));
            actions.appendChild(ctx.btn('🗑 Unplace', () => ctx.unplaceArea(info.area.id), '', 'Take this area off the map; the area itself is untouched'));
            if (window.VW && window.VW.inspector) {
                actions.appendChild(ctx.btn('🔎 Open area', () => {
                    ctx.state.overlay.remove();
                    window.VW.inspector.showNode(info.area.id);
                }, '', 'Open this area in the graph inspector'));
            }
        }
        if (info.child) {
            actions.appendChild(ctx.btn(`📂 Open ${info.child.name || info.child.id}`, () => {
                ctx.load(info.child.id);
            }, '', 'Drill into this sub-zone'));
            actions.appendChild(ctx.btn('🗑 Remove sub-zone', () => ctx.removeFeature(info.child.id), '', 'Take the child scope off this cell (the scope itself is kept)'));
        }
        if (info.painted) {
            actions.appendChild(ctx.btn('🧽 Clear paint', () => ctx.clearCell(p, info.x, info.y), '', 'Erase every paint layer on this one cell (one undo step)'));
        }
        if (!actions.childNodes.length) {
            actions.appendChild(ctx.el('span', 'color:var(--text-muted,#999);', 'Nothing to do here - paint it, or place an area/feature on it.'));
        }
        wrap.appendChild(actions);
        const seams = _seamPanel(ctx, p, info.area && info.area.id);
        if (seams)
            wrap.appendChild(seams);
        if (info.area) {
            wrap.appendChild(ctx.btn('🪜 Make this a scope…', () => ctx.promoteArea(info.area.id), 'margin-top:8px;width:100%;', 'Turn this area into a child scope of '
                + `${p.scope.name}, with a way in from its cell`));
        }
        return wrap;
    }
    function _seamPanel(ctx, p, areaId) {
        if (!areaId)
            return null;
        const rows = (p.boundary_ways || []).filter((w) => w.area_id === areaId);
        const taken = (p.boundary_overrides || []).filter((o) => {
            const row = rows.find((w) => w.way_id === o.way_id);
            return row === undefined;
        });
        if (!rows.length && !taken.length)
            return null;
        const box = ctx.el('div', 'margin-top:8px;padding-top:8px;border-top:1px solid ' +
            'var(--border,#3a3a44);display:flex;flex-direction:column;gap:3px;');
        box.setAttribute('data-role', 'wp-seams');
        box.appendChild(ctx.el('div', 'color:var(--text-muted,#999);font-size:11px;', 'Ways out of this area - Generate made these, you decide'));
        const line = (label, title, action) => {
            const r = ctx.el('div', 'display:flex;gap:6px;align-items:center;');
            const text = ctx.el('span', 'flex:1;min-width:0;', label);
            text.title = title || label;
            r.appendChild(text);
            if (action)
                r.appendChild(action);
            box.appendChild(r);
        };
        rows.forEach((w) => {
            const seamId = w.way_id;
            const where = w.to_name || w.to_id || 'somewhere';
            const label = w.direction ? `${w.direction} → ${where}` : `to ${where}`;
            if (w.overridden) {
                line(label, 'You have taken this seam over; Generate leaves it alone', null);
                return;
            }
            line(label, 'Remove this way. Generate will not put it back.', ctx.btn('✕', () => ctx.setSeam(p, seamId, 'suppress'), 'padding:1px 7px;', 'Delete this way and keep Generate from re-adding it'));
        });
        taken.forEach((o) => {
            const restore = ctx.btn('↺', () => ctx.setSeam(p, o.way_id, 'auto'), 'padding:1px 7px;', 'Hand this seam back to Generate');
            const what = o.action === 'hand' && o.hand_way_id
                ? `your own way (${o.hand_way_id})` : 'removed by you';
            line(`to ${what}`, 'Generate left this one alone; restore it', restore);
        });
        return box;
    }
    function _blockerBadge(ctx, blockers) {
        const wrap = ctx.el('div', 'display:inline-flex;gap:6px;align-items:center;padding:2px 8px;' +
            'border-radius:12px;font-size:11px;font-weight:600;cursor:pointer;');
        const errors = (blockers || []).filter((b) => b.severity === 'error');
        const warns = (blockers || []).filter((b) => b.severity === 'warning');
        if (errors.length) {
            wrap.style.background = 'rgba(248,81,73,0.18)';
            wrap.style.border = '1px solid #f85149';
            wrap.style.color = '#ff7b72';
            wrap.textContent = `! ${errors.length} blocker${errors.length === 1 ? '' : 's'}`;
        }
        else if (warns.length) {
            wrap.style.background = 'rgba(210,153,34,0.18)';
            wrap.style.border = '1px solid #d29922';
            wrap.style.color = '#e3b341';
            wrap.textContent = `! ${warns.length} warning${warns.length === 1 ? '' : 's'}`;
        }
        else {
            wrap.style.background = 'rgba(63,185,80,0.15)';
            wrap.style.border = '1px solid #3fb950';
            wrap.style.color = '#56d364';
            wrap.textContent = 'ok ready to compile';
        }
        wrap.addEventListener('click', () => {
            const lines = (blockers || []).map((b) => `[${b.severity.toUpperCase()}] ${b.text || b.code}${b.remedy ? ' -> ' + b.remedy : ''}`);
            window.Dialog?.alert?.({
                title: 'Scope preflight checks',
                message: lines.length ? lines.join('\n\n') : 'No blockers found. This scope can compile to areas and ways cleanly.'
            });
        });
        return wrap;
    }
    function _featureBar(ctx, p) {
        const wrap = ctx.el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;');
        wrap.appendChild(ctx.el('span', 'font-size:12px;color:var(--text-muted,#999);', 'Feature:'));
        const sel = ctx.el('select', 'padding:3px;border-radius:5px;min-width:160px;');
        sel.setAttribute('data-role', 'wp-feature');
        const none = ctx.el('option', null, '- none (click a placed feature) -');
        none.value = '';
        sel.appendChild(none);
        (p.children || []).forEach((c) => {
            const opt = ctx.el('option', null, `${c.name}${c.placed ? ' (placed)' : ''}`);
            opt.value = c.id;
            if (c.id === ctx.state.selectedChild)
                opt.selected = true;
            sel.appendChild(opt);
        });
        sel.addEventListener('change', () => { ctx.state.selectedChild = sel.value || null; ctx.render(); });
        wrap.appendChild(sel);
        if (ctx.state.selectedChild) {
            const pl = (p.placements || []).find((x) => x.id === ctx.state.selectedChild);
            if (pl) {
                wrap.appendChild(ctx.el('span', 'font-size:11px;color:var(--text-muted,#999);', `on (${pl.x},${pl.y})`));
                wrap.appendChild(ctx.btn('Take off map', () => ctx.removeFeature(pl.id), 'font-size:11px;padding:2px 8px;', 'Remove this feature from the grid (its scope is untouched)'));
            }
            else {
                wrap.appendChild(ctx.el('span', 'font-size:11px;color:#e3b341;', 'Click a cell to place this feature'));
            }
        }
        return wrap;
    }
    function _areaBar(ctx, p) {
        const wrap = ctx.el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;');
        wrap.appendChild(ctx.el('span', 'font-size:12px;color:var(--text-muted,#999);', 'Area:'));
        const areas = ctx.GM().placeableAreas(p);
        const sel = ctx.el('select', 'padding:3px;border-radius:5px;min-width:160px;');
        sel.setAttribute('data-role', 'wp-area');
        const none = ctx.el('option', null, '- pick an area to place -');
        none.value = '';
        sel.appendChild(none);
        areas.forEach((a) => {
            const opt = ctx.el('option', null, `${a.name}${a.placed ? ' (placed)' : ''}`);
            opt.value = a.id;
            if (a.id === ctx.state.selectedArea)
                opt.selected = true;
            sel.appendChild(opt);
        });
        sel.addEventListener('change', () => { ctx.state.selectedArea = sel.value || null; ctx.render(); });
        wrap.appendChild(sel);
        const current = ctx.state.selectedArea;
        const placed = (p.area_placements || []).find((a) => a.id === current);
        if (placed) {
            wrap.appendChild(ctx.el('span', 'font-size:11px;color:var(--text-muted,#999);', `on (${placed.x},${placed.y})`));
            wrap.appendChild(ctx.btn('Take off map', () => ctx.unplaceArea(placed.id), 'font-size:11px;padding:2px 8px;', 'Take this area off the grid. The area itself, its items, and its ways are untouched.'));
            wrap.appendChild(ctx.btn('Promote to scope', () => ctx.promoteArea(placed.id), 'font-size:11px;padding:2px 8px;', 'Make this area its own child scope and open its grid so you can paint rooms inside it.'));
        }
        else if (current) {
            wrap.appendChild(ctx.el('span', 'font-size:11px;color:#e3b341;', 'Click a cell to place this area'));
        }
        return wrap;
    }
    function _gridHud(ctx, p) {
        const bar = ctx.el('div', 'position:absolute;top:10px;left:10px;z-index:2;' +
            'display:flex;gap:6px;align-items:center;padding:4px 8px;border-radius:6px;' +
            'background:rgba(13,17,23,0.85);backdrop-filter:blur(4px);' +
            'border:1px solid var(--border,#3a3a44);font-size:12px;');
        bar.setAttribute('data-role-hud', 'wp-hud');
        const dims = ctx.btn(p.grid ? `${p.grid.w}x${p.grid.h}` : 'no grid', () => ctx.openGridDialog(p), 'font-weight:600;', 'Change grid dimensions, mode, and coordinate units');
        dims.setAttribute('data-role', 'wp-grid-dims');
        ctx.state.dimsBtn = dims;
        bar.appendChild(dims);
        const refCtrl = _referenceControl(ctx, p);
        bar.appendChild(refCtrl);
        if (p.grid) {
            const fit = ctx.btn('Fit', () => ctx.fitGrid(p), null, 'Fit whole grid into canvas');
            bar.appendChild(fit);
            const zIn = ctx.btn('+', () => ctx.zoomBy(p, 1.25), 'padding:2px 8px;font-weight:bold;', 'Zoom in');
            const zOut = ctx.btn('-', () => ctx.zoomBy(p, 1 / 1.25), 'padding:2px 8px;font-weight:bold;', 'Zoom out');
            ctx.state.zoomInBtn = zIn;
            ctx.state.zoomOutBtn = zOut;
            bar.appendChild(zIn);
            bar.appendChild(zOut);
            ctx.syncZoomButtons();
        }
        return bar;
    }
    function _referenceControl(ctx, p) {
        const wrap = ctx.el('div', 'display:inline-flex;gap:4px;align-items:center;');
        wrap.setAttribute('data-role-ref', 'wp-reference-control');
        const ref = p.reference;
        const hasImg = Boolean(ref && ref.image);
        if (!hasImg) {
            const pick = ctx.btn('+ Background', () => _promptUpload(ctx, p), 'font-size:11px;padding:2px 8px;', 'Load an image file as a reference background');
            wrap.appendChild(pick);
            return wrap;
        }
        const visBtn = ctx.btn(ref?.visible ? 'Hide ref' : 'Show ref', async () => {
            await ctx.updateReference({ visible: !ref?.visible });
        }, 'font-size:11px;padding:2px 6px;');
        wrap.appendChild(visBtn);
        const opInput = ctx.el('input', 'width:50px;vertical-align:middle;');
        opInput.type = 'range';
        opInput.min = '0';
        opInput.max = '1';
        opInput.step = '0.05';
        opInput.value = String(ref?.opacity != null ? ref.opacity : 0.5);
        opInput.title = `Reference opacity: ${Math.round(parseFloat(opInput.value) * 100)}%`;
        opInput.addEventListener('input', () => {
            const val = parseFloat(opInput.value);
            if (ctx.state.refNode) {
                ctx.state.refNode.opacity(val);
                ctx.state.stage?.batchDraw();
            }
        });
        opInput.addEventListener('change', async () => {
            const val = parseFloat(opInput.value);
            await ctx.updateReference({ opacity: val });
        });
        wrap.appendChild(opInput);
        const editBtn = ctx.btn(ctx.state.refEdit ? 'Done adjust' : 'Adjust', () => {
            ctx.state.refEdit = !ctx.state.refEdit;
            if (ctx.state.refEdit)
                ctx.state.gridEdit = false;
            ctx.redrawDecor();
            ctx.softRender();
            ctx.status(ctx.state.refEdit
                ? 'Adjust mode: drag corners to scale, edges to crop, interior to move image.'
                : 'Exited adjust mode.');
        }, 'font-size:11px;padding:2px 6px;' + (ctx.state.refEdit ? 'background:#e3b341;color:#000;' : ''));
        wrap.appendChild(editBtn);
        const matchBtn = ctx.btn('Match aspect', async () => {
            await ctx.gridFromReference(p);
        }, 'font-size:11px;padding:2px 6px;', 'Match grid dimensions to image aspect ratio');
        wrap.appendChild(matchBtn);
        const dropBtn = ctx.btn('x', async () => {
            const ok = await window.Dialog?.confirm?.({
                title: 'Remove background image',
                message: 'Remove the reference image from this scope?'
            });
            if (ok)
                await ctx.updateReference({ image: null });
        }, 'font-size:11px;padding:2px 6px;color:#ff7b72;', 'Remove background image');
        wrap.appendChild(dropBtn);
        return wrap;
    }
    function _promptUpload(ctx, p) {
        const inp = document.createElement('input');
        inp.type = 'file';
        inp.accept = 'image/*';
        inp.style.display = 'none';
        inp.addEventListener('change', async () => {
            const file = inp.files && inp.files[0];
            if (!file)
                return;
            const reader = new FileReader();
            reader.onload = async () => {
                const dataUrl = reader.result;
                await ctx.updateReference({ image: dataUrl, visible: true, opacity: 0.5 });
            };
            reader.readAsDataURL(file);
        });
        document.body.appendChild(inp);
        inp.click();
        setTimeout(() => inp.remove(), 1000);
    }
    function _railOptions(ctx, p) {
        const count = ctx.selectedCells(p).length;
        if (ctx.state.tool === 'select') {
            const box = ctx.el('div', 'display:flex;flex-direction:column;gap:4px;align-items:flex-start;');
            box.appendChild(ctx.el('span', 'font-size:11px;color:var(--text-muted,#999);', count ? `${count} cell${count === 1 ? '' : 's'} selected` : 'no cells selected'));
            box.appendChild(ctx.btn('Select all', () => {
                const cells = {};
                for (let y = 0; y < p.grid.h; y += 1) {
                    for (let x = 0; x < p.grid.w; x += 1)
                        cells[ctx.GM().cellKey(x, y)] = true;
                }
                ctx.setSelection(p, cells);
                ctx.status(`Selected all ${p.grid.w * p.grid.h} cells.`);
            }, 'width:100%;', 'Select every cell on this grid (Ctrl+A)'));
            box.appendChild(ctx.btn('Clear', () => {
                ctx.setSelection(p, {});
                ctx.status('Selection cleared.');
            }, 'width:100%;', 'Select nothing (Escape)'));
            if (count) {
                box.appendChild(ctx.btn('Invert', () => {
                    const next = {};
                    for (let y = 0; y < p.grid.h; y += 1) {
                        for (let x = 0; x < p.grid.w; x += 1) {
                            const k = ctx.GM().cellKey(x, y);
                            if (!ctx.sel(p)[k])
                                next[k] = true;
                        }
                    }
                    ctx.setSelection(p, next);
                }, 'width:100%;', 'Select everything you had not selected'));
            }
            return box;
        }
        if (ctx.state.tool === 'move') {
            const box = ctx.el('div', 'display:flex;flex-direction:column;gap:4px;align-items:flex-start;');
            box.appendChild(ctx.el('span', 'font-size:11px;color:var(--text-muted,#999);', count ? `Move ${count} cell${count === 1 ? '' : 's'}` : 'Select cells first'));
            const grid = ctx.el('div', 'display:grid;grid-template-columns:repeat(3,1fr);gap:2px;');
            grid.appendChild(ctx.el('span'));
            grid.appendChild(ctx.btn('^', () => ctx.nudge(p, 0, -1), 'padding:2px 6px;', 'Up'));
            grid.appendChild(ctx.el('span'));
            grid.appendChild(ctx.btn('<-', () => ctx.nudge(p, -1, 0), 'padding:2px 6px;', 'Left'));
            grid.appendChild(ctx.btn('v', () => ctx.nudge(p, 0, 1), 'padding:2px 6px;', 'Down'));
            grid.appendChild(ctx.btn('->', () => ctx.nudge(p, 1, 0), 'padding:2px 6px;', 'Right'));
            box.appendChild(grid);
            return box;
        }
        if (ctx.state.tool === 'paint' || ctx.state.tool === 'erase' || ctx.state.tool === 'route') {
            const box = ctx.el('div', 'display:flex;flex-direction:column;gap:4px;align-items:flex-start;');
            box.appendChild(ctx.el('span', 'font-size:11px;color:var(--text-muted,#999);', 'brush'));
            const brushSel = ctx.el('select', 'padding:3px;border-radius:5px;');
            brushSel.setAttribute('data-role', 'wp-brush');
            [1, 2, 3, 5, 8, 12].forEach((n) => {
                const opt = ctx.el('option', null, `${n}x${n}`);
                opt.value = String(n);
                if (n === ctx.state.brush)
                    opt.selected = true;
                brushSel.appendChild(opt);
            });
            brushSel.addEventListener('change', () => {
                ctx.state.brush = parseInt(brushSel.value, 10) || 1;
                brushSel.blur();
            });
            box.appendChild(brushSel);
            return box;
        }
        if (ctx.state.tool === 'vision') {
            const box = ctx.el('div', 'display:flex;flex-direction:column;gap:5px;align-items:flex-start;width:100%;');
            const orig = ctx.state.visionOrigin;
            const tgt = ctx.state.visionTarget;
            box.appendChild(ctx.el('span', 'font-size:11px;font-weight:600;color:var(--text,#ddd);', 'Raycast Debugger'));
            box.appendChild(ctx.el('span', 'font-size:10.5px;color:var(--text-muted,#999);line-height:1.3;', orig ? `Origin: (${orig.x}, ${orig.y}) z=${orig.floor ?? 0}` : 'Click canvas to set origin'));
            if (tgt) {
                box.appendChild(ctx.el('span', 'font-size:10.5px;color:var(--text-muted,#999);line-height:1.3;', `Target: (${tgt.x}, ${tgt.y}) z=${tgt.floor ?? 0}`));
            }
            const lensBtn = ctx.btn(ctx.state.visionLens ? 'Visible arc: ON' : 'Visible arc: OFF', () => {
                ctx.state.visionLens = !ctx.state.visionLens;
                ctx.recomputeVisionField(p);
                ctx.redrawDecor();
                ctx.render();
            }, 'font-size:11px;width:100%;margin-top:4px;' + (ctx.state.visionLens ? 'background:#2f7d5a;color:#fff;' : ''));
            box.appendChild(lensBtn);
            return box;
        }
        return null;
    }
    async function setSeam(ctx, p, wayId, action) {
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/boundary_override`, { way_id: wayId, action });
            ctx.status(action === 'auto'
                ? 'Generate will mint that way again.'
                : 'Way removed - Generate will not put it back.');
            ctx.notify(true);
            ctx.render();
        }
        catch (e) {
            ctx.status(`Could not change that way: ${ctx.errText(e)}`, true);
        }
    }
    async function clearCell(ctx, p, x, y) {
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, {
                edits: ctx.GM().PAINT_LAYERS.map((layer) => ({ layer, x, y, value: null })),
            });
            ctx.status(`Cleared the paint on (${x},${y}).`);
            ctx.notify(true);
            ctx.render();
        }
        catch (e) {
            ctx.status(`Clear failed: ${ctx.errText(e)}`, true);
        }
    }
    async function setCellName(ctx, p, x, y, name) {
        const wanted = String(name || '').trim();
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/name`, { x, y, name: wanted });
            ctx.status(wanted
                ? `Named (${x},${y}) "${wanted}".`
                : `Cleared the name on (${x},${y}).`);
            ctx.notify(true);
            ctx.softRender();
        }
        catch (e) {
            ctx.status(`Name failed: ${ctx.errText(e)}`, true);
        }
    }
    const WorldPainterPalette = {
        blockerBadge: _blockerBadge,
        featureBar: _featureBar,
        areaBar: _areaBar,
        gridHud: _gridHud,
        referenceControl: _referenceControl,
        railOptions: _railOptions,
        setSeam,
        clearCell,
        setCellName,
        clearPaletteMemos: _clearPaletteMemos,
        layerOptions: _layerOptions,
        climateLegend: _climateLegend,
        paletteSections: _paletteSections,
        defaultValueForLayer: _defaultValueForLayer,
        valueControl: _valueControl,
        palettePanel: _palettePanel,
        cellPanel: _cellPanel,
        seamPanel: _seamPanel,
    };
    window.WorldPainterPalette = WorldPainterPalette;
    window.VW = window.VW || {};
    window.VW.worldPainterPalette = WorldPainterPalette;
})();
