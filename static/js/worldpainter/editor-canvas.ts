/**
 * @module worldpainter/editor-canvas - WorldPainter Konva canvas rendering and stroke handling
 * @contributes Konva layer rendering passes, grid lines, vision decor, and paint stroke accumulation
 * @powers WorldPainter canvas visualization and painting (task-880)
 * @relates static/js/worldpainter/editor.js; static/js/worldpainter/grid-model.js
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(function () {
    'use strict';

    function _drawGridLines(ctx: any, c2d: CanvasRenderingContext2D, p: any): void {
        const CELL = ctx.CELL || 22;
        const ext = ctx.gridExtent(p);
        const preview = ctx.state.cellSizePreview;
        const hasRefImg = Boolean(ctx.state.refImage && ctx.state.refImage.naturalWidth
            && p.reference && p.reference.image);
        const refRect = (preview && hasRefImg) ? ctx.refRectCells(p, ctx.state.refImage, preview) : null;
        const w = refRect ? (refRect.w * CELL) : (ext.w * CELL);
        const h = refRect ? (refRect.h * CELL) : (ext.h * CELL);
        const maxCols = refRect ? Math.ceil(refRect.w) : ext.w;
        const maxRows = refRect ? Math.ceil(refRect.h) : ext.h;
        c2d.save();
        const scale = ctx.state.stage ? ctx.state.stage.scaleX() : 1;
        c2d.strokeStyle = ctx.state.gridEdit ? '#e3b341' : 'rgba(255,255,255,0.45)';
        c2d.lineWidth = 2 / scale;
        c2d.strokeRect(0, 0, w, h);
        const bounds = ctx.GM().paintedBounds(p);
        if (bounds) {
            c2d.fillStyle = 'rgba(227,179,65,0.08)';
            c2d.fillRect(bounds.x * CELL, bounds.y * CELL, bounds.w * CELL, bounds.h * CELL);
            c2d.strokeStyle = 'rgba(227,179,65,0.5)';
            c2d.lineWidth = 1 / scale;
            c2d.setLineDash([5 / scale, 4 / scale]);
            c2d.strokeRect(bounds.x * CELL, bounds.y * CELL, bounds.w * CELL, bounds.h * CELL);
            c2d.setLineDash([]);
        }
        c2d.fillStyle = '#e3b341';
        c2d.beginPath();
        c2d.arc(0, 0, 4 / scale, 0, Math.PI * 2);
        c2d.fill();
        c2d.font = `${11 / scale}px sans-serif`;
        c2d.fillText(preview
            ? `0,0 · snaps to ${ext.w}×${ext.h} (1 cell ≈ ${Math.round(preview.pxPerCell)}px)`
            : `0,0 · ${ext.w}×${ext.h}`, 6 / scale, -5 / scale);
        if (CELL * scale >= 4) {
            c2d.save();
            c2d.beginPath();
            c2d.rect(0, 0, w, h);
            c2d.clip();
            const hasRef = Boolean(p.reference && p.reference.image && p.reference.visible);
            c2d.strokeStyle = preview
                ? 'rgba(255,230,140,0.60)'
                : (hasRef ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.09)');
            c2d.lineWidth = (preview ? 1.25 : 1) / scale;
            c2d.beginPath();
            for (let x = 0; x <= maxCols; x += 1) {
                c2d.moveTo(x * CELL, 0);
                c2d.lineTo(x * CELL, h);
            }
            for (let y = 0; y <= maxRows; y += 1) {
                c2d.moveTo(0, y * CELL);
                c2d.lineTo(w, y * CELL);
            }
            c2d.stroke();
            c2d.restore();
        }
        if (preview) {
            c2d.fillStyle = 'rgba(247,119,119,0.30)';
            c2d.strokeStyle = '#f77';
            c2d.lineWidth = 1 / scale;
            ctx.GM().strandedCells(p, preview.w, preview.h).forEach((c: any) => {
                c2d.fillRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
                c2d.strokeRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
            });
        }
        c2d.restore();
    }

    function _drawPaint(ctx: any, c2d: CanvasRenderingContext2D, p: any): void {
        if (!p.grid) return;
        const CELL = ctx.CELL || 22;
        if (typeof document !== 'undefined' && typeof document.createElement === 'function') {
            ctx.ensurePaintCache(p);
            if (ctx.state.paintCache) {
                c2d.save();
                c2d.globalAlpha = ctx.state.paintAlpha == null ? 1 : ctx.state.paintAlpha;
                c2d.imageSmoothingEnabled = false;
                c2d.drawImage(ctx.state.paintCache, 0, 0, p.grid.w, p.grid.h, 0, 0, p.grid.w * CELL, p.grid.h * CELL);
                c2d.restore();
                return;
            }
        }
        c2d.save();
        c2d.globalAlpha = ctx.state.paintAlpha == null ? 1 : ctx.state.paintAlpha;
        const layers = p.layers || {};
        Object.keys(layers).forEach((layer) => {
            const cells = layers[layer] || {};
            Object.keys(cells).forEach((key) => {
                const pos = ctx.GM().parseCellKey(key);
                if (!pos) return;
                const color = ctx.GM().layerColor(layer, cells[key]);
                if (!color) return;
                c2d.fillStyle = color;
                c2d.fillRect(pos.x * CELL, pos.y * CELL, CELL, CELL);
            });
        });
        c2d.restore();
    }

    function _ellipsize(text: unknown, max: number): string {
        const s = String(text == null ? '' : text);
        return s.length > max ? `${s.slice(0, max - 1)}…` : s;
    }

    function _drawFeatures(ctx: any, c2d: CanvasRenderingContext2D, p: any): void {
        const CELL = ctx.CELL || 22;
        c2d.save();
        c2d.globalAlpha = ctx.state.paintAlpha == null ? 1 : ctx.state.paintAlpha;
        const scale = ctx.state.stage ? ctx.state.stage.scaleX() : 1;
        c2d.font = `${Math.max(9, CELL - 8)}px sans-serif`;
        c2d.textAlign = 'center';
        c2d.textBaseline = 'middle';
        (p.placements || []).forEach((pl: any) => {
            const selected = pl.id === ctx.state.selectedChild;
            c2d.fillStyle = selected ? '#f5c542' : 'rgba(123,90,166,0.82)';
            c2d.fillRect(pl.x * CELL + 4, pl.y * CELL + 4, CELL - 8, CELL - 8);
            c2d.strokeStyle = selected ? '#fff' : '#d8c4f0';
            c2d.lineWidth = 1 / scale;
            c2d.strokeRect(pl.x * CELL + 4, pl.y * CELL + 4, CELL - 8, CELL - 8);
            c2d.fillStyle = '#fff';
            c2d.font = `${Math.max(8, CELL - 10)}px sans-serif`;
            c2d.fillText('🏠', pl.x * CELL + CELL / 2, pl.y * CELL + CELL / 2 - (CELL * scale >= 20 && pl.name ? 2 : 0));
            if (CELL * scale >= 20 && pl.name) {
                const label = _ellipsize(pl.name, 14);
                c2d.font = `${Math.max(3, Math.min(9, 10 / scale))}px sans-serif`;
                c2d.strokeStyle = 'rgba(13,17,23,0.9)';
                c2d.lineWidth = 2.5 / scale;
                c2d.strokeText(label, pl.x * CELL + CELL / 2, pl.y * CELL + CELL - 3);
                c2d.fillStyle = selected ? '#fff6cc' : '#f0e6ff';
                c2d.fillText(label, pl.x * CELL + CELL / 2, pl.y * CELL + CELL - 3);
            }
        });
        (p.area_placements || []).forEach((a: any) => {
            const selected = a.id === ctx.state.selectedArea;
            c2d.fillStyle = selected ? '#f5c542' : '#2f7d5a';
            c2d.fillRect(a.x * CELL + 2, a.y * CELL + 2, CELL - 4, CELL - 4);
            c2d.strokeStyle = '#d9f2e5';
            c2d.lineWidth = 1;
            c2d.strokeRect(a.x * CELL + 2.5, a.y * CELL + 2.5, CELL - 5, CELL - 5);
            if (CELL * scale >= 20 && a.name) {
                const label = _ellipsize(a.name, 12);
                c2d.font = '9px sans-serif';
                c2d.strokeStyle = 'rgba(13,17,23,0.9)';
                c2d.lineWidth = 2.5 / scale;
                c2d.strokeText(label, a.x * CELL + CELL / 2, a.y * CELL + CELL + 8);
                c2d.fillStyle = '#d9f2e5';
                c2d.fillText(label, a.x * CELL + CELL / 2, a.y * CELL + CELL + 8);
            }
        });
        c2d.restore();
    }

    function _drawVisionDecor(ctx: any, c2d: CanvasRenderingContext2D): void {
        if (ctx.state.tool !== 'vision' && !ctx.state.visionLens) return;
        const CELL = ctx.CELL || 22;

        if (ctx.state.visionVisibleSet && (ctx.state.visionLens || ctx.state.tool === 'vision')) {
            c2d.save();
            c2d.fillStyle = 'rgba(45, 85, 132, 0.28)';
            ctx.state.visionVisibleSet.forEach((key: string) => {
                const c = ctx.GM().parseCellKey(key);
                if (c) {
                    c2d.fillRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
                }
            });
            c2d.restore();
        }

        if (ctx.state.visionOrigin) {
            const ox = ctx.state.visionOrigin.x * CELL + CELL / 2;
            const oy = ctx.state.visionOrigin.y * CELL + CELL / 2;
            c2d.save();
            c2d.beginPath();
            c2d.arc(ox, oy, CELL * 0.45, 0, Math.PI * 2);
            c2d.fillStyle = 'rgba(45, 85, 132, 0.7)';
            c2d.fill();
            c2d.lineWidth = 2;
            c2d.strokeStyle = '#58a6ff';
            c2d.stroke();

            c2d.beginPath();
            c2d.arc(ox, oy, CELL * 0.18, 0, Math.PI * 2);
            c2d.fillStyle = '#ffffff';
            c2d.fill();

            if (ctx.state.visionFacing) {
                const compassAngles: Record<string, number> = {
                    e: 0, se: 45, s: 90, sw: 135,
                    w: 180, nw: 225, n: 270, ne: 315
                };
                const f = ctx.state.visionFacing.toLowerCase();
                if (compassAngles[f] != null) {
                    const centerRad = (compassAngles[f] * Math.PI) / 180;
                    const halfRad = (60 * Math.PI) / 180;
                    c2d.beginPath();
                    c2d.moveTo(ox, oy);
                    c2d.arc(ox, oy, CELL * 2.5, centerRad - halfRad, centerRad + halfRad);
                    c2d.closePath();
                    c2d.fillStyle = 'rgba(88, 166, 255, 0.18)';
                    c2d.fill();
                    c2d.strokeStyle = '#58a6ff';
                    c2d.lineWidth = 1;
                    c2d.stroke();
                }
            }
            c2d.restore();
        }

        if (ctx.state.visionOrigin && ctx.state.visionTarget && ctx.state.visionRay) {
            const ox = ctx.state.visionOrigin.x * CELL + CELL / 2;
            const oy = ctx.state.visionOrigin.y * CELL + CELL / 2;
            const tx = ctx.state.visionTarget.x * CELL + CELL / 2;
            const ty = ctx.state.visionTarget.y * CELL + CELL / 2;

            c2d.save();
            const steps = ctx.state.visionRay.steps || [];
            steps.forEach((s: any) => {
                c2d.fillStyle = s.blocked ? 'rgba(248, 81, 73, 0.35)' : 'rgba(63, 185, 80, 0.2)';
                c2d.fillRect(s.x * CELL + 1, s.y * CELL + 1, CELL - 2, CELL - 2);
                if (s.blocked) {
                    c2d.strokeStyle = '#f85149';
                    c2d.lineWidth = 1.5;
                    c2d.strokeRect(s.x * CELL + 1, s.y * CELL + 1, CELL - 2, CELL - 2);
                }
            });

            c2d.beginPath();
            c2d.moveTo(ox, oy);
            c2d.lineTo(tx, ty);
            c2d.lineWidth = 2.5;
            c2d.strokeStyle = ctx.state.visionRay.visible ? '#3fb950' : '#f85149';
            c2d.stroke();

            c2d.beginPath();
            c2d.arc(tx, ty, 4, 0, Math.PI * 2);
            c2d.fillStyle = ctx.state.visionRay.visible ? '#3fb950' : '#f85149';
            c2d.fill();

            c2d.restore();
        }
    }

    function _drawRoute(ctx: any, c2d: CanvasRenderingContext2D): void {
        const CELL = ctx.CELL || 22;
        if (ctx.state.stroke && ctx.state.stroke.length) {
            c2d.save();
            c2d.globalAlpha = ctx.state.paintAlpha == null ? 1 : ctx.state.paintAlpha;
            c2d.fillStyle = ctx.state.strokeValue == null
                ? '#8a8a8a'
                : (ctx.GM().layerColor(ctx.state.strokeLayer, ctx.state.strokeValue) || '#cccccc');
            ctx.state.stroke.forEach((c: any) => {
                c2d.fillRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
            });
            c2d.restore();
        }
        const hover = ctx.state.brushHover;
        if (hover && hover.length && ctx.state.payload) {
            c2d.save();
            c2d.strokeStyle = 'rgba(255,255,255,0.55)';
            c2d.lineWidth = Math.max(1, 1.5 / ((ctx.state.stage && ctx.state.stage.scaleX()) || 1));
            c2d.setLineDash([4 / ((ctx.state.stage && ctx.state.stage.scaleX()) || 1), 3 / ((ctx.state.stage && ctx.state.stage.scaleX()) || 1)]);
            hover.forEach((c: any) => {
                c2d.strokeRect(c.x * CELL + 0.5, c.y * CELL + 0.5, CELL - 1, CELL - 1);
            });
            c2d.setLineDash([]);
            c2d.restore();
        }
        _drawVisionDecor(ctx, c2d);
        const pts = ctx.state.route || [];
        if (!pts.length) return;
        c2d.save();
        c2d.strokeStyle = '#7ab';
        c2d.lineWidth = Math.max(1.5, CELL / 6);
        c2d.setLineDash([6, 4]);
        if (pts.length > 1) {
            c2d.beginPath();
            pts.forEach((pt: any, i: number) => {
                const cx = pt.x * CELL + CELL / 2;
                const cy = pt.y * CELL + CELL / 2;
                if (i === 0) c2d.moveTo(cx, cy); else c2d.lineTo(cx, cy);
            });
            c2d.stroke();
        }
        c2d.setLineDash([]);
        c2d.fillStyle = '#f5c542';
        pts.forEach((pt: any) => {
            c2d.beginPath();
            c2d.arc(pt.x * CELL + CELL / 2, pt.y * CELL + CELL / 2, 3, 0, Math.PI * 2);
            c2d.fill();
        });
        c2d.restore();
    }

    function _strokeAdd(ctx: any, p: any, cell: any): boolean {
        if (!cell) return false;
        const keys = ctx.state.strokeKeys || (ctx.state.strokeKeys = {});
        let added = false;
        ctx.brushCells(p, cell.x, cell.y).forEach((b: any) => {
            const k = ctx.GM().cellKey(b.x, b.y);
            if (!keys[k]) { keys[k] = true; ctx.state.stroke.push(b); added = true; }
        });
        return added;
    }

    function _sel(ctx: any, p: any): Record<string, boolean> {
        const id = (p && p.scope && p.scope.id) || ctx.state.scopeId || '';
        if (!ctx.state.selection[id]) ctx.state.selection[id] = {};
        return ctx.state.selection[id];
    }

    function _selectedCells(ctx: any, p: any): any[] {
        return Object.keys(_sel(ctx, p)).map((k) => ctx.GM().parseCellKey(k))
            .filter(Boolean)
            .map((c: any) => ({ x: c.x, y: c.y }));
    }

    function _setSelection(ctx: any, p: any, keys: Record<string, boolean>): void {
        _sel(ctx, p);
        ctx.state.selection[(p && p.scope && p.scope.id) || ctx.state.scopeId || ''] = keys;
    }

    function _marqueeCells(ctx: any, p: any, to: any): Record<string, boolean> {
        const a = (ctx.state.marquee && ctx.state.marquee.anchor) || to;
        const x0 = Math.max(0, Math.min(a.x, to.x));
        const x1 = Math.min(p.grid!.w - 1, Math.max(a.x, to.x));
        const y0 = Math.max(0, Math.min(a.y, to.y));
        const y1 = Math.min(p.grid!.h - 1, Math.max(a.y, to.y));
        const out: Record<string, boolean> = {};
        for (let y = y0; y <= y1; y += 1) {
            for (let x = x0; x <= x1; x += 1) out[ctx.GM().cellKey(x, y)] = true;
        }
        return out;
    }

    function _commitMarquee(ctx: any, p: any): void {
        const m = ctx.state.marquee;
        if (!m) return;
        ctx.state.marquee = null;
        const covered = _marqueeCells(ctx, p, m.to);
        if (m.add) {
            const next = Object.assign({}, _sel(ctx, p));
            Object.keys(covered).forEach((k) => { next[k] = true; });
            _setSelection(ctx, p, next);
        } else {
            _setSelection(ctx, p, covered);
        }
        const count = _selectedCells(ctx, p).length;
        ctx.status(count ? `Selected ${count} cell(s).` : 'Selection cleared.');
        ctx.redrawDecor();
    }

    function _bindKeys(ctx: any): void {
        _unbindKeys(ctx);
        const onKeyDown = (e: KeyboardEvent) => {
            if (e.target && /input|textarea|select/i.test((e.target as HTMLElement).tagName)) return;
            if (e.key === ' ' || e.code === 'Space') {
                if (!ctx.state.spaceDown) {
                    ctx.state.spaceDown = true;
                    ctx.syncDraggable?.();
                }
                e.preventDefault();
                return;
            }
            if (e.key === 'Escape') {
                if (ctx.state.marquee) {
                    ctx.state.marquee = null;
                    ctx.redrawDecor();
                    return;
                }
                if (ctx.state.route && ctx.state.route.length) {
                    ctx.state.route = [];
                    ctx.redrawDecor();
                    ctx.render();
                    return;
                }
            }
            if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
                if (e.shiftKey) (window as any).UndoHistory?.redo?.();
                else (window as any).UndoHistory?.undo?.();
                e.preventDefault();
                return;
            }
        };
        const onKeyUp = (e: KeyboardEvent) => {
            if (e.key === ' ' || e.code === 'Space') {
                ctx.state.spaceDown = false;
                ctx.syncDraggable?.();
                e.preventDefault();
            }
        };
        ctx.state._keyDown = onKeyDown;
        ctx.state._keyUp = onKeyUp;
        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup', onKeyUp);
    }

    function _unbindKeys(ctx: any): void {
        if (ctx.state._keyDown) window.removeEventListener('keydown', ctx.state._keyDown);
        if (ctx.state._keyUp) window.removeEventListener('keyup', ctx.state._keyUp);
        ctx.state._keyDown = null;
        ctx.state._keyUp = null;
    }

    function _invalidatePaintCache(ctx: any, cells?: Array<{ x: number; y: number }>): void {
        if (cells && ctx.patchPaintCache) {
            ctx.patchPaintCache(ctx.state.payload, cells);
        } else {
            ctx.state.paintCacheValid = false;
        }
    }

    async function _commitStroke(ctx: any, p: WpPayload): Promise<void> {
        const edits = (ctx.state.stroke || []).map((c: any) => ({
            layer: ctx.state.strokeLayer,
            x: c.x,
            y: c.y,
            value: ctx.state.strokeValue,
        }));
        ctx.state.stroke = [];
        ctx.state.strokeKeys = {};
        ctx.state.stroking = false;
        if (!edits.length) return;
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, { edits });
            _invalidatePaintCache(ctx, edits);
            ctx.notify(true);
            ctx.softRender();
        } catch (e) {
            ctx.status(`Stroke failed: ${ctx.errText(e)}`, true);
        }
    }

    async function _nudge(ctx: any, p: WpPayload, dx: number, dy: number): Promise<void> {
        const sel = _selectedCells(ctx, p);
        if (!sel.length) return;
        const edits: any[] = [];
        const nextSel: Record<string, boolean> = {};
        const layers = p.layers || {};
        sel.forEach((c) => {
            const nx = c.x + dx;
            const ny = c.y + dy;
            if (nx >= 0 && ny >= 0 && nx < p.grid!.w && ny < p.grid!.h) {
                nextSel[ctx.GM().cellKey(nx, ny)] = true;
                ctx.GM().PAINT_LAYERS.forEach((layer: string) => {
                    const val = layers[layer] && layers[layer][ctx.GM().cellKey(c.x, c.y)];
                    if (val !== undefined) edits.push({ layer, x: nx, y: ny, value: val });
                });
            }
            ctx.GM().PAINT_LAYERS.forEach((layer: string) => {
                edits.push({ layer, x: c.x, y: c.y, value: null });
            });
        });
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, { edits });
            _invalidatePaintCache(ctx, edits);
            _setSelection(ctx, ctx.state.payload, nextSel);
            ctx.notify(true);
            ctx.softRender();
        } catch (e) {
            ctx.status(`Move failed: ${ctx.errText(e)}`, true);
        }
    }

    async function _applyToSelection(ctx: any, p: WpPayload): Promise<boolean> {
        const sel = _selectedCells(ctx, p);
        if (!sel.length) return false;
        const val = ctx.state.tool === 'erase' ? null : ctx.state.value;
        const edits = sel.map((c) => ({ layer: ctx.state.layer, x: c.x, y: c.y, value: val }));
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, { edits });
            _invalidatePaintCache(ctx, edits);
            ctx.notify(true);
            ctx.softRender();
            ctx.status(`Applied to ${sel.length} cell(s).`);
            return true;
        } catch (e) {
            ctx.status(`Batch paint failed: ${ctx.errText(e)}`, true);
            return false;
        }
    }

    async function onCellClick(ctx: any, p: WpPayload, x: number, y: number): Promise<void> {
        if (ctx.state.tool === 'inspect') {
            ctx.inspectCell(p, x, y);
            return;
        }
        if (ctx.state.tool === 'select') {
            const k = ctx.GM().cellKey(x, y);
            const next = Object.assign({}, _sel(ctx, p));
            if (next[k]) delete next[k];
            else next[k] = true;
            _setSelection(ctx, p, next);
            ctx.redrawDecor();
            return;
        }
        if (ctx.state.tool === 'route') {
            const rt = (ctx.state.route || []).slice();
            const last = rt.length ? rt[rt.length - 1] : null;
            if (last && last.x === x && last.y === y) {
                rt.pop();
            } else {
                rt.push({ x, y });
            }
            ctx.state.route = rt;
            ctx.redrawDecor();
            return;
        }
        if (ctx.state.tool === 'feature') {
            if (ctx.state.selectedChild) {
                await placeFeature(ctx, ctx.state.selectedChild, x, y);
            }
            return;
        }
        if (ctx.state.tool === 'area') {
            await onAreaCellClick(ctx, p, x, y);
            return;
        }
        if (!p.scope.has_grid) return;
        return paintAt(ctx, p, x, y);
    }

    async function onAreaCellClick(ctx: any, p: WpPayload, x: number, y: number): Promise<void> {
        if (!p.scope.has_grid) { ctx.status('This scope has no grid to place on.', true); return; }
        const here = ctx.GM().areaAt(p, x, y);
        if (here) {
            const ok = await (window as any).Dialog?.confirm?.({
                title: 'Unplace Area',
                message: `Take "${here.name}" off this map? The area itself stays.`
            });
            if (!ok) return;
            await unplaceArea(ctx, here.id);
            return;
        }
        if (!ctx.state.selectedArea) {
            ctx.status('Pick an area from the Area dropdown first.');
            return;
        }
        await placeArea(ctx, ctx.state.selectedArea, x, y);
    }

    async function placeArea(ctx: any, areaId: string, x: number, y: number, onOverlap?: string): Promise<void> {
        const p = ctx.state.payload!;
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/place_area`,
                { area_id: areaId, x, y, on_overlap: onOverlap || 'forbid' });
            ctx.status(`Placed on cell (${x},${y}).`);
            ctx.notify(true);
            ctx.render();
        } catch (e) {
            const msg = ctx.errText(e);
            if (/already holds/.test(msg)) {
                const ok = await (window as any).Dialog?.confirm?.({
                    title: 'Displace Occupant',
                    message: `${msg}\n\nDisplace it?`,
                    danger: true
                });
                if (ok) {
                    await placeArea(ctx, areaId, x, y, 'displace');
                    return;
                }
            }
            ctx.status(`Place failed: ${msg}`, true);
        }
    }

    async function unplaceArea(ctx: any, areaId: string): Promise<void> {
        const p = ctx.state.payload!;
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/unplace_area`,
                { area_id: areaId });
            if (ctx.state.selectedArea === areaId) ctx.state.selectedArea = null;
            ctx.status('Taken off the map (the area itself is untouched).');
            ctx.notify(true);
            ctx.render();
        } catch (e) {
            ctx.status(`Unplace failed: ${ctx.errText(e)}`, true);
        }
    }

    async function paintAt(ctx: any, p: WpPayload, x: number, y: number): Promise<void> {
        const value = ctx.state.tool === 'erase' ? null : ctx.state.value;
        if (ctx.state.tool === 'paint' && (value == null || value === '')) {
            ctx.status('Pick a paint value, or use Erase.');
            return;
        }
        const cells = ctx.brushCells(p, x, y);
        try {
            if (cells.length === 1) {
                ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/paint`,
                    { layer: ctx.state.layer, x, y, value });
            } else {
                ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                    { edits: cells.map((c: any) => ({ layer: ctx.state.layer, x: c.x, y: c.y, value })) });
            }
            _invalidatePaintCache(ctx, cells);
            ctx.notify(true);
            ctx.render();
        } catch (e) {
            ctx.status(`Paint failed: ${ctx.errText(e)}`, true);
        }
    }

    async function placeFeature(ctx: any, childId: string, x: number, y: number, onOverlap?: string): Promise<void> {
        const p = ctx.state.payload!;
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/place`,
                { child_id: childId, x, y, on_overlap: onOverlap || 'forbid' });
            ctx.notify(true);
            ctx.render();
        } catch (e) {
            if (!onOverlap && /already holds/.test(ctx.errText(e))) {
                const ok = await (window as any).Dialog?.confirm?.({
                    title: 'Displace Feature',
                    message: `${ctx.errText(e)}\n\nDisplace the occupant?`,
                    danger: true
                });
                if (ok) return placeFeature(ctx, childId, x, y, 'displace');
            }
            ctx.status(`Place failed: ${ctx.errText(e)}`, true);
        }
    }

    async function removeFeature(ctx: any, childId: string): Promise<void> {
        try {
            ctx.state.payload = await ctx.post(
                `/${encodeURIComponent(ctx.state.payload!.scope.id)}/grid/remove`,
                { child_id: childId });
            ctx.state.selectedChild = null;
            ctx.notify(true);
            ctx.render();
        } catch (e) {
            ctx.status(`Remove failed: ${ctx.errText(e)}`, true);
        }
    }

    async function applyRoute(ctx: any): Promise<void> {
        const p = ctx.state.payload;
        if (!p || !p.grid) return;
        const pts = ctx.state.route || [];
        if (pts.length < 2) {
            ctx.status('Click at least two waypoints before applying.');
            return;
        }
        const cells = ctx.GM().routeCells(pts);
        const edits = cells.map((c: any) => ({ layer: 'road', x: c.x, y: c.y, value: ctx.state.value || 'road' }));
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, { edits });
            _invalidatePaintCache(ctx, cells);
            ctx.state.route = [];
            ctx.notify(true);
            ctx.render();
            ctx.status(`Route applied (${cells.length} cells).`);
        } catch (e) {
            ctx.status(`Route failed: ${ctx.errText(e)}`, true);
        }
    }

    const WorldPainterCanvas = {
        bindKeys: _bindKeys,
        unbindKeys: _unbindKeys,
        commitStroke: _commitStroke,
        nudge: _nudge,
        applyToSelection: _applyToSelection,
        onCellClick,
        onAreaCellClick,
        placeArea,
        unplaceArea,
        paintAt,
        placeFeature,
        removeFeature,
        applyRoute,
        drawGridLines: _drawGridLines,
        drawPaint: _drawPaint,
        drawFeatures: _drawFeatures,
        ellipsize: _ellipsize,
        drawVisionDecor: _drawVisionDecor,
        drawRoute: _drawRoute,
        strokeAdd: _strokeAdd,
        sel: _sel,
        selectedCells: _selectedCells,
        setSelection: _setSelection,
        marqueeCells: _marqueeCells,
        commitMarquee: _commitMarquee,
    };

    (window as any).WorldPainterCanvas = WorldPainterCanvas;
    window.VW = window.VW || {};
    (window.VW as any).worldPainterCanvas = WorldPainterCanvas;
})();