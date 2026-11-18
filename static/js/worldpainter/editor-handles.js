"use strict";
/**
 * @module worldpainter/editor-handles - WorldPainter interactive canvas resize and drag handles
 * @contributes interactive frame boundary, corner resize, and reference image handles
 * @powers WorldPainter canvas interaction and grid framing (task-880)
 * @relates static/js/worldpainter/editor.js; static/js/worldpainter/grid-model.js
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(function () {
    'use strict';
    function _scaleRefRect(rect, oldGrid, newGrid) {
        const sx = (oldGrid.w > 0 && newGrid.w > 0) ? (newGrid.w / oldGrid.w) : 1;
        const sy = (oldGrid.h > 0 && newGrid.h > 0) ? (newGrid.h / oldGrid.h) : 1;
        return {
            x: rect.x * sx,
            y: rect.y * sy,
            w: rect.w * sx,
            h: rect.h * sy,
        };
    }
    function _anchorStageToRefScreen(ctx, beforeScreen, afterCells) {
        const stage = ctx.state.stage;
        const CELL = ctx.CELL || 22;
        const MAX_SCALE = ctx.MAX_SCALE || 20;
        if (!stage || !beforeScreen || beforeScreen.w <= 0 || beforeScreen.h <= 0
            || afterCells.w <= 0 || afterCells.h <= 0)
            return;
        const scaleW = beforeScreen.w / (afterCells.w * CELL);
        const scaleH = beforeScreen.h / (afterCells.h * CELL);
        const nextScale = Math.max(0.05, Math.min(MAX_SCALE, Math.max(scaleW, scaleH)));
        const cx = beforeScreen.x + beforeScreen.w / 2;
        const cy = beforeScreen.y + beforeScreen.h / 2;
        const nextX = cx - (afterCells.x + afterCells.w / 2) * CELL * nextScale;
        const nextY = cy - (afterCells.y + afterCells.h / 2) * CELL * nextScale;
        stage.scale({ x: nextScale, y: nextScale });
        stage.position({ x: nextX, y: nextY });
        if (ctx.captureView)
            ctx.captureView();
        if (ctx.syncZoomButtons)
            ctx.syncZoomButtons();
    }
    function _refScreenBox(ctx, p, extOverride) {
        const stage = ctx.state.stage;
        const CELL = ctx.CELL || 22;
        if (!stage)
            return null;
        const rect = ctx.refRectCells(p, ctx.state.refImage, extOverride);
        const scale = stage.scaleX() || 1;
        return {
            x: stage.x() + rect.x * CELL * scale,
            y: stage.y() + rect.y * CELL * scale,
            w: rect.w * CELL * scale,
            h: rect.h * CELL * scale,
        };
    }
    function _refHandlePoints(ctx, rect) {
        return ctx.GM().referenceHandlePoints(rect);
    }
    function _drawRefHandles(ctx, c2d, p) {
        if (!ctx.state.refEdit || !ctx.state.refImage || !(p.reference && p.reference.image))
            return;
        const CELL = ctx.CELL || 22;
        const rect = ctx.refRectCells(p, ctx.state.refImage);
        const scale = (ctx.state.stage && ctx.state.stage.scaleX()) || 1;
        c2d.save();
        c2d.strokeStyle = '#58a6ff';
        c2d.lineWidth = 1.5 / scale;
        c2d.setLineDash([6 / scale, 4 / scale]);
        c2d.strokeRect(rect.x * CELL, rect.y * CELL, rect.w * CELL, rect.h * CELL);
        c2d.setLineDash([]);
        const pts = _refHandlePoints(ctx, rect);
        Object.keys(pts).forEach((key) => {
            c2d.beginPath();
            c2d.arc(pts[key].x * CELL, pts[key].y * CELL, 5 / scale, 0, Math.PI * 2);
            c2d.fillStyle = key.length === 2 ? '#58a6ff' : '#e3b341';
            c2d.fill();
        });
        c2d.restore();
    }
    function _refHit(ctx, p, pos) {
        const CELL = ctx.CELL || 22;
        const rect = ctx.refRectCells(p, ctx.state.refImage);
        const scale = (ctx.state.stage && ctx.state.stage.scaleX()) || 1;
        const tol = 9 / scale;
        const pts = _refHandlePoints(ctx, rect);
        for (const key of Object.keys(pts)) {
            if (Math.abs(pos.x - pts[key].x * CELL) <= tol
                && Math.abs(pos.y - pts[key].y * CELL) <= tol) {
                return { kind: key.length === 2 ? 'resize' : 'crop', key };
            }
        }
        const x = rect.x * CELL, y = rect.y * CELL, w = rect.w * CELL, h = rect.h * CELL;
        if (pos.x >= x && pos.x <= x + w && pos.y >= y && pos.y <= y + h) {
            return { kind: 'move', key: null };
        }
        return null;
    }
    function _refMouseDown(ctx, p) {
        if (!ctx.state.refImage || !(p.reference && p.reference.image))
            return;
        const CELL = ctx.CELL || 22;
        const pos = ctx.state.stage.getRelativePointerPosition();
        if (!pos)
            return;
        const target = _refHit(ctx, p, pos);
        if (!target)
            return;
        const initialRect = ctx.refRectCells(p, ctx.state.refImage);
        const initialCrop = Object.assign({ x: 0, y: 0, w: 1, h: 1 }, (p.reference || {}).crop || {});
        ctx.state.refDrag = {
            kind: target.kind,
            key: target.key,
            start: { x: pos.x / CELL, y: pos.y / CELL },
            originRect: initialRect,
            originCrop: initialCrop,
            rect: initialRect,
            crop: initialCrop,
        };
    }
    function _refMouseMove(ctx, p) {
        const drag = ctx.state.refDrag;
        if (!drag)
            return;
        const CELL = ctx.CELL || 22;
        const pos = ctx.state.stage.getRelativePointerPosition();
        if (!pos)
            return;
        const cx = pos.x / CELL;
        const cy = pos.y / CELL;
        let r = Object.assign({}, drag.originRect);
        let crop = Object.assign({}, drag.originCrop);
        if (drag.kind === 'move') {
            r.x = drag.originRect.x + (cx - drag.start.x);
            r.y = drag.originRect.y + (cy - drag.start.y);
        }
        else {
            const next = ctx.GM().referenceHandleDrag(drag.originRect, drag.originCrop, drag.key, cx, cy);
            r = next.rect;
            crop = next.crop;
        }
        drag.rect = r;
        drag.crop = crop;
        p.reference = Object.assign({}, p.reference, { rect: r, crop });
        ctx.applyRefTransform(p);
        ctx.redrawGrid();
    }
    function _refMouseUp(ctx) {
        const drag = ctx.state.refDrag;
        if (!drag)
            return;
        ctx.state.refDrag = null;
        const p = ctx.state.payload;
        if (!p || !(p.reference && p.reference.image))
            return;
        ctx.updateReference({ rect: drag.rect, crop: drag.crop });
    }
    function _gridExtent(ctx, p) {
        const drag = ctx.state.gridDrag;
        if (drag && drag.kind === 'resize' && drag.w && drag.h) {
            return { w: drag.w, h: drag.h };
        }
        const preview = ctx.state.cellSizePreview;
        if (preview)
            return { w: preview.w, h: preview.h };
        return { w: p.grid.w, h: p.grid.h };
    }
    function _cellCornerHandlePoint(ctx, p) {
        if (!ctx.state.refImage || !ctx.state.refImage.naturalWidth || !(p.reference && p.reference.image)) {
            return null;
        }
        const rect = ctx.refRectCells(p, ctx.state.refImage);
        return { x: rect.x + 1, y: rect.y + 1 };
    }
    function _drawAnchorBadge(c2d, CELL, scale, anchor) {
        if (!anchor || typeof anchor.x !== 'number' || typeof anchor.y !== 'number')
            return;
        const cx = (anchor.x + 0.5) * CELL;
        const cy = (anchor.y + 0.5) * CELL;
        const r = Math.max(CELL * 0.42, 7 / scale);
        c2d.save();
        c2d.strokeStyle = '#ff9f43';
        c2d.fillStyle = 'rgba(255, 159, 67, 0.22)';
        c2d.lineWidth = 2 / scale;
        c2d.beginPath();
        c2d.arc(cx, cy, r, 0, Math.PI * 2);
        c2d.fill();
        c2d.stroke();
        c2d.beginPath();
        c2d.moveTo(cx - r * 1.35, cy);
        c2d.lineTo(cx + r * 1.35, cy);
        c2d.moveTo(cx, cy - r * 1.35);
        c2d.lineTo(cx, cy + r * 1.35);
        c2d.stroke();
        c2d.fillStyle = '#ff9f43';
        c2d.font = `bold ${10 / scale}px sans-serif`;
        c2d.fillText(`ANCHOR (${anchor.x},${anchor.y})`, cx + r + 3 / scale, cy - 3 / scale);
        c2d.restore();
    }
    function _drawGhostGrid(c2d, CELL, scale, rx, ry, w, h, ghostPayload) {
        const gw = Math.max(1, w) * CELL;
        const gh = Math.max(1, h) * CELL;
        c2d.save();
        c2d.fillStyle = 'rgba(88, 166, 255, 0.08)';
        c2d.fillRect(rx, ry, gw, gh);
        c2d.strokeStyle = 'rgba(88, 166, 255, 0.55)';
        c2d.lineWidth = 1.5 / scale;
        c2d.setLineDash([5 / scale, 4 / scale]);
        c2d.strokeRect(rx, ry, gw, gh);
        c2d.setLineDash([]);
        // Draw subtle internal ghost grid lines (cap density for huge grids).
        const step = Math.max(1, Math.ceil(Math.max(w, h) / 60));
        c2d.strokeStyle = 'rgba(88, 166, 255, 0.20)';
        c2d.lineWidth = 0.75 / scale;
        c2d.beginPath();
        for (let x = step; x < w; x += step) {
            c2d.moveTo(rx + x * CELL, ry);
            c2d.lineTo(rx + x * CELL, ry + gh);
        }
        for (let y = step; y < h; y += step) {
            c2d.moveTo(rx, ry + y * CELL);
            c2d.lineTo(rx + gw, ry + y * CELL);
        }
        c2d.stroke();
        // Draw projected placed areas and features in the ghost preview.
        if (ghostPayload) {
            c2d.fillStyle = 'rgba(63, 185, 80, 0.35)';
            c2d.strokeStyle = 'rgba(63, 185, 80, 0.85)';
            c2d.lineWidth = 1.25 / scale;
            const drawMark = (item) => {
                if (!item || typeof item.x !== 'number' || typeof item.y !== 'number')
                    return;
                const px = rx + item.x * CELL;
                const py = ry + item.y * CELL;
                c2d.fillRect(px + 1, py + 1, CELL - 2, CELL - 2);
                c2d.strokeRect(px + 1, py + 1, CELL - 2, CELL - 2);
            };
            (ghostPayload.area_placements || []).forEach(drawMark);
            (ghostPayload.placements || []).forEach(drawMark);
        }
        c2d.restore();
    }
    function _drawGridHandles(ctx, c2d, p) {
        const preview = ctx.state.gridPreview;
        if (!ctx.state.gridEdit && !preview)
            return;
        const CELL = ctx.CELL || 22;
        const scale = (ctx.state.stage && ctx.state.stage.scaleX()) || 1;
        const drag = ctx.state.gridDrag;
        const ext = _gridExtent(ctx, p);
        const offX = (drag && drag.kind === 'resize' && drag.offsetX) ? drag.offsetX : 0;
        const offY = (drag && drag.kind === 'resize' && drag.offsetY) ? drag.offsetY : 0;
        const frameX = -offX * CELL;
        const frameY = -offY * CELL;
        c2d.save();
        if (drag && drag.kind === 'resize') {
            const ghost = ctx.GM().expandGridMargins(p, {
                west: offX,
                north: offY,
                east: drag.w - p.grid.w - offX,
                south: drag.h - p.grid.h - offY,
            });
            _drawGhostGrid(c2d, CELL, scale, frameX, frameY, drag.w, drag.h, ghost);
        }
        else if (drag && drag.kind === 'cell-size' && ctx.state.cellSizePreview) {
            const anchor = ctx.state.gridAnchor || { x: 0, y: 0 };
            const s = ctx.state.cellSizePreview.w / Math.max(1, p.grid.w);
            const ghost = ctx.GM().scaleGridWithAnchor(p, anchor, s, ctx.state.cellSizePreview);
            _drawGhostGrid(c2d, CELL, scale, 0, 0, ctx.state.cellSizePreview.w, ctx.state.cellSizePreview.h, ghost);
        }
        else if (preview) {
            const pOffX = preview.offsetX || 0;
            const pOffY = preview.offsetY || 0;
            let ghost = null;
            if (preview.anchor && preview.scaleFactor) {
                ghost = ctx.GM().scaleGridWithAnchor(p, preview.anchor, preview.scaleFactor, { w: preview.w, h: preview.h });
            }
            else {
                ghost = ctx.GM().expandGridMargins(p, {
                    west: pOffX,
                    north: pOffY,
                    east: preview.w - p.grid.w - pOffX,
                    south: preview.h - p.grid.h - pOffY,
                });
            }
            _drawGhostGrid(c2d, CELL, scale, -pOffX * CELL, -pOffY * CELL, preview.w, preview.h, ghost);
        }
        const activeAnchor = (preview && preview.anchor) || ctx.state.gridAnchor;
        _drawAnchorBadge(c2d, CELL, scale, activeAnchor);
        if (ctx.state.gridEdit) {
            const pts = ctx.GM().gridHandlePoints(ext.w, ext.h);
            Object.keys(pts).forEach((key) => {
                c2d.beginPath();
                c2d.arc(frameX + pts[key].x * CELL, frameY + pts[key].y * CELL, 6 / scale, 0, Math.PI * 2);
                c2d.fillStyle = key.length === 2 ? '#e3b341' : '#58a6ff';
                c2d.fill();
            });
            const cellCorner = _cellCornerHandlePoint(ctx, p);
            if (cellCorner) {
                const rx = (cellCorner.x - 1) * CELL;
                const ry = (cellCorner.y - 1) * CELL;
                c2d.strokeStyle = '#3fb950';
                c2d.lineWidth = 1.75 / scale;
                c2d.setLineDash([4 / scale, 3 / scale]);
                c2d.strokeRect(rx, ry, CELL, CELL);
                c2d.setLineDash([]);
                c2d.beginPath();
                c2d.arc(cellCorner.x * CELL, cellCorner.y * CELL, 6.5 / scale, 0, Math.PI * 2);
                c2d.fillStyle = '#3fb950';
                c2d.fill();
                c2d.strokeStyle = '#0d1117';
                c2d.lineWidth = 1.5 / scale;
                c2d.stroke();
            }
        }
        if (drag && drag.kind === 'move') {
            const off = drag.offset;
            c2d.fillStyle = '#e3b341';
            c2d.font = `${12 / scale}px sans-serif`;
            c2d.fillText(`offset ${off.x.toFixed(1)}, ${off.y.toFixed(1)}`, 8 / scale, (ext.h * CELL) + 14 / scale);
        }
        else if (drag && drag.kind === 'cell-size' && ctx.state.cellSizePreview) {
            const pr = ctx.state.cellSizePreview;
            c2d.fillStyle = '#3fb950';
            c2d.font = `${12 / scale}px sans-serif`;
            c2d.fillText(`1 cell ≈ ${Math.round(pr.pxPerCell)}px -> snaps to ${pr.w}×${pr.h}`, 8 / scale, (ext.h * CELL) + 14 / scale);
        }
        else if (drag && drag.w && drag.h) {
            c2d.fillStyle = '#e3b341';
            c2d.font = `${12 / scale}px sans-serif`;
            const shiftNote = (offX || offY) ? ` (shift x${offX >= 0 ? '+' : ''}${offX}, y${offY >= 0 ? '+' : ''}${offY})` : '';
            c2d.fillText(`${drag.w}×${drag.h}${shiftNote}`, frameX + 8 / scale, frameY + (ext.h * CELL) + 14 / scale);
        }
        c2d.restore();
    }
    function _gridHit(ctx, p, pos) {
        const CELL = ctx.CELL || 22;
        const scale = (ctx.state.stage && ctx.state.stage.scaleX()) || 1;
        const tol = 10 / scale;
        const cellCorner = _cellCornerHandlePoint(ctx, p);
        if (cellCorner && Math.abs(pos.x - cellCorner.x * CELL) <= tol
            && Math.abs(pos.y - cellCorner.y * CELL) <= tol) {
            return { kind: 'cell-size', key: 'cell' };
        }
        const pts = ctx.GM().gridHandlePoints(p.grid.w, p.grid.h);
        for (const key of Object.keys(pts)) {
            if (Math.abs(pos.x - pts[key].x * CELL) <= tol
                && Math.abs(pos.y - pts[key].y * CELL) <= tol) {
                return { kind: 'resize', key };
            }
        }
        const w = p.grid.w * CELL;
        const h = p.grid.h * CELL;
        if (pos.x >= 0 && pos.x <= w && pos.y >= 0 && pos.y <= h) {
            return { kind: 'move', key: null };
        }
        return null;
    }
    function _gridMouseDown(ctx, p, ev) {
        const CELL = ctx.CELL || 22;
        const raw = (ev || {});
        const pos = ctx.state.stage.getRelativePointerPosition();
        if (!pos)
            return;
        const target = _gridHit(ctx, p, pos);
        if (!target)
            return;
        const anchorScreen = target.kind === 'cell-size' ? _refScreenBox(ctx, p, p.grid) : null;
        const imgW = (ctx.state.refImage && ctx.state.refImage.naturalWidth) || 0;
        const startPx = (target.kind === 'cell-size' && imgW > 0)
            ? (ctx.GM().cellSizeForGrid(imgW, p.grid.w) || 32)
            : null;
        ctx.state.gridDrag = {
            kind: target.kind,
            key: target.key,
            start: { x: pos.x / CELL, y: pos.y / CELL },
            clientX: typeof raw.clientX === 'number' ? raw.clientX : 0,
            clientY: typeof raw.clientY === 'number' ? raw.clientY : 0,
            w: p.grid.w,
            h: p.grid.h,
            offsetX: 0,
            offsetY: 0,
            moved: false,
            offset: Object.assign({ x: 0, y: 0 }, p.map_offset || {}),
            startOffset: Object.assign({ x: 0, y: 0 }, p.map_offset || {}),
            anchorScreen,
            pxPerCell: startPx,
        };
        _gridDragWatch(ctx, p);
    }
    function _gridDragWatch(ctx, p) {
        _gridDragRelease(ctx);
        const onMove = (ev) => {
            if (!ctx.state.gridDrag)
                return;
            if (ev.cancelable)
                ev.preventDefault();
            if (ctx.state.gridDrag.kind === 'cell-size') {
                _gridDragCellCornerScreen(ctx, p, ev.clientX, ev.clientY);
                return;
            }
            const cell = _gridPointerCell(ctx, ev.clientX, ev.clientY);
            if (cell)
                _gridDragTo(ctx, p, cell.x, cell.y);
        };
        const onUp = () => {
            _gridDragRelease(ctx);
            _gridMouseUp(ctx, p);
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        ctx.state.gridDragRelease = function () {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    }
    function _gridDragRelease(ctx) {
        if (ctx.state.gridDragRelease) {
            ctx.state.gridDragRelease();
            ctx.state.gridDragRelease = null;
        }
    }
    function _gridDragCellCornerScreen(ctx, p, clientX, clientY) {
        const drag = ctx.state.gridDrag;
        const stage = ctx.state.stage;
        const img = ctx.state.refImage;
        if (!drag || !stage || !img || !img.naturalWidth || !drag.anchorScreen)
            return;
        const holderRect = ctx.state.gridHolder ? ctx.state.gridHolder.getBoundingClientRect() : null;
        if (!holderRect)
            return;
        const sx = clientX - holderRect.left - drag.anchorScreen.x;
        const sy = clientY - holderRect.top - drag.anchorScreen.y;
        const screenCellPx = Math.max(4, Math.max(sx, sy));
        const imgPxPerScreenPx = img.naturalWidth / Math.max(1, drag.anchorScreen.w);
        const range = ctx.GM().cellSizeRange(img.naturalWidth, img.naturalHeight);
        if (!range)
            return;
        const px = Math.min(range.max, Math.max(range.min, Math.round(screenCellPx * imgPxPerScreenPx)));
        const next = ctx.GM().gridForCellSize(img.naturalWidth, img.naturalHeight, px);
        if (!next)
            return;
        drag.w = next.w;
        drag.h = next.h;
        drag.pxPerCell = px;
        ctx.state.cellSizePreview = { w: next.w, h: next.h, pxPerCell: px };
        ctx.applyRefTransform(p);
        const afterCells = ctx.refRectCells(p, img, ctx.state.cellSizePreview);
        _anchorStageToRefScreen(ctx, drag.anchorScreen, afterCells);
        if (ctx.state.dimsBtn) {
            ctx.state.dimsBtn.textContent = `${next.w}×${next.h} · 1 cell = 1 turn ≈ ${px}px`;
        }
        if (ctx.state.stage)
            ctx.state.stage.batchDraw();
    }
    function _gridPointerCell(ctx, clientX, clientY) {
        const CELL = ctx.CELL || 22;
        const drag = ctx.state.gridDrag;
        const stage = ctx.state.stage;
        if (!drag || !stage)
            return null;
        const scale = stage.scaleX() || 1;
        return {
            x: drag.start.x + (clientX - drag.clientX) / (CELL * scale),
            y: drag.start.y + (clientY - drag.clientY) / (CELL * scale),
        };
    }
    function _gridDragTo(ctx, p, cx, cy) {
        const drag = ctx.state.gridDrag;
        if (!drag)
            return;
        if (drag.kind === 'move') {
            const dx = cx - drag.start.x;
            const dy = cy - drag.start.y;
            if ((dx * dx + dy * dy) > 0.04)
                drag.moved = true;
            ctx.state.gridDrag.offset = {
                x: drag.startOffset.x + dx,
                y: drag.startOffset.y + dy,
            };
        }
        else {
            const next = ctx.GM().gridHandleDragMargins(p.grid.w, p.grid.h, drag.key, { x: cx, y: cy });
            ctx.state.gridDrag.w = next.w;
            ctx.state.gridDrag.h = next.h;
            ctx.state.gridDrag.offsetX = next.offsetX;
            ctx.state.gridDrag.offsetY = next.offsetY;
        }
        const bg = ctx.state.layers && ctx.state.layers.bg;
        if (bg)
            bg.batchDraw();
        ctx.redrawDecor();
    }
    async function _gridMouseUp(ctx, p) {
        const drag = ctx.state.gridDrag;
        if (!drag)
            return;
        ctx.state.gridDrag = null;
        const savedAnchor = drag.anchorScreen;
        const oldGrid = { w: p.grid.w, h: p.grid.h };
        ctx.state.cellSizePreview = null;
        try {
            if (drag.kind === 'move') {
                if (!drag.moved) {
                    const ax = Math.max(0, Math.min(p.grid.w - 1, Math.floor(drag.start.x)));
                    const ay = Math.max(0, Math.min(p.grid.h - 1, Math.floor(drag.start.y)));
                    ctx.state.gridAnchor = { x: ax, y: ay };
                    ctx.status(`Origin anchor set to (${ax}, ${ay}).`, false);
                    ctx.redrawDecor();
                    return;
                }
                const offset = {
                    x: Math.round(drag.offset.x * 10) / 10,
                    y: Math.round(drag.offset.y * 10) / 10,
                };
                const resp = await ctx.post(`/${encodeURIComponent(p.scope.id)}/offset`, offset);
                p.map_offset = (resp && resp.map_offset) || offset;
                ctx.status(`Grid offset set to ${offset.x}, ${offset.y} cells.`, false);
            }
            else if (drag.kind === 'cell-size' && (drag.w !== p.grid.w || drag.h !== p.grid.h)) {
                const why = drag.pxPerCell ? `1 cell ≈ ${Math.round(drag.pxPerCell)}px` : 'cell resize';
                const anchor = ctx.state.gridAnchor || { x: 0, y: 0 };
                const scaleFactor = drag.w / Math.max(1, oldGrid.w);
                const committed = await _commitGridSize(ctx, p, drag.w, drag.h, why, oldGrid, {
                    anchor,
                    scaleFactor,
                });
                if (!committed) {
                    ctx.applyRefTransform(p);
                    if (savedAnchor) {
                        const origCells = ctx.refRectCells(p, ctx.state.refImage, oldGrid);
                        _anchorStageToRefScreen(ctx, savedAnchor, origCells);
                    }
                    ctx.redrawGrid();
                    return;
                }
            }
            else if (drag.w !== p.grid.w || drag.h !== p.grid.h || drag.offsetX || drag.offsetY) {
                await _commitGridSize(ctx, p, drag.w, drag.h, 'frame resize', undefined, {
                    offsetX: drag.offsetX || 0,
                    offsetY: drag.offsetY || 0,
                });
            }
            ctx.notify(true);
        }
        catch (e) {
            ctx.status(`Grid adjust failed: ${ctx.errText(e)}`, true);
        }
        ctx.render();
        if (drag.kind === 'cell-size' && ctx.state.payload && savedAnchor) {
            const afterCells = ctx.refRectCells(ctx.state.payload, ctx.state.refImage);
            _anchorStageToRefScreen(ctx, savedAnchor, afterCells);
            ctx.redrawGrid();
        }
    }
    async function _commitGridSize(ctx, p, w, h, why, rescaleRefFrom, opts) {
        const offsetX = (opts && opts.offsetX) || 0;
        const offsetY = (opts && opts.offsetY) || 0;
        const anchor = opts && opts.anchor;
        const scaleFactor = opts && opts.scaleFactor;
        const stranded = (offsetX || offsetY || (anchor && scaleFactor))
            ? 0
            : ctx.GM().strandedCount(p, w, h);
        if (stranded > 0) {
            const ok = await window.Dialog?.confirm?.({
                title: 'Resize Grid',
                message: `Resize the grid to ${w}×${h} (${why})?\n\n${stranded} painted cell(s) or placement(s) outside it will be removed. This can be undone.`,
                danger: true
            });
            if (!ok)
                return false;
        }
        const storedRect = (p.reference || {}).rect;
        const body = { w, h, mode: p.mode };
        if (offsetX)
            body.offset_x = offsetX;
        if (offsetY)
            body.offset_y = offsetY;
        if (anchor && scaleFactor && Number.isFinite(scaleFactor) && scaleFactor > 0) {
            body.anchor_x = anchor.x;
            body.anchor_y = anchor.y;
            body.scale_factor = scaleFactor;
        }
        ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid`, body);
        if ((offsetX || offsetY) && storedRect && typeof storedRect.x === 'number' && typeof storedRect.y === 'number'
            && ctx.state.payload) {
            const ref = ctx.state.payload.reference || {};
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/reference`, {
                image: ref.image || null,
                opacity: ref.opacity,
                visible: ref.visible,
                crop: ref.crop,
                rect: Object.assign({}, storedRect, {
                    x: storedRect.x + offsetX,
                    y: storedRect.y + offsetY,
                }),
            });
        }
        else if (rescaleRefFrom && storedRect && typeof storedRect.w === 'number' && storedRect.w > 0
            && (rescaleRefFrom.w !== w || rescaleRefFrom.h !== h) && ctx.state.payload) {
            const scaledRect = _scaleRefRect(storedRect, rescaleRefFrom, { w, h });
            const ref = ctx.state.payload.reference || {};
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/reference`, {
                image: ref.image || null,
                opacity: ref.opacity,
                visible: ref.visible,
                crop: ref.crop,
                rect: scaledRect,
            });
        }
        ctx.status(`Grid set to ${w}×${h} (${why})`
            + (stranded ? `, ${stranded} out-of-bounds cell(s) removed` : '') + '.', false);
        return true;
    }
    function ensureRefImage(ctx, p) {
        const ref = p.reference;
        if (!ref || !ref.image) {
            ctx.state.refImage = null;
            return null;
        }
        if (ctx.state.refImage && ctx.state.refImage.__src === ref.image)
            return ctx.state.refImage;
        const img = new window.Image();
        img.__src = ref.image;
        img.onload = () => {
            ctx.state.refImage = img;
            if (ctx.state.refNode && ctx.state.payload) {
                ctx.state.refNode.image(img);
                applyRefTransform(ctx, ctx.state.payload);
                ctx.redrawGrid();
            }
        };
        img.onerror = () => { ctx.state.refImage = null; };
        img.src = ref.image;
        return img;
    }
    function refRectCells(ctx, p, img, extOverride) {
        const savedGrid = p.grid || { w: 1, h: 1 };
        const preview = extOverride || ctx.state.cellSizePreview;
        const ext = preview || savedGrid;
        const stored = (p.reference || {}).rect;
        const iw = (img && img.naturalWidth) || ext.w || 1;
        const ih = (img && img.naturalHeight) || ext.h || 1;
        if (preview && preview.pxPerCell && preview.pxPerCell > 0 && iw > 1 && ih > 1) {
            return { x: 0, y: 0, w: iw / preview.pxPerCell, h: ih / preview.pxPerCell };
        }
        if (stored && typeof stored.x === 'number' && typeof stored.y === 'number'
            && typeof stored.w === 'number' && typeof stored.h === 'number'
            && stored.w > 0 && stored.h > 0) {
            if (ext.w !== savedGrid.w || ext.h !== savedGrid.h) {
                return _scaleRefRect(stored, savedGrid, ext);
            }
            return { x: stored.x, y: stored.y, w: stored.w, h: stored.h };
        }
        const gw = ext.w || 0;
        const gh = ext.h || 0;
        return ctx.GM().fitReferenceRect(gw, gh, iw, ih);
    }
    function applyRefTransform(ctx, p) {
        const node = ctx.state.refNode;
        if (!node)
            return;
        const img = ctx.state.refImage;
        const rect = refRectCells(ctx, p, img);
        const CELL = ctx.CELL || 22;
        node.x(rect.x * CELL);
        node.y(rect.y * CELL);
        node.width(rect.w * CELL);
        node.height(rect.h * CELL);
        const iw = (img && img.naturalWidth) || 0;
        const ih = (img && img.naturalHeight) || 0;
        if (!iw || !ih)
            return;
        const crop = (p.reference || {}).crop;
        node.crop(crop && crop.w
            ? { x: crop.x * iw, y: crop.y * ih, width: crop.w * iw, height: crop.h * ih }
            : { x: 0, y: 0, width: iw, height: ih });
    }
    async function gridFromReference(ctx, p) {
        const img = ctx.state.refImage;
        if (!img || !img.naturalWidth) {
            ctx.status('Load a reference image first.');
            return;
        }
        const next = ctx.GM().gridForImageAspect(p.grid && p.grid.w, img.naturalWidth, img.naturalHeight);
        if (!next) {
            ctx.status('That image has no readable size - try another file.', true);
            return;
        }
        const prune = ctx.GM().pruneGrid(p, next.w, next.h);
        if (prune.total > 0) {
            const lines = [];
            if (prune.areas)
                lines.push(`${prune.areas} area(s)`);
            if (prune.features)
                lines.push(`${prune.features} feature(s)`);
            if (prune.paint)
                lines.push(`${prune.paint} painted cell(s)`);
            const ok = await window.Dialog?.confirm?.({
                title: 'Shrink grid to match reference',
                message: `Matching ${next.w}x${next.h} will drop ${lines.join(', ')} outside the new bounds.\n\nContinue?`,
                danger: true
            });
            if (!ok)
                return;
        }
        await _commitGridSize(ctx, p, next.w, next.h, 'match-reference', p.grid || undefined);
    }
    async function updateReference(ctx, patch) {
        const p = ctx.state.payload;
        if (!p)
            return;
        try {
            ctx.state.payload = await ctx.post(`/${encodeURIComponent(p.scope.id)}/grid/reference`, patch);
            ctx.notify(false);
            ctx.render();
            ctx.status('Reference updated.');
        }
        catch (e) {
            ctx.status(`Reference failed: ${ctx.errText(e)}`, true);
        }
    }
    const WorldPainterHandles = {
        ensureRefImage,
        refRectCells,
        applyRefTransform,
        gridFromReference,
        updateReference,
        scaleRefRect: _scaleRefRect,
        anchorStageToRefScreen: _anchorStageToRefScreen,
        refScreenBox: _refScreenBox,
        refHandlePoints: _refHandlePoints,
        drawRefHandles: _drawRefHandles,
        refHit: _refHit,
        refMouseDown: _refMouseDown,
        refMouseMove: _refMouseMove,
        refMouseUp: _refMouseUp,
        gridExtent: _gridExtent,
        cellCornerHandlePoint: _cellCornerHandlePoint,
        drawGridHandles: _drawGridHandles,
        gridHit: _gridHit,
        gridMouseDown: _gridMouseDown,
        gridDragWatch: _gridDragWatch,
        gridDragRelease: _gridDragRelease,
        gridDragCellCornerScreen: _gridDragCellCornerScreen,
        gridPointerCell: _gridPointerCell,
        gridDragTo: _gridDragTo,
        gridMouseUp: _gridMouseUp,
        commitGridSize: _commitGridSize,
    };
    window.WorldPainterHandles = WorldPainterHandles;
    window.VW = window.VW || {};
    window.VW.worldPainterHandles = WorldPainterHandles;
})();
