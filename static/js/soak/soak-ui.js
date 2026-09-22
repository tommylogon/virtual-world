/**
 * @module soak-ui — DOM rendering + interaction for the Soak Lab
 * @contributes form binding, progress/stat readouts, tab panes, all charts and tables, toasts, shortcuts
 * @powers the entire /soak dashboard experience
 * @relates consumes soak-state.js, soak-charts.js, soak-presets.js, soak-format.js
 * @docs none
 */
(function () {
    'use strict';

    const F = window.SoakFormat;
    const C = window.SoakCharts;
    const P = window.SoakPresets;
    const S = window.SoakState;
    const el = (id) => document.getElementById(id);
    const esc = F.esc;

    const GROWTH_LABELS = {
        game_log: 'Game log', turn_events: 'Turn events', delayed_events: 'Delayed events',
        graph_nodes: 'Graph nodes', total_memories: 'Memories', total_trace: 'Traces',
    };
    const CHART_COLORS = ['#58a6ff', '#3fb950', '#e3b341', '#f85149', '#bc8cff', '#f778ba'];

    const ui = {
        activeTab: 'overview',
        vitalMetrics: null,
        vitalMode: 'avg',
        vitalBand: true,
        vitalPct: false,
        growthMetrics: null,
        growthLog: true,
        eventKinds: null,
        eventSearch: '',
        eventAutoscroll: true,
        deathSearch: '',
        charSearch: '',
        charFilter: 'all',
        charSort: 'name',
        charSelected: null,
        trackVitals: null,
        lastDeathCount: 0,
        compareData: null,
    };

    // ─────────────────────────── small utilities ───────────────────────────

    function toast(message, kind, ms) {
        const box = el('soak-toasts');
        if (!box) return;
        const node = document.createElement('div');
        node.className = 'soak-toast soak-toast-' + (kind || 'info');
        node.textContent = message;
        box.appendChild(node);
        setTimeout(() => node.remove(), ms || (kind === 'error' ? 9000 : 4500));
    }

    async function copy(text, label) {
        try {
            await navigator.clipboard.writeText(text);
            toast((label || 'Copied') + ' to clipboard', 'success', 2500);
        } catch (err) {
            // Clipboard API needs a secure context; fall back to a temp textarea.
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); toast((label || 'Copied') + ' to clipboard', 'success', 2500); }
            catch (e2) { toast('Copy failed — select the text manually', 'warn'); }
            ta.remove();
        }
    }

    function download(url) {
        const a = document.createElement('a');
        a.href = url;
        a.download = '';
        document.body.appendChild(a);
        a.click();
        a.remove();
    }

    function data() { return S.selected(); }
    function meta() { return S.state.meta || {}; }
    function scenarioInfo(path) {
        return (meta().scenarios || []).find((s) => s.path === path) || {};
    }
    function minutesPerTick(config) {
        const chosen = Number((config || {}).minutes_per_tick);
        if (chosen > 0) return chosen;
        const s = scenarioInfo((config || {}).scenario);
        const m = Number(s.minutes_per_tick);
        return m > 0 ? m : 1;
    }
    function gameSpan(ticks, config) {
        const total = Math.max(0, ticks || 0) * minutesPerTick(config);
        const days = Math.floor(total / 1440);
        const hours = Math.floor((total % 1440) / 60);
        const mins = Math.floor(total % 60);
        return `${days}d${String(hours).padStart(2, '0')}h${String(mins).padStart(2, '0')}m`;
    }

    // ─────────────────────────── form ───────────────────────────

    function renderScenarioOptions() {
        const sel = el('soak-scenario');
        if (!sel) return;
        const current = S.getConfig().scenario;
        sel.innerHTML = (meta().scenarios || []).map((s) => {
            const bits = [];
            if (s.characters != null) bits.push(`${s.characters} chars`);
            if (s.minutes_per_tick) bits.push(`${s.minutes_per_tick} min/tick`);
            if (s.error) bits.push('unreadable');
            const label = `${s.is_template ? '★ ' : ''}${s.name}${bits.length ? ' — ' + bits.join(', ') : ''}`;
            return `<option value="${esc(s.path)}"${s.path === current ? ' selected' : ''}>${esc(label)}</option>`;
        }).join('');
    }

    function setForm(config) {
        const c = config || S.getConfig();
        el('soak-scenario').value = c.scenario;
        el('soak-ticks').value = c.ticks;
        el('soak-minutes').value = c.minutes_per_tick == null ? '' : c.minutes_per_tick;
        el('soak-seed').value = c.seed;
        el('soak-sample-every').value = c.sample_every || 0;
        el('soak-label').value = c.label || '';
        el('soak-engine-decay').checked = !!c.engine_decay;
        el('soak-neutral').checked = !!c.neutral_environment;
        el('soak-background-all').checked = !!c.background_all;
        el('soak-mature').checked = !!c.mature;
        el('soak-debug-hp').checked = !!c.debug_hp;
        el('soak-track-characters').checked = c.track_characters !== false;
        el('soak-overrides').value = stringifyMap(c.decay_overrides);
        el('soak-set').value = stringifyMap(c.starting_vitals);
        el('soak-traits').value = stringifyMap(c.traits);
        ui.trackVitals = (c.track_vitals && c.track_vitals.length)
            ? c.track_vitals.slice() : (meta().defaults.track_vitals || []).slice();
        renderTrackVitalChips();
        updateHorizon();
    }

    function stringifyMap(value) {
        if (!value) return '';
        if (typeof value === 'string') return value;
        return Object.keys(value).map((k) => `${k}=${value[k]}`).join(',');
    }

    function readForm() {
        const num = (id, fallback) => {
            const v = el(id).value;
            return v === '' ? fallback : Number(v);
        };
        return {
            scenario: el('soak-scenario').value,
            ticks: Math.max(1, Math.round(num('soak-ticks', 10080))),
            minutes_per_tick: el('soak-minutes').value === '' ? null : Number(el('soak-minutes').value),
            seed: Math.round(num('soak-seed', 1234)),
            sample_every: Math.max(0, Math.round(num('soak-sample-every', 0))),
            label: el('soak-label').value.trim(),
            engine_decay: el('soak-engine-decay').checked,
            neutral_environment: el('soak-neutral').checked,
            background_all: el('soak-background-all').checked,
            mature: el('soak-mature').checked,
            debug_hp: el('soak-debug-hp').checked,
            track_characters: el('soak-track-characters').checked,
            decay_overrides: el('soak-overrides').value.trim(),
            starting_vitals: el('soak-set').value.trim(),
            traits: el('soak-traits').value.trim(),
            track_vitals: ui.trackVitals || [],
        };
    }

    function applyConfig(config) {
        S.setConfig(config);
        setForm(config);
    }

    function updateHorizon() {
        const cfg = S.getConfig();
        const ticks = Number(el('soak-ticks').value) || 0;
        const isr = scenarioInfo(cfg.scenario);
        const cast = isr.characters != null ? `${isr.characters} chars · ` : '';
        el('soak-horizon').textContent =
            `${cast}${gameSpan(ticks, cfg)} (${F.fmtInt(ticks)} ticks @ ${minutesPerTick(cfg)} min/tick)`;
    }

    function renderTrackVitalChips() {
        const box = el('soak-track-vitals');
        if (!box) return;
        if (!ui.trackVitals) ui.trackVitals = [];
        box.innerHTML = (meta().core_vitals || []).map((v) => {
            const on = ui.trackVitals.includes(v);
            return `<button type="button" class="soak-chip-toggle${on ? ' on' : ''}" data-vital="${esc(v)}" style="color:${F.vitalColor(v)}">`
                + `<span class="dot"></span>${esc(v)}</button>`;
        }).join('');
        box.querySelectorAll('[data-vital]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const v = btn.getAttribute('data-vital');
                if (ui.trackVitals.includes(v)) ui.trackVitals = ui.trackVitals.filter((x) => x !== v);
                else ui.trackVitals.push(v);
                renderTrackVitalChips();
                S.setConfig({ track_vitals: ui.trackVitals.slice() });
            });
        });
    }

    function showFormError(message) {
        const box = el('soak-form-error');
        if (!message) { box.hidden = true; box.textContent = ''; return; }
        box.hidden = false;
        box.textContent = message;
    }

    // ─────────────────────────── presets / saved ───────────────────────────

    function renderPresets() {
        const box = el('soak-presets');
        if (!box) return;
        box.innerHTML = P.PRESETS.map((p) => (
            `<button type="button" class="soak-preset" data-preset="${esc(p.id)}">`
            + `<span class="soak-preset-icon">${p.icon}</span><span>`
            + `<span class="soak-preset-name">${esc(p.name)}</span>`
            + `<span class="soak-preset-hint">${esc(p.hint)}</span></span></button>`
        )).join('');
        box.querySelectorAll('[data-preset]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const preset = P.PRESETS.find((p) => p.id === btn.getAttribute('data-preset'));
                if (!preset) return;
                applyConfig(P.resolve(preset, S.getConfig(), meta().defaults));
                toast(`Preset applied: ${preset.name}`, 'info', 2200);
            });
        });
    }

    function renderSaved() {
        const box = el('soak-saved');
        if (!box) return;
        const list = P.loadSaved();
        if (!list.length) {
            box.innerHTML = '<div class="soak-hint">No saved configs yet.</div>';
            return;
        }
        box.innerHTML = list.map((item, idx) => (
            `<div class="soak-saved"><span class="name" data-load="${idx}" title="${esc(item.name)}">`
            + `💾 ${esc(item.name)}</span>`
            + `<button type="button" data-del="${idx}" title="Delete">✕</button></div>`
        )).join('');
        box.querySelectorAll('[data-load]').forEach((node) => {
            node.addEventListener('click', () => {
                const item = P.loadSaved()[Number(node.getAttribute('data-load'))];
                if (item) { applyConfig(Object.assign({}, meta().defaults, item.config)); toast('Config loaded', 'info', 2000); }
            });
        });
        box.querySelectorAll('[data-del]').forEach((node) => {
            node.addEventListener('click', () => {
                P.removeSaved(Number(node.getAttribute('data-del')));
                renderSaved();
            });
        });
    }

    // ─────────────────────────── run list / chips ───────────────────────────

    function statusChip(status) {
        const cls = { running: 'soak-chip-running', finished: 'soak-chip-finished',
            stopped: 'soak-chip-stopped', error: 'soak-chip-error', queued: 'soak-chip-idle' }[status] || '';
        return `<span class="soak-chip ${cls}">${esc(status || '—')}</span>`;
    }

    function renderRunList() {
        const box = el('soak-run-list');
        if (!box) return;
        const runs = S.state.runs || [];
        el('soak-run-count').textContent = runs.length;
        if (!runs.length) { box.innerHTML = '<div class="soak-hint">No runs yet this session.</div>'; return; }
        box.innerHTML = runs.map((r) => {
            const selected = r.id === S.state.selectedRunId ? ' selected' : '';
            const frac = Math.round((r.progress_frac || 0) * 100);
            return `<div class="soak-run${selected}" data-run="${esc(r.id)}">`
                + `<div class="soak-run-head"><span class="soak-run-title" title="${esc(r.label)}">${esc(r.label)}</span>`
                + `${statusChip(r.status)}`
                + `<button type="button" class="soak-run-del" data-del="${esc(r.id)}" title="Delete run">✕</button></div>`
                + `<div class="soak-run-sub"><span>${esc(r.scenario_name)}</span>`
                + `<span>${F.fmtInt(r.tick)}/${F.fmtInt(r.ticks)}</span>`
                + `<span>${r.alive}↑ ${r.dead}☠</span>`
                + `<span>${esc(F.fmtClock(r.created_at))}</span></div>`
                + `<div class="soak-run-bar"><div style="width:${frac}%"></div></div></div>`;
        }).join('');
        box.querySelectorAll('[data-run]').forEach((node) => {
            node.addEventListener('click', (ev) => {
                if (ev.target.getAttribute('data-del')) return;
                S.selectRun(node.getAttribute('data-run')).catch((e) => toast(e.message, 'error'));
            });
        });
        box.querySelectorAll('[data-del]').forEach((node) => {
            node.addEventListener('click', async (ev) => {
                ev.stopPropagation();
                try { await S.removeRun(node.getAttribute('data-del')); }
                catch (e) { toast(e.message, 'error'); }
            });
        });
    }

    function renderTopChips() {
        const active = S.state.serverActiveRunId;
        const chip = el('soak-active-chip');
        chip.textContent = active ? `running ${active}` : 'idle';
        chip.className = 'soak-chip ' + (active ? 'soak-chip-running' : 'soak-chip-idle');
        const run = data() && data().run;
        el('soak-scenario-chip').textContent = run && run.scenario
            ? `${run.scenario_name || run.scenario}` : '—';
        const running = !!(active || (run && run.status === 'running'));
        el('soak-stop').disabled = !running;
        el('soak-start').disabled = !!active;
        el('soak-start').textContent = active ? '▶ Running…' : '▶ Start soak';
    }

    // ─────────────────────────── progress ───────────────────────────

    function renderProgress() {
        const d = data();
        if (!d || !d.run) return;
        const run = d.run;
        const p = d.progress || {};
        el('soak-run-title').textContent = run.label || run.id;
        const statusEl = el('soak-status-chip');
        statusEl.textContent = run.status;
        statusEl.className = 'soak-chip ' + ({ running: 'soak-chip-running', finished: 'soak-chip-finished',
            stopped: 'soak-chip-stopped', error: 'soak-chip-error' }[run.status] || '');
        const frac = p.fraction || 0;
        el('soak-progress-fill').style.width = `${(frac * 100).toFixed(1)}%`;
        el('soak-progress-pct').textContent = F.pct(frac, 1);
        el('soak-progress-tick').textContent = `tick ${F.fmtInt(p.tick)} / ${F.fmtInt(p.ticks)}`;
        el('soak-progress-gamespan').textContent = `${p.game_span || '—'} of ${p.total_game_span || '—'}`;
        el('soak-progress-rate').textContent = `${F.fmtNum(p.ticks_per_second, 0)} t/s`;
        el('soak-progress-rate-now').textContent = `now ${F.fmtNum(p.instant_tps, 0)} t/s`;
        el('soak-progress-elapsed').textContent = F.fmtDuration(p.elapsed_s);
        el('soak-progress-eta').textContent = F.fmtDuration(p.eta_s);
        el('soak-progress-alive').textContent = F.fmtInt(p.alive);
        el('soak-progress-dead').textContent = F.fmtInt(p.dead);
        const proj = p.projected_wall_seconds || {};
        el('soak-progress-proj').textContent = `${F.fmtDuration(proj['1day'])} · ${F.fmtDuration(proj['1week'])} · ${F.fmtDuration(proj['1month'])}`;
        el('soak-progress-clock').textContent = run.status === 'running'
            ? `ETA ${F.fmtDuration(p.eta_s)}` : (run.finished_at ? 'finished ' + F.fmtClock(run.finished_at) : '—');
    }

    // ─────────────────────────── chart helpers ───────────────────────────

    function samples() { const d = data(); return (d && d.samples) || []; }
    function charactersCount() {
        const d = data();
        if (d && d.progress && d.progress.characters) return d.progress.characters;
        if (d && d.run && d.run.characters) return d.run.characters;
        return 0;
    }

    function vitalSeries(stat, mode) {
        return samples().map((s) => {
            const agg = (s.vitals || {})[stat];
            return [s.tick, agg && agg[mode] != null ? agg[mode] : null];
        });
    }

    function vitalBand(stat) {
        return {
            lower: samples().map((s) => [s.tick, ((s.vitals || {})[stat] || {}).min]),
            upper: samples().map((s) => [s.tick, ((s.vitals || {})[stat] || {}).max]),
        };
    }

    function survivalPoints() {
        const total = charactersCount() || 1;
        return samples().map((s) => [s.tick, (s.alive / total) * 100]);
    }

    function deathsByCause() {
        const d = data();
        if (d && d.report && d.report.summary && d.report.summary.causes) return d.report.summary.causes;
        if (d && d.progress && d.progress.deaths_by_cause && Object.keys(d.progress.deaths_by_cause).length) {
            return d.progress.deaths_by_cause;
        }
        const counts = {};
        ((d && d.deaths) || []).forEach((x) => { counts[x.cause] = (counts[x.cause] || 0) + 1; });
        return counts;
    }

    function deathsByArea() {
        const d = data();
        if (d && d.report && d.report.summary && d.report.summary.death_by_area) return d.report.summary.death_by_area;
        const counts = {};
        ((d && d.deaths) || []).forEach((x) => { const k = x.area || 'unknown'; counts[k] = (counts[k] || 0) + 1; });
        return counts;
    }

    function panelWidth() {
        const box = el('soak-dashboard');
        return Math.max(420, (box ? box.clientWidth : 800) - 40);
    }

    // ─────────────────────────── panes ───────────────────────────

    function renderOverview() {
        const vitals = ui.vitalMetrics && ui.vitalMetrics.length
            ? ui.vitalMetrics : ['Hunger', 'Thirst', 'Energy', 'HP'];
        const series = vitals.map((v, i) => ({
            name: v, color: F.vitalColor(v, i), points: vitalSeries(v, 'avg'), width: 1.9,
        }));
        el('soak-overview-vitals').innerHTML = C.renderLineChart({
            width: panelWidth(), height: 260, series: series,
            yLabel: 'avg vital', xLabel: 'ticks', emptyText: 'Waiting for the first sample…',
        });
        el('soak-overview-vitals-legend').innerHTML = series.map((s) => (
            `<span class="soak-legend-item"><span class="soak-legend-swatch" style="background:${s.color}"></span>${esc(s.name)}</span>`
        )).join('');

        const causes = deathsByCause();
        const causeColors = Object.keys(causes).map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);
        el('soak-overview-causes').innerHTML = C.renderDonut({
            slices: Object.keys(causes).map((k, i) => ({ label: k, value: causes[k], color: causeColors[i] })),
            centerLabel: 'deaths', size: 170, emptyText: 'No deaths',
        });
        el('soak-overview-causes-legend').innerHTML = Object.keys(causes).map((k, i) => (
            `<span class="soak-legend-item"><span class="soak-legend-swatch" style="background:${causeColors[i]}"></span>${esc(F.titleCase(k))} · ${F.fmtInt(causes[k])}</span>`
        )).join('') || '<span class="soak-hint">Every character is still alive.</span>';

        const areas = deathsByArea();
        el('soak-overview-areas').innerHTML = C.renderBarChart({
            width: panelWidth(), height: Math.max(120, 40 + Object.keys(areas).length * 26),
            items: Object.keys(areas).sort((a, b) => areas[b] - areas[a]).slice(0, 14)
                .map((k) => ({ label: k, value: areas[k] })),
            color: '#f85149', emptyText: 'No deaths by area',
        });

        renderDeltas();
        renderAlerts();
    }

    function renderDeltas() {
        const rows = samples();
        // The final sample of a wipe has no living characters, so its aggregate
        // vitals are empty — fall back to the last sample that still had data.
        const first = rows.find((s) => Object.keys(s.vitals || {}).length);
        let last = null;
        for (let i = rows.length - 1; i >= 0; i -= 1) {
            if (Object.keys(rows[i].vitals || {}).length) { last = rows[i]; break; }
        }
        if (!first || !last) {
            el('soak-overview-deltas').innerHTML = '<span class="soak-hint">No tracked vitals yet.</span>';
            return;
        }
        const keys = Object.keys(last.vitals).filter((k) => first.vitals[k] && last.vitals[k]);
        el('soak-overview-deltas').innerHTML = keys.map((k) => {
            const delta = last.vitals[k].avg - first.vitals[k].avg;
            const cls = Math.abs(delta) < 0.05 ? 'soak-flat' : (delta > 0 ? 'soak-up' : 'soak-down');
            return `<div class="soak-delta"><div class="soak-delta-label" style="color:${F.vitalColor(k)}">${esc(k)}</div>`
                + `<div class="soak-delta-value ${cls}">${F.fmtNum(last.vitals[k].avg)}</div>`
                + `<div class="soak-delta-sub">${F.fmtSigned(delta)} from ${F.fmtNum(first.vitals[k].avg)}`
                + (last !== rows[rows.length - 1] ? ' (last living)' : '') + '</div></div>';
        }).join('') || '<span class="soak-hint">No tracked vitals yet.</span>';
    }

    function renderAlerts() {
        const box = el('soak-overview-alerts');
        const p = (data() && data().progress) || {};
        const messages = [];
        const total = p.characters || charactersCount() || 0;
        if (p.dead && total && p.dead / total >= 0.5) {
            messages.push(['danger', `Mass casualty: ${p.dead}/${total} dead (${F.pct(p.dead / total, 0)}).`]);
        } else if (p.dead) {
            messages.push(['warn', `${p.dead} dead of ${total}; first at ${(data().deaths[0] || {}).game_span || '—'}.`]);
        }
        if (p.fraction > 0.5 && !p.dead && total) {
            messages.push(['info', 'No deaths past the halfway mark — decay is sustainable at these settings.']);
        }
        if (p.ticks_per_second && p.ticks_per_second < 50) {
            messages.push(['warn', `Throughput is only ${F.fmtNum(p.ticks_per_second, 0)} ticks/s; long horizons will be slow.`]);
        }
        const run = data() && data().run;
        if (run && run.status === 'error') messages.push(['danger', run.error || 'Run failed.']);
        el('soak-overview-alerts').innerHTML = messages.map(([kind, text]) => (
            `<div class="soak-alert soak-alert-${kind}">${esc(text)}</div>`
        )).join('');
    }

    function ensureVitalMetrics() {
        if (ui.vitalMetrics && ui.vitalMetrics.length) return;
        const core = S.coreVitals();
        ui.vitalMetrics = ['Hunger', 'Thirst', 'Energy', 'HP'].filter((v) => core.includes(v));
        if (!ui.vitalMetrics.length) ui.vitalMetrics = core.slice(0, 4);
    }

    function renderVitalMetrics() {
        ensureVitalMetrics();
        const box = el('soak-vital-metrics');
        box.innerHTML = S.coreVitals().map((v) => {
            const on = ui.vitalMetrics.includes(v);
            return `<button type="button" class="soak-chip-toggle${on ? ' on' : ''}" data-vital="${esc(v)}" style="color:${F.vitalColor(v)}">`
                + `<span class="dot"></span>${esc(v)}</button>`;
        }).join('');
        box.querySelectorAll('[data-vital]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const v = btn.getAttribute('data-vital');
                if (ui.vitalMetrics.includes(v)) {
                    if (ui.vitalMetrics.length === 1) return;
                    ui.vitalMetrics = ui.vitalMetrics.filter((x) => x !== v);
                } else ui.vitalMetrics.push(v);
                renderVitalMetrics();
                renderVitals();
            });
        });
    }

    function renderVitals() {
        ensureVitalMetrics();
        const pct = ui.vitalPct;
        const series = ui.vitalMetrics.map((v) => {
            let points = vitalSeries(v, ui.vitalMode);
            let base = null;
            if (pct) {
                const first = points.find((p) => p[1] != null);
                base = first ? first[1] : null;
                points = points.map(([x, y]) => [x, (y == null || !base) ? null : (y / base) * 100]);
            }
            const s = { name: v, color: F.vitalColor(v), points: points, width: 1.9 };
            if (ui.vitalBand && ui.vitalMode === 'avg' && !pct) {
                const band = vitalBand(v);
                s.area = { lower: band.lower, upper: band.upper };
            }
            return s;
        });
        el('soak-vital-chart').innerHTML = C.renderLineChart({
            width: panelWidth(), height: 320, series: series,
            yLabel: pct ? '% of starting value' : ui.vitalMode,
            xLabel: 'ticks',
            yFormat: (v) => (pct ? `${F.fmtNum(v, 0)}%` : F.fmtNum(v, 1)),
            emptyText: 'Waiting for samples…',
        });
    }

    function renderSurvival() {
        const pts = survivalPoints();
        el('soak-survival-chart').innerHTML = C.renderLineChart({
            width: panelWidth() / 2 - 20, height: 240,
            series: [{ name: 'Alive %', color: '#3fb950', points: pts, width: 2.2 }],
            yDomain: [0, 100], yLabel: '% alive', xLabel: 'ticks',
            yFormat: (v) => `${Math.round(v)}%`, emptyText: 'Waiting for samples…',
        });
        const deathTicks = ((data() && data().deaths) || []).map((d) => d.tick);
        el('soak-death-histogram').innerHTML = C.renderVerticalBars({
            width: panelWidth() / 2 - 20, height: 240,
            items: C.histogram(deathTicks, 12),
            color: '#f85149', emptyText: 'No deaths recorded',
        });
        renderDeathsTable();
    }

    function renderDeathsTable() {
        const d = data() || {};
        const deaths = (d.deaths || []).filter((x) => {
            if (!ui.deathSearch) return true;
            const q = ui.deathSearch.toLowerCase();
            return `${x.name} ${x.cause} ${x.area}`.toLowerCase().includes(q);
        });
        el('soak-death-count').textContent = deaths.length;
        if (!deaths.length) { el('soak-deaths-table').innerHTML = '<div class="soak-hint">No deaths match.</div>'; return; }
        el('soak-deaths-table').innerHTML = '<table class="soak-table"><thead><tr>'
            + '<th>Game time</th><th>Tick</th><th>Name</th><th>Cause</th><th>Area</th>'
            + '<th>Hunger</th><th>Thirst</th><th>Energy</th><th>HP</th><th>Tags</th></tr></thead><tbody>'
            + deaths.map((x) => `<tr><td>${esc(x.game_span)}</td><td>${F.fmtInt(x.tick)}</td>`
                + `<td>${esc(x.name)}</td><td>${esc(F.titleCase(x.cause))}</td><td>${esc(x.area || '—')}</td>`
                + `<td>${F.fmtNum(x.hunger)}</td><td>${F.fmtNum(x.thirst)}</td>`
                + `<td>${F.fmtNum(x.energy)}</td><td>${F.fmtNum(x.hp)}</td>`
                + `<td>${(x.tags || []).slice(0, 4).map((t) => `<span class="soak-tag">${esc(t)}</span>`).join('')}</td></tr>`).join('')
            + '</tbody></table>';
    }

    function growthKeys() {
        const rows = samples();
        const seen = new Set();
        rows.forEach((s) => Object.keys(s.growth || {}).forEach((k) => seen.add(k)));
        return [...seen].length ? [...seen] : Object.keys(GROWTH_LABELS);
    }

    function renderGrowthMetrics() {
        const keys = growthKeys();
        if (!ui.growthMetrics) ui.growthMetrics = keys.slice();
        el('soak-growth-metrics').innerHTML = keys.map((k) => {
            const on = ui.growthMetrics.includes(k);
            const color = CHART_COLORS[keys.indexOf(k) % CHART_COLORS.length];
            return `<button type="button" class="soak-chip-toggle${on ? ' on' : ''}" data-metric="${esc(k)}" style="color:${color}">`
                + `<span class="dot"></span>${esc(GROWTH_LABELS[k] || k)}</button>`;
        }).join('');
        el('soak-growth-metrics').querySelectorAll('[data-metric]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const k = btn.getAttribute('data-metric');
                if (ui.growthMetrics.includes(k)) {
                    if (ui.growthMetrics.length === 1) return;
                    ui.growthMetrics = ui.growthMetrics.filter((x) => x !== k);
                } else ui.growthMetrics.push(k);
                renderGrowthMetrics(); renderGrowth();
            });
        });
    }

    function renderGrowth() {
        if (!ui.growthMetrics) renderGrowthMetrics();
        const keys = growthKeys();
        const series = ui.growthMetrics.map((k) => ({
            name: GROWTH_LABELS[k] || k,
            color: CHART_COLORS[keys.indexOf(k) % CHART_COLORS.length],
            points: samples().map((s) => [s.tick, (s.growth || {})[k]]),
            width: 1.8,
        }));
        el('soak-growth-chart').innerHTML = C.renderLineChart({
            width: panelWidth(), height: 300, series: series, logY: ui.growthLog,
            yLabel: ui.growthLog ? 'count (log)' : 'count', xLabel: 'ticks',
            yFormat: (v) => F.fmtNum(v, 0), emptyText: 'Waiting for samples…',
        });
        el('soak-throughput').innerHTML = C.renderLineChart({
            width: panelWidth() / 2 - 20, height: 110,
            series: [{ name: 'ticks/s', color: '#e3b341', points: samples().map((s) => [s.tick, s.ticks_per_second]), width: 1.6 }],
            xLabel: 'ticks', yFormat: (v) => F.fmtNum(v, 0), emptyText: 'No throughput data',
        });
        const finalGrowth = samples().length ? (samples()[samples().length - 1].growth || {}) : {};
        const firstGrowth = samples().length ? (samples()[0].growth || {}) : {};
        el('soak-growth-table').innerHTML = '<table class="soak-table"><thead><tr><th>Metric</th><th>First</th><th>Latest</th><th>Δ</th></tr></thead><tbody>'
            + Object.keys(GROWTH_LABELS).map((k) => {
                const a = firstGrowth[k]; const b = finalGrowth[k];
                const delta = (b != null && a != null) ? b - a : null;
                return `<tr><td>${esc(GROWTH_LABELS[k])}</td><td>${F.fmtInt(a)}</td><td>${F.fmtInt(b)}</td>`
                    + `<td class="${delta > 0 ? 'soak-up' : 'soak-flat'}">${delta == null ? '—' : F.fmtSigned(delta, 0)}</td></tr>`;
            }).join('') + '</tbody></table>';
    }

    async function renderCharacters() {
        let chars = (data() && data().characters) || [];
        if (!chars.length) {
            try { chars = await S.loadCharacters(); } catch (e) { chars = []; }
        }
        el('soak-char-count').textContent = chars.length;
        let rows = chars.filter((c) => {
            if (ui.charFilter === 'alive' && !c.alive) return false;
            if (ui.charFilter === 'dead' && c.alive) return false;
            if (!ui.charSearch) return true;
            const q = ui.charSearch.toLowerCase();
            return `${c.name} ${c.area} ${(c.tags || []).join(' ')} ${c.cause || ''}`.toLowerCase().includes(q);
        });
        rows.sort((a, b) => {
            if (ui.charSort === 'death') return (a.death_tick || Infinity) - (b.death_tick || Infinity);
            if (ui.charSort === 'hp') return (b.vitals.HP || 0) - (a.vitals.HP || 0);
            if (ui.charSort === 'hunger') return (b.vitals.Hunger || 0) - (a.vitals.Hunger || 0);
            if (ui.charSort === 'thirst') return (b.vitals.Thirst || 0) - (a.vitals.Thirst || 0);
            if (ui.charSort === 'energy') return (b.vitals.Energy || 0) - (a.vitals.Energy || 0);
            return a.name.localeCompare(b.name);
        });
        if (!rows.length) {
            el('soak-char-table').innerHTML = '<div class="soak-hint">No characters match. Character data loads when a run finishes (or open this tab after the first sample).</div>';
            return;
        }
        const vitals = ['HP', 'Hunger', 'Thirst', 'Energy', 'Sanity', 'Social'];
        el('soak-char-table').innerHTML = '<table class="soak-table"><thead><tr>'
            + '<th>Name</th><th>State</th><th>Area</th><th>Died</th>'
            + vitals.map((v) => `<th>${v}</th>`).join('') + '<th>Tags</th></tr></thead><tbody>'
            + rows.map((c) => `<tr class="clickable" data-char="${esc(c.name)}">`
                + `<td>${esc(c.name)}</td>`
                + `<td><span class="soak-pill ${c.alive ? 'soak-pill-alive' : 'soak-pill-dead'}">${c.alive ? 'alive' : esc(F.titleCase(c.cause || 'dead'))}</span></td>`
                + `<td>${esc(c.area || '—')}</td><td>${esc(c.death_game_span || '—')}</td>`
                + vitals.map((v) => `<td>${F.fmtNum((c.vitals || {})[v])}</td>`).join('')
                + `<td>${(c.tags || []).slice(0, 3).map((t) => `<span class="soak-tag">${esc(t)}</span>`).join('')}</td></tr>`).join('')
            + '</tbody></table>';
        el('soak-char-table').querySelectorAll('[data-char]').forEach((row) => {
            row.addEventListener('click', () => openCharacter(row.getAttribute('data-char')));
        });
    }

    async function openCharacter(name) {
        ui.charSelected = name;
        const box = el('soak-char-detail');
        box.hidden = false;
        el('soak-char-detail-title').textContent = name;
        el('soak-char-detail-chart').innerHTML = '<div class="soak-hint">Loading series…</div>';
        let series = null;
        try { series = await S.characterSeries(name); } catch (e) { series = null; }
        if (!series || !series.series) {
            el('soak-char-detail-chart').innerHTML = '<div class="soak-hint">No per-character series for this run (enable “Record per-character series”).</div>';
            el('soak-char-detail-stats').innerHTML = '';
            return;
        }
        const metrics = Object.keys(series.series);
        const points = metrics.map((m, i) => ({
            name: m, color: F.vitalColor(m, i),
            points: series.series[m].map((y, idx) => [series.ticks[idx], y]),
            width: 1.6,
        }));
        el('soak-char-detail-chart').innerHTML = C.renderLineChart({
            width: panelWidth(), height: 300, series: points, yLabel: 'vital', xLabel: 'ticks',
            emptyText: 'No samples',
        });
        const char = ((data() && data().characters) || []).find((c) => c.name === name);
        const stats = (char && char.stats) || {};
        el('soak-char-detail-stats').innerHTML = Object.keys(stats).map((m) => (
            `<div class="soak-delta"><div class="soak-delta-label" style="color:${F.vitalColor(m)}">${esc(m)}</div>`
            + `<div class="soak-delta-value">${F.fmtNum(stats[m].last)}</div>`
            + `<div class="soak-delta-sub">min ${F.fmtNum(stats[m].min)} · max ${F.fmtNum(stats[m].max)} · avg ${F.fmtNum(stats[m].avg)}</div></div>`
        )).join('');
    }

    function renderEventKinds() {
        const kinds = ['info', 'warn', 'error', 'death', 'hp'];
        if (!ui.eventKinds) ui.eventKinds = {}; 
        kinds.forEach((k) => { if (ui.eventKinds[k] === undefined) ui.eventKinds[k] = (k !== 'hp'); });
        el('soak-event-kinds').innerHTML = kinds.map((k) => (
            `<button type="button" class="soak-chip-toggle${ui.eventKinds[k] ? ' on' : ''}" data-kind="${k}">`
            + `<span class="dot"></span>${esc(k)}</button>`
        )).join('');
        el('soak-event-kinds').querySelectorAll('[data-kind]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const k = btn.getAttribute('data-kind');
                ui.eventKinds[k] = !ui.eventKinds[k];
                renderEventKinds(); renderEvents();
            });
        });
    }

    function renderEvents() {
        const box = el('soak-events');
        const all = (data() && data().events) || [];
        const q = ui.eventSearch.toLowerCase();
        const filtered = all.filter((e) => {
            if (ui.eventKinds && ui.eventKinds[e.kind] === false) return false;
            if (q && !e.message.toLowerCase().includes(q)) return false;
            return true;
        });
        el('soak-event-count').textContent = filtered.length;
        const stick = ui.eventAutoscroll && (box.scrollTop + box.clientHeight >= box.scrollHeight - 30);
        box.innerHTML = filtered.slice(-500).map((e) => (
            `<div class="soak-event soak-event-${esc(e.kind)}"><span class="soak-event-t">${esc(F.fmtDuration(e.t))}</span>`
            + `<span class="soak-event-kind">${esc(e.kind)}</span>`
            + `<span class="soak-event-msg">${esc(e.message)}</span></div>`
        )).join('') || '<div class="soak-hint">No events yet.</div>';
        if (stick) box.scrollTop = box.scrollHeight;
    }

    async function renderCompare(force) {
        const selA = el('soak-compare-a');
        const selB = el('soak-compare-b');
        const runs = S.state.runs || [];
        if (!selA.options.length || force) {
            const opts = runs.map((r) => `<option value="${esc(r.id)}">${esc(r.label)} (${esc(r.status)})</option>`).join('');
            const a = selA.value; const b = selB.value;
            selA.innerHTML = opts; selB.innerHTML = opts;
            if (a) selA.value = a;
            if (b) selB.value = b;
            else if (runs.length > 1) { selB.value = runs[1].id; selA.value = runs[0].id; }
        }
        const metricSel = el('soak-compare-metric');
        if (!metricSel.options.length) {
            metricSel.innerHTML = S.coreVitals().map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
        }
    }

    async function runCompare() {
        const a = el('soak-compare-a').value;
        const b = el('soak-compare-b').value;
        const metric = el('soak-compare-metric').value;
        if (!a || !b) { toast('Pick two runs to compare', 'warn'); return; }
        if (a === b) { toast('Pick two different runs', 'warn'); return; }
        el('soak-compare-chart').innerHTML = '<div class="soak-hint">Loading samples…</div>';
        let A; let B;
        try {
            [A, B] = await Promise.all([S.fullSamples(a), S.fullSamples(b)]);
        } catch (e) { toast(e.message, 'error'); return; }
        const toSeries = (body, color, dash) => ({
            name: (body.summary && body.summary.scenario_name) || 'run',
            color: color, dash: dash,
            points: (body.samples || []).map((s) => [s.tick, (((s.vitals || {})[metric]) || {}).avg]),
        });
        ui.compareData = { A: A, B: B, metric: metric };
        el('soak-compare-chart').innerHTML = C.renderLineChart({
            width: panelWidth(), height: 300,
            series: [toSeries(A, '#58a6ff'), toSeries(B, '#e3b341', '5 4')],
            yLabel: metric + ' (avg)', xLabel: 'ticks', emptyText: 'No samples in these runs',
        });
        const runsById = {};
        (S.state.runs || []).forEach((r) => { runsById[r.id] = r; });
        const fields = ['ticks_completed', 'characters', 'deaths', 'survivors', 'ticks_per_second',
            'game_log_entries', 'total_memories', 'total_trace', 'graph_nodes'];
        const getVal = (body, id, field) => {
            if (body.summary && body.summary[field] !== undefined) return body.summary[field];
            const r = runsById[id] || {};
            return r[field];
        };
        el('soak-compare-table').innerHTML = '<table class="soak-table"><thead><tr><th>Field</th>'
            + `<th>${esc((runsById[a] || {}).label || 'A')}</th><th>${esc((runsById[b] || {}).label || 'B')}</th></tr></thead><tbody>`
            + fields.map((f) => `<tr><td>${esc(F.titleCase(f))}</td><td>${F.fmtNum(getVal(A, a, f), 1)}</td><td>${F.fmtNum(getVal(B, b, f), 1)}</td></tr>`).join('')
            + '</tbody></table>';
    }

    function buildCli(config) {
        const parts = ['python tools/soak_sim.py', '--scenario', config.scenario];
        parts.push('--ticks', config.ticks);
        if (config.minutes_per_tick) parts.push('--minutes-per-tick', config.minutes_per_tick);
        if (config.engine_decay) parts.push('--engine-decay');
        if (config.neutral_environment) parts.push('--neutral-environment');
        if (config.background_all) parts.push('--background-all');
        if (config.mature) parts.push('--mature');
        if (config.debug_hp) parts.push('--debug-hp');
        const overrides = stringifyMap(config.decay_overrides);
        const seeded = stringifyMap(config.starting_vitals);
        const traits = stringifyMap(config.traits);
        if (overrides) parts.push('--override', `"${overrides}"`);
        if (seeded) parts.push('--set', `"${seeded}"`);
        if (traits) parts.push('--apply-trait', `"${traits}"`);
        if (Number(config.seed) !== 1234) parts.push('--seed', config.seed);
        return parts.join(' ');
    }

    function renderExport() {
        const d = data();
        // Reproduce the selected run (not just the form) when one is loaded.
        const config = (d && d.run && d.run.config) || S.getConfig();
        el('soak-cli').textContent = buildCli(config);
        el('soak-json-preview').textContent = d && d.report
            ? JSON.stringify(d.report.summary, null, 2)
            : 'Report is available once the run finishes.';
    }

    // ─────────────────────────── render orchestration ───────────────────────────

    let chartTimer = null;
    function scheduleCharts() {
        if (chartTimer) return;
        chartTimer = setTimeout(() => { chartTimer = null; renderCharts(); }, 650);
    }

    function renderCharts() {
        const d = data();
        if (!d || !d.run) return;
        switch (ui.activeTab) {
        case 'overview': renderOverview(); break;
        case 'vitals': renderVitals(); break;
        case 'survival': renderSurvival(); break;
        case 'growth': renderGrowthMetrics(); renderGrowth(); break;
        case 'characters': renderCharacters(); break;
        case 'events': renderEvents(); break;
        case 'export': renderExport(); break;
        default: break;
        }
    }

    function renderPane() {
        const hasData = !!data();
        el('soak-dashboard').hidden = !hasData;
        el('soak-empty').hidden = hasData;
        renderProgress();
        if (hasData) scheduleCharts();
    }

    function switchTab(tab) {
        ui.activeTab = tab;
        document.querySelectorAll('.soak-tab').forEach((t) => t.classList.toggle('active', t.getAttribute('data-tab') === tab));
        document.querySelectorAll('.soak-pane').forEach((p) => p.classList.toggle('active', p.getAttribute('data-pane') === tab));
        renderCharts();
    }

    // ─────────────────────────── wiring ───────────────────────────

    function bindForm() {
        const ids = ['soak-scenario', 'soak-ticks', 'soak-minutes', 'soak-seed', 'soak-sample-every',
            'soak-label', 'soak-engine-decay', 'soak-neutral', 'soak-background-all', 'soak-mature',
            'soak-debug-hp', 'soak-track-characters', 'soak-overrides', 'soak-set', 'soak-traits'];
        ids.forEach((id) => {
            const node = el(id);
            node.addEventListener('change', () => { S.setConfig(readForm()); updateHorizon(); });
            if (node.type === 'text' || node.type === 'number') {
                node.addEventListener('input', () => { S.setConfig(readForm()); updateHorizon(); });
            }
        });
        document.querySelectorAll('[data-days]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const cfg = S.getConfig();
                const days = Number(btn.getAttribute('data-days'));
                const ticks = Math.max(1, Math.round((days * 1440) / minutesPerTick(cfg)));
                el('soak-ticks').value = ticks;
                S.setConfig(readForm()); updateHorizon();
                toast(`${days}-day horizon → ${F.fmtInt(ticks)} ticks`, 'info', 2200);
            });
        });
        el('soak-form').addEventListener('submit', async (ev) => {
            ev.preventDefault();
            showFormError('');
            try {
                const run = await S.start();
                toast(`Soak started: ${run.label}`, 'success');
            } catch (e) {
                showFormError(e.message);
                toast(e.message, 'error');
            }
        });
        el('soak-stop').addEventListener('click', async () => {
            try { await S.stop(); toast('Stop requested', 'warn'); }
            catch (e) { toast(e.message, 'error'); }
        });
        el('soak-save-config').addEventListener('click', () => {
            const name = el('soak-saved-name').value.trim() || `Config ${new Date().toLocaleTimeString()}`;
            P.addSaved(name, S.getConfig());
            el('soak-saved-name').value = '';
            renderSaved();
            toast(`Saved “${name}”`, 'success', 2200);
        });
        el('soak-poll-pause').addEventListener('click', () => {
            const paused = !S.state.pollingPaused;
            S.setPollingPaused(paused);
            el('soak-poll-pause').textContent = paused ? '▶ Resume' : '⏸ Pause';
            toast(paused ? 'Live updates paused' : 'Live updates resumed', 'info', 1800);
        });
        el('soak-refresh').addEventListener('click', async () => {
            try { await S.refreshRuns(); toast('Runs refreshed', 'info', 1500); }
            catch (e) { toast(e.message, 'error'); }
        });
        el('soak-vital-mode').addEventListener('change', () => { ui.vitalMode = el('soak-vital-mode').value; renderVitals(); });
        el('soak-vital-band').addEventListener('change', () => { ui.vitalBand = el('soak-vital-band').checked; renderVitals(); });
        el('soak-vital-pct').addEventListener('change', () => { ui.vitalPct = el('soak-vital-pct').checked; renderVitals(); });
        el('soak-growth-log').addEventListener('change', () => { ui.growthLog = el('soak-growth-log').checked; renderGrowth(); });
        el('soak-death-search').addEventListener('input', () => { ui.deathSearch = el('soak-death-search').value; renderDeathsTable(); });
        el('soak-event-search').addEventListener('input', () => { ui.eventSearch = el('soak-event-search').value; renderEvents(); });
        el('soak-event-autoscroll').addEventListener('change', () => { ui.eventAutoscroll = el('soak-event-autoscroll').checked; });
        el('soak-char-search').addEventListener('input', () => { ui.charSearch = el('soak-char-search').value; renderCharacters(); });
        el('soak-char-filter').addEventListener('change', () => { ui.charFilter = el('soak-char-filter').value; renderCharacters(); });
        el('soak-char-sort').addEventListener('change', () => { ui.charSort = el('soak-char-sort').value; renderCharacters(); });
        el('soak-char-detail-close').addEventListener('click', () => { el('soak-char-detail').hidden = true; });
        el('soak-compare-load').addEventListener('click', runCompare);
        el('soak-compare-a').addEventListener('change', renderCompare);
        el('soak-copy-cli').addEventListener('click', () => copy(el('soak-cli').textContent, 'CLI command'));
        el('soak-copy-link').addEventListener('click', () => {
            const d = data();
            const config = (d && d.run && d.run.config) || S.getConfig();
            const qs = F.configToQuery(config);
            const runId = S.state.selectedRunId ? `&run=${S.state.selectedRunId}` : '';
            copy(`${window.location.origin}/soak?${qs}${runId}`, 'Share link');
        });
        document.querySelectorAll('.soak-tab').forEach((tab) => {
            tab.addEventListener('click', () => switchTab(tab.getAttribute('data-tab')));
        });
        document.querySelectorAll('[data-export]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const id = S.state.selectedRunId;
                if (!id) { toast('No run selected', 'warn'); return; }
                const kind = btn.getAttribute('data-export');
                if (kind === 'report') download(`/api/soak/runs/${id}/report?download=1`);
                else if (kind === 'report-samples') download(`/api/soak/runs/${id}/report?download=1&samples=1`);
                else download(window.SoakApi.exportUrl(id, kind));
            });
        });
        window.addEventListener('resize', () => scheduleCharts());
        document.addEventListener('keydown', (ev) => {
            const tag = (ev.target.tagName || '').toLowerCase();
            const typing = tag === 'input' || tag === 'textarea' || tag === 'select';
            if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
                ev.preventDefault();
                el('soak-form').requestSubmit();
                return;
            }
            if (ev.key === 'Escape') {
                if (!el('soak-stop').disabled) el('soak-stop').click();
                return;
            }
            if (typing) return;
            if (ev.key === 'r') el('soak-refresh').click();
            if (ev.key === ' ') { ev.preventDefault(); el('soak-poll-pause').click(); }
            if (ev.key >= '1' && ev.key <= '8') {
                const tabs = document.querySelectorAll('.soak-tab');
                const idx = Number(ev.key) - 1;
                if (tabs[idx]) switchTab(tabs[idx].getAttribute('data-tab'));
            }
        });
    }

    function bindState() {
        S.on((type, payload) => {
            switch (type) {
            case 'meta':
                renderScenarioOptions(); renderPresets(); renderSaved();
                setForm(S.getConfig()); renderCompare(true);
                break;
            case 'config':
                updateHorizon();
                break;
            case 'runs':
                renderRunList(); renderTopChips(); renderCompare();
                break;
            case 'data':
                renderPane(); renderTopChips();
                if (payload && payload.finished && payload.characters && payload.characters.length) {
                    if (ui.activeTab === 'characters') renderCharacters();
                }
                break;
            case 'events': {
                const events = payload || [];
                const deaths = events.filter((e) => e.kind === 'death');
                deaths.forEach((e) => toast(e.message, 'warn', 5000));
                if (ui.activeTab === 'events') renderEvents();
                break;
            }
            case 'report':
                if (ui.activeTab === 'export') renderExport();
                break;
            case 'error':
                toast((payload && payload.message) || 'Request failed', 'error');
                break;
            default: break;
            }
        });
    }

    function init() {
        bindForm();
        bindState();
        renderEventKinds();
    }

    window.SoakUI = { init, toast, switchTab };
})();
