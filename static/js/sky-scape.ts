/**
 * sky-scape.js — Engine-driven Sky Clock (task-228/229/234 UI, roadmap 3.3).
 *
 * Renders the sky state the ENGINE computes (game_time, game_day, moon_phase,
 * forecast schedule + override) in two places:
 *   - the compact top-bar widget (replaces the bare `#ui-time` clock): a single
 *     live line — time · date · moon · weather
 *   - the **World Sky panel** (modal): the animated sky STAGE from
 *     docs/design/sky-clock-mockup-v2-real-moon.html, ported to be driven by
 *     live state instead of demo chips. Controls (time skips, moon/weather
 *     displays) read the engine; authoring happens through the forecast APIs.
 *
 * Pure presentation — no state of its own; every render takes `state` from
 * `/api/state` (worldState.data) and refreshes on state:updated.
 *
 * @module sky-scape — the engine-driven Sky Clock UI
 * @contributes SkyScape: top-bar time/date/moon/weather line + the World Sky modal stage
 * @powers Time & weather — seeing the sky state the engine computes (task-228/229/234)
 * @relates pure presentation over /api/state; refreshes on state:updated
 * @docs docs/design/sky-widget-reconciled.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

// The local binding is `_SkyScape` because `SkyScape` is already a declared
// ambient global in types/globals.d.ts; a top-level `const SkyScape` would be a
// duplicate declaration.
const _SkyScape = (() => {
    'use strict';

    // ── Weather chips (from Time & Weather.md + forecast states) ──
    const WEATHER_CHIP: Record<string, string> = {
        'clear': '☀️', 'cloudy': '☁️', 'rainy': '🌧️', 'stormy': '⛈️',
        'foggy': '🌫️', 'windy': '💨', 'snowy': '🌨️', 'rain': '🌧️',
        'storm': '⛈️', 'snow': '🌨️',
    };
    // The map above is the **fallback** now (task-772): the weather vocabulary
    // is library data (`data/library/weather`), so the live icons are fetched
    // from `/api/vocabulary/weather` and override it. The built-in map still
    // covers the first frame before the fetch resolves and the non-canonical
    // spellings ("rain", "storm") an authored schedule may carry.
    const _WEATHER_ICONS: Record<string, string> = {};
    // The canonical registry ids, in registry order — kept separate from
    // `_WEATHER_ICONS`, which also holds alias spellings for chip lookup and
    // must not be offered as selectable weather in a dropdown.
    const _WEATHER_IDS: string[] = [];
    let _vocabLoaded = false;
    let _repaint: (() => void) | null = null;

    /** Icon for a weather value: registry first, built-in map, else the fallback. */
    function _weatherChip(w: string, fallback = '☀️'): string {
        return _WEATHER_ICONS[w] || WEATHER_CHIP[w] || fallback;
    }

    /** Fetch the weather-type icons from the library registry once (task-772). */
    function _loadWeatherVocabulary(): void {
        if (_vocabLoaded) return;
        _vocabLoaded = true;
        fetch('/api/vocabulary/weather', { cache: 'no-store' })
            .then((r) => (r.ok ? r.json() : null))
            .then((d) => {
                const entries = (d && d.entries) || [];
                _WEATHER_IDS.length = 0;
                for (const e of entries) {
                    const icon = e && e.record && e.record.icon;
                    if (e && e.id && icon) _WEATHER_ICONS[e.id] = icon;
                    if (e && e.id && !_WEATHER_IDS.includes(e.id)) _WEATHER_IDS.push(e.id);
                }
                // Resolve authored spellings ("overcast") to their canonical
                // id's icon; the alias table comes from the engine, not a copy.
                const aliases: Record<string, string> = (d && d.aliases) || {};
                for (const [spelling, cid] of Object.entries(aliases)) {
                    if (_WEATHER_ICONS[cid]) _WEATHER_ICONS[spelling] = _WEATHER_ICONS[cid];
                }
                if (_repaint) _repaint();
            })
            .catch(() => { /* keep the fallback icons */ });
    }
    const MOON_CHIP: Record<string, string> = {
        'new_moon': '🌑', 'crescent': '🌒', 'quarter': '🌓', 'gibbous': '🌔',
        'full_moon': '🌕', 'waning': '🌖', 'blood_moon': '🔴',
    };
    // The month→season table is **not here** (task-554). It was duplicated in
    // this file — once as SEASON_BY_MONTH and once inline in the iframe
    // postMessage — while the engine read a season nowhere, so "winter" only ever
    // meant a sky tint. The engine resolves the season from the clock and ships it
    // in world_state; these two functions are the one place it is read.

    let _modalEl: HTMLElement | null = null;
    let _timer: ReturnType<typeof setInterval> | null = null;

    // ── state helpers ──────────────────────────────────────────────────

    function _monthName(m: number): string {
        return ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m % 13] || '';
    }

    /** Days in a game month, from the scenario's calendar (default 30). */
    function _daysPerMonth(state: SkyState): number {
        const cfg = state && state.calendar_config;
        const n = cfg && Number(cfg.days_per_month);
        return Number.isFinite(n) && (n as number) > 0 ? Math.floor(n as number) : 30;
    }
    /** Day-of-month (1-based). ``game_day`` is the absolute day, so the raw
     *  counter must be reduced mod the month length to read as a date. */
    function _dayOfMonth(state: SkyState): number {
        const dpm = _daysPerMonth(state);
        return ((Math.max(1, Number(state?.game_day) || 1) - 1) % dpm) + 1;
    }
    /**
     * The season the engine says it is, with the old month table as a fallback
     * only for the frames before the first state arrives. That fallback is
     * deliberately the *old* table and nothing more: a second real table is what
     * this change removed.
     */
    function _season(state: SkyState): string {
        const fromEngine = state?.season;
        if (typeof fromEngine === 'string' && fromEngine) return fromEngine;
        const m = Math.max(1, Math.min(12, (state?.game_month || 1)));
        return ['winter', 'winter', 'spring', 'spring', 'spring',
            'summer', 'summer', 'summer', 'autumn', 'autumn', 'autumn',
            'winter'][m - 1] || 'summer';
    }

    /** Effective weather: override wins, else the forecast entry at "now". */
    function effectiveWeather(state: SkyState): string {
        const ov = state?.forecast_override;
        if (ov && ov.weather) return ov.weather;
        const sched = state?.forecast_schedule;
        if (sched && Array.isArray(sched.entries) && sched.entries.length) {
            const period = GRANULARITY_MINUTES[sched.granularity || ''] || 1440;
            const day = (state?.game_day || 1) - 1;
            const [hh, mm] = (state?.game_time || '00:00').split(':').map(Number);
            const offset = ((sched.granularity === 'hourly' ? 0 : day * 1440) + (hh || 0) * 60 + (mm || 0)) % period;
            let found = null;
            for (let i = 0; i < sched.entries.length; i++) {
                const e = sched.entries[i];
                const start = Number(e.offset || 0);
                const end = i + 1 < sched.entries.length ? Number(sched.entries[i + 1].offset || 0) : period;
                if (start <= offset && offset < end) { found = e; break; }
            }
            if (found && found.weather) return found.weather;
        }
        return 'clear';
    }

    /** Next forecast change from "now" (minutes + label), for the widget. */
    function nextForecastChange(state: SkyState): ForecastChange | null {
        const sched = state?.forecast_schedule;
        if (!sched || !Array.isArray(sched.entries) || sched.entries.length < 2) return null;
        const period = GRANULARITY_MINUTES[sched.granularity || ''] || 1440;
        const day = sched.granularity === 'hourly' ? 0 : ((state?.game_day || 1) - 1) * 1440;
        const [hh, mm] = (state?.game_time || '00:00').split(':').map(Number);
        const now = (day + (hh || 0) * 60 + (mm || 0)) % period;
        const sorted = [...sched.entries].sort((a, b) => (a.offset || 0) - (b.offset || 0));
        for (const e of sorted) {
            const off = Number(e.offset || 0);
            if (off > now) {
                const delta = Math.round(off - now);
                const h = Math.floor(delta / 60), m = delta % 60;
                const when = h > 0 ? (m ? `${h}h ${m}m` : `${h}h`) : `${m}m`;
                return { when, weather: e.weather || 'change', label: `in ${when}: ${e.weather || 'change'}` };
            }
        }
        const first = Number(sorted[0]?.offset || 0) + period;
        const delta = Math.round(first - now);
        return { when: `${Math.floor(delta / 60)}h`, weather: sorted[0]?.weather, label: `in ${Math.floor(delta / 60)}h` };
    }

    // ── top-bar widget ─────────────────────────────────────────────────

    function renderTopBar(el: SkyTopBarEl | null, state: SkyState) {
        if (!el) return;
        const moon = state?.moon_phase || {};
        const weather = effectiveWeather(state);
        const moonIcon = MOON_CHIP[moon.name || ''] || '🌑';
        const weatherIcon = _weatherChip(weather);
        const date = `${_monthName(state?.game_month || 0)} ${_dayOfMonth(state)}, ${state?.game_year || 1}`;
        const moonLabel = (moon.name || '').replace(/_/g, ' ');
        const next = nextForecastChange(state);
        let html = `🕐 ${(state?.game_time || '').slice(0, 5)}`;
        html += ` · ${date}`;
        html += ` · <span title="Moon phase (light bonus ${moon.light_bonus || 0})">${moonIcon} ${moonLabel}</span>`;
        html += ` · <span title="Weather">${weatherIcon} ${weather}</span>`;
        if (next) html += ` · <span title="Next forecast change">${next.weather ? _weatherChip(next.weather, '⛅') : ''} ${next.label}</span>`;
        el.textContent = '';
        el.title = 'World Sky — click to open';
        el.style.cursor = 'pointer';
        const span = document.createElement('span');
        span.innerHTML = html;
        el.appendChild(span);
        if (!el._skyClickBound) {
            el._skyClickBound = true;
            el.addEventListener('click', () => _SkyScape.openWorldSky());
        }    }

    // ── World Sky modal ────────────────────────────────────────────────

    function openWorldSky() {
        if (_modalEl) { _modalEl.style.display = 'flex'; _sendStateToIframe(); return; }
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);display:flex;align-items:flex-start;justify-content:center;z-index:21000;';
        const box = document.createElement('div');
        // task-762: the box must scroll. It now carries the forecast editor below
        // the stage, so with `overflow:hidden` the editor was clipped and
        // unreachable on any viewport shorter than the whole modal.
        box.style.cssText = 'background:var(--bg-card,#121522);border:1px solid var(--border,#262c3f);border-radius:16px;margin-top:6vh;width:min(960px,94vw);max-width:94vw;max-height:90vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,0.5);';
        box.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:11px 18px;border-bottom:1px solid var(--border,#262c3f);">
                <div style="font-weight:700;font-size:13px;letter-spacing:.16em;">🌍 ATMOSPHERE <span style="font-size:10px;color:var(--text-dim,#6b7390);margin-left:2px;">time · season · weather · moon</span></div>
                <button class="btn btn-sm btn-ghost" id="sky-close" style="padding:0 6px;">✕</button>
            </div>
            <iframe id="sky-atmosphere-frame" src="/static/sky-atmosphere.html" style="width:100%;border:none;display:block;background:#000;min-height:520px;"></iframe>
            <div style="padding:8px 14px;border-top:1px solid var(--border,#262c3f);display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
                <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">⏰ Time:</span>
                <input type="time" id="sky-time-input" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;width:80px;" title="Exact time (HH:MM)">
                <button class="btn btn-sm btn-ghost sky-set-time" style="font-size:10px;padding:3px 8px;">Set</button>
                <span style="border-left:1px solid var(--border,#262c3f);height:22px;width:0;"></span>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="-15">-15m</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="-60">-1h</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="15">+15m</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="60">+1h</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="1440">+1d</button>
                <span style="border-left:1px solid var(--border,#262c3f);height:22px;width:0;"></span>
                <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">📅 Date:</span>
                <input type="number" id="sky-date-day" min="1" max="30" style="width:44px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="Day">
                <span style="color:var(--text-dim);font-size:11px;">/</span>
                <input type="number" id="sky-date-month" min="1" max="12" style="width:44px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="Month">
                <span style="color:var(--text-dim);font-size:11px;">/</span>
                <input type="number" id="sky-date-year" min="1" style="width:56px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="Year">
                <button class="btn btn-sm btn-ghost sky-set-date" style="font-size:10px;padding:3px 8px;">Set</button>
            </div>
            <div style="padding:8px 14px;border-top:1px solid var(--border,#262c3f);display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
                <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">🌤 Override:</span>
                <select id="sky-override-weather" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;">
                    <option value="">— weather</option>
                    <option value="clear">☀️ clear</option><option value="cloudy">☁️ cloudy</option><option value="rainy">🌧️ rainy</option>
                    <option value="stormy">⛈️ stormy</option><option value="snowy">🌨️ snowy</option><option value="foggy">🌫️ foggy</option><option value="windy">💨 windy</option>
                </select>
                <select id="sky-override-wind" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;">
                    <option value="">— wind</option>
                    <option value="none">none</option><option value="breeze">breeze</option><option value="wind">wind</option>
                    <option value="gale">gale</option><option value="storm">storm</option><option value="hurricane">hurricane</option>
                </select>
                <select id="sky-override-wind-direction" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="wind direction (from)">
                    <option value="">— dir</option>
                    <option value="north">N ↑</option><option value="northeast">NE ↗</option><option value="east">E →</option>
                    <option value="southeast">SE ↘</option><option value="south">S ↓</option><option value="southwest">SW ↙</option>
                    <option value="west">W ←</option><option value="northwest">NW ↖</option>
                </select>
                <select id="sky-override-humidity" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;">
                    <option value="">— humidity</option>
                    <option value="dry">dry</option><option value="humid">humid</option><option value="wet">wet</option><option value="flooding">flooding</option>
                </select>
                <input type="number" id="sky-override-duration" min="1" value="5" style="width:52px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="duration (turns)">
                <button class="btn btn-sm btn-primary" id="sky-override-set" style="font-size:11px;">Set</button>
                <button class="btn btn-sm btn-ghost" id="sky-override-clear" style="font-size:11px;">Clear</button>
                <span class="sky-override-active" style="display:none;font-size:10px;color:var(--orange,#f0883e);margin-left:4px;">● override active</span>
            </div>
            <div style="padding:8px 14px;border-top:1px solid var(--border,#262c3f);">
                <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:6px;">
                    <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">🌦 Forecast:</span>
                    <select id="sky-sched-mode" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="schedule mode">
                        <option value="authored">authored</option>
                        <option value="deterministic">deterministic</option>
                        <option value="random">random</option>
                        <option value="hybrid">hybrid</option>
                        <option value="generated">generated</option>
                    </select>
                    <select id="sky-sched-granularity" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="period over which entries repeat">
                        <option value="hourly">hourly (1 day)</option>
                        <option value="weekly">weekly (7 days)</option>
                        <option value="yearly">yearly (365 days)</option>
                    </select>
                    <label style="font-size:10px;color:var(--text-dim,#6b7390);">seed <input type="number" id="sky-sched-seed" style="width:76px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="reproducibility seed"></label>
                    <label style="font-size:10px;color:var(--text-dim,#6b7390);">interval <input type="number" id="sky-sched-interval" min="1" value="1" style="width:56px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="ticks between state-machine transitions"></label>
                    <button class="btn btn-sm btn-ghost" id="sky-sched-add" style="font-size:10px;padding:3px 8px;">+ entry</button>
                    <button class="btn btn-sm btn-primary" id="sky-sched-save" style="font-size:10px;padding:3px 8px;">Save schedule</button>
                    <span class="sky-sched-status" style="font-size:10px;color:var(--text-dim,#6b7390);margin-left:auto;"></span>
                </div>
                <div id="sky-sched-timeline" style="position:relative;height:20px;border-bottom:1px solid var(--border,#262c3f);margin-bottom:4px;"></div>
                <div id="sky-sched-entries" style="display:flex;flex-direction:column;gap:4px;max-height:180px;overflow:auto;"></div>
                <div style="font-size:9.5px;color:var(--text-dim,#6b7390);margin-top:4px;line-height:1.45;">Offsets are minutes into the period; entries repeat each period. Temperature and light are shown <em>in-game</em> as engine-derived values (base_temperature + diurnal/seasonal curve + climate); here you author only the <code>temperature_mod</code>/<code>light_mod</code> deltas. <code>wind</code> is magnitude; <code>wind_direction</code> is where it blows <em>from</em>. No precipitation is modelled yet. authored &amp; hybrid use the entries; deterministic / random / generated roll the table.</div>
                <details style="margin-top:6px;">
                    <summary style="font-size:10px;color:var(--text-dim,#6b7390);cursor:pointer;">transition table (deterministic / random / generated)</summary>
                    <textarea id="sky-sched-table" spellcheck="false" placeholder='{ "clear": { "clear": 7, "cloudy": 2 } }' style="width:100%;min-height:92px;margin-top:4px;font-family:ui-monospace,monospace;font-size:10.5px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:6px;box-sizing:border-box;"></textarea>
                </details>
            </div>
            <div style="padding:8px 14px;font-size:10.5px;color:var(--text-dim,#6b7390);border-top:1px solid var(--border,#262c3f);">Clock: <code id="sky-clock-readout"></code> · Moon: <code id="sky-moon-readout"></code> · Forecast: <code id="sky-forecast-readout"></code></div>
        `;
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        _modalEl = overlay;
        overlay.addEventListener('mousedown', (ev) => { if (ev.target === overlay) _closeSky(); });
        box.querySelector('#sky-close')!.addEventListener('click', _closeSky);
        box.querySelectorAll<HTMLElement>('.sky-skip').forEach(btn => {
            btn.addEventListener('click', () => {
                _skipTime(Number(btn.dataset.min || 60));
                _populateControls();
            });
        });
        box.querySelector('.sky-set-time')?.addEventListener('click', _setExactTime);
        box.querySelector('.sky-set-date')?.addEventListener('click', _setExactDate);
        box.querySelector('#sky-override-set')?.addEventListener('click', _setOverride);
        box.querySelector('#sky-override-clear')?.addEventListener('click', _clearOverride);
        box.querySelector('#sky-sched-add')?.addEventListener('click', () => _addEntryRow());
        box.querySelector('#sky-sched-save')?.addEventListener('click', _saveSchedule);
        // Wire iframe load → feed state
        const iframe = document.getElementById('sky-atmosphere-frame') as HTMLIFrameElement | null;
        iframe!.addEventListener('load', () => _sendStateToIframe());
        // Listen for 'sky:ready' from the iframe
        window.addEventListener('message', (ev) => {
            if (ev.data?.type === 'sky:ready') _sendStateToIframe();
        });
        _populateControls();
        _sendStateToIframe();
        // Poll state updates to the iframe
        if (_timer) clearInterval(_timer);
        _timer = setInterval(() => {
            if (document.contains(overlay)) _sendStateToIframe();
        }, 3000);
    }

    function _sendStateToIframe() {
        const iframe = document.getElementById('sky-atmosphere-frame') as HTMLIFrameElement | null;
        if (!iframe || !iframe.contentWindow) return;
        const state = _state();
        const t = (state?.game_time || '09:40').split(':').map(Number);
        const hour = (t[0] || 0) + (t[1] || 0) / 60;
        // The engine's season, from the same helper the header uses (task-554).
        const season = _season(state);
        const weather = effectiveWeather(state);
        const weatherMap: Record<string, string> = { clear: 'clear', cloudy: 'overcast', rainy: 'rain', stormy: 'storm', snowy: 'snow', foggy: 'fog', windy: 'partly' };
        const moonIdx: Record<string, number> = { new_moon: 0, crescent: 1, quarter: 2, gibbous: 3, full_moon: 4, waning: 5, blood_moon: 4 };
        const moon = state?.moon_phase || {};
        const phase = moonIdx[moon.name || ''] !== undefined ? moonIdx[moon.name || ''] : 0;
        iframe.contentWindow.postMessage({
            type: 'engine:sky-state',
            t: hour,
            season: season,
            weather: weatherMap[weather] || 'clear',
            phase: phase,
            engineTime: (state?.game_time || '').slice(0, 5),
            engineDay: state?.game_day || 1,
        }, '*');
    }

    function _closeSky() {
        if (_timer) { clearInterval(_timer); _timer = null; }
        if (_modalEl) _modalEl.remove();
        _modalEl = null;
    }

    function _state(): SkyState {
        return (typeof worldState !== 'undefined' && worldState.data) || {};
    }

    function _skipTime(minutes: number) {
        const state = _state();
        const [hh, mm] = (state.game_time || '08:00').split(':').map(Number);
        const targetMin = ((hh || 0) * 60 + (mm || 0) + minutes) % 1440;
        // Clamp to 0..1439 (negative wraparound)
        const clamped = ((targetMin % 1440) + 1440) % 1440;
        fetch('/api/settings/clock_start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clock_start_hour: Math.floor(clamped / 60), clock_start_minute: clamped % 60 })
        }).then(() => worldState?.fetch?.());
    }

    function _setExactTime() {
        const input = document.getElementById('sky-time-input') as HTMLInputElement | null;
        if (!input || !input.value) return;
        const [h, m] = input.value.split(':').map(Number);
        if (isNaN(h) || isNaN(m)) return;
        fetch('/api/settings/clock_start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clock_start_hour: h, clock_start_minute: m })
        }).then(() => worldState?.fetch?.());
    }

    function _setExactDate() {
        const d = parseInt((document.getElementById('sky-date-day') as HTMLInputElement | null)?.value || '');
        const m = parseInt((document.getElementById('sky-date-month') as HTMLInputElement | null)?.value || '');
        const y = parseInt((document.getElementById('sky-date-year') as HTMLInputElement | null)?.value || '');
        if (isNaN(d) && isNaN(m) && isNaN(y)) return;
        const body: Record<string, number> = {};
        if (!isNaN(d)) body.day = d;
        if (!isNaN(m)) body.month = m;
        if (!isNaN(y)) body.year = y;
        fetch('/api/settings/date', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }).then(() => worldState?.fetch?.());
    }

    function _setOverride() {
        const weather = (document.getElementById('sky-override-weather') as HTMLSelectElement | null)?.value || '';
        const wind = (document.getElementById('sky-override-wind') as HTMLSelectElement | null)?.value || '';
        const windDir = (document.getElementById('sky-override-wind-direction') as HTMLSelectElement | null)?.value || '';
        const humidity = (document.getElementById('sky-override-humidity') as HTMLSelectElement | null)?.value || '';
        const dur = parseInt((document.getElementById('sky-override-duration') as HTMLInputElement | null)?.value || '5');
        const data: Record<string, unknown> = {};
        if (weather) data.weather = weather;
        if (wind) data.wind = wind;
        if (windDir) data.wind_direction = windDir;
        if (humidity) data.humidity = humidity;
        if (dur > 0) data.duration_ticks = dur;
        fetch('/api/settings/forecast-override', {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-WV-Editor': 'sky-widget' },
            body: JSON.stringify(data)
        }).then(() => worldState?.fetch?.());
    }

    function _clearOverride() {
        fetch('/api/settings/forecast-override', {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-WV-Editor': 'sky-widget' },
            body: JSON.stringify({ clear_all: true })
        }).then(() => worldState?.fetch?.());
    }

    function _populateControls() {
        const state = _state();
        if (!state) return;
        const timeInput = document.getElementById('sky-time-input') as HTMLInputElement | null;
        const dayInput = document.getElementById('sky-date-day') as HTMLInputElement | null;
        const monthInput = document.getElementById('sky-date-month') as HTMLInputElement | null;
        const yearInput = document.getElementById('sky-date-year') as HTMLInputElement | null;
        const clockReadout = document.getElementById('sky-clock-readout');
        const moonReadout = document.getElementById('sky-moon-readout');
        const forecastReadout = document.getElementById('sky-forecast-readout');
        const overrideActive = document.querySelector<HTMLElement>('.sky-override-active');
        if (timeInput) {
            const t = (state.game_time || '09:40').slice(0, 5);
            timeInput.value = t;
        }
        if (dayInput) { dayInput.value = String(_dayOfMonth(state)); dayInput.max = String(_daysPerMonth(state)); }
        if (monthInput) monthInput.value = String(state.game_month || 1);
        if (yearInput) yearInput.value = String(state.game_year || 1);
        if (clockReadout) clockReadout.textContent = `${state.game_time || '?'} · Day ${state.game_day || 1}, ${_monthName(state.game_month || 1)} ${state.game_year || 1}`;
        if (moonReadout) {
            const moon = state.moon_phase || {};
            const icon = MOON_CHIP[moon.name || ''] || '🌑';
            const label = (moon.name || '').replace(/_/g, ' ');
            const bonus = moon.light_bonus || 0;
            const next = nextForecastChange(state);
            moonReadout.textContent = `${icon} ${label} (+${bonus} night light) · ${next ? `next: ${next.weather || 'change'} ${next.label}` : 'no forecast change'}`;
        }
        if (forecastReadout) {
            const sched = state.forecast_schedule || {};
            const entries = (sched.entries || []).length;
            const ov = state.forecast_override;
            forecastReadout.textContent = `${entries} entries (${sched.granularity || 'hourly'})${ov ? ' · GM override ACTIVE' : ''}`;
        }
        if (overrideActive) {
            const ov = state.forecast_override;
            overrideActive.style.display = ov ? 'inline' : 'none';
        }
        _populateWeatherSelect();
        _renderScheduleEditor();
    }

    // ── forecast schedule editor (task-762) ─────────────────────────────
    // Author and view `forecast_schedule` over the existing GET/POST
    // /api/settings/forecast — no second engine. The timeline lays the entries
    // out over the period granularity and each row edits one entry; the columns
    // are honest (deltas, not a per-entry temperature; no precipitation, which
    // is not modelled).

    const SCHED_WEATHER_ORDER = ['clear', 'cloudy', 'windy', 'rainy', 'stormy', 'foggy', 'snowy'];
    const SCHED_WINDS = ['none', 'breeze', 'wind', 'gale', 'storm', 'hurricane'];
    const SCHED_DIRECTIONS = ['north', 'northeast', 'east', 'southeast',
        'south', 'southwest', 'west', 'northwest'];
    const SCHED_HUMIDITIES = ['dry', 'humid', 'wet', 'flooding'];
    // offset · weather · wind · dir · humidity · tempΔ · lightΔ · air · message · ✕
    // min-width keeps the grid from crushing; the container scrolls sideways.
    const SCHED_ROW_STYLE = 'display:grid;grid-template-columns:76px 1.05fr 0.85fr 0.85fr 0.8fr 58px 58px 0.75fr 1.3fr 22px;gap:4px;align-items:center;min-width:860px;';
    const SCHED_FIELD_STYLE = 'font-size:10.5px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:5px;padding:3px;min-width:0;';

    /** Minimal HTML-escape for values the author types into the modal. */
    function _esc(s: unknown): string {
        return String(s == null ? '' : s).replace(/[&<>"]/g, (c) =>
            ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] as string));
    }

    function _options(values: string[], selected: string, blank: string): string {
        let html = `<option value="">${_esc(blank)}</option>`;
        for (const v of values) {
            html += `<option value="${_esc(v)}"${v === selected ? ' selected' : ''}>${_esc(v)}</option>`;
        }
        if (selected && !values.includes(selected)) {
            html += `<option value="${_esc(selected)}" selected>${_esc(selected)}</option>`;
        }
        return html;
    }

    /** Weather ids for the entry select: the canonical set plus any registry ids. */
    function _weatherIds(): string[] {
        const ids = [...SCHED_WEATHER_ORDER];
        for (const id of _WEATHER_IDS) if (!ids.includes(id)) ids.push(id);
        return ids;
    }

    /** Rebuild the override weather dropdown from the registry (task-772), so a
     *  world's own extreme types are selectable, not just the built-in seven. */
    function _populateWeatherSelect(): void {
        const sel = document.getElementById('sky-override-weather') as HTMLSelectElement | null;
        if (!sel) return;
        const ids = _weatherIds();
        const sig = ids.join(',');
        if (sel.dataset.sig === sig) return;     // registry unchanged since last build
        sel.dataset.sig = sig;
        const current = sel.value;
        sel.innerHTML = '<option value="">— weather</option>' + ids.map((id) => {
            const chip = _weatherChip(id, '');
            return `<option value="${_esc(id)}"${id === current ? ' selected' : ''}>${chip ? chip + ' ' : ''}${_esc(id)}</option>`;
        }).join('');
    }

    /** A compact "where in the period" label for an offset in minutes. */
    function _offsetHint(off: number, granularity: string): string {
        if (!Number.isFinite(off) || off < 0) return '';
        const hh = Math.floor((off % 1440) / 60);
        const mm = off % 60;
        const t = `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
        const days = Math.floor(off / 1440);
        if (granularity === 'hourly') return t;
        if (granularity === 'weekly') return `D${days + 1} ${t}`;
        return `+${days}d ${t}`;
    }

    function _entryFieldsHtml(e: ForecastEntry): string {
        const num = (v: unknown) => (v === undefined || v === null || v === '' ? '' : String(v));
        return ''
            + `<input type="number" data-f="offset" value="${num(e.offset ?? 0)}" title="minutes into the period" style="${SCHED_FIELD_STYLE}">`
            + `<select data-f="weather" title="weather" style="${SCHED_FIELD_STYLE}">${_options(_weatherIds(), e.weather || '', '— weather')}</select>`
            + `<select data-f="wind" title="wind magnitude" style="${SCHED_FIELD_STYLE}">${_options(SCHED_WINDS, e.wind || '', '— wind')}</select>`
            + `<select data-f="wind_direction" title="wind blows from" style="${SCHED_FIELD_STYLE}">${_options(SCHED_DIRECTIONS, e.wind_direction || '', '— dir')}</select>`
            + `<select data-f="humidity" title="humidity" style="${SCHED_FIELD_STYLE}">${_options(SCHED_HUMIDITIES, e.humidity || '', '— humidity')}</select>`
            + `<input type="number" step="0.5" data-f="temperature_mod" value="${num(e.temperature_mod)}" title="temperature delta (°C)" style="${SCHED_FIELD_STYLE}">`
            + `<input type="number" step="1" data-f="light_mod" value="${num(e.light_mod)}" title="light delta" style="${SCHED_FIELD_STYLE}">`
            + `<input type="text" data-f="air" value="${_esc(e.air)}" placeholder="air" title="air (free text)" style="${SCHED_FIELD_STYLE}">`
            + `<input type="text" data-f="message" value="${_esc(e.message)}" placeholder="message" title="log message on this entry" style="${SCHED_FIELD_STYLE}">`
            + `<button class="btn btn-sm btn-ghost sky-sched-del" title="remove entry" style="padding:0 4px;font-size:10px;">✕</button>`;
    }

    function _wireRow(row: HTMLElement): void {
        row.querySelector('.sky-sched-del')?.addEventListener('click', () => row.remove());
    }

    function _addEntryRow(e?: ForecastEntry): void {
        const box = document.getElementById('sky-sched-entries');
        if (!box) return;
        const granularity = (document.getElementById('sky-sched-granularity') as HTMLSelectElement | null)?.value || 'hourly';
        const row = document.createElement('div');
        row.className = 'sky-sched-row';
        row.setAttribute('style', SCHED_ROW_STYLE);
        row.innerHTML = _entryFieldsHtml(e || { offset: _nextOffset() });
        _wireRow(row);
        // Drop the "no entries" placeholder if present.
        box.querySelector('div:not(.sky-sched-row)')?.remove();
        box.appendChild(row);
        if (e?.offset !== undefined) {
            const off = row.querySelector('[data-f="offset"]') as HTMLInputElement | null;
            if (off) off.title = _offsetHint(Number(e.offset), granularity);
        }
    }

    /** One past the last entry's offset, so a new row lands after the others. */
    function _nextOffset(): number {
        let max = -1;
        document.querySelectorAll('#sky-sched-entries [data-f="offset"]').forEach((el) => {
            const v = parseFloat((el as HTMLInputElement).value);
            if (Number.isFinite(v) && v > max) max = v;
        });
        return max + 60;
    }

    function _renderScheduleEditor(): void {
        const state = _state();
        const sched = (state.forecast_schedule || {}) as ForecastSchedule;
        const mode = document.getElementById('sky-sched-mode') as HTMLSelectElement | null;
        const gran = document.getElementById('sky-sched-granularity') as HTMLSelectElement | null;
        const seed = document.getElementById('sky-sched-seed') as HTMLInputElement | null;
        const interval = document.getElementById('sky-sched-interval') as HTMLInputElement | null;
        if (mode) mode.value = sched.mode || 'authored';
        if (gran) gran.value = sched.granularity || 'hourly';
        if (seed) seed.value = (sched.seed === null || sched.seed === undefined) ? '' : String(sched.seed);
        if (interval) interval.value = String(sched.transition_interval || 1);
        const table = document.getElementById('sky-sched-table') as HTMLTextAreaElement | null;
        if (table) {
            const tt = sched.transition_table;
            table.value = (tt && Object.keys(tt).length) ? JSON.stringify(tt, null, 2) : '';
        }
        _renderTimeline(sched);
        const box = document.getElementById('sky-sched-entries');
        if (!box) return;
        const entries = Array.isArray(sched.entries) ? sched.entries : [];
        if (!entries.length) {
            box.innerHTML = `<div style="font-size:10px;color:var(--text-dim,#6b7390);">no entries — click “+ entry”</div>`;
            return;
        }
        box.innerHTML = '';
        for (const e of entries) _addEntryRow(e);
    }

    /** A thin bar over the period with a chip per entry — the "timeline". */
    function _renderTimeline(sched: ForecastSchedule): void {
        const bar = document.getElementById('sky-sched-timeline');
        if (!bar) return;
        const granularity = sched.granularity || 'hourly';
        const period = GRANULARITY_MINUTES[granularity] || 1440;
        const entries = Array.isArray(sched.entries) ? sched.entries : [];
        const marks = entries.map((e) => {
            const off = Number(e.offset || 0);
            const pct = Math.min(100, Math.max(0, (off / period) * 100));
            const label = `${_offsetHint(off, granularity)} ${e.weather || ''}`.trim();
            return `<span title="${_esc(label)}" style="position:absolute;left:${pct}%;transform:translateX(-50%);font-size:12px;line-height:20px;">${_weatherChip(e.weather || '', '·')}</span>`;
        }).join('');
        bar.innerHTML = marks;
    }

    /** Read the editor DOM back into a schedule, or report a validation error. */
    function _collectSchedule(): { schedule?: Record<string, unknown>; error?: string } {
        const mode = (document.getElementById('sky-sched-mode') as HTMLSelectElement | null)?.value || 'authored';
        const granularity = (document.getElementById('sky-sched-granularity') as HTMLSelectElement | null)?.value || 'hourly';
        const seedRaw = (document.getElementById('sky-sched-seed') as HTMLInputElement | null)?.value ?? '';
        const intervalRaw = (document.getElementById('sky-sched-interval') as HTMLInputElement | null)?.value ?? '1';
        const tableRaw = (document.getElementById('sky-sched-table') as HTMLTextAreaElement | null)?.value ?? '';
        let transition_table: unknown = {};
        if (tableRaw.trim()) {
            try { transition_table = JSON.parse(tableRaw); }
            catch { return { error: 'transition table is not valid JSON' }; }
            if (typeof transition_table !== 'object' || transition_table === null || Array.isArray(transition_table)) {
                return { error: 'transition table must be a JSON object' };
            }
        }
        const entries: Record<string, unknown>[] = [];
        document.querySelectorAll('#sky-sched-entries .sky-sched-row').forEach((row) => {
            const get = (f: string) => (row.querySelector(`[data-f="${f}"]`) as HTMLInputElement | HTMLSelectElement | null)?.value ?? '';
            const entry: Record<string, unknown> = { offset: parseInt(get('offset') || '0', 10) || 0 };
            for (const f of ['weather', 'wind', 'wind_direction', 'humidity', 'air', 'message']) {
                const v = get(f).trim();
                if (v) entry[f] = v;
            }
            const tm = parseFloat(get('temperature_mod'));
            if (Number.isFinite(tm)) entry.temperature_mod = tm;
            const lm = parseFloat(get('light_mod'));
            if (Number.isFinite(lm)) entry.light_mod = lm;
            entries.push(entry);
        });
        entries.sort((a, b) => (Number(a.offset) || 0) - (Number(b.offset) || 0));
        const schedule: Record<string, unknown> = {
            mode, granularity, entries,
            current_state: ((_state().forecast_schedule || {}) as ForecastSchedule).current_state || 'clear',
            transition_interval: Math.max(1, parseInt(intervalRaw, 10) || 1),
            transition_table,
            seed: seedRaw.trim() ? (parseInt(seedRaw, 10) || 0) : null,
        };
        return { schedule };
    }

    function _saveSchedule(): void {
        const status = document.querySelector<HTMLElement>('.sky-sched-status');
        const collected = _collectSchedule();
        if (collected.error) {
            if (status) { status.textContent = '✗ ' + collected.error; status.style.color = 'var(--red,#f85149)'; }
            return;
        }
        fetch('/api/settings/forecast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-WV-Editor': 'sky-widget' },
            body: JSON.stringify({ schedule: collected.schedule }),
        })
            .then((r) => (r.ok ? r.json() : Promise.reject('HTTP ' + r.status)))
            .then(() => {
                if (status) { status.textContent = '✓ saved'; status.style.color = 'var(--green,#3fb950)'; }
                return worldState?.fetch?.();
            })
            .catch((err) => {
                if (status) { status.textContent = '✗ ' + err; status.style.color = 'var(--red,#f85149)'; }
            });
    }

    // ── wiring ─────────────────────────────────────────────────────────

    // Declared before `wire` is bound so `_done` is a plain `boolean` rather
    // than the `false` literal TypeScript would otherwise infer here.
    const _wireState = { done: false };
    function wire() {
        if (_wireState.done) return;
        _wireState.done = true;
        function _paint() {
            const el = document.getElementById('sky-time') as SkyTopBarEl | null;
            if (el && worldState?.data) renderTopBar(el, _state());
            if (_modalEl) {
                _populateWeatherSelect();
                _sendStateToIframe();
            }
        }
        try {
            const bus = (window as unknown as { appEvents?: typeof appEvents }).appEvents;
            if (bus && typeof bus.on === 'function') {
                bus.on('state:updated', _paint);
            }
            if (typeof worldState !== 'undefined' && worldState?.on) {
                worldState.on('update', _paint);
            }
        } catch (e) { /* event wiring optional */ }
        _repaint = _paint;
        _loadWeatherVocabulary();
        _paint();
        setTimeout(_paint, 600);
    }

    return {
        renderTopBar, effectiveWeather, nextForecastChange,
        openWorldSky, close: _closeSky, wire,
    };
})();
(window as unknown as { SkyScape: typeof _SkyScape }).SkyScape = _SkyScape;

// Auto-wire after DOM ready.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => (window as unknown as { SkyScape?: typeof _SkyScape }).SkyScape?.wire());
} else {
    setTimeout(() => (window as unknown as { SkyScape?: typeof _SkyScape }).SkyScape?.wire(), 200);
}

/**
 * Type declarations live BELOW the first value statement on purpose: TypeScript
 * drops a file's leading JSDoc when the first statement is type-only, and
 * `tools/js_module_index.py` reads `@module` out of the emitted .js.
 */

/** The `#sky-time` top-bar element, which carries a private click-binding flag. */
interface SkyTopBarEl extends HTMLElement {
    _skyClickBound?: boolean;
}

/** One forecast entry inside a schedule. */
interface ForecastEntry {
    offset?: number;
    weather?: string;
    wind?: string;
    wind_direction?: string;
    humidity?: string;
    temperature_mod?: number;
    light_mod?: number;
    air?: string;
    message?: string;
}

/** The engine's forecast schedule. */
interface ForecastSchedule {
    mode?: 'authored' | 'deterministic' | 'random' | 'hybrid' | 'generated' | string;
    granularity?: 'hourly' | 'weekly' | 'yearly' | string;
    seed?: number | null;
    current_state?: string;
    transition_interval?: number;
    transition_table?: Record<string, Record<string, number>>;
    entries?: ForecastEntry[];
}

/** The slice of `/api/state` this module reads. */
interface SkyState {
    season?: string;
    calendar_config?: { days_per_month?: number; months_per_year?: number; year_start_day?: number };
    game_time?: string;
    game_day?: number;
    game_month?: number;
    game_year?: number;
    moon_phase?: { name?: string; light_bonus?: number };
    forecast_schedule?: ForecastSchedule;
    forecast_override?: { weather?: string; wind?: string; wind_direction?: string; humidity?: string } | null;
    [key: string]: unknown;
}

/** What nextForecastChange reports. */
interface ForecastChange {
    when: string;
    weather?: string;
    label: string;
}

/** Minutes in one schedule period, by granularity. */
const GRANULARITY_MINUTES: Record<string, number> = {
    hourly: 1440, weekly: 10080, yearly: 525600,
};
