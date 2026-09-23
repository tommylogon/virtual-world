/**
 * @module soak-presets — built-in experiment presets + locally saved run configs
 * @contributes preset definitions, localStorage-backed saved configs, merge/resolve helpers
 * @powers one-click experiments, save/load your own configs, shareable setups
 * @relates used by soak-ui.js; produces config fragments consumed by soak-state.js
 * @docs none
 */
(function () {
    'use strict';

    const LS_KEY = 'soak.savedConfigs.v1';

    // `days` is resolved against the currently selected minutes/tick so a preset
    // means "one game week" regardless of tick length.
    const PRESETS = [
        {
            id: 'authored', name: 'Authored baseline', icon: '🧭',
            hint: 'Whatever the scenario ships with, no overrides.',
            config: {},
        },
        {
            id: 'engine-decay', name: 'Engine decay', icon: '⚙️',
            hint: 'Drop baked decay_rates so engine defaults apply.',
            config: { engine_decay: true },
        },
        {
            id: 'neutral', name: 'Neutral environment', icon: '🌤️',
            hint: 'Force 20C/fresh/quiet everywhere; removes weather confounds.',
            config: { engine_decay: true, neutral_environment: true },
        },
        {
            id: 'immortal', name: 'No decay (immortal)', icon: '🧟',
            hint: 'Zero Hunger/Thirst/Energy decay to isolate other systems.',
            config: { engine_decay: true, decay_overrides: { Energy: 0, Thirst: 0, Hunger: 0 } },
        },
        {
            id: 'mature', name: 'Mature systems on', icon: '💗',
            hint: 'Enables Arousal/Stimulation/Pleasure vitals and decay.',
            config: { mature: true },
        },
        {
            id: 'background', name: 'All background (fast)', icon: '💨',
            hint: 'Every character on the deterministic survival path.',
            config: { background_all: true },
        },
        {
            id: 'starve', name: 'Starve them out', icon: '🥵',
            hint: 'Start everyone at the edge of death.',
            config: { engine_decay: true, starting_vitals: { Hunger: 99, Thirst: 99 } },
        },
        {
            id: 'debug-hp', name: 'Debug HP drops', icon: '🩸',
            hint: 'Log every HP loss with conditions and environment.',
            config: { debug_hp: true },
        },
        {
            id: 'week', name: 'One game week', icon: '📅',
            hint: 'Horizon = 7 game days at the selected tick length.',
            config: {}, days: 7,
        },
        {
            id: 'month', name: 'One game month', icon: '🗓️',
            hint: 'Horizon = 30 game days at the selected tick length.',
            config: {}, days: 30,
        },
    ];

    function loadSaved() {
        try {
            const raw = localStorage.getItem(LS_KEY);
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch (err) {
            return [];
        }
    }

    function saveSaved(list) {
        try {
            localStorage.setItem(LS_KEY, JSON.stringify(list.slice(0, 40)));
        } catch (err) { /* quota/private mode — silently ignore */ }
    }

    function addSaved(name, config) {
        const list = loadSaved();
        list.unshift({ name: name || 'Untitled', config: config, savedAt: Date.now() });
        saveSaved(list);
        return list;
    }

    function removeSaved(index) {
        const list = loadSaved();
        list.splice(index, 1);
        saveSaved(list);
        return list;
    }

    /** Merge a preset (or saved config) over a base config, resolving `days`. */
    function resolve(preset, baseConfig, metaDefaults) {
        const out = Object.assign({}, baseConfig || {}, preset.config || {});
        if (preset.days) {
            const mpt = Number(out.minutes_per_tick) || Number((metaDefaults || {}).minutes_per_tick) || 1;
            out.ticks = Math.max(1, Math.round((preset.days * 1440) / mpt));
        }
        return out;
    }

    window.SoakPresets = { PRESETS, loadSaved, saveSaved, addSaved, removeSaved, resolve };
})();
