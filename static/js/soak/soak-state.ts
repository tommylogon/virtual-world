/**
 * @module soak-state — the Soak Lab store: config, run list, incremental polling
 * @contributes single-source app state, cursor-based sample/event merging, poll lifecycle, run selection, telemetry cache
 * @powers live progress, run history, character/report loading, compare + export data access, the space-time view
 * @relates consumes soak-api.js; observed by soak-ui.js and seeded by soak-app.js
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

/**
 * Shapes the soak lab's REST payloads produce (see routes/soak*.py) and this
 * store merges. `deaths`, `events`, `samples` and `characters` stay `unknown[]`
 * on purpose: the lab renders them through per-view readers in soak-ui.js, and
 * naming the element type here would freeze a payload shape this file never reads.
 */
interface SoakSample { vitals?: Record<string, unknown>; [key: string]: unknown; }

interface SoakRunSummary {
    id: string;
    status?: string;
    [key: string]: unknown;
}

/** `tick` is compared unguarded in applySnapshot, so it is typed as always present. */
interface SoakProgress { tick: number; [key: string]: unknown; }

interface SoakSnapshot {
    run?: SoakRunSummary | null;
    progress?: SoakProgress | null;
    samples?: SoakSample[] | null;
    deaths?: unknown[] | null;
    events?: unknown[] | null;
    next_since?: number;
    next_event_since?: number;
    finished?: boolean;
}

interface SoakMeta {
    defaults?: SoakStateSoakRunConfig;
    core_vitals?: string[];
    scenarios?: unknown[];
    [key: string]: unknown;
}

interface SoakReport { summary?: unknown; [key: string]: unknown; }

interface SoakStateSoakRunConfig { [key: string]: unknown; }

interface SoakRunData {
    run: SoakRunSummary | null;
    progress: SoakProgress | null;
    samples: SoakSample[];
    deaths: unknown[];
    events: unknown[];
    nextSince: number;
    nextEventSince: number;
    characters: unknown[];
    summary: unknown;
    report: SoakReport | null;
    finished: boolean;
}

interface SoakLabState {
    meta: SoakMeta | null;
    runs: SoakRunSummary[];
    selectedRunId: string | null;
    serverActiveRunId: string | null;
    config: SoakStateSoakRunConfig;
    pollingPaused: boolean;
    data: SoakRunData | null; // per-run view model, see _blankData()
    lastError: string | null;
}

type SoakListener = (type: string, payload?: unknown) => void;

interface SoakApiClient {
    meta(): Promise<unknown>;
    listRuns(): Promise<unknown>;
    getRun(id: string, since?: number, eventSince?: number): Promise<unknown>;
    startRun(config: SoakStateSoakRunConfig): Promise<unknown>;
    stopRun(id: string): Promise<unknown>;
    deleteRun(id: string): Promise<unknown>;
    report(id: string, opts?: { download?: boolean; samples?: boolean }): Promise<unknown>;
    characters(id: string): Promise<unknown>;
    characterSeries(id: string, name: string): Promise<unknown>;
    samples(id: string): Promise<unknown>;
    events(id: string): Promise<unknown>;
    telemetry(id: string, withEvents?: boolean): Promise<unknown>;
}

// soak-api.js and soak-format.js are classic-script singletons that globals.d.ts
// does not declare. They are reached through a local cast at each use site — the
// alternative, a cached `_api()` binding, would add a value statement to the
// emitted classic script and a global name this module never had.
type SoakWin = {
    SoakApi: SoakApiClient;
    SoakFormat: { queryToConfig(search: string): SoakStateSoakRunConfig | null };
};

(function () {
    'use strict';

    const listeners: SoakListener[] = [];
    const SERIES_CACHE = new Map<string, unknown>();

    const state: SoakLabState = {
        meta: null,
        runs: [],
        selectedRunId: null,
        serverActiveRunId: null,
        config: {},
        pollingPaused: false,
        data: null, // per-run view model, see _blankData()
        lastError: null,
    };

    function _blankData(): SoakRunData {
        return {
            run: null,
            progress: null,
            samples: [],
            deaths: [],
            events: [],
            nextSince: 0,
            nextEventSince: 0,
            characters: [],
            summary: null,
            report: null,
            finished: false,
        };
    }

    function on(fn: SoakListener): void { listeners.push(fn); }
    function emit(type: string, payload?: unknown): void {
        listeners.forEach((fn) => {
            try { fn(type, payload); } catch (err) { console.error('[soak] listener', err); }
        });
    }

    // ── meta / config ──

    async function init(): Promise<unknown> {
        const meta = await (window as unknown as SoakWin).SoakApi.meta() as SoakMeta;
        state.meta = meta;
        const fromUrl = (window as unknown as SoakWin).SoakFormat.queryToConfig(window.location.search);
        state.config = Object.assign({}, meta.defaults, fromUrl || {});
        emit('meta', meta);
        await refreshRuns();
        const params = new URLSearchParams(window.location.search);
        const wanted = params.get('run');
        const target = wanted || state.serverActiveRunId
            || (state.runs.length ? state.runs[0].id : null);
        if (target) await selectRun(target);
        return meta;
    }

    function setConfig(patch: Partial<SoakStateSoakRunConfig>): void {
        state.config = Object.assign({}, state.config, patch);
        emit('config', state.config);
    }

    function getConfig(): SoakStateSoakRunConfig { return Object.assign({}, state.config); }

    function coreVitals(): string[] {
        const seen = new Set<string>(state.meta ? state.meta.core_vitals : []);
        if (state.data) {
            state.data.samples.forEach((s: SoakSample) => Object.keys(s.vitals || {}).forEach((k) => seen.add(k)));
        }
        return [...seen];
    }

    // ── runs ──

    async function refreshRuns(): Promise<SoakRunSummary[]> {
        const body = await (window as unknown as SoakWin).SoakApi.listRuns() as { runs?: SoakRunSummary[]; active_run_id?: string | null };
        state.runs = body.runs || [];
        state.serverActiveRunId = body.active_run_id || null;
        emit('runs', state.runs);
        return state.runs;
    }

    async function start(): Promise<SoakRunSummary> {
        const snapshot = await (window as unknown as SoakWin).SoakApi.startRun(state.config) as { run: SoakRunSummary };
        await refreshRuns();
        await selectRun(snapshot.run.id);
        return snapshot.run;
    }

    async function stop(id?: string | null): Promise<SoakSnapshot | null> {
        const target = id || state.selectedRunId || state.serverActiveRunId;
        if (!target) return null;
        await (window as unknown as SoakWin).SoakApi.stopRun(target);
        await refreshRuns();
        // The stop response can be staler than a poll that already observed the
        // terminal state, so re-read the run and apply the freshest snapshot.
        const d = state.data;
        const snapshot = await (window as unknown as SoakWin).SoakApi.getRun(
            target, d ? d.nextSince : 0, d ? d.nextEventSince : 0) as SoakSnapshot;
        await applySnapshot(snapshot);
        if (snapshot.finished) {
            stopTimer('stopped');
            await loadFinal(target);
        } else {
            startTimer();
        }
        return snapshot;
    }

    async function removeRun(id: string): Promise<void> {
        await (window as unknown as SoakWin).SoakApi.deleteRun(id);
        if (state.selectedRunId === id) {
            state.selectedRunId = null;
            state.data = null;
            stopTimer();
            emit('data', null);
        }
        SERIES_CACHE.delete(id);
        await refreshRuns();
    }

    async function selectRun(id: string): Promise<SoakRunData | null> {
        if (state.selectedRunId !== id) {
            state.data = _blankData();
            state.data.run = state.runs.find((r) => r.id === id) || { id };
            emit('data', state.data);
        }
        state.selectedRunId = id;
        const snapshot = await (window as unknown as SoakWin).SoakApi.getRun(id, 0, 0) as SoakSnapshot;
        await applySnapshot(snapshot);
        if (snapshot.finished) {
            await loadFinal(id);
        } else {
            startTimer();
        }
        return state.data;
    }

    function selected(): SoakRunData | null { return state.data; }
    function selectedRun(): SoakRunSummary | null { return state.data && state.data.run; }

    // ── polling ──

    let timer: ReturnType<typeof setInterval> | null = null;
    let inFlight = false;
    let listTick = 0;

    function startTimer(): void {
        if (timer) return;
        timer = setInterval(tick, 450);
    }

    function stopTimer(reason?: string): void {
        if (timer) {
            if (reason === 'error') console.error('[soak] polling stopped after error', debug());
            clearInterval(timer);
            timer = null;
        }
    }

    async function tick(): Promise<void> {
        if (inFlight || state.pollingPaused) return;
        const id = state.selectedRunId;
        if (!id) { stopTimer('no selected run'); return; }
        inFlight = true;
        try {
            const since = state.data ? state.data.nextSince : 0;
            const eventSince = state.data ? state.data.nextEventSince : 0;
            const snapshot = await (window as unknown as SoakWin).SoakApi.getRun(id, since, eventSince) as SoakSnapshot;
            await applySnapshot(snapshot);
            listTick += 1;
            if (listTick % 6 === 0 || snapshot.finished) await refreshRuns();
            if (snapshot.finished) {
                stopTimer('finished');
                await loadFinal(id);
                await refreshRuns();
            }
        } catch (err) {
            // Original spelling kept: a thrown non-Error has always yielded
            // `undefined` here, and lastError is only read for diagnostics.
            state.lastError = (err as Error).message;
            console.error('[soak] poll failed', err);
            emit('error', err);
            stopTimer('error');
        } finally {
            inFlight = false;
        }
    }

    async function applySnapshot(snapshot: SoakSnapshot | null | undefined): Promise<void> {
        if (!snapshot) return;
        if (state.selectedRunId && snapshot.run && snapshot.run.id !== state.selectedRunId) return;
        // Never let a late/stale response walk the view backwards; once a run is
        // terminal it stays terminal.
        const existing = state.data;
        if (existing && existing.progress && snapshot.progress
                && snapshot.progress.tick < existing.progress.tick) return;
        const data = state.data || (state.data = _blankData());
        data.run = snapshot.run || data.run;
        data.progress = snapshot.progress || data.progress;
        if (snapshot.samples && snapshot.samples.length) {
            data.samples = data.samples.concat(snapshot.samples);
        }
        data.nextSince = snapshot.next_since !== undefined ? snapshot.next_since : data.nextSince;
        if (snapshot.events && snapshot.events.length) {
            data.events = data.events.concat(snapshot.events).slice(-4000);
        }
        data.nextEventSince = snapshot.next_event_since !== undefined
            ? snapshot.next_event_since : data.nextEventSince;
        if (snapshot.deaths) data.deaths = snapshot.deaths;
        data.finished = !!snapshot.finished;
        emit('data', data);
        if (snapshot.events && snapshot.events.length) emit('events', snapshot.events);
        if (snapshot.samples && snapshot.samples.length) emit('samples', snapshot.samples);
    }

    async function loadFinal(id: string): Promise<void> {
        try {
            const [report, chars] = await Promise.all([
                (window as unknown as SoakWin).SoakApi.report(id), (window as unknown as SoakWin).SoakApi.characters(id),
            ]) as [SoakReport, { characters?: unknown[] }];
            if (state.selectedRunId !== id || !state.data) return;
            state.data.report = report;
            state.data.summary = report.summary;
            state.data.characters = (chars.characters || []) as never[];
            emit('report', report);
            emit('data', state.data);
        } catch (err) {
            emit('error', err);
        }
    }

    async function loadCharacters(): Promise<unknown[]> {
        const id = state.selectedRunId;
        if (!id || !state.data) return [];
        if (state.data.characters.length) return state.data.characters;
        const chars = await (window as unknown as SoakWin).SoakApi.characters(id) as { characters?: unknown[] };
        state.data.characters = (chars.characters || []) as never[];
        emit('data', state.data);
        return state.data.characters;
    }

    async function characterSeries(name: string): Promise<unknown> {
        const id = state.selectedRunId;
        if (!id) return null;
        const key = `${id}::${name}`;
        if (SERIES_CACHE.has(key)) return SERIES_CACHE.get(key);
        const series = await (window as unknown as SoakWin).SoakApi.characterSeries(id, name);
        SERIES_CACHE.set(key, series);
        return series;
    }

    async function fullSamples(id: string): Promise<unknown> {
        const key = `samples::${id}`;
        if (SERIES_CACHE.has(key)) return SERIES_CACHE.get(key);
        const body = await (window as unknown as SoakWin).SoakApi.samples(id);
        SERIES_CACHE.set(key, body);
        return body;
    }

    /**
     * The run's telemetry payload (task-543/544).
     *
     * Cached per run because the space-time view re-reads it on every tab switch
     * and every range change, and it is the heaviest thing the lab fetches: a
     * week-long run is tens of thousands of intervals. `withEvents` opts into the
     * unbounded action stream, which only the "why over time" stack needs.
     *
     * Not cached across run selection — a stale payload from a previous run would
     * draw the wrong lanes, which is worse than a slow redraw.
     */
    async function telemetry(withEvents?: boolean): Promise<unknown> {
        const id = state.selectedRunId;
        if (!id) return null;
        const key = `telemetry::${id}::${withEvents ? 'full' : 'slim'}`;
        if (SERIES_CACHE.has(key)) return SERIES_CACHE.get(key);
        const body = await (window as unknown as SoakWin).SoakApi.telemetry(id, withEvents);
        SERIES_CACHE.set(key, body);
        // A run that is still going gains intervals every tick, so the cached
        // copy is dropped on the next poll rather than left to go stale.
        if (state.data && state.data.run && state.data.run.status === 'running') {
            SERIES_CACHE.delete(key);
        }
        return body;
    }

    /** Drop a run's cached series (used when a run is deleted or restarted). */
    function invalidate(id: string): void {
        Array.from(SERIES_CACHE.keys())
            .filter((key) => key.includes(id))
            .forEach((key) => SERIES_CACHE.delete(key));
    }

    function setPollingPaused(paused: unknown): void {
        state.pollingPaused = !!paused;
        emit('paused', state.pollingPaused);
    }

    function debug(): Record<string, unknown> {
        return { hasTimer: !!timer, inFlight, listTick, paused: state.pollingPaused,
            selected: state.selectedRunId, serverActive: state.serverActiveRunId,
            lastError: state.lastError };
    }

    function destroy(): void { stopTimer(); listeners.length = 0; }

    // globals.d.ts types `window.SoakState` as the narrow two-member surface
    // soak-app.js reads; this module publishes the full store, so the assignment
    // goes through a cast rather than being trimmed to the declared surface.
    (window as unknown as { SoakState: unknown }).SoakState = {
        state, init, on, emit, setConfig, getConfig, coreVitals,
        refreshRuns, start, stop, removeRun, selectRun, selected, selectedRun,
        loadCharacters, characterSeries, fullSamples, telemetry, invalidate,
        applySnapshot, setPollingPaused, debug, destroy,
    };
}());
