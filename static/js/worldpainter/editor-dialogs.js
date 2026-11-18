"use strict";
/**
 * @module worldpainter/editor-dialogs - WorldPainter modal and popover dialogs
 * @contributes modal and popover dialogs for grid dimensions, heightmap import/export, and scope generation
 * @powers WorldPainter grid editing workflows (task-880)
 * @relates static/js/worldpainter/editor.js; static/js/worldpainter/grid-model.js
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(function () {
    'use strict';
    function _openGridDialog(ctx, p) {
        if (ctx.state.body) {
            const existing = ctx.state.body.querySelector("[data-role='wp-grid-dialog']");
            if (existing) {
                ctx.state.gridPreview = null;
                if (ctx.redrawDecor)
                    ctx.redrawDecor();
                existing.remove();
                return;
            }
        }
        const wrap = ctx.el('div', 'display:flex;flex-direction:column;gap:8px;' +
            'padding:10px;border:1px solid var(--border,#3a3a44);border-radius:8px;' +
            'background:var(--bg-card,#23232b);margin-bottom:8px;max-width:620px;');
        const cur = p.grid || { w: 10, h: 10 };
        const modes = (ctx.GM().MODES || ['world', 'town', 'interior']);
        const inputStyle = 'width:54px;padding:3px 6px;border-radius:5px;' +
            'border:1px solid var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);';
        const labelStyle = 'font-size:12px;color:var(--text-muted,#999);';
        const row1 = ctx.el('div', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;');
        row1.appendChild(ctx.el('span', labelStyle, 'Width:'));
        const wIn = ctx.el('input', inputStyle);
        wIn.type = 'number';
        wIn.min = '1';
        wIn.max = '400';
        wIn.value = String(cur.w);
        wIn.setAttribute('data-role', 'wp-grid-w');
        row1.appendChild(wIn);
        row1.appendChild(ctx.el('span', labelStyle, 'Height:'));
        const hIn = ctx.el('input', inputStyle);
        hIn.type = 'number';
        hIn.min = '1';
        hIn.max = '400';
        hIn.value = String(cur.h);
        hIn.setAttribute('data-role', 'wp-grid-h');
        row1.appendChild(hIn);
        row1.appendChild(ctx.el('span', labelStyle, 'Mode:'));
        const modeSel = ctx.el('select', 'padding:3px 6px;border-radius:5px;' +
            'border:1px solid var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
        modeSel.setAttribute('data-role', 'wp-grid-mode');
        modes.forEach((m) => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            if (m === p.mode)
                opt.selected = true;
            modeSel.appendChild(opt);
        });
        row1.appendChild(modeSel);
        wrap.appendChild(row1);
        // Origin-anchored resolution scaling controls (task-931).
        const scaleRow = ctx.el('div', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;' +
            'padding-top:6px;border-top:1px solid var(--border,#333);');
        const scaleChk = document.createElement('input');
        scaleChk.type = 'checkbox';
        scaleChk.setAttribute('data-role', 'wp-grid-scale-enabled');
        const scaleLbl = ctx.el('label', 'display:flex;align-items:center;gap:4px;font-size:12px;color:var(--text,#ddd);cursor:pointer;');
        scaleLbl.appendChild(scaleChk);
        scaleLbl.appendChild(document.createTextNode('Scale from anchor'));
        scaleRow.appendChild(scaleLbl);
        scaleRow.appendChild(ctx.el('span', labelStyle, 'Scale:'));
        const scaleIn = ctx.el('input', inputStyle);
        scaleIn.type = 'number';
        scaleIn.min = '0.25';
        scaleIn.max = '4';
        scaleIn.step = '0.05';
        scaleIn.value = '1';
        scaleIn.setAttribute('data-role', 'wp-grid-scale');
        scaleRow.appendChild(scaleIn);
        const defaultAnchor = ctx.state.gridAnchor || { x: Math.floor(cur.w / 2), y: Math.floor(cur.h / 2) };
        scaleRow.appendChild(ctx.el('span', labelStyle, 'Anchor X:'));
        const axIn = ctx.el('input', inputStyle);
        axIn.type = 'number';
        axIn.value = String(defaultAnchor.x);
        axIn.setAttribute('data-role', 'wp-grid-anchor-x');
        scaleRow.appendChild(axIn);
        scaleRow.appendChild(ctx.el('span', labelStyle, 'Y:'));
        const ayIn = ctx.el('input', inputStyle);
        ayIn.type = 'number';
        ayIn.value = String(defaultAnchor.y);
        ayIn.setAttribute('data-role', 'wp-grid-anchor-y');
        scaleRow.appendChild(ayIn);
        scaleRow.appendChild(ctx.btn('Center', () => {
            axIn.value = String(Math.floor(cur.w / 2));
            ayIn.value = String(Math.floor(cur.h / 2));
            scaleChk.checked = true;
            updatePreview();
        }, 'font-size:11px;padding:2px 6px;'));
        scaleRow.appendChild(ctx.btn('Origin (0,0)', () => {
            axIn.value = '0';
            ayIn.value = '0';
            scaleChk.checked = true;
            updatePreview();
        }, 'font-size:11px;padding:2px 6px;'));
        wrap.appendChild(scaleRow);
        // 4-way margin expansion controls (task-931).
        const marginRow = ctx.el('div', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;');
        marginRow.appendChild(ctx.el('span', labelStyle, 'Margins (+N/S/E/W):'));
        const mkMargin = (lbl, role) => {
            marginRow.appendChild(ctx.el('span', labelStyle, lbl));
            const inp = ctx.el('input', 'width:44px;padding:2px 4px;border-radius:5px;' +
                'border:1px solid var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            inp.type = 'number';
            inp.value = '0';
            inp.setAttribute('data-role', role);
            marginRow.appendChild(inp);
            return inp;
        };
        const mNorth = mkMargin('N:', 'wp-grid-margin-n');
        const mSouth = mkMargin('S:', 'wp-grid-margin-s');
        const mEast = mkMargin('E:', 'wp-grid-margin-e');
        const mWest = mkMargin('W:', 'wp-grid-margin-w');
        wrap.appendChild(marginRow);
        // Live preview canvas + summary (task-931).
        const previewRow = ctx.el('div', 'display:flex;gap:10px;align-items:center;flex-wrap:wrap;');
        const previewCanvas = document.createElement('canvas');
        previewCanvas.width = 160;
        previewCanvas.height = 100;
        previewCanvas.style.cssText = 'border:1px solid var(--border,#444);border-radius:4px;background:#14161c;';
        previewCanvas.setAttribute('data-role', 'wp-grid-preview-canvas');
        previewRow.appendChild(previewCanvas);
        const previewInfo = ctx.el('div', 'font-size:11px;color:var(--text-muted,#999);line-height:1.4;');
        previewInfo.setAttribute('data-role', 'wp-grid-preview-info');
        previewRow.appendChild(previewInfo);
        wrap.appendChild(previewRow);
        const getParams = () => {
            const w = Math.max(1, Math.min(400, parseInt(wIn.value, 10) || cur.w));
            const h = Math.max(1, Math.min(400, parseInt(hIn.value, 10) || cur.h));
            const s = Math.max(0.1, Math.min(10, parseFloat(scaleIn.value) || 1));
            const ax = parseInt(axIn.value, 10) || 0;
            const ay = parseInt(ayIn.value, 10) || 0;
            const north = parseInt(mNorth.value, 10) || 0;
            const south = parseInt(mSouth.value, 10) || 0;
            const east = parseInt(mEast.value, 10) || 0;
            const west = parseInt(mWest.value, 10) || 0;
            return { w, h, s, ax, ay, north, south, east, west, scaleOn: scaleChk.checked };
        };
        const renderMiniPreview = (pr, ghost) => {
            const c2d = previewCanvas.getContext('2d');
            if (!c2d)
                return;
            const cw = previewCanvas.width;
            const ch = previewCanvas.height;
            c2d.clearRect(0, 0, cw, ch);
            const maxDim = Math.max(1, cur.w, cur.h, pr.w, pr.h);
            const pad = 10;
            const cellPx = Math.min((cw - pad * 2) / maxDim, (ch - pad * 2) / maxDim);
            const ox = pad + (cw - pad * 2 - pr.w * cellPx) / 2;
            const oy = pad + (ch - pad * 2 - pr.h * cellPx) / 2;
            // Old grid outline.
            c2d.strokeStyle = 'rgba(255,255,255,0.22)';
            c2d.strokeRect(ox + pr.west * cellPx, oy + pr.north * cellPx, cur.w * cellPx, cur.h * cellPx);
            // New grid outline.
            c2d.strokeStyle = '#58a6ff';
            c2d.fillStyle = 'rgba(88,166,255,0.10)';
            c2d.fillRect(ox, oy, pr.w * cellPx, pr.h * cellPx);
            c2d.strokeRect(ox, oy, pr.w * cellPx, pr.h * cellPx);
            if (ghost) {
                c2d.fillStyle = '#3fb950';
                const drawPt = (item) => {
                    if (!item || typeof item.x !== 'number' || typeof item.y !== 'number')
                        return;
                    c2d.fillRect(ox + item.x * cellPx, oy + item.y * cellPx, Math.max(2, cellPx), Math.max(2, cellPx));
                };
                (ghost.area_placements || []).forEach(drawPt);
                (ghost.placements || []).forEach(drawPt);
            }
            if (pr.scaleOn) {
                const px = ox + (pr.ax + 0.5) * cellPx;
                const py = oy + (pr.ay + 0.5) * cellPx;
                c2d.strokeStyle = '#ff9f43';
                c2d.beginPath();
                c2d.arc(px, py, 4, 0, Math.PI * 2);
                c2d.stroke();
            }
        };
        const updatePreview = () => {
            const pr = getParams();
            let ghost;
            if (pr.scaleOn) {
                ghost = ctx.GM().scaleGridWithAnchor(p, { x: pr.ax, y: pr.ay }, pr.s, { w: pr.w, h: pr.h });
                ctx.state.gridPreview = {
                    w: pr.w,
                    h: pr.h,
                    offsetX: 0,
                    offsetY: 0,
                    anchor: { x: pr.ax, y: pr.ay },
                    scaleFactor: pr.s,
                };
                previewInfo.textContent = `Preview: ${pr.w}×${pr.h} · scale ${pr.s.toFixed(2)}× around (${pr.ax}, ${pr.ay})`;
            }
            else {
                ghost = ctx.GM().expandGridMargins(p, {
                    north: pr.north,
                    south: pr.south,
                    east: pr.east,
                    west: pr.west,
                });
                ctx.state.gridPreview = {
                    w: pr.w,
                    h: pr.h,
                    offsetX: pr.west,
                    offsetY: pr.north,
                    anchor: null,
                    scaleFactor: 1,
                };
                const shift = (pr.west || pr.north) ? ` · shift (${pr.west >= 0 ? '+' : ''}${pr.west}, ${pr.north >= 0 ? '+' : ''}${pr.north})` : '';
                previewInfo.textContent = `Preview: ${pr.w}×${pr.h}${shift}`;
            }
            renderMiniPreview(pr, ghost);
            if (ctx.redrawDecor)
                ctx.redrawDecor();
        };
        scaleIn.addEventListener('input', () => {
            scaleChk.checked = true;
            const s = Math.max(0.1, Math.min(10, parseFloat(scaleIn.value) || 1));
            wIn.value = String(Math.max(1, Math.min(400, Math.round(cur.w * s))));
            hIn.value = String(Math.max(1, Math.min(400, Math.round(cur.h * s))));
            updatePreview();
        });
        [mNorth, mSouth, mEast, mWest].forEach((inp) => {
            inp.addEventListener('input', () => {
                scaleChk.checked = false;
                const pr = getParams();
                wIn.value = String(Math.max(1, Math.min(400, cur.w + pr.east + pr.west)));
                hIn.value = String(Math.max(1, Math.min(400, cur.h + pr.north + pr.south)));
                updatePreview();
            });
        });
        [wIn, hIn, axIn, ayIn, scaleChk].forEach((inp) => {
            inp.addEventListener('input', updatePreview);
            inp.addEventListener('change', updatePreview);
        });
        const clearPreview = () => {
            ctx.state.gridPreview = null;
            if (ctx.redrawDecor)
                ctx.redrawDecor();
        };
        const actions = ctx.el('div', 'display:flex;gap:6px;');
        actions.appendChild(ctx.btn('Apply', async () => {
            const pr = getParams();
            const mode = modeSel.value || p.mode;
            const hasMarginOffset = !pr.scaleOn && (pr.west !== 0 || pr.north !== 0);
            const stranded = (pr.scaleOn || hasMarginOffset) ? 0 : ctx.GM().strandedCount(p, pr.w, pr.h);
            if (stranded > 0) {
                const ok = await window.Dialog?.confirm?.({
                    title: 'Resize Grid',
                    message: `Shrink to ${pr.w}×${pr.h}?\n\n${stranded} painted cell(s) or placement(s) outside it will be pruned. This cannot be undone.`,
                    danger: true
                });
                if (!ok)
                    return;
            }
            const body = { w: pr.w, h: pr.h, mode };
            if (pr.scaleOn) {
                body.anchor_x = pr.ax;
                body.anchor_y = pr.ay;
                body.scale_factor = pr.s;
                ctx.state.gridAnchor = { x: pr.ax, y: pr.ay };
            }
            else if (hasMarginOffset) {
                body.offset_x = pr.west;
                body.offset_y = pr.north;
            }
            clearPreview();
            try {
                ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid`, body);
                ctx.notify(true);
                ctx.render();
                ctx.status(`Grid set to ${pr.w}×${pr.h} (${mode})`
                    + (stranded ? `, ${stranded} out-of-bounds cell(s) pruned` : '') + '.');
            }
            catch (e) {
                ctx.status(`Grid save failed: ${ctx.errText(e)}`, true);
            }
        }, 'font-weight:600;'));
        actions.appendChild(ctx.btn('Cancel', () => {
            clearPreview();
            wrap.remove();
        }));
        wrap.appendChild(actions);
        updatePreview();
        if (ctx.state.body) {
            wrap.setAttribute("data-role", "wp-grid-dialog");
            ctx.state.body.insertBefore(wrap, ctx.state.body.firstChild);
        }
    }
    function _openHeightmapImportDialog(ctx, p) {
        const wrap = ctx.el('div', 'display:flex;flex-direction:column;gap:10px;padding:12px;' +
            'border:1px solid var(--border,#3a3a44);border-radius:8px;background:var(--bg-card,#23232b);' +
            'max-width:540px;margin-bottom:10px;');
        wrap.setAttribute('data-role', 'wp-heightmap-import-dialog');
        const titleRow = ctx.el('div', 'display:flex;justify-content:space-between;align-items:center;');
        titleRow.appendChild(ctx.el('span', 'font-weight:600;font-size:13px;', 'Import Greyscale Heightmap'));
        titleRow.appendChild(ctx.btn('✕', () => wrap.remove(), 'padding:2px 8px;font-size:12px;'));
        wrap.appendChild(titleRow);
        const desc = ctx.el('div', 'font-size:12px;color:var(--text-muted,#999);line-height:1.4;', 'Upload a greyscale image. Black (0) maps to the minimum height, white (255) to the maximum. ' +
            'Storeys are quantised dynamically per the calibrated metres-per-storey scale.');
        wrap.appendChild(desc);
        const fileInput = ctx.el('input', 'font-size:12px;');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.setAttribute('data-role', 'wp-heightmap-file');
        wrap.appendChild(fileInput);
        const rangeRow = ctx.el('div', 'display:flex;align-items:center;gap:12px;flex-wrap:wrap;');
        const mkNum = (label, defVal, role) => {
            rangeRow.appendChild(ctx.el('span', 'font-size:12px;color:var(--text-muted,#999);', label));
            const inp = ctx.el('input', 'width:64px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            inp.type = 'number';
            inp.value = String(defVal);
            inp.setAttribute('data-role', role);
            rangeRow.appendChild(inp);
            return inp;
        };
        const blackInput = mkNum('Black (m):', 0, 'wp-heightmap-black');
        const whiteInput = mkNum('White (m):', 60, 'wp-heightmap-white');
        wrap.appendChild(rangeRow);
        const previewInfo = ctx.el('div', 'font-size:11px;color:var(--text-muted,#999);line-height:1.4;');
        previewInfo.setAttribute('data-role', 'wp-heightmap-info');
        wrap.appendChild(previewInfo);
        let parsedFloorMap = null;
        let climbSteps = 0;
        const updatePreview = () => {
            if (!fileInput.files || !fileInput.files[0])
                return;
            const file = fileInput.files[0];
            const minM = parseFloat(blackInput.value) || 0;
            const maxM = parseFloat(whiteInput.value) || (minM + 3);
            const metresPerStorey = (ctx.state.vocab && ctx.state.vocab.metres_per_storey) || 3.0;
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const grid = p.grid || { w: 10, h: 10 };
                    canvas.width = grid.w;
                    canvas.height = grid.h;
                    const c2d = canvas.getContext('2d');
                    if (!c2d)
                        return;
                    c2d.drawImage(img, 0, 0, grid.w, grid.h);
                    const imgData = c2d.getImageData(0, 0, grid.w, grid.h).data;
                    parsedFloorMap = {};
                    let minS = Infinity;
                    let maxS = -Infinity;
                    for (let y = 0; y < grid.h; y += 1) {
                        for (let x = 0; x < grid.w; x += 1) {
                            const idx = (y * grid.w + x) * 4;
                            const lum = Math.round(0.299 * imgData[idx] + 0.587 * imgData[idx + 1] + 0.114 * imgData[idx + 2]);
                            const m = ctx.GM().luminanceToMetres(lum, minM, maxM);
                            const storeys = ctx.GM().metresToStoreys(m, metresPerStorey);
                            parsedFloorMap[ctx.GM().cellKey(x, y)] = storeys;
                            if (storeys < minS)
                                minS = storeys;
                            if (storeys > maxS)
                                maxS = storeys;
                        }
                    }
                    climbSteps = ctx.GM().climbGatedSteps(grid, parsedFloorMap, 3);
                    previewInfo.textContent = `Image: ${img.width}×${img.height} (scaled to grid ${grid.w}×${grid.h}) · ` +
                        `Storey range: ${minS} to ${maxS} · Climb gated steps (|Δ| > 3): ${climbSteps}`;
                };
                img.src = e.target?.result;
            };
            reader.readAsDataURL(file);
        };
        fileInput.addEventListener('change', updatePreview);
        blackInput.addEventListener('input', updatePreview);
        whiteInput.addEventListener('input', updatePreview);
        const actions = ctx.el('div', 'display:flex;gap:8px;justify-content:flex-end;margin-top:4px;');
        const applyBtn = ctx.btn('Apply to Floor Layer', async () => {
            if (!parsedFloorMap) {
                ctx.status('Select an image first.', true);
                return;
            }
            if (climbSteps > 0) {
                const ok = await window.Dialog?.confirm?.({
                    title: 'Climb Gated Steps Detected',
                    message: `This heightmap creates ${climbSteps} neighbouring cell transitions with steep storey changes (|Δ| > 3) that require climbing abilities. Proceed?`,
                    danger: true
                });
                if (!ok)
                    return;
            }
            const grid = p.grid || { w: 10, h: 10 };
            const edits = [];
            for (let y = 0; y < grid.h; y += 1) {
                for (let x = 0; x < grid.w; x += 1) {
                    const key = ctx.GM().cellKey(x, y);
                    const s = parsedFloorMap[key];
                    if (s !== undefined) {
                        edits.push({ layer: 'floor', x, y, value: String(s) });
                    }
                }
            }
            try {
                ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, { edits });
                ctx.state.paintCacheValid = false;
                ctx.notify(true);
                ctx.render();
                wrap.remove();
                ctx.status(`Imported heightmap (${edits.length} cells).`, false);
            }
            catch (e) {
                ctx.status(`Import failed: ${ctx.errText(e)}`, true);
            }
        }, 'font-weight:600;');
        applyBtn.setAttribute('data-role', 'wp-heightmap-apply');
        actions.appendChild(applyBtn);
        actions.appendChild(ctx.btn('Cancel', () => wrap.remove()));
        wrap.appendChild(actions);
        if (ctx.state.body) {
            ctx.state.body.appendChild(wrap);
        }
    }
    function _openHeightmapExportDialog(ctx, p) {
        const wrap = ctx.el('div', 'display:flex;flex-direction:column;gap:10px;padding:12px;' +
            'border:1px solid var(--border,#3a3a44);border-radius:8px;background:var(--bg-card,#23232b);' +
            'max-width:540px;margin-bottom:10px;');
        wrap.setAttribute('data-role', 'wp-heightmap-export-dialog');
        const titleRow = ctx.el('div', 'display:flex;justify-content:space-between;align-items:center;');
        titleRow.appendChild(ctx.el('span', 'font-weight:600;font-size:13px;', 'Export Greyscale Heightmap'));
        titleRow.appendChild(ctx.btn('✕', () => wrap.remove(), 'padding:2px 8px;font-size:12px;'));
        wrap.appendChild(titleRow);
        const grid = p.grid || { w: 10, h: 10 };
        const floorMap = (p.layers && p.layers.floor) || {};
        const metresPerStorey = (ctx.state.vocab && ctx.state.vocab.metres_per_storey) || 3.0;
        let minStorey = Infinity;
        let maxStorey = -Infinity;
        for (let y = 0; y < grid.h; y += 1) {
            for (let x = 0; x < grid.w; x += 1) {
                const rawVal = floorMap[ctx.GM().cellKey(x, y)];
                const s = rawVal != null ? Number(rawVal) : 0;
                if (s < minStorey)
                    minStorey = s;
                if (s > maxStorey)
                    maxStorey = s;
            }
        }
        const minM = ctx.GM().storeysToMetres(minStorey, metresPerStorey);
        const maxM = ctx.GM().storeysToMetres(maxStorey, metresPerStorey);
        const info = ctx.el('div', 'font-size:11px;color:var(--text-muted,#999);', `Grid: ${grid.w}×${grid.h} · Storeys: ${minStorey} to ${maxStorey} · Metres: ${minM}m to ${maxM}m`);
        wrap.appendChild(info);
        const rangeRow = ctx.el('div', 'display:flex;align-items:center;gap:12px;flex-wrap:wrap;');
        const mkNum = (label, defVal, role) => {
            rangeRow.appendChild(ctx.el('span', 'font-size:12px;color:var(--text-muted,#999);', label));
            const inp = ctx.el('input', 'width:64px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            inp.type = 'number';
            inp.value = String(defVal);
            inp.setAttribute('data-role', role);
            rangeRow.appendChild(inp);
            return inp;
        };
        const blackInput = mkNum('Black (m):', minM, 'wp-heightmap-export-black');
        const whiteInput = mkNum('White (m):', Math.max(minM + 3, maxM), 'wp-heightmap-export-white');
        wrap.appendChild(rangeRow);
        const actions = ctx.el('div', 'display:flex;gap:8px;justify-content:flex-end;margin-top:4px;');
        const exportBtn = ctx.btn('Download Heightmap PNG', () => {
            const expMinM = parseFloat(blackInput.value) || 0;
            const expMaxM = parseFloat(whiteInput.value) || (expMinM + 3);
            const canvas = document.createElement('canvas');
            canvas.width = grid.w;
            canvas.height = grid.h;
            const c2d = canvas.getContext('2d');
            if (!c2d)
                return;
            const imgData = c2d.createImageData(grid.w, grid.h);
            for (let y = 0; y < grid.h; y += 1) {
                for (let x = 0; x < grid.w; x += 1) {
                    const idx = (y * grid.w + x) * 4;
                    const s = floorMap[ctx.GM().cellKey(x, y)] != null ? floorMap[ctx.GM().cellKey(x, y)] : 0;
                    const m = ctx.GM().storeysToMetres(s, metresPerStorey);
                    const lum = ctx.GM().metresToLuminance(m, expMinM, expMaxM);
                    imgData.data[idx] = lum;
                    imgData.data[idx + 1] = lum;
                    imgData.data[idx + 2] = lum;
                    imgData.data[idx + 3] = 255;
                }
            }
            c2d.putImageData(imgData, 0, 0);
            const link = document.createElement('a');
            link.download = `heightmap_${p.scope.id}_${expMinM}m_to_${expMaxM}m.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
            wrap.remove();
            ctx.status(`Heightmap exported (${grid.w}×${grid.h}, ${expMinM}m to ${expMaxM}m).`, false);
        }, 'font-weight:600;');
        exportBtn.setAttribute('data-role', 'wp-heightmap-download');
        actions.appendChild(exportBtn);
        actions.appendChild(ctx.btn('Cancel', () => wrap.remove()));
        wrap.appendChild(actions);
        if (ctx.state.body) {
            ctx.state.body.appendChild(wrap);
        }
    }
    async function _promptNewScope(ctx, parentId) {
        const promptRes = await window.Dialog?.prompt?.({
            title: 'New Feature Scope',
            fields: [{ key: 'name', label: 'Feature Name', value: 'New feature' }]
        });
        const name = promptRes?.name?.trim();
        if (!name)
            return;
        const mode = parentId && ctx.state.payload
            ? ctx.GM().nextMode(ctx.state.payload.mode) : 'world';
        const body = { name, parent_id: parentId || null, mode };
        if (ctx.state.payload && ctx.state.payload.grid) {
            body.w = Math.max(1, Math.min(8, ctx.state.payload.grid.w));
            body.h = Math.max(1, Math.min(8, ctx.state.payload.grid.h));
        }
        try {
            const created = await ctx.post('', body);
            ctx.notify(true);
            if (parentId && ctx.state.payload) {
                ctx.state.selectedChild = created.scope.id;
                ctx.state.payload = await ctx.req(`/api/world/scopes/${encodeURIComponent(parentId)}/grid`, { cache: 'no-store' });
                ctx.render();
                ctx.status(`Created "${created.scope.name}" - pick Feature and click a cell to place it.`);
            }
            else {
                ctx.load(created.scope.id);
            }
        }
        catch (e) {
            ctx.status(`Create failed: ${ctx.errText(e)}`, true);
        }
    }
    async function _paintInterior(ctx) {
        const p = ctx.state.payload;
        if (!p)
            return;
        const vocab = ctx.state.vocab || {};
        const options = (vocab.b ? vocab.b : (vocab.biomes || []))
            .filter((r) => (r.tags || []).indexOf('building') >= 0)
            .map((r) => r.id || '');
        if (!options.length) {
            ctx.status('No building types in the vocabulary.', true);
            return;
        }
        const pickRes = await window.Dialog?.prompt?.({
            title: 'Paint Building Interior',
            message: `Paint which building's interior into "${p.scope.name}"?\n\nAvailable: ${options.join(', ')}`,
            fields: [{ key: 'building', label: 'Building Type', value: options.indexOf('inn') >= 0 ? 'inn' : options[0] }]
        });
        const pick = pickRes?.building?.trim();
        if (!pick || !options.includes(pick)) {
            if (pick)
                ctx.status(`${pick} is not a building type.`, true);
            return;
        }
        try {
            const res = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/interior`, { building: pick });
            ctx.state.payload = res;
            ctx.state.paintCacheValid = false;
            const notes = (res.report && res.report.notes) || [];
            ctx.status(`Painted the ${pick} plan - edit the cells, then ⚙ Generate.`);
            for (let i = 0; i < Math.min(notes.length, 2); i += 1) {
                ctx.status(notes[i]);
            }
            ctx.notify(true);
            ctx.render();
        }
        catch (e) {
            ctx.status(`Could not paint that interior: ${ctx.errText(e)}`, true);
        }
    }
    async function _promoteArea(ctx, areaId) {
        const p = ctx.state.payload;
        if (!p)
            return;
        const area = ((p.area_placements || []).find((a) => a.id === areaId))
            || ((p.unplaced_areas || []).find((a) => a.id === areaId));
        if (!area) {
            ctx.status(`No area '${areaId}' on this map to make a scope of.`, true);
            return;
        }
        const defaultName = `${area.name} interior`;
        const promptRes = await window.Dialog?.prompt?.({
            title: 'Promote to Scope',
            fields: [
                { key: 'name', label: 'Name for the new child scope', value: defaultName },
                { key: 'id', label: 'ID for the new scope (lower-case, no spaces)', value: ctx.slug(defaultName) }
            ]
        });
        const name = (promptRes?.name || '').trim();
        if (!name)
            return;
        const scopeId = (promptRes?.id || '').trim() || ctx.slug(name);
        const hasCell = Number.isInteger(area.x) && Number.isInteger(area.y);
        const body = {
            scope_id: scopeId,
            name,
            area_ids: [areaId],
            parent_id: p.scope.id,
            entry_area_id: areaId,
            mode: 'interior',
        };
        if (hasCell)
            body.cell = { x: area.x, y: area.y };
        try {
            const res = await ctx.postRoot('/api/world/promote', body);
            ctx.state.selectedArea = null;
            await ctx.reloadPayload();
            ctx.status(`"${res.name}" is now a scope of its own, entered from `
                + `${hasCell ? `cell (${area.x},${area.y})` : 'nowhere yet'}.`);
            ctx.notify(true);
        }
        catch (e) {
            ctx.status(`Promote failed: ${ctx.errText(e)}`, true);
        }
    }
    async function _renameScope(ctx, scopeId, currentName) {
        const promptRes = await window.Dialog?.prompt?.({
            title: 'Rename Scope',
            fields: [{ key: 'name', label: 'Scope Name', value: currentName || scopeId }]
        });
        if (!promptRes)
            return;
        const clean = (promptRes.name || '').trim();
        if (!clean || clean === currentName)
            return;
        try {
            await ctx.post(`/${encodeURIComponent(scopeId)}/rename`, { name: clean });
            ctx.notify(true);
            if (ctx.state.scopeId === scopeId)
                await ctx.load(scopeId);
            else
                await ctx.reloadPayload();
            ctx.status(`Renamed to "${clean}".`, false);
        }
        catch (e) {
            ctx.status(`Rename failed: ${ctx.errText(e)}`, true);
        }
    }
    async function _deleteScope(ctx, scopeId, name) {
        const label = name || scopeId;
        const ok = await window.Dialog?.confirm?.({
            title: 'Delete Scope',
            message: `Delete scope "${label}"?\n\nThis removes the scope, unplaces it, and deletes the areas/ways/items generated for it. Scopes that still have children must be emptied first.`,
            danger: true
        });
        if (!ok)
            return;
        const trail = (ctx.state.payload && ctx.state.payload.breadcrumb) || [];
        const parentId = trail.length > 1 ? trail[trail.length - 2].id : null;
        try {
            const result = await ctx.post(`/${encodeURIComponent(scopeId)}/delete`, {});
            ctx.notify(true);
            if (ctx.state.scopeId === scopeId) {
                if (parentId)
                    ctx.load(parentId);
                else
                    ctx.open(null);
            }
            else if (!ctx.state.scopeId) {
                if (ctx.showChooser)
                    await ctx.showChooser(ctx);
                else
                    await showChooser(ctx);
            }
            else {
                await ctx.reloadPayload();
            }
            ctx.status(`Deleted "${label}" (${result.deleted_nodes || 0} generated node(s)).`, false);
        }
        catch (e) {
            ctx.status(`Delete failed: ${ctx.errText(e)}`, true);
        }
    }
    function _generate(ctx) {
        const p = ctx.state.payload;
        if (!p)
            return;
        const est = ctx.GM().estimateCompile(p, ctx.state.merge);
        const needConfirm = est.total > 3000;
        const run = async (allowRegenerate) => {
            if (needConfirm && !allowRegenerate) {
                const ok = await window.Dialog?.confirm?.({
                    title: 'Large Grid Warning',
                    message: `This will create about ${est.areas} areas and ${est.ways} ways (${est.total} nodes).\n\nThe graph view may become unresponsive. Consider "merge same-biome", or generating smaller zones.`,
                    danger: true
                });
                if (!ok)
                    return;
            }
            const body = { region_merge: !!ctx.state.merge };
            if (!allowRegenerate) {
                try {
                    const prev = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/generate/preview`, body);
                    if (prev && prev.preview) {
                        const areaNames = (prev.areas || []).map((a) => a.name).join(', ') || 'none';
                        const itemNames = (prev.items || []).map((i) => i.name).join(', ') || 'none';
                        const wayNames = (prev.ways || []).map((w) => w.name).join(', ') || 'none';
                        const missing = Object.keys(prev.missing_tags || {}).join(', ') || 'none';
                        const seed = prev.seed || 'default';
                        const recipe = prev.recipe_id || 'painted grid';
                        const ok = await window.Dialog?.confirm?.({
                            title: 'Generation Preview',
                            message: `Recipe: ${recipe} (seed: ${seed})\n\nAreas (${prev.areas?.length || 0}): ${areaNames}\n\nItems (${prev.items?.length || 0}): ${itemNames}\n\nWays (${prev.ways?.length || 0}): ${wayNames}\n\nMissing tag candidates: ${missing}\n\nApply patch and generate scope?`,
                            confirmLabel: 'Apply Patch'
                        });
                        if (!ok)
                            return;
                    }
                }
                catch (prevErr) {
                    if (/already materialized/.test(ctx.errText(prevErr))) {
                        const ok = await window.Dialog?.confirm?.({
                            title: 'Re-run Generation',
                            message: `${ctx.errText(prevErr)}\n\nRe-run generation?`,
                            danger: true
                        });
                        if (ok)
                            return run(true);
                        return;
                    }
                }
            }
            try {
                const result = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/generate`, allowRegenerate ? { ...body, allow_regenerate: true } : body);
                ctx.state.payload = result;
                ctx.state.selectedChild = null;
                ctx.notify(true);
                const r = result.report || {};
                const notes = (r.notes || []).join('; ');
                ctx.status(`⚙ Generated ${r.node_count || 0} node(s), ` +
                    `${r.edge_count || 0} edge(s)` +
                    (notes ? ` - ${notes}` : ''), false);
                ctx.render();
            }
            catch (e) {
                if (!allowRegenerate && /already materialized|not a regenerable generated node/.test(ctx.errText(e))) {
                    const ok = await window.Dialog?.confirm?.({
                        title: 'Re-run Generation',
                        message: `${ctx.errText(e)}\n\nRe-run generation?`,
                        danger: true
                    });
                    if (ok)
                        return run(true);
                }
                ctx.status(`Generate failed: ${ctx.errText(e)}`, true);
            }
        };
        return run(false);
    }
    function _ungenerate(ctx) {
        const p = ctx.state.payload;
        if (!p || !p.scope)
            return;
        (async () => {
            const ok = await window.Dialog?.confirm?.({
                title: 'Ungenerate Scope',
                message: `Delete every generated node for "${p.scope.name}"?\n\nThe painted grid, reference and placements are kept, and the scope returns to unmade so you can ⚙ Generate again.`,
                danger: true
            });
            if (!ok)
                return;
            try {
                const result = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/ungenerate`, {});
                ctx.state.payload = result;
                ctx.state.selectedChild = null;
                ctx.notify(true);
                ctx.status(`🧹 Removed ${result.deleted_nodes || 0} generated node(s) - grid kept.`, false);
            }
            catch (e) {
                ctx.status(`Ungenerate failed: ${ctx.errText(e)}`, true);
            }
        })();
    }
    async function showChooser(ctx) {
        ctx.state.scopeId = null;
        ctx.state.payload = null;
        const box = ctx.renderShell('🗺️ WorldPainter');
        box.appendChild(ctx.el('div', 'color:var(--text-muted,#999);margin-bottom:10px;', 'Choose a scope to open its grid.'));
        const list = ctx.el('div', 'display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;', 'Loading…');
        box.appendChild(list);
        box.appendChild(ctx.btn('+ New root scope', () => _promptNewScope(ctx, null)));
        try {
            const root = await ctx.req('/api/world/scopes', { cache: 'no-store' });
            list.textContent = '';
            const scopeOptions = window.ScopeOptions;
            const scopes = scopeOptions
                ? scopeOptions.flattenScopes(root)
                : (root.children || []);
            if (!scopes.length) {
                list.appendChild(ctx.el('div', 'color:var(--text-muted,#999);', 'No scopes yet. Create one to start painting.'));
                return;
            }
            scopes.forEach((card) => list.appendChild(scopeCard(ctx, card, () => ctx.load(card.id))));
        }
        catch (e) {
            list.textContent = `Failed to load scopes: ${ctx.errText(e)}`;
        }
    }
    function scopeCard(ctx, card, onOpen) {
        const indent = '  '.repeat(Math.max(0, card.depth || 0));
        const el = ctx.el('div', 'border:1px solid var(--border,#444);border-radius:8px;padding:8px 10px;' +
            'min-width:150px;cursor:pointer;background:var(--bg-card,#24242b);' +
            (card.depth ? 'margin-left:' + (card.depth * 16) + 'px;' : ''));
        const head = ctx.el('div', 'display:flex;align-items:center;gap:6px;');
        head.appendChild(ctx.el('span', 'font-weight:600;flex:1 1 auto;', indent + (card.name || card.id)));
        head.appendChild(_iconBtn(ctx, '✏️', 'Rename scope', () => _renameScope(ctx, card.id, card.name)));
        head.appendChild(_iconBtn(ctx, '🗑', 'Delete scope', () => _deleteScope(ctx, card.id, card.name)));
        el.appendChild(head);
        const areas = card.area_count != null ? card.area_count : card.areaCount;
        const items = card.item_count != null ? card.item_count : card.itemCount;
        const bits = [`${card.kind || 'scope'} · ${card.state || ''}${card.mode ? ' · ' + card.mode : ''}`];
        if (areas != null)
            bits.push(`${areas} area${areas === 1 ? '' : 's'}`);
        if (items)
            bits.push(`${items} item${items === 1 ? '' : 's'}`);
        el.appendChild(ctx.el('div', 'font-size:10px;color:var(--text-muted,#999);', bits.join(' · ')));
        el.addEventListener('click', () => (onOpen ? onOpen(card) : ctx.load(card.id)));
        return el;
    }
    function _iconBtn(ctx, label, title, onClick) {
        const b = ctx.el('button', 'cursor:pointer;border:1px solid var(--border,#444);background:transparent;' +
            'color:var(--text,#ddd);border-radius:5px;padding:1px 5px;font-size:11px;line-height:1.2;', label);
        b.title = title;
        b.addEventListener('click', (e) => { e.stopPropagation(); onClick(); });
        return b;
    }
    const WorldPainterDialogs = {
        showChooser,
        scopeCard,
        openGridDialog: _openGridDialog,
        openHeightmapImportDialog: _openHeightmapImportDialog,
        openHeightmapExportDialog: _openHeightmapExportDialog,
        promptNewScope: _promptNewScope,
        paintInterior: _paintInterior,
        promoteArea: _promoteArea,
        renameScope: _renameScope,
        deleteScope: _deleteScope,
        generate: _generate,
        ungenerate: _ungenerate,
    };
    window.WorldPainterDialogs = WorldPainterDialogs;
    window.VW = window.VW || {};
    window.VW.worldPainterDialogs = WorldPainterDialogs;
})();
