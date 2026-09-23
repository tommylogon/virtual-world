/**
 * @module soak-state — the Soak Lab store: config, run list, incremental polling
 * @contributes single-source app state, cursor-based sample/event merging, poll lifecycle, run selection
 * @powers live progress, run history, character/report loading, compare + export data access
 * @relates consumes soak-api.js; observed by soak-ui.js and seeded by soak-app.js
 * @docs none
 */
(function () {
    'use strict';

    const listeners = [];
    const SERIES_CACHE = new Map();

    const state = {
        meta: null,
        runs: [],
        selectedRunId: null,
        serverActiveRunId: null,
        config: {},
        pollingPaused: false,
        data: null, // per-run view model, see _blankData()
        lastError: null,
    };

    function _blankData() {
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

    function on(fn) { listeners.push(fn); }
    function emit(type, payload) {
        listeners.forEach((fn) => {
            try { fn(type, payload); } catch (err) { console.error('[soak] listener', err); }
        });
    }

    // ── meta / config ──

    async function init() {
        const meta = await window.SoakApi.meta();
        state.meta = meta;
        const fromUrl = window.SoakFormat.queryToConfig(window.location.search);
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

    function setConfig(patch) {
        state.config = Object.assign({}, state.config, patch);
        emit('config', state.config);
    }

    function getConfig() { return Object.assign({}, state.config); }

    function coreVitals() {
        const seen = new Set(state.meta ? state.meta.core_vitals : []);
        if (state.data) {
            state.data.samples.forEach((s) => Object.keys(s.vitals || {}).forEach((k) => seen.add(k)));
        }
        return [...seen];
    }

    // ── runs ──

    async function refreshRuns() {
        const body = await window.SoakApi.listRuns();
        state.runs = body.runs || [];
        state.serverActiveRunId = body.active_run_id || null;
        emit('runs', state.runs);
        return state.runs;
    }

    async function start() {
        const snapshot = await window.SoakApi.startRun(state.config);
        await refreshRuns();
        await selectRun(snapshot.run.id);
        return snapshot.run;
    }

    async function stop(id) {
        const target = id || state.selectedRunId || state.serverActiveRunId;
        if (!target) return null;
        await window.SoakApi.stopRun(target);
        await refreshRuns();
        // The stop response can be staler than a poll that already observed the
        // terminal state, so re-read the run and apply the freshest snapshot.
        const d = state.data;
        const snapshot = await window.SoakApi.getRun(
            target, d ? d.nextSince : 0, d ? d.nextEventSince : 0);
        await applySnapshot(snapshot);
        if (snapshot.finished) {
            stopTimer('stopped');
            await loadFinal(target);
        } else {
            startTimer();
        }
        return snapshot;
    }

    async function removeRun(id) {
        await window.SoakApi.deleteRun(id);
        if (state.selectedRunId === id) {
            state.selectedRunId = null;
            state.data = null;
            stopTimer();
            emit('data', null);
        }
        SERIES_CACHE.delete(id);
        await refreshRuns();
    }

    async function selectRun(id) {
        if (state.selectedRunId !== id) {
            state.data = _blankData();
            state.data.run = state.runs.find((r) => r.id === id) || { id };
            emit('data', state.data);
        }
        state.selectedRunId = id;
        const snapshot = await window.SoakApi.getRun(id, 0, 0);
        await applySnapshot(snapshot);
        if (snapshot.finished) {
            await loadFinal(id);
        } else {
            startTimer();
        }
        return state.data;
    }

    function selected() { return state.data; }
    function selectedRun() { return state.data && state.data.run; }

    // ── polling ──

    let timer = null;
    let inFlight = false;
    let listTick = 0;

    function startTimer() {
        if (timer) return;
        timer = setInterval(tick, 450);
    }

    function stopTimer(reason) {
        if (timer) {
            if (reason === 'error') console.error('[soak] polling stopped after error', debug());
            clearInterval(timer);
            timer = null;
        }
    }

    async function tick() {
        if (inFlight || state.pollingPaused) return;
        const id = state.selectedRunId;
        if (!id) { stopTimer('no selected run'); return; }
        inFlight = true;
        try {
            const since = state.data ? state.data.nextSince : 0;
            const eventSince = state.data ? state.data.nextEventSince : 0;
            const snapshot = await window.SoakApi.getRun(id, since, eventSince);
            await applySnapshot(snapshot);
            listTick += 1;
            if (listTick % 6 === 0 || snapshot.finished) await refreshRuns();
            if (snapshot.finished) {
                stopTimer('finished');
                await loadFinal(id);
                await refreshRuns();
            }
        } catch (err) {
            state.lastError = err.message;
            console.error('[soak] poll failed', err);
            emit('error', err);
            stopTimer('error');
        } finally {
            inFlight = false;
        }
    }

    async function applySnapshot(snapshot) {
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

    async function loadFinal(id) {
        try {
            const [report, chars] = await Promise.all([
                window.SoakApi.report(id), window.SoakApi.characters(id),
            ]);
            if (state.selectedRunId !== id || !state.data) return;
            state.data.report = report;
            state.data.summary = report.summary;
            state.data.characters = chars.characters || [];
            emit('report', report);
            emit('data', state.data);
        } catch (err) {
            emit('error', err);
        }
    }

    async function loadCharacters() {
        const id = state.selectedRunId;
        if (!id || !state.data) return [];
        if (state.data.characters.length) return state.data.characters;
        const chars = await window.SoakApi.characters(id);
        state.data.characters = chars.characters || [];
        emit('data', state.data);
        return state.data.characters;
    }

    async function characterSeries(name) {
        const id = state.selectedRunId;
        if (!id) return null;
        const key = `${id}::${name}`;
        if (SERIES_CACHE.has(key)) return SERIES_CACHE.get(key);
        const series = await window.SoakApi.characterSeries(id, name);
        SERIES_CACHE.set(key, series);
        return series;
    }

    async function fullSamples(id) {
        const key = `samples::${id}`;
        if (SERIES_CACHE.has(key)) return SERIES_CACHE.get(key);
        const body = await window.SoakApi.samples(id);
        SERIES_CACHE.set(key, body);
        return body;
    }

    function setPollingPaused(paused) {
        state.pollingPaused = !!paused;
        emit('paused', state.pollingPaused);
    }

    function debug() {
        return { hasTimer: !!timer, inFlight, listTick, paused: state.pollingPaused,
            selected: state.selectedRunId, serverActive: state.serverActiveRunId,
            lastError: state.lastError };
    }

    function destroy() { stopTimer(); listeners.length = 0; }

    window.SoakState = {
        state, init, on, emit, setConfig, getConfig, coreVitals,
        refreshRuns, start, stop, removeRun, selectRun, selected, selectedRun,
        loadCharacters, characterSeries, fullSamples, applySnapshot,
        setPollingPaused, debug, destroy,
    };
})();
