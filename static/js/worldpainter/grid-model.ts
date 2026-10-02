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
 * @contributes cell keys, drill-down mode suggestion, render rows, layer colours, storey reads, cell names, placed areas, compile estimate, cell inspector, scope-grouped area picker
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
    const PAINT_LAYERS = ['biome', 'road', 'floor', 'climate'];

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
        if (n === null) return '—';
        if (n === 0) return 'ground (0)';
        return n > 0 ? `floor ${n}` : `${-n} below ground (${n})`;
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
        // under merge.
        const regionOf: Record<string, number> = {};
        let rid = 0;
        if (!regionMerge) {
            liveCells.forEach((k) => { regionOf[k] = rid++; });
        } else {
            liveCells.forEach((start) => {
                if (regionOf[start] != null) return;
                const kind = identity(start);
                const stack: string[] = [start];
                regionOf[start] = rid;
                while (stack.length) {
                    const k = stack.pop() as string;
                    ring(k).forEach((nk: string | null) => {
                        if (nk && present[nk] && regionOf[nk] == null && identity(nk) === kind) {
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
     * How much of a grid's content would fall outside it if it were resized to
     * `{w, h}` — the number the `▦ match` button shows before it acts, because a
     * shrink *prunes* out-of-bounds paint and placements server-side
     * (`world_grid.ensure_grid`) rather than leaving them dangling.
     */
    function strandedCount(payload: GridPayload, w: number, h: number): number {
        const nw = Number(w) || 0;
        const nh = Number(h) || 0;
        if (!payload || nw < 1 || nh < 1) return 0;
        let count = 0;
        Object.keys((payload.layers) || {}).forEach((layer) => {
            Object.keys(payload.layers[layer] || {}).forEach((key) => {
                const cell = parseCellKey(key);
                if (!cell) return;
                if (cell.x < 0 || cell.y < 0 || cell.x >= nw || cell.y >= nh) count += 1;
            });
        });
        ((payload.area_placements) || []).forEach((a: any) => {
            if (a.x < 0 || a.y < 0 || a.x >= nw || a.y >= nh) count += 1;
        });
        ((payload.placements) || []).forEach((a: any) => {
            if (a.x < 0 || a.y < 0 || a.x >= nw || a.y >= nh) count += 1;
        });
        return count;
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

    const gridModel = {
        MODES, PAINT_LAYERS, BIOME_COLORS, ROAD_COLORS,
        CLIMATES, CLIMATE_IDS, DEFAULT_CLIMATE, useClimatesFromVocab,
        cellKey, parseCellKey, cellId, nextMode, layerColor,
        floorNumber, floorLabel,
        lineCells, routeCells, routeStats, estimateCompile,
        cellValue, cellName, cellKind, cellEnter, cellNeighbours, featureAt, placementFor,
        paintedBounds, gridHandlePoints, gridHandleDrag,
        buildRows, featureMap,
        pruneGrid, childrenAvailable,
        areaMap, areaAt, areaPlacementFor, placeableAreas, areaGroups, cellInfo,
        fitReferenceRect, gridForImageAspect, strandedCount,
        referenceHandlePoints, referenceHandleDrag,
    };
    // main.js (loaded last) does `window.VW = {}` and re-registers singletons, so
    // the bare global is what survives; VW.gridModel is (re)attached there too.
    (window as unknown as { gridModel: unknown }).gridModel = gridModel;
    window.VW = window.VW || {};
    (window.VW as Record<string, unknown>).gridModel = gridModel;
})();
