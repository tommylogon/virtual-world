/**
 * grid-model.js — pure helpers for the WorldPainter editor.
 *
 * No DOM and no network: the editor (`static/js/worldpainter/editor.js`) keeps
 * its rendering dumb by deriving cell rows, colours, and feature placement from
 * these functions, which are covered by `tools/unit/test_worldpainter.js`.
 *
 * Mirrors the server contract in `engine/world_grid.py` (task-495): a scope owns
 * a bounded grid, paint lives on layers `biome`/`road`/`floor`, and features
 * are child scopes placed at a cell. `floor` is a **storey index** — 0 ground,
 * 1 one up, -1 one down, unbounded (an 80-storey tower, a lake bottom at -2, a
 * hole to hell at -900) — never a height fraction and never a ground material;
 * the material lives in the biome/road record's `surface`.
 *
 * @module grid-model — WorldPainter grid view-model and cell maths
 * @contributes cell keys, drill-down mode suggestion, render rows, layer colours, storey reads, cell names, placed areas, compile estimate, cell inspector, scope-grouped area picker, palette grouping/filtering and tile descriptions
 * @powers WorldPainter editor grid rendering, placement and inspection (task-495, task-528, task-540, task-541)
 * @relates static/js/worldpainter/editor.js; engine/world_grid.py; routes/world_grid_ops.py
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.


/** A grid cell. Coordinates are cell indices; `key` is the `x,y` pair. */
interface Cell { x: number; y: number; }

interface Rect { x: number; y: number; w: number; h: number; }

/**
 * Everything below reads a `/api/world/painter/...` payload (grid, layers,
 * placements, area_placements, unplaced_areas, children, names) or a vocabulary
 * blob. Those shapes are owned by `routes/world_grid_ops.py`, not by this
 * view-model, and every read here is already null-guarded, so the payload
 * arguments stay `any` rather than freezing a contract this file does not own.
 */
type GridPayload = any;
type Vocabulary = any;

(function () {
    'use strict';

    const MODES = ['world', 'town', 'interior'];
    // Mirrors engine/world_grid.py PAINT_LAYERS. A layer missing from either list
    // is dropped on save (the backend normalises against its own tuple) or paints
    // a colour nothing reads — so the two must move together.
    const PAINT_LAYERS = ['biome', 'road', 'floor', 'climate', 'current'];

    // The coarse climates a grid may be painted with, and the colours that make
    // one readable at a glance (task-557). The **ids and base °C come from the
    // server** (`/api/world/painter/vocabulary`) and land in `CLIMATE_IDS` /
    // `CLIMATE_BASE`; only the colour is decided here, because a colour is a
    // display choice the backend has no opinion about. `CLIMATES` below is the
    // offline fallback so the module is usable in the unit sandbox with no fetch —
    // a palette showing one base while the compiler writes another is exactly the
    // disagreement the server payload exists to prevent.
    const CLIMATE_COLORS: Record<string, string> = {
        arctic: '#7fb3d5', alpine: '#a8bfc9', temperate: '#7fbf7f',
        arid: '#d9b26a', tropical: '#4f9f6a',
    };
    const CLIMATE_LABELS: Record<string, string> = {
        arctic: 'Arctic', alpine: 'Alpine', temperate: 'Temperate',
        arid: 'Arid', tropical: 'Tropical',
    };
    const CLIMATES: Record<string, { label: string; base: number; color: string }> = {
        arctic: { label: 'Arctic', base: -8, color: CLIMATE_COLORS.arctic },
        alpine: { label: 'Alpine', base: 2, color: CLIMATE_COLORS.alpine },
        temperate: { label: 'Temperate', base: 21, color: CLIMATE_COLORS.temperate },
        arid: { label: 'Arid', base: 31, color: CLIMATE_COLORS.arid },
        tropical: { label: 'Tropical', base: 27, color: CLIMATE_COLORS.tropical },
    };
    const CLIMATE_IDS = Object.keys(CLIMATES);
    const DEFAULT_CLIMATE = 'temperate';

    /**
     * Adopt the server's climate list: ids and base °C from the backend, colours
     * kept from the local table. Called once the vocabulary arrives, so a new
     * climate is a backend change and nothing else.
     */
    function useClimatesFromVocab(vocab: Vocabulary): boolean {
        const list = vocab && (vocab.climates || (vocab.c && vocab.c.climates));
        if (!Array.isArray(list) || !list.length) return false;
        const next: Record<string, { label: string; base: number; color: string }> = {};
        const ids: string[] = [];
        list.forEach((row) => {
            const id = String((row && row.id) || '').trim();
            if (!id) return;
            next[id] = {
                label: (CLIMATE_LABELS[id] || id),
                base: Number(row.base),
                color: (CLIMATE_COLORS[id] || '#888'),
            };
            ids.push(id);
        });
        if (!ids.length) return false;
        Object.keys(CLIMATES).forEach((k) => { delete CLIMATES[k]; });
        ids.forEach((id) => { CLIMATES[id] = next[id]; });
        CLIMATE_IDS.length = 0;
        ids.forEach((id) => CLIMATE_IDS.push(id));
        return true;
    }

    // Keys are the real ids in `data/worldpainter/biomes.json` / `features`, so a
    // painted cell reads at a glance; anything else gets a deterministic hash
    // colour, so an unknown value is still stable (never blank).
    const BIOME_COLORS: Record<string, string> = {
        sparse_forest: '#6f9b52', dense_forest: '#2f6b34', pine_forest: '#2b5a4b',
        farmland: '#b6a24f', hills: '#8a7d52', mountains: '#6d6a63', cliff: '#7d746a',
        chasm: '#3a3a42', ravine: '#4a4640', beach: '#cbb78a', spring: '#4f9bb0',
        stream: '#3f88a0', river: '#2f6f96', lake: '#245a7a', deep_water: '#1b3a5b',
        ocean: '#1b3a5b',
        // Structure (task-562): the cells that are *not* places. They need their own
        // colours, because a hash colour would make a wall look like a biome and the
        // whole point of painting one is that it changes what the map means. A void
        // is deliberately dark like a chasm — "nothing you can stand on" — and a
        // window is the one cell you can see *through*, so it reads lighter than the
        // wall it sits in.
        wall: '#55525c', void: '#22222a', window: '#8fc4d8', door: '#a8763f',
        // A public bath: pale blue stone so it reads as water without looking
        // like a river crossed by mistake.
        bathhouse: '#6f9bb0',
    };
    const ROAD_COLORS: Record<string, string> = {
        road: '#8a7d5f', bridge: '#7a5a3a', ford: '#5f7f96', gate: '#6f7276',
        tunnel: '#3a3a42', town: '#a8763f', village: '#a8763f', ruin: '#6b6157',
        building: '#8a6b5a',
    };

    function cellKey(x: number, y: number): string {
        return `${Math.trunc(x)},${Math.trunc(y)}`;
    }

    function parseCellKey(key: unknown): Cell | null {
        const parts = String(key == null ? '' : key).split(',');
        if (parts.length !== 2) return null;
        const x = Number(parts[0]);
        const y = Number(parts[1]);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
        return { x, y };
    }

    function cellId(scopeId: string, x: number, y: number): string {
        return `${scopeId}:${Math.trunc(x)},${Math.trunc(y)}`;
    }

    /** The mode a child scope should open in, given its parent's mode. */
    function nextMode(mode: string): string {
        const i = MODES.indexOf(mode);
        if (i < 0) return MODES[0];
        return MODES[Math.min(i + 1, MODES.length - 1)];
    }

    function _hash(text: unknown): number {
        let h = 0;
        const s = String(text == null ? '' : text);
        for (let i = 0; i < s.length; i += 1) {
            h = (h * 31 + s.charCodeAt(i)) | 0;
        }
        return Math.abs(h);
    }

    function layerColor(layer: string, value: unknown): string | null {
        if (value == null || value === '') return null;
        const key = String(value).toLowerCase();
        if (layer === 'biome') return BIOME_COLORS[key] || `hsl(${_hash(key) % 360},45%,45%)`;
        if (layer === 'road') return ROAD_COLORS[key] || `hsl(${_hash(key) % 360},18%,55%)`;
        if (layer === 'floor') {
            const n = Number(value);
            if (!Number.isFinite(n)) return '#666';
            // Storeys, not a 0..1 height: 0 is ground, up is cooler/lighter, down
            // is warmer/darker. The clamp is for *colour* only — a cell may sit
            // at 80 or -900, and every one of those should still read as "far
            // above/below" rather than as a distinguishable shade.
            const f = Math.max(-4, Math.min(4, n));
            const light = f >= 0 ? 76 - f * 4 : 76 + f * 7;
            return `hsl(${f < 0 ? 28 : 208},${8 + Math.abs(f) * 10}%,${Math.max(34, light)}%)`;
        }
        if (layer === 'climate') {
            // A known climate gets its own colour; an unknown one is a typo the
            // generate report will name, and here it reads as a hash so it is
            // visibly *not* one of the five rather than quietly temperate.
            return (CLIMATES[key] && CLIMATES[key].color)
                || `hsl(${_hash(key) % 360},70%,55%)`;
        }
        return `hsl(${_hash(key) % 360},40%,50%)`;
    }

    /**
     * A cell's **storey index** as a number, or `null` when the cell is unpainted.
     *
     * 0 is a real painted value (the author said "ground"), so callers must test
     * `!= null`, never truthiness. Non-numeric paint reads as `null` rather than
     * 0 so a typo cannot silently become ground.
     */
    function floorNumber(value: unknown): number | null {
        if (value === null || value === undefined || value === '') return null;
        const n = Number(value);
        if (!Number.isFinite(n)) return null;
        return Math.round(n);
    }

    /** How a storey index reads out loud: "ground", "floor 3", "3 below ground". */
    function floorLabel(value: unknown): string {
        const n = floorNumber(value);
        if (n === null) return '-';
        if (n === 0) return 'ground (0)';
        return n > 0 ? `floor ${n}` : `${-n} below ground (${n})`;
    }

    /**
     * Convert metres to whole storeys: `round(metres / metresPerStorey)` (task-877).
     *
     * Boundaries for 3 m/storey fall at 1.5 m, 4.5 m, 7.5 m, etc.
     * Rounding uses standard Math.round.
     */
    function metresToStoreys(metres: number, metresPerStorey?: number | null): number {
        const m = Number(metres);
        if (!Number.isFinite(m)) return 0;
        const scale = (metresPerStorey && metresPerStorey > 0) ? metresPerStorey : 3;
        return Math.round(m / scale);
    }

    /** Convert whole storeys to metres: `storeys * metresPerStorey` (task-877). */
    function storeysToMetres(storeys: number, metresPerStorey?: number | null): number {
        const s = Number(storeys);
        if (!Number.isFinite(s)) return 0;
        const scale = (metresPerStorey && metresPerStorey > 0) ? metresPerStorey : 3;
        return Math.round(s) * scale;
    }

    /**
     * Interpolate greyscale luminance (0..255) into a metre range [minM, maxM].
     */
    function luminanceToMetres(luminance: number, minM: number, maxM: number): number {
        const lum = Math.max(0, Math.min(255, Number(luminance) || 0));
        const fraction = lum / 255.0;
        return minM + fraction * (maxM - minM);
    }

    /**
     * Map a metre value into 0..255 greyscale luminance given a metre range [minM, maxM].
     */
    function metresToLuminance(metres: number, minM: number, maxM: number): number {
        if (maxM <= minM) return 0;
        const m = Math.max(minM, Math.min(maxM, Number(metres) || 0));
        const fraction = (m - minM) / (maxM - minM);
        return Math.round(fraction * 255);
    }

    /**
     * Count neighbouring cell pairs whose storey delta strictly exceeds maxStoreyStep.
     *
     * Checks orthogonal neighbouring pairs (E and S of each cell) so each seam is
     * counted once. Unpainted cells are ground (0 storeys).
     */
    function climbGatedSteps(grid: { w: number; h: number }, floorMap: Record<string, number>, maxStoreyStep?: number | null): number {
        const w = (grid && grid.w) || 0;
        const h = (grid && grid.h) || 0;
        const limit = (maxStoreyStep != null && maxStoreyStep >= 0) ? maxStoreyStep : 3;
        let count = 0;
        for (let y = 0; y < h; y += 1) {
            for (let x = 0; x < w; x += 1) {
                const k = cellKey(x, y);
                const cur = floorMap[k] != null ? floorMap[k] : 0;
                // East neighbour
                if (x + 1 < w) {
                    const eK = cellKey(x + 1, y);
                    const eVal = floorMap[eK] != null ? floorMap[eK] : 0;
                    if (Math.abs(cur - eVal) > limit) count += 1;
                }
                // South neighbour
                if (y + 1 < h) {
                    const sK = cellKey(x, y + 1);
                    const sVal = floorMap[sK] != null ? floorMap[sK] : 0;
                    if (Math.abs(cur - sVal) > limit) count += 1;
                }
            }
        }
        return count;
    }

    /**
     * Bresenham line of cells from *a* to *b*, inclusive. The route tool uses
     * this so a two-click route paints the exact cells a straight trail covers
     * (a hand-rolled line rasteriser is standard, not a wheel worth a library).
     */
    function lineCells(a: Cell, b: Cell): Cell[] {
        let x0 = Math.trunc(a.x);
        let y0 = Math.trunc(a.y);
        const x1 = Math.trunc(b.x);
        const y1 = Math.trunc(b.y);
        const cells: Cell[] = [];
        const dx = Math.abs(x1 - x0);
        const dy = Math.abs(y1 - y0);
        const sx = x0 < x1 ? 1 : -1;
        const sy = y0 < y1 ? 1 : -1;
        let err = dx - dy;
        for (;;) {
            cells.push({ x: x0, y: y0 });
            if (x0 === x1 && y0 === y1) break;
            const e2 = 2 * err;
            if (e2 > -dy) { err -= dy; x0 += sx; }
            if (e2 < dx) { err += dx; y0 += sy; }
        }
        return cells;
    }

    /**
     * Conservative supercover line rasterization between a and b.
     * Crucially seals diagonal corner transits by visiting both orthogonal
     * cells when stepping diagonally (task-882).
     */
    function supercoverLine(a: Cell, b: Cell): Cell[] {
        const x0 = Math.trunc(a.x);
        const y0 = Math.trunc(a.y);
        const x1 = Math.trunc(b.x);
        const y1 = Math.trunc(b.y);
        const dx = x1 - x0;
        const dy = y1 - y0;
        const nx = Math.abs(dx);
        const ny = Math.abs(dy);
        const signX = dx > 0 ? 1 : dx < 0 ? -1 : 0;
        const signY = dy > 0 ? 1 : dy < 0 ? -1 : 0;

        let px = x0;
        let py = y0;
        const points: Cell[] = [{ x: px, y: py }];
        if (nx === 0 && ny === 0) return points;

        let ix = 0;
        let iy = 0;
        while (ix < nx || iy < ny) {
            const decision = (1 + 2 * ix) * ny - (1 + 2 * iy) * nx;
            if (decision === 0) {
                points.push({ x: px + signX, y: py });
                points.push({ x: px, y: py + signY });
                px += signX;
                py += signY;
                ix += 1;
                iy += 1;
            } else if (decision < 0) {
                px += signX;
                ix += 1;
            } else {
                py += signY;
                iy += 1;
            }
            points.push({ x: px, y: py });
        }
        return points;
    }

    function tileHeight(payload: any, x: number, y: number, vocab?: any): number {
        const key = cellKey(x, y);
        const bId = (payload?.layers?.biome || {})[key];
        if (!bId) return 0;
        if (vocab?.biomes) {
            const b = vocab.biomes.find((v: any) => v.id === bId);
            if (b && typeof b.height === 'number') return b.height;
        }
        const bStr = String(bId).toLowerCase();
        if (bStr.includes('mountain') || bStr.includes('peak') || bStr.includes('cliff')) return 20;
        if (bStr.includes('hill')) return 5;
        if (bStr.includes('wall')) return 2;
        if (bStr.includes('dense_forest') || bStr.includes('jungle')) return 3;
        if (bStr.includes('sparse_forest') || bStr.includes('forest') || bStr.includes('wood')) return 2;
        if (bStr.includes('marsh') || bStr.includes('swamp') || bStr.includes('scrub')) return 1;
        return 0;
    }

    function tileObscurity(payload: any, x: number, y: number, vocab?: any): number {
        const key = cellKey(x, y);
        const bId = (payload?.layers?.biome || {})[key];
        if (!bId) return 0;
        if (vocab?.biomes) {
            const b = vocab.biomes.find((v: any) => v.id === bId);
            if (b && typeof b.obscurity === 'number') return Math.max(0, Math.min(1, b.obscurity));
        }
        const bStr = String(bId).toLowerCase();
        if (bStr.includes('mountain') || bStr.includes('peak') || bStr.includes('cliff') || bStr.includes('wall')) return 1.0;
        if (bStr.includes('dense_forest') || bStr.includes('jungle')) return 0.8;
        if (bStr.includes('sparse_forest') || bStr.includes('forest') || bStr.includes('wood')) return 0.4;
        if (bStr.includes('marsh') || bStr.includes('swamp') || bStr.includes('scrub')) return 0.2;
        if (bStr.includes('hill')) return 0.3;
        return 0;
    }

    function tileFloor(payload: any, x: number, y: number): number {
        const v = (payload?.layers?.floor || {})[cellKey(x, y)];
        const n = Number(v);
        return Number.isFinite(n) ? n : 0;
    }

    interface SightRayResult {
        visible: boolean;
        blockedBy?: Cell | null;
        obscurity: number;
        cells: Cell[];
        blockedElevation?: number;
    }

    interface ScanStep {
        c: Cell;
        d: number;
        seen: boolean;
        hidden: number;
        blocker: Cell | null;
    }

    function scanRay(
        cells: Cell[],
        x0: number,
        y0: number,
        zEye: number,
        maxRange: number,
        props: (cx: number, cy: number) => { floor: number; height: number; obscurity: number }
    ): ScanStep[] {
        let opaqueSlope: number | null = null;
        let opaqueCell: Cell | null = null;
        const partial: Array<{ slope: number; obs: number; cell: Cell }> = [];
        const steps: ScanStep[] = [];

        for (const c of cells) {
            if (c.x === x0 && c.y === y0) continue;
            const d = Math.hypot(c.x - x0, c.y - y0);
            if (d > maxRange) break;

            const { floor: floorE, height: obsH, obscurity: obsV } = props(c.x, c.y);
            const drop = Math.max(0, d - 40) * 1.0;
            const slope = (floorE + obsH - drop - zEye) / d;

            let hidden = 0.0;
            let blocker: Cell | null = null;
            if (opaqueSlope !== null && opaqueSlope >= slope - 1e-9) {
                hidden = 1.0;
                blocker = opaqueCell;
            } else {
                for (const p of partial) {
                    if (p.slope >= slope - 1e-9) {
                        hidden += p.obs;
                        blocker = p.cell;
                    }
                }
                if (hidden < 1.0) blocker = null;
            }

            const seen = hidden < 1.0;
            steps.push({ c, d, seen, hidden, blocker });

            const groundSlope = (floorE - drop - zEye) / d;
            if (opaqueSlope === null || groundSlope > opaqueSlope) {
                opaqueSlope = groundSlope;
                opaqueCell = c;
            }
            if (obsH > 0 && obsV > 0) {
                if (obsV >= 1.0) {
                    if (slope > opaqueSlope) {
                        opaqueSlope = slope;
                        opaqueCell = c;
                    }
                } else {
                    partial.push({ slope, obs: obsV, cell: c });
                }
            }
        }
        return steps;
    }

    function castSightRay(
        origin: Cell & { z?: number },
        target: Cell & { z?: number },
        payload: any,
        eyeHeight = 0.5,
        maxRange = 60,
        vocab?: any
    ): SightRayResult {
        const x0 = Math.trunc(origin.x);
        const y0 = Math.trunc(origin.y);
        const z0 = typeof origin.z === 'number' ? origin.z : tileFloor(payload, x0, y0);
        const zEye = z0 + eyeHeight;

        const x1 = Math.trunc(target.x);
        const y1 = Math.trunc(target.y);
        const explicitZ1 = typeof target.z === 'number' ? target.z : null;

        if (x0 === x1 && y0 === y1) {
            return { visible: true, blockedBy: null, obscurity: 0, cells: [{ x: x0, y: y0 }] };
        }

        const distTotal = Math.hypot(x1 - x0, y1 - y0);
        if (distTotal > maxRange) {
            return { visible: false, blockedBy: null, obscurity: 1, cells: [] };
        }

        const cells = supercoverLine({ x: x0, y: y0 }, { x: x1, y: y1 });
        const props = (cx: number, cy: number) => {
            let floor = tileFloor(payload, cx, cy);
            if (explicitZ1 !== null && cx === x1 && cy === y1) {
                floor = explicitZ1;
            }
            const height = tileHeight(payload, cx, cy, vocab);
            const obscurity = tileObscurity(payload, cx, cy, vocab);
            return { floor, height, obscurity };
        };

        const steps = scanRay(cells, x0, y0, zEye, maxRange, props);
        let resultVisible = true;
        let blockedBy: Cell | null = null;
        let obscurity = 0;

        for (const st of steps) {
            if (st.c.x === x1 && st.c.y === y1) {
                resultVisible = st.seen;
                obscurity = st.hidden;
                if (!st.seen) blockedBy = st.blocker;
            }
        }

        if (blockedBy !== null) {
            const { floor, height } = props(blockedBy.x, blockedBy.y);
            return {
                visible: false,
                blockedBy,
                blockedElevation: floor + height,
                obscurity,
                cells,
            };
        }

        return { visible: resultVisible, blockedBy: null, obscurity, cells };
    }

    const FACING_ANGLES: Record<string, number> = {
        east: 0, e: 0,
        southeast: 45, se: 45,
        south: 90, s: 90,
        southwest: 135, sw: 135,
        west: 180, w: 180,
        northwest: -135, nw: -135,
        north: -90, n: -90,
        northeast: -45, ne: -45,
    };

    function computeVisibleCells(
        origin: Cell & { z?: number },
        payload: any,
        maxRange = 60,
        facing?: string | null,
        arcDegrees = 360,
        peripheralRange = 3,
        vocab?: any
    ): Set<string> {
        const x0 = Math.trunc(origin.x);
        const y0 = Math.trunc(origin.y);
        const w = payload?.grid?.w || 0;
        const h = payload?.grid?.h || 0;
        const visible = new Set<string>();
        visible.add(cellKey(x0, y0));
        if (!w || !h) return visible;

        let headingAngle: number | null = null;
        if (facing && arcDegrees < 360) {
            const angle = FACING_ANGLES[String(facing).toLowerCase()];
            if (typeof angle === 'number') headingAngle = angle;
        }

        const halfArc = headingAngle !== null ? arcDegrees / 2.0 : 180;
        const r = Math.min(maxRange, Math.max(w, h));
        const minX = Math.max(0, x0 - r);
        const maxX = Math.min(w - 1, x0 + r);
        const minY = Math.max(0, y0 - r);
        const maxY = Math.min(h - 1, y0 + r);

        const perimeterTargets: Cell[] = [];
        for (let x = minX; x <= maxX; x++) {
            perimeterTargets.push({ x, y: minY });
            perimeterTargets.push({ x, y: maxY });
        }
        for (let y = minY; y <= maxY; y++) {
            perimeterTargets.push({ x: minX, y });
            perimeterTargets.push({ x: maxX, y });
        }

        const z0 = typeof origin.z === 'number' ? origin.z : tileFloor(payload, x0, y0);
        const zEye = z0 + 0.5;

        const memo = new Map<string, { floor: number; height: number; obscurity: number }>();
        const props = (cx: number, cy: number) => {
            const k = cellKey(cx, cy);
            let got = memo.get(k);
            if (!got) {
                got = {
                    floor: tileFloor(payload, cx, cy),
                    height: tileHeight(payload, cx, cy, vocab),
                    obscurity: tileObscurity(payload, cx, cy, vocab),
                };
                memo.set(k, got);
            }
            return got;
        };

        for (const target of perimeterTargets) {
            if (target.x === x0 && target.y === y0) continue;
            const rayCells = supercoverLine({ x: x0, y: y0 }, target);
            const inside: Cell[] = [];
            for (const c of rayCells) {
                if (c.x < 0 || c.x >= w || c.y < 0 || c.y >= h) break;
                inside.push(c);
            }
            const steps = scanRay(inside, x0, y0, zEye, maxRange, props);
            for (const st of steps) {
                if (!st.seen) continue;
                if (headingAngle !== null) {
                    const cellAngle = (Math.atan2(st.c.y - y0, st.c.x - x0) * 180) / Math.PI;
                    const angleDiff = Math.abs(((cellAngle - headingAngle + 180) % 360) - 180);
                    if (angleDiff > halfArc) {
                        const { height: obsH } = props(st.c.x, st.c.y);
                        if (st.d > peripheralRange && obsH < 5.0) continue;
                    }
                }
                visible.add(cellKey(st.c.x, st.c.y));
            }
        }

        return visible;
    }

    /** Chain waypoint segments into one de-duplicated cell path. */
    function routeCells(points: Cell[]): Cell[] {
        const pts = points || [];
        const out: Cell[] = [];
        const seen: Record<string, boolean> = {};
        if (pts.length === 1) return [{ x: Math.trunc(pts[0].x), y: Math.trunc(pts[0].y) }];
        for (let i = 0; i + 1 < pts.length; i += 1) {
            lineCells(pts[i], pts[i + 1]).forEach((c) => {
                const k = cellKey(c.x, c.y);
                if (!seen[k]) { seen[k] = true; out.push(c); }
            });
        }
        return out;
    }

    /**
     * Turn a cell count into the game-time figures the world is authored in:
     * 1 cell = 1 turn = 1 minute, 60 turns/hour (240 cells => "4 h 00 m").
     */
    function routeStats(cellCount: number, minutesPerCell?: number | null): any {
        const per = minutesPerCell == null ? 1 : minutesPerCell;
        const turns = Math.round((Number(cellCount) || 0) * per);
        const hours = Math.floor(turns / 60);
        const mins = turns % 60;
        const label = turns >= 60
            ? `${cellCount} cells · ${turns} turns · ${hours} h ${String(mins).padStart(2, '0')} m`
            : `${cellCount} cells · ${turns} turns`;
        return { cells: cellCount, turns, minutes: turns, hours: hours + mins / 60, label };
    }

    function cellValue(payload: GridPayload, layer: string, x: number, y: number): any {
        const layers = (payload && payload.layers) || {};
        return (layers[layer] || {})[cellKey(x, y)];
    }

    function featureAt(payload: GridPayload, x: number, y: number): any {
        const feature = (payload && payload.feature) || {};
        return feature[cellKey(x, y)] || null;
    }

    /**
     * The author's name for a cell, or `null` (task-560).
     *
     * A name is metadata *about* a cell, not paint on it, so it lives in its own
     * `names` map beside `layers` — there is no name vocabulary, and the eraser
     * should not wipe a name. A named cell may be unpainted, so this never implies
     * anything about `painted`.
     */
    function cellName(payload: GridPayload, x: number, y: number): string | null {
        const names = (payload && payload.names) || {};
        const value = names[cellKey(x, y)];
        const text = value == null ? '' : String(value).trim();
        return text || null;
    }

    function placementFor(payload: GridPayload, childId: string): any {
        const list = (payload && payload.placements) || [];
        return list.find((p: any) => p.id === childId) || null;
    }

    /**
     * Full render model: rows of cells (y-major) carrying paint + feature, so the
     * editor only maps colours to styles. Off-grid when the scope has no grid.
     */
    function buildRows(payload: GridPayload): any[][] {
        const grid = (payload && payload.grid) || null;
        if (!grid || !grid.w || !grid.h) return [];
        const rows: any[][] = [];
        for (let y = 0; y < grid.h; y += 1) {
            const row: any[] = [];
            for (let x = 0; x < grid.w; x += 1) {
                const cell: Record<string, any> = { x, y, key: cellKey(x, y), feature: featureAt(payload, x, y) };
                PAINT_LAYERS.forEach((layer) => {
                    const value = cellValue(payload, layer, x, y);
                    if (value != null && value !== '') {
                        cell[layer] = value;
                        cell.color = cell.color || layerColor(layer, value);
                    }
                });
                row.push(cell);
            }
            rows.push(row);
        }
        return rows;
    }

    /** Feature placements as a Map-like lookup for selection/badges. */
    function featureMap(payload: GridPayload): Record<string, any> {
        const out: Record<string, any> = {};
        ((payload && payload.placements) || []).forEach((p: any) => {
            out[cellKey(p.x, p.y)] = p;
        });
        return out;
    }

    /**
     * Pure mirror of `engine/world_grid.ensure_grid` pruning, used by the editor's
     * resize dialog to warn how much paint/placement a shrink would drop.
     */
    function pruneGrid(payload: GridPayload, w: number, h: number): { paintKept: number; placementsKept: number } {
        const inBounds = (x: number, y: number) => x >= 0 && y >= 0 && x < w && y < h;
        const layers: Record<string, Record<string, any>> = {};
        Object.keys((payload && payload.layers) || {}).forEach((layer) => {
            const kept: Record<string, any> = {};
            Object.keys(payload.layers[layer]).forEach((key) => {
                const pos = parseCellKey(key);
                if (pos && inBounds(pos.x, pos.y)) kept[key] = payload.layers[layer][key];
            });
            if (Object.keys(kept).length) layers[layer] = kept;
        });
        const placements = ((payload && payload.placements) || [])
            .filter((p: any) => inBounds(p.x, p.y));
        return {
            paintKept: Object.keys(layers).reduce((n, l) => n + Object.keys(layers[l]).length, 0),
            placementsKept: placements.length,
        };
    }

    /**
     * How many areas + ways a painted grid would compile to, so the author sees
     * the node cost *before* minting it (a 5,000-cell paint is 5,000 areas plus
     * their passages, which is what makes the graph view choke).
     *
     * Mirrors `engine/world_compile.compile_grid`: every painted cell becomes an
     * area, whether it carries a biome, a road, or both (task-496 — a road cell
     * is a place in its own right, and the road *is* the cell's identity, so a
     * road painted over forest merges with other road cells but never with
     * forest). Without merge it is one area per cell and a way per adjacent pair
     * (8-neighbour, so diagonals connect), with merge it is one area per
     * same-identity flood-fill region. Each disconnected component beyond the
     * main one becomes one extra "link" way (an island joined to the nearest
     * cell).
     */
    function estimateCompile(payload: GridPayload, regionMerge?: boolean): any {
        const layers = (payload && payload.layers) || {};
        const biome = layers.biome || {};
        const road = layers.road || {};
        // Ordered (y, x) like the compiler's own cell order, so the estimate and
        // the mint agree on which region is "first" (the scope's entry area).
        const cells = Object.keys(biome).concat(Object.keys(road))
            .filter((k, i, all) => all.indexOf(k) === i)
            .sort((a, b) => {
                const pa = parseCellKey(a) || { x: 0, y: 0 };
                const pb = parseCellKey(b) || { x: 0, y: 0 };
                return (pa.y - pb.y) || (pa.x - pb.x);
            });
        if (!cells.length) return { areas: 0, ways: 0, total: 0, isolated: 0, links: 0 };
        // What *kind* of place a cell is: the road if painted, else the biome.
        const identity = (k: string) => {
            const r = road[k];
            if (r != null && r !== '') return `road:${r}`;
            return `biome:${biome[k]}`;
        };
        const present: Record<string, boolean> = {};
        cells.forEach((k) => { present[k] = true; });
        // A cell holding a hand-placed area is not compiled (task-528), so the
        // estimate has to drop it too — otherwise the header promises one more
        // area than Generate actually mints.
        const taken = Object.keys(areaMap(payload));
        taken.forEach((k) => { delete present[k]; });
        const liveCells = cells.filter((k) => present[k]);
        if (!liveCells.length) return { areas: 0, ways: 0, total: 0, isolated: 0, links: 0, placed: taken.length };
        // 8-neighbour deltas. The four "south half" ones (east, south, south-
        // east, south-west) count each shared pair exactly once; the full ring
        // is used for connectivity checks and region flood-fill.
        const at = (k: string, dx: number, dy: number) => {
            const p = parseCellKey(k);
            return p ? cellKey(p.x + dx, p.y + dy) : null;
        };
        const halfNeighbours = (k: string) => [at(k, 1, 0), at(k, 0, 1), at(k, 1, 1), at(k, -1, 1)];
        const ring = (k: string) => [at(k, 1, 0), at(k, -1, 0), at(k, 0, 1), at(k, 0, -1),
                             at(k, 1, 1), at(k, -1, 1), at(k, 1, -1), at(k, -1, -1)];

        // One region per cell, or a same-identity flood-fill (8-neighbour) region
        // under merge. Cells holding a placed child scope (placements) never merge
        // with adjacent same-biome cells so each placed feature stays its own area.
        const placedFeatures = featureMap(payload);
        const regionOf: Record<string, number> = {};
        let rid = 0;
        if (!regionMerge) {
            liveCells.forEach((k) => { regionOf[k] = rid++; });
        } else {
            liveCells.forEach((start) => {
                if (regionOf[start] != null) return;
                if (placedFeatures[start]) {
                    regionOf[start] = rid++;
                    return;
                }
                const kind = identity(start);
                const stack: string[] = [start];
                regionOf[start] = rid;
                while (stack.length) {
                    const k = stack.pop() as string;
                    ring(k).forEach((nk: string | null) => {
                        if (nk && present[nk] && !placedFeatures[nk] && regionOf[nk] == null && identity(nk) === kind) {
                            regionOf[nk] = rid;
                            stack.push(nk);
                        }
                    });
                }
                rid += 1;
            });
        }

        // One way per adjacent region pair (each pair counted once).
        const pairs: Record<string, boolean> = {};
        liveCells.forEach((k) => {
            halfNeighbours(k).forEach((nk) => {
                if (!nk || !present[nk] || regionOf[nk] === regionOf[k]) return;
                const a = regionOf[k];
                const b = regionOf[nk];
                pairs[`${Math.min(a, b)},${Math.max(a, b)}`] = true;
            });
        });
        const degree: Record<number, number> = {};
        Object.keys(pairs).forEach((key) => {
            const [a, b] = key.split(',').map(Number);
            degree[a] = (degree[a] || 0) + 1;
            degree[b] = (degree[b] || 0) + 1;
        });

        // The compiler joins every disconnected component but the main one with
        // a single way, so add (components - 1) links.
        const parent = Array.from({ length: rid }, (_, i) => i);
        const find = (i: number): number => {
            let j = i;
            while (parent[j] !== j) { parent[j] = parent[parent[j]]; j = parent[j]; }
            return j;
        };
        Object.keys(pairs).forEach((key) => {
            const [a, b] = key.split(',').map(Number);
            const ra = find(a);
            const rb = find(b);
            if (ra !== rb) parent[Math.max(ra, rb)] = Math.min(ra, rb);
        });
        const roots = new Set<number>();
        for (let i = 0; i < rid; i += 1) roots.add(find(i));
        const links = Math.max(0, roots.size - 1);

        let isolated = 0;
        for (let i = 0; i < rid; i += 1) if (!degree[i]) isolated += 1;
        const ways = Object.keys(pairs).length + links;
        return { areas: rid, ways, total: rid + ways, isolated, links };
    }

    function childrenAvailable(payload: GridPayload): any[] {
        return ((payload && payload.children) || []).filter((c: any) => !c.placed);
    }

    // ── placed areas (task-528) ────────────────────────────────────────────
    //
    // A placed area is an area node the author wrote by hand, parked on a cell
    // (`area_placements` in the payload). It is a different kind of occupant from
    // a child-scope placement: the node already exists in the graph, and the
    // compiler skips the cell so Generate cannot mint a second area on top.

    /** `{cellKey: area}` for every placed area, mirroring `featureMap`. */
    function areaMap(payload: GridPayload): Record<string, any> {
        const out: Record<string, any> = {};
        ((payload && payload.area_placements) || []).forEach((a: any) => {
            out[cellKey(a.x, a.y)] = a;
        });
        return out;
    }

    /** The area placed on a cell, or null. */
    function areaAt(payload: GridPayload, x: number, y: number): any {
        return areaMap(payload)[cellKey(x, y)] || null;
    }

    /** Where an area is placed on this grid, or null. */
    function areaPlacementFor(payload: GridPayload, areaId: string): any {
        return ((payload && payload.area_placements) || [])
            .find((a: any) => a.id === areaId) || null;
    }

    /**
     * Every area the place tool's picker offers, flattened across the scope
     * groups — the areas already on this grid, this scope's unplaced areas, and
     * the ones that belong to another scope. The editor renders the groups
     * (see :func:`areaGroups`); this is the flat view of the same list.
     */
    function placeableAreas(payload: GridPayload, selectedId?: string): any[] {
        const groups = areaGroups(payload, selectedId);
        return groups.reduce((all, g) => all.concat(g.areas), []);
    }

    /**
     * The picker grouped by scope (task-541).
     *
     * A flat list of every unplaced area in the world made a child scope's
     * interior show up in the *world* map's picker as if it belonged there, so
     * membership is what decides the grouping:
     *
     * 1. `placed`  — already parked on THIS grid (with their cell), still
     *    selectable so they can be moved to another cell.
     * 2. `mine`    — belongs to this scope and has no cell: the things you came
     *    here to place. An area with no scope at all counts as this scope's, since
     *    it belongs to nobody and this is the map being painted.
     * 3. `elsewhere` — a member of some *other* scope. Kept reachable, but under
     *    its own heading with that scope's name, because picking one is a
     *    membership change (task-539) and should not read as a placement.
     */
    function areaGroups(payload: GridPayload, selectedId?: string): any[] {
        const scopeId = (payload && payload.scope && payload.scope.id) || null;
        const placed = areaMap(payload);
        const byId: Record<string, any> = {};
        Object.keys(placed).forEach((k) => { byId[placed[k].id] = placed[k]; });
        const candidates = ((payload && payload.unplaced_areas) || []);
        const mine: any[] = [];
        const elsewhere: any[] = [];
        candidates.forEach((a: any) => {
            // The server already leaves placed areas out of `unplaced_areas`, but
            // an area on this grid belongs in the `placed` group only — never
            // listed twice.
            if (byId[a.id]) return;
            const entry = { ...a, placedHere: null };
            if (!a.scope_id || a.scope_id === scopeId) mine.push(entry);
            else elsewhere.push(entry);
        });
        const onGrid = (payload && payload.area_placements) || [];
        const groups: { key: string; label: string; areas: any[] }[] = [
            { key: 'placed', label: `On this grid (${onGrid.length})`, areas: onGrid.map(
                (a: any) => ({ id: a.id, name: a.name, x: a.x, y: a.y, scope_id: scopeId,
                           placedHere: { x: a.x, y: a.y } })) },
            { key: 'mine', label: `This scope, not placed (${mine.length})`, areas: mine },
            { key: 'elsewhere', label: 'Elsewhere in the world', areas: elsewhere },
        ];
        if (selectedId && !groups.some((g) => g.areas.some((a) => a.id === selectedId))) {
            // Never drop the selection out of the picker: the author has to be able
            // to move the area they already picked.
            const here = byId[selectedId];
            const known = candidates.find((a: any) => a.id === selectedId);
            if (!here) {
                const group = !known || !known.scope_id || known.scope_id === scopeId
                    ? groups[1] : groups[2];
                group.areas.push({ id: selectedId, name: known ? known.name : selectedId,
                                   scope_id: known ? known.scope_id : scopeId,
                                   placedHere: null });
                group.label = group.label.replace(/\(\d+\)/, `(${group.areas.length})`);
            }
        }
        return groups.filter((g) => g.areas.length);
    }

    /**
     * What is on a cell (task-540) — the payload half of the painter's cell
     * inspector, kept pure so it can be unit-tested without a canvas.
     *
     * Returns `{x, y, key, name, biome, road, floor, area, child, painted, empty}`:
     * the three paint layers (with `floor` as a numeric storey index — `null`
     * when the author painted no storey, which still counts as *painted* when it
     * is 0), the author-set **name** for the cell (task-560, `null` when unnamed),
     * the hand-placed area on the cell, and the child scope placed on it.
     * `empty` is true when nothing is there at all, which is the case the hover
     * readout needs to say "nothing here" instead of printing three empty fields.
     */
    function cellInfo(payload: GridPayload, x: number, y: number, vocab?: Vocabulary): any {
        const biome = cellValue(payload, 'biome', x, y) || null;
        const road = cellValue(payload, 'road', x, y) || null;
        const floor = floorNumber(cellValue(payload, 'floor', x, y));
        const area = areaAt(payload, x, y);
        // `feature` is the derived `{cellKey: child_scope_id}` view; the readable
        // card (name, kind, state) comes from the scope's own `placements` list.
        const childId = featureAt(payload, x, y);
        const card = (payload && payload.placements || []).find((c: any) => c.id === childId);
        const child = childId ? { id: childId, name: card ? card.name : childId,
                                  kind: card ? card.kind : null } : null;
        const name = cellName(payload, x, y);
        return {
            x, y,
            key: cellKey(x, y),
            name,
            biome, road, floor,
            // Structure, and what it is to movement (task-562). `null` for a cell
            // that will become a place, so the inspector can say "not a place"
            // instead of leaving the author to wonder why their wall is gone.
            // The vocabulary is passed in rather than read from `state`, so this
            // stays a pure function of its arguments and unit-testable.
            kind: cellKind(vocab, biome),
            // A building is entered with `in`, not walked onto (task-563). Null
            // for anything that is not a building, and for a road painted over a
            // building — the compiler does not treat that cell as one either.
            enter: cellEnter(vocab, road ? null : biome, child),
            area: area ? { id: area.id, name: area.name, x: area.x, y: area.y } : null,
            child,
            painted: Boolean(biome || road || floor !== null),
            empty: !biome && !road && floor === null && !name
                   && !area && !child,
        };
    }

    /**
     * What lies on the four cells touching (x, y) — the painter's answer to
     * "where is the exit from here?" (task-596). The ways a grid compiles into
     * join *adjacent* cells, so a cell's exits are exactly its passable
     * neighbours: a road, a door, open ground, or another building. A solid
     * neighbour (`wall`, `void`) is a wall to the author's face, not an exit.
     *
     * Pure and grid-bounded: an off-grid direction is `null`, not an error, so
     * the editor says "— map edge" rather than pretending the world ends in a
     * wall. Each entry is `{dir, x, y, biome, road, kind, name}`.
     */
    function cellNeighbours(payload: GridPayload, x: number, y: number, vocab?: Vocabulary): Record<string, any> {
        const grid = (payload && payload.grid) || {};
        const dirs: [string, number, number][] = [['N', 0, -1], ['E', 1, 0], ['S', 0, 1], ['W', -1, 0]];
        const out: Record<string, any> = {};
        dirs.forEach(([dir, dx, dy]) => {
            const nx = x + dx;
            const ny = y + dy;
            if (grid.w != null && (nx < 0 || ny < 0 || nx >= grid.w || ny >= grid.h)) {
                out[dir] = null;
                return;
            }
            const biome = cellValue(payload, 'biome', nx, ny) || null;
            const road = cellValue(payload, 'road', nx, ny) || null;
            out[dir] = {
                dir, x: nx, y: ny, biome, road,
                kind: cellKind(vocab, biome),
                name: cellName(payload, nx, ny),
            };
        });
        return out;
    }

    /**
     * The bounding box, in cells, of everything the author has put on the grid
     * (task-597) — paint, names, placed areas, placed scopes.
     *
     * The frame makes the grid's *extent* obvious but says nothing about how much
     * of it is used; a 160×100 region with one road in the corner looks identical
     * to a full one. Returns `null` when the grid is entirely empty, so the editor
     * draws no box rather than a box over nothing.
     */
    function paintedBounds(payload: GridPayload): Rect | null {
        if (!payload) return null;
        let minX = Infinity; let minY = Infinity;
        let maxX = -Infinity; let maxY = -Infinity;
        const put = (x: number, y: number) => {
            if (!Number.isFinite(x) || !Number.isFinite(y)) return;
            if (x < minX) minX = x;
            if (y < minY) minY = y;
            if (x > maxX) maxX = x;
            if (y > maxY) maxY = y;
        };
        const layers = payload.layers || {};
        Object.keys(layers).forEach((layer) => {
            Object.keys(layers[layer] || {}).forEach((k) => {
                const c = parseCellKey(k);
                if (c) put(c.x, c.y);
            });
        });
        Object.keys(payload.names || {}).forEach((k) => {
            const c = parseCellKey(k);
            if (c) put(c.x, c.y);
        });
        (payload.area_placements || []).forEach((a: any) => put(a.x, a.y));
        (payload.placements || []).forEach((a: any) => put(a.x, a.y));
        if (!Number.isFinite(minX)) return null;
        return { x: minX, y: minY, w: maxX - minX + 1, h: maxY - minY + 1 };
    }

    /**
     * The resize handles on the grid frame (task-597). The origin is fixed at
     * (0,0) — moving it would re-key every painted cell — so only the far edges
     * and the bottom-right corner can be dragged to grow or shrink the extent.
     * The near edges are deliberately absent rather than present-and-broken.
     */
    function gridHandlePoints(w: number, h: number): Record<string, Cell> {
        return {
            se: { x: w, y: h },
            e: { x: w, y: h / 2 },
            s: { x: w / 2, y: h },
        };
    }

    /** Snap a dragged resize handle to whole cells, never below 1×1 (task-597). */
    function gridHandleDrag(w: number, h: number, key: string, cell: Cell): { w: number; h: number } {
        let nw = w;
        let nh = h;
        if (key === 'e' || key === 'se') nw = Math.max(1, Math.round(cell.x));
        if (key === 's' || key === 'se') nh = Math.max(1, Math.round(cell.y));
        return { w: nw, h: nh };
    }

    /** How a painted cell is to movement, or null when it is a place (task-562). */
    function cellKind(vocab: Vocabulary, biomeId?: string | null): string | null {
        if (!biomeId) return null;
        const biome = ((vocab && vocab.biomes) || []).find((b: any) => b.id === biomeId);
        const tags = ((biome && biome.tags) || []).map((t: any) => String(t).toLowerCase());
        if (!tags.includes('not_a_place')) return null;
        for (const tag of tags) {
            if (tag.indexOf('cell_kind:') === 0) return tag.split(':')[1];
        }
        return 'solid';
    }

    /**
     * How a building cell is entered, or '' when it is not a building (task-563).
     *
     * A building is a place you go *into*: `in` from any side that has a way. With
     * a child scope on the cell, `in` leads to that interior; without one the door
     * is shut and the world answers with a refusal drawn from the building's
     * category. The vocabulary carries that sentence (`biomes[].refusal`, built by
     * the same `world_compile.building_refusal` the compiler uses), so the line
     * the author reads here is the line the world gives — one implementation
     * rather than two, which is the only way a preview stays true.
     */
    function cellEnter(vocab: Vocabulary, biomeId?: string | null, child?: any): string {
        if (!biomeId) return '';
        const biome = ((vocab && vocab.biomes) || []).find((b: any) => b.id === biomeId);
        const tags = ((biome && biome.tags) || []).map((t: any) => String(t).toLowerCase());
        if (!tags.includes('building')) return '';
        if (child) return `in → ${child.name || child.id}`;
        return biome && biome.refusal ? `in → ${biome.refusal}` : 'in';
    }

    /**
     * A grid whose aspect ratio matches a reference image (the `▦ match` button).
     *
     * The painter fits the image *into* the grid (contain, centred), so a grid
     * with a different ratio than the picture leaves empty bands — the painted
     * cells and the art then disagree about where the place is. Matching the
     * aspect removes the bands: the width is kept (it is what the author already
     * laid out horizontally) and the height is derived.
     *
     * Returns `null` for an image whose size is unknown, so the caller can say
     * "load an image first" instead of posting a nonsense grid. The height is
     * clamped to `[1, MAX_GRID_CELLS / w]`: a very wide picture on a narrow grid
     * would otherwise ask for a height of 0 (or a 1px sliver of a cell), and the
     * compiler would mint an absurd number of cells.
     */
    const MAX_GRID_CELLS = 20000;
    function gridForImageAspect(gridW: number, imgW: number, imgH: number): { w: number; h: number; cells: number; aspect: number } | null {
        const iw = Number(imgW) || 0;
        const ih = Number(imgH) || 0;
        if (iw <= 0 || ih <= 0) return null;
        const w = Math.max(1, Math.min(400, Number(gridW) || 160));
        const raw = Math.round(w * ih / iw);
        const h = Math.max(1, Math.min(MAX_GRID_CELLS, Math.floor(MAX_GRID_CELLS / w), raw));
        return { w, h, cells: w * h, aspect: iw / ih };
    }

    /**
     * A grid framed by the *size of a cell* rather than by a count (task-597).
     *
     * `px / cell` is the one number the author can actually see on the reference
     * image: its width divided by the number of columns. A count is the *inverse*
     * of that, so asking for one makes the author solve for the thing they care
     * about backwards. Both axes come from the same unit, so the grid's aspect is
     * the image's by construction and `▦ match` becomes this function's
     * degenerate case ("keep the width I already have").
     *
     * Returns `null` for an unreadable image or a non-positive cell size, so a
     * caller can say why instead of posting a nonsense grid. The clamps are
     * :func:`gridForImageAspect`'s: at least one cell per axis, at most 400
     * columns, and at most `MAX_GRID_CELLS` cells, so a 1px cell on a large map
     * cannot ask the compiler for a hundred thousand areas.
     */
    function gridForCellSize(imgW: number, imgH: number, pxPerCell: number):
        { w: number; h: number; cells: number; aspect: number; pxPerCell: number } | null {
        const iw = Number(imgW) || 0;
        const ih = Number(imgH) || 0;
        const px = Number(pxPerCell) || 0;
        if (iw <= 0 || ih <= 0 || px <= 0) return null;
        const w = Math.max(1, Math.min(400, Math.round(iw / px)));
        const h = Math.max(1, Math.min(MAX_GRID_CELLS, Math.floor(MAX_GRID_CELLS / w),
            Math.round(ih / px)));
        return { w, h, cells: w * h, aspect: iw / ih, pxPerCell: px };
    }

    /**
     * The `px / cell` the current grid already implies for this image, so a
     * control can open where the author left it instead of jumping to a default.
     * `null` when either number is missing.
     *
     * The unit is derived client-side and deliberately **not** persisted: the
     * stored grid stays `{w, h}`, and a scope whose reference image is swapped
     * gets a new cell size rather than a stale one baked into the save.
     */
    function cellSizeForGrid(imgW: number, gridW: number): number | null {
        const iw = Number(imgW) || 0;
        const gw = Number(gridW) || 0;
        if (iw <= 0 || gw <= 0) return null;
        return iw / gw;
    }

    /**
     * The `px / cell` range a control should offer: the smallest cell the clamps
     * permit through the largest that still changes anything.
     *
     * Both ends come from the same limits :func:`gridForCellSize` enforces, so a
     * slider cannot be dragged to a value whose grid is then silently clamped
     * underneath it. `null` for an unreadable image.
     */
    function cellSizeRange(imgW: number, imgH: number): { min: number; max: number } | null {
        const iw = Number(imgW) || 0;
        const ih = Number(imgH) || 0;
        if (iw <= 0 || ih <= 0) return null;
        // 400 columns is the widest grid; `MAX_GRID_CELLS` is the area cap, which
        // for a large image is the stricter of the two on the small end.
        const byWidth = iw / 400;
        const byArea = Math.sqrt((iw * ih) / MAX_GRID_CELLS);
        const min = Math.max(1, Math.ceil(Math.max(byWidth, byArea)));
        // A cell bigger than the shorter side is already one cell on that axis,
        // and nothing above it changes the grid.
        const max = Math.max(min + 1, Math.floor(Math.min(iw, ih)));
        return { min, max };
    }

    /**
     * Every painted cell, area placement and feature placement that a grid of
     * `{w, h}` would leave **outside** it (task-597): the author-facing answer to
     * "what would this shrink cost me?".
     *
     * One definition of "outside", so the number a warning shows and the cells the
     * canvas highlights cannot disagree. Entries are counted, not deduplicated: a
     * cell that is both painted and holds a feature loses two things when it goes.
     */
    function strandedCells(payload: GridPayload, w: number, h: number): { x: number; y: number; kind: string }[] {
        const nw = Number(w) || 0;
        const nh = Number(h) || 0;
        if (!payload || nw < 1 || nh < 1) return [];
        const out: { x: number; y: number; kind: string }[] = [];
        const outside = (x: number, y: number): boolean => x < 0 || y < 0 || x >= nw || y >= nh;
        Object.keys((payload.layers) || {}).forEach((layer) => {
            Object.keys(payload.layers[layer] || {}).forEach((key) => {
                const cell = parseCellKey(key);
                if (cell && outside(cell.x, cell.y)) out.push({ x: cell.x, y: cell.y, kind: 'paint' });
            });
        });
        ((payload.area_placements) || []).forEach((a: any) => {
            if (outside(a.x, a.y)) out.push({ x: a.x, y: a.y, kind: 'area' });
        });
        ((payload.placements) || []).forEach((a: any) => {
            if (outside(a.x, a.y)) out.push({ x: a.x, y: a.y, kind: 'feature' });
        });
        return out;
    }

    /**
     * How much of a grid's content would fall outside it if it were resized to
     * `{w, h}` — the number the `▦ match` button shows before it acts, because a
     * shrink *prunes* out-of-bounds paint and placements server-side
     * (`world_grid.ensure_grid`) rather than leaving them dangling.
     */
    function strandedCount(payload: GridPayload, w: number, h: number): number {
        return strandedCells(payload, w, h).length;
    }

    /**
     * Fit a reference image into a grid (contain, centred), in **cell** units.
     * Used when the reference has no stored rect (task-524).
     */
    function fitReferenceRect(gridW: number, gridH: number, imgW: number, imgH: number): Rect {
        const gw = Number(gridW) || 0;
        const gh = Number(gridH) || 0;
        const iw = Number(imgW) || gw || 1;
        const ih = Number(imgH) || gh || 1;
        const s = Math.min((gw || iw) / iw, (gh || ih) / ih);
        const w = iw * s;
        const h = ih * s;
        return { x: ((gw || w) - w) / 2, y: ((gh || h) - h) / 2, w, h };
    }

    /**
     * The eight handle anchors for a reference rect (cell units): corners
     * (`nw`/`ne`/`sw`/`se`) resize, edges (`n`/`e`/`s`/`w`) crop.
     */
    function referenceHandlePoints(rect: Rect): Record<string, Cell> {
        const x = rect.x, y = rect.y, w = rect.w, h = rect.h;
        return {
            nw: { x, y }, ne: { x: x + w, y }, sw: { x, y: y + h }, se: { x: x + w, y: y + h },
            n: { x: x + w / 2, y }, s: { x: x + w / 2, y: y + h },
            w: { x, y: y + h / 2 }, e: { x: x + w, y: y + h / 2 },
        };
    }

    /**
     * New `{rect, crop}` after dragging a handle to (cx, cy) in cell units.
     *
     * Corners resize the picture (the crop window is unchanged, so it scales).
     * Edges crop it: the dragged edge follows the pointer and the source window
     * shrinks proportionally, so the remaining content keeps its scale — a cut,
     * not a stretch. `crop` is normalized (0..1).
     */
    function referenceHandleDrag(rect: Rect, crop: Rect, key: string, cx: number, cy: number): { rect: Rect; crop: Rect } {
        const r = { x: rect.x, y: rect.y, w: rect.w, h: rect.h };
        const c = { x: crop.x, y: crop.y, w: crop.w, h: crop.h };
        if (key.length === 2) {
            const right = rect.x + rect.w;
            const bottom = rect.y + rect.h;
            if (key.indexOf('w') >= 0) { r.x = Math.min(cx, right - 0.5); r.w = right - r.x; }
            if (key.indexOf('e') >= 0) { r.w = Math.max(0.5, cx - rect.x); }
            if (key.indexOf('n') >= 0) { r.y = Math.min(cy, bottom - 0.5); r.h = bottom - r.y; }
            if (key.indexOf('s') >= 0) { r.h = Math.max(0.5, cy - rect.y); }
            return { rect: r, crop: c };
        }
        const fx = Math.min(0.95, Math.max(0.05, (cx - rect.x) / rect.w));
        const fy = Math.min(0.95, Math.max(0.05, (cy - rect.y) / rect.h));
        if (key === 'w') {
            r.x = rect.x + fx * rect.w; r.w = rect.w * (1 - fx);
            c.x = crop.x + fx * crop.w; c.w = crop.w * (1 - fx);
        } else if (key === 'e') {
            r.w = rect.w * fx; c.w = crop.w * fx;
        } else if (key === 'n') {
            r.y = rect.y + fy * rect.h; r.h = rect.h * (1 - fy);
            c.y = crop.y + fy * crop.h; c.h = crop.h * (1 - fy);
        } else if (key === 's') {
            r.h = rect.h * fy; c.h = crop.h * fy;
        }
        return { rect: r, crop: c };
    }

    // ── palette view-model (task-759) ───────────────────────────────────────
    // The palette the WorldPainter opens is a *view* over the vocabulary the
    // backend already serves (`handle_painter_vocabulary`). These helpers group,
    // filter and describe tiles with no DOM, so the editor renders and the unit
    // tests assert the same derivation. The rail is derived from the record's
    // own `terrain` + `tags` - never a hand-kept category list, which would be a
    // second taxonomy beside `biomes.json`.

    /** A vocabulary record as the painter receives it (see the route). */
    interface PaletteEntry {
        id?: string;
        name?: string;
        tags?: string[];
        descriptions?: string[];
        biomes?: string[];
        entry_phrase?: string;
        surface?: string;
        refusal?: string;
        terrain?: string;
        climate?: Record<string, number[]>;
        natural_neighbors?: string[];
        unlikely_neighbors?: string[];
        transition_biomes?: string[];
    }

    type PaletteTileKind = 'place' | 'building' | 'not-a-place' | 'road' | 'climate';

    interface PaletteTile {
        id: string;
        name: string;
        kind: PaletteTileKind;
        rec: PaletteEntry;
    }

    /** One rail entry: a run of tiles under a stable, derived heading. */
    interface PaletteSection {
        id: string;
        label: string;
        tiles: PaletteTile[];
    }

    // The wild-terrain order a reader expects: the ground you walk, then the
    // water you cross, then the stone you climb, then the worked land.
    const TERRAIN_ORDER = ['forest', 'grass', 'water', 'rock', 'coast', 'farm'];
    const TERRAIN_LABELS: Record<string, string> = {
        forest: 'Forest', grass: 'Grassland', water: 'Water', rock: 'Rock & mountains',
        coast: 'Coast', farm: 'Farmland', urban: 'Built', indoor: 'Indoor',
    };
    // A room's purpose, in the order a plan is drawn (task-568): arrive, move,
    // then the rooms you pass. Mirrors the grouping the painter shipped.
    const ROOM_PURPOSES = ['circulation', 'living', 'sleeping', 'cooking', 'eating',
        'storage', 'workshop', 'worship', 'records', 'study', 'trade', 'civic',
        'service', 'outdoor'];
    const BUILDING_CATEGORIES = ['residential', 'religious', 'commercial', 'civic',
        'craft', 'industrial', 'military', 'rural', 'transport'];
    const titleCase = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1);

    function tileKind(layer: string, rec: PaletteEntry): PaletteTileKind {
        if (layer === 'road') return 'road';
        if (layer === 'climate') return 'climate';
        const tags = (rec.tags || []).map((t) => String(t).toLowerCase());
        if (tags.includes('not_a_place')) return 'not-a-place';
        if (tags.includes('building')) return 'building';
        return 'place';
    }

    /**
     * One line describing a tile (task-596): what it is, and what it does, from
     * the same record the compiler reads. `Bridge - A span... · crosses river,
     * ravine · "cross the bridge"` versus `Road - A worn track...`.
     */
    function tileDetail(layer: string, rec: PaletteEntry): string {
        const name = rec.name || rec.id || '';
        const desc = ((rec.descriptions || [])[0]) || '';
        if (layer === 'road') {
            const bits = [desc];
            if ((rec.biomes || []).length) bits.push('crosses ' + (rec.biomes || []).join(', '));
            if (rec.entry_phrase) bits.push('\u201c' + rec.entry_phrase + '\u201d');
            return (name + ' - ' + bits.filter(Boolean).join(' \u00b7 ')).replace(/ - $/, '');
        }
        if (layer === 'biome') {
            const tags = (rec.tags || []).map((t) => String(t).toLowerCase());
            let kind = 'place';
            if (tags.includes('not_a_place')) {
                const ck = tags.find((t) => t.indexOf('cell_kind:') === 0) || 'cell_kind:solid';
                kind = 'not a place (' + (ck.split(':')[1] || 'solid') + ')';
            } else if (tags.includes('building')) {
                kind = 'building';
            }
            const bits = [desc, kind];
            if (rec.surface) bits.push('ground ' + rec.surface);
            if (rec.refusal) bits.push(rec.refusal);
            return name + ' - ' + bits.filter(Boolean).join(' \u00b7 ');
        }
        return (name + ' - ' + desc).replace(/ - $/, '');
    }

    /** Labelled rows for the palette's detail panel; absent fields are omitted. */
    function detailRows(layer: string, rec: PaletteEntry): { label: string; value: string }[] {
        const rows: { label: string; value: string }[] = [];
        const push = (label: string, value?: string | string[] | null): void => {
            const v = Array.isArray(value) ? value.filter(Boolean).join(', ') : (value || '');
            if (v) rows.push({ label, value: String(v) });
        };
        const descs = (rec.descriptions || []).filter(Boolean);
        if (descs.length) push('About', descs.join(' '));
        if (layer === 'biome') {
            push('Kind', tileKind(layer, rec).replace('-', ' '));
            push('Ground', rec.surface);
            push('Crosses', rec.biomes);
            push('Door', rec.refusal);
            // Descriptive climate + adjacency (task-758); present only once a
            // record is authored, so an un-authored one shows nothing here.
            const climate = rec.climate || {};
            const parts: string[] = [];
            ['temperature', 'rainfall', 'elevation'].forEach((f) => {
                const r = climate[f];
                if (Array.isArray(r) && r.length === 2) parts.push(f + ' ' + r[0] + '\u2013' + r[1]);
            });
            push('Climate', parts);
            push('Near', rec.natural_neighbors);
            push('Unlikely', rec.unlikely_neighbors);
            push('Transitions', rec.transition_biomes);
        } else if (layer === 'road') {
            push('Crosses', rec.biomes);
            push('Arrive', rec.entry_phrase);
        }
        push('Tags', rec.tags);
        return rows;
    }

    // Memoize paletteSections by (layer, entry-id signature) so repeated calls
    // across renders and value changes return the cached grouping (task-776).
    const _paletteSectionsMemo = new Map<string, PaletteSection[]>();

    /**
     * Group the layer's records into rail sections. Derived entirely from each
     * record's `terrain` and `tags`:
     *   - not-a-place -> Structure
     *   - indoor -> one section per room purpose
     *   - building -> one section per building category
     *   - everything else -> one section per `terrain`
     * A layer without groups (road/climate) is a single section.
     */
    function paletteSections(layer: string, entries: PaletteEntry[]): PaletteSection[] {
        const list = entries || [];
        const sig = layer + ':' + list.map((e) => (e && e.id) || '').join(',');
        const cached = _paletteSectionsMemo.get(sig);
        if (cached && list.length > 0 && cached.reduce((n, s) => n + s.tiles.length, 0) === list.filter((e) => e && e.id).length) {
            return cached;
        }
        const tiles: PaletteTile[] = list.filter((e) => e && e.id)
            .map((e) => ({ id: String(e.id), name: e.name || String(e.id), kind: tileKind(layer, e), rec: e }));
        if (layer !== 'biome') {
            const only: PaletteSection = { id: layer, label: titleCase(layer), tiles };
            const res = tiles.length ? [only] : [];
            _paletteSectionsMemo.set(sig, res);
            return res;
        }
        const byId = new Map<string, PaletteSection>();
        const order: string[] = [];
        const put = (id: string, label: string, t: PaletteTile): void => {
            if (!byId.has(id)) { byId.set(id, { id, label, tiles: [] }); order.push(id); }
            byId.get(id)!.tiles.push(t);
        };
        for (const t of tiles) {
            const tags = (t.rec.tags || []).map((x) => String(x).toLowerCase());
            if (tags.includes('not_a_place')) { put('structure', 'Structure', t); continue; }
            if (tags.includes('indoor')) {
                const purpose = ROOM_PURPOSES.find((p) => tags.includes(p)) || 'other';
                put('room:' + purpose, 'Rooms \u00b7 ' + titleCase(purpose), t);
                continue;
            }
            if (tags.includes('building')) {
                const cat = BUILDING_CATEGORIES.find((c) => tags.includes(c)) || 'other';
                put('building:' + cat, 'Buildings \u00b7 ' + titleCase(cat), t);
                continue;
            }
            const terrain = String(t.rec.terrain || 'other').toLowerCase();
            put('terrain:' + terrain, TERRAIN_LABELS[terrain] || titleCase(terrain), t);
        }
        // Stable rail order: wild terrain first, then rooms, then buildings, then
        // structure - a plan is where terrain gives way to rooms and buildings.
        const rank = (id: string): number => {
            if (id.indexOf('terrain:') === 0) {
                const i = TERRAIN_ORDER.indexOf(id.slice(8));
                return i < 0 ? TERRAIN_ORDER.length : i;
            }
            if (id.indexOf('room:') === 0) return 100 + Math.max(0, ROOM_PURPOSES.indexOf(id.slice(5)));
            if (id.indexOf('building:') === 0) return 200 + Math.max(0, BUILDING_CATEGORIES.indexOf(id.slice(9)));
            return 300;
        };
        const res = order.sort((a, b) => rank(a) - rank(b)).map((id) => byId.get(id)!);
        _paletteSectionsMemo.set(sig, res);
        return res;
    }

    /**
     * Which rail sections a scope mode does not offer (task-774).
     *
     * A world map paints terrain, so room and building tiles are noise there
     * (53 of the 106 biome records are indoor, 32 are buildings). A town paints
     * buildings and streets but not floor-plan rooms, except the `outdoor`
     * purpose (porch, courtyard, balcony), which are open space a town uses.
     * Interior scopes are left unfiltered: no evidence yet of which terrain an
     * interior legitimately paints. Structure (walls, solids) is never hidden.
     * Matching is by section id prefix, so it follows `paletteSections`' own
     * grouping and is not a second category list.
     */
    const MODE_HIDDEN_SECTIONS: Record<string, string[]> = {
        world: ['room:', 'building:'],
        town: ['room:'],
    };
    const MODE_KEPT_SECTIONS: Record<string, string[]> = {
        town: ['room:outdoor'],
    };

    /** Drop the sections a map mode has no use for. Unknown or missing mode is a no-op. */
    function paletteForMode(sections: PaletteSection[], mode?: string | null): PaletteSection[] {
        const hidden = MODE_HIDDEN_SECTIONS[String(mode || '')];
        if (!hidden) return sections;
        const kept = MODE_KEPT_SECTIONS[String(mode)] || [];
        return sections.filter((s) =>
            kept.includes(s.id) || !hidden.some((prefix) => s.id.indexOf(prefix) === 0));
    }

    /** Search sections by name or id; empty sections are dropped. */
    function filterPalette(sections: PaletteSection[], needle: string): PaletteSection[] {
        const n = String(needle || '').trim().toLowerCase();
        if (!n) return sections;
        const hit = (t: PaletteTile): boolean =>
            t.name.toLowerCase().indexOf(n) >= 0 || t.id.toLowerCase().indexOf(n) >= 0;
        return sections
            .map((s) => ({ id: s.id, label: s.label, tiles: s.tiles.filter(hit) }))
            .filter((s) => s.tiles.length);
    }

    /** Every tile, in rail order - the default-value and keyboard path. */
    function flattenPalette(sections: PaletteSection[]): PaletteTile[] {
        const out: PaletteTile[] = [];
        for (const s of sections) for (const t of s.tiles) out.push(t);
        return out;
    }

    function paletteTile(sections: PaletteSection[], id: string): PaletteTile | null {
        for (const s of sections) for (const t of s.tiles) if (t.id === id) return t;
        return null;
    }

    const COMPASS_8_OFFSETS = [
        { dx: 1, dy: 0 },   // 0: East
        { dx: 1, dy: 1 },   // 1: Southeast
        { dx: 0, dy: 1 },   // 2: South
        { dx: -1, dy: 1 },  // 3: Southwest
        { dx: -1, dy: 0 },  // 4: West
        { dx: -1, dy: -1 }, // 5: Northwest
        { dx: 0, dy: -1 },  // 6: North
        { dx: 1, dy: -1 },  // 7: Northeast
    ];
    const COMPASS_8_BEARINGS = ['e', 'se', 's', 'sw', 'w', 'nw', 'n', 'ne'];

    function isWaterCell(payload: any, x: number, y: number, vocab?: any): boolean {
        const bId = cellValue(payload, 'biome', x, y);
        if (!bId) return false;
        const bStr = String(bId).toLowerCase();
        if (bStr.includes('river') || bStr.includes('water') || bStr.includes('lake') ||
            bStr.includes('ocean') || bStr.includes('stream') || bStr.includes('rapids') ||
            bStr.includes('waterfall') || bStr.includes('sea')) {
            return true;
        }
        if (vocab && Array.isArray(vocab.biomes)) {
            const b = vocab.biomes.find((v: any) => v.id === bId);
            if (b) {
                if (b.terrain === 'water') return true;
                if (b.surface === 'shallow_water' || b.surface === 'deep_water') return true;
                const tags = (b.tags || []).map((t: any) => String(t).toLowerCase());
                if (tags.some((t: string) => ['water', 'river', 'stream', 'lake', 'ocean', 'rapids', 'waterfall'].includes(t))) {
                    return true;
                }
            }
        }
        return false;
    }

    function slopeToCurrentStrength(dropStoreys: number): number {
        if (dropStoreys <= 0) return 1;
        if (dropStoreys === 1) return 5;
        if (dropStoreys === 2 || dropStoreys === 3) return 10;
        return 20;
    }

    function deriveWaterCurrent(payload: any, x: number, y: number, vocab?: any): any {
        if (!isWaterCell(payload, x, y, vocab)) return null;

        const layers = payload?.layers || {};
        const currentLayer = layers.current || {};
        const key = cellKey(x, y);
        let manual: any = null;
        if (key in currentLayer) {
            const val = currentLayer[key];
            if (val && typeof val === 'object') manual = val;
            else if (typeof val === 'number') manual = { strength: val, direction: 0 };
        }

        const bId = cellValue(payload, 'biome', x, y);
        let bHazard: string | null = null;
        if (vocab && Array.isArray(vocab.biomes)) {
            const b = vocab.biomes.find((v: any) => v.id === bId);
            if (b && b.hazard_id) bHazard = String(b.hazard_id);
        }

        if (manual !== null) {
            const s = Math.max(1, Math.min(20, Number(manual.strength) || 5));
            const d = (Number(manual.direction) || 0) % 8;
            return {
                direction: d,
                bearing: COMPASS_8_BEARINGS[d],
                strength: s,
                drop: 0,
                hazard_id: manual.hazard_id || bHazard || 'river',
                slope_percent: 0.0,
                manual_override: true,
            };
        }

        const z0 = tileFloor(payload, x, y);
        let bestDrop = -999999;
        let bestIdx = 0;
        let bestDist = 80.0;
        let downstreamFound = false;

        for (let i = 0; i < COMPASS_8_OFFSETS.length; i++) {
            const off = COMPASS_8_OFFSETS[i];
            const nx = x + off.dx;
            const ny = y + off.dy;
            if (!isWaterCell(payload, nx, ny, vocab)) continue;
            const nz = tileFloor(payload, nx, ny);
            const drop = z0 - nz;
            const dist = (off.dx === 0 || off.dy === 0) ? 80.0 : (80.0 * 1.41421356);
            if (drop > 0) {
                downstreamFound = true;
                const grad = drop / dist;
                const bestGrad = bestDrop > 0 ? (bestDrop / bestDist) : -1.0;
                if (grad > bestGrad) {
                    bestDrop = drop;
                    bestIdx = i;
                    bestDist = dist;
                }
            } else if (!downstreamFound && drop === 0 && bestDrop < 0) {
                bestDrop = 0;
                bestIdx = i;
                bestDist = dist;
            }
        }

        if (bestDrop < 0) {
            bestDrop = 0;
            bestIdx = 0;
            bestDist = 80.0;
        }

        const strength = slopeToCurrentStrength(bestDrop);
        const slopePct = bestDrop > 0 ? (bestDrop * 3.0 / bestDist) * 100.0 : 0.0;

        let hazardId: string | null = null;
        if (bestDrop >= 4 || bId === 'waterfall') hazardId = 'fall';
        else if (bestDrop === 2 || bestDrop === 3 || bId === 'river_rapids') hazardId = 'rapids';
        else if (bHazard) hazardId = bHazard;
        else if (bestDrop === 1 || bId === 'river_swift' || bId === 'river') hazardId = 'river';
        else hazardId = null;

        return {
            direction: bestIdx,
            bearing: COMPASS_8_BEARINGS[bestIdx],
            strength,
            drop: Math.max(0, bestDrop),
            hazard_id: hazardId,
            slope_percent: Number(slopePct.toFixed(2)),
            manual_override: false,
        };
    }

    const gridModel = {
        MODES, PAINT_LAYERS, BIOME_COLORS, ROAD_COLORS,
        CLIMATES, CLIMATE_IDS, DEFAULT_CLIMATE, useClimatesFromVocab,
        cellKey, parseCellKey, cellId, nextMode, layerColor,
        floorNumber, floorLabel,
        metresToStoreys, storeysToMetres, luminanceToMetres, metresToLuminance, climbGatedSteps,
        lineCells, routeCells, routeStats, estimateCompile,
        supercoverLine, tileHeight, tileObscurity, castSightRay, computeVisibleCells,
        isWaterCell, slopeToCurrentStrength, deriveWaterCurrent,
        cellValue, cellName, cellKind, cellEnter, cellNeighbours, featureAt, placementFor,
        paintedBounds, gridHandlePoints, gridHandleDrag,
        buildRows, featureMap,
        pruneGrid, childrenAvailable,
        areaMap, areaAt, areaPlacementFor, placeableAreas, areaGroups, cellInfo,
        fitReferenceRect, gridForImageAspect, gridForCellSize, cellSizeForGrid,
        cellSizeRange, strandedCount, strandedCells,
        referenceHandlePoints, referenceHandleDrag,
        tileKind, tileDetail, detailRows,
        paletteSections, paletteForMode, filterPalette, flattenPalette, paletteTile,
    };
    // main.js (loaded last) does `window.VW = {}` and re-registers singletons, so
    // the bare global is what survives; VW.gridModel is (re)attached there too.
    (window as unknown as { gridModel: unknown }).gridModel = gridModel;
    window.VW = window.VW || {};
    (window.VW as Record<string, unknown>).gridModel = gridModel;
})();
