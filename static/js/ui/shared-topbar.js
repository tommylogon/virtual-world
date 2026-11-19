"use strict";
/**
 * shared-topbar.ts - Standalone shared topbar controller for /commons, /bench, /soak.
 * Reads scenario name, dirty/commit status, and world clock directly from API endpoints,
 * and provides Restart + in-place Quick Settings controls.
 */
(function () {
    'use strict';
    function getGlobalConfig() {
        return window.config;
    }
    function getGlobalStorage() {
        return window.storage;
    }
    function openConfigDb() {
        return new Promise((resolve) => {
            if (typeof indexedDB === 'undefined') {
                resolve(null);
                return;
            }
            try {
                const req = indexedDB.open('VirtualWorldDB', 5);
                req.onupgradeneeded = (e) => {
                    const db = e.target.result;
                    if (!db.objectStoreNames.contains('config')) {
                        db.createObjectStore('config', { keyPath: 'key' });
                    }
                };
                req.onsuccess = (e) => {
                    resolve(e.target.result);
                };
                req.onerror = () => resolve(null);
            }
            catch (_) {
                resolve(null);
            }
        });
    }
    async function readConfigValue(key, fallback) {
        const st = getGlobalStorage();
        if (st && typeof st.getConfig === 'function') {
            try {
                const val = await st.getConfig(key);
                return val !== null && val !== undefined ? String(val) : fallback;
            }
            catch (_) { /* fall through */ }
        }
        const db = await openConfigDb();
        if (db) {
            try {
                const val = await new Promise((resolve) => {
                    const tx = db.transaction('config', 'readonly');
                    const store = tx.objectStore('config');
                    const req = store.get(key);
                    req.onsuccess = () => resolve(req.result ? req.result.value : null);
                    req.onerror = () => resolve(null);
                });
                db.close();
                if (val !== null && val !== undefined)
                    return String(val);
            }
            catch (_) {
                try {
                    db.close();
                }
                catch (_2) { /* ignore */ }
            }
        }
        try {
            const lsVal = localStorage.getItem('vw_config_' + key);
            if (lsVal !== null)
                return lsVal;
        }
        catch (_) { /* ignore */ }
        return fallback;
    }
    async function writeConfigValue(key, value) {
        const st = getGlobalStorage();
        if (st && typeof st.setConfig === 'function') {
            try {
                await st.setConfig(key, value);
                return;
            }
            catch (_) { /* fall through */ }
        }
        const db = await openConfigDb();
        if (db) {
            try {
                await new Promise((resolve) => {
                    const tx = db.transaction('config', 'readwrite');
                    const store = tx.objectStore('config');
                    store.put({ key, value });
                    tx.oncomplete = () => resolve();
                    tx.onerror = () => resolve();
                });
                db.close();
                return;
            }
            catch (_) {
                try {
                    db.close();
                }
                catch (_2) { /* ignore */ }
            }
        }
        try {
            localStorage.setItem('vw_config_' + key, value);
        }
        catch (_) { /* ignore */ }
    }
    function applyTopbarState(stRes, scRes) {
        const nameEl = document.getElementById('shared-scenario-name');
        const commitBtn = document.getElementById('shared-commit-btn');
        const timeEl = document.getElementById('shared-sky-time');
        const scenName = scRes?.scenario_name || scRes?.name || stRes?.scenario_name;
        if (nameEl && scenName)
            nameEl.textContent = String(scenName);
        if (commitBtn && scRes) {
            const dirty = Boolean(scRes.dirty || scRes.has_changes || scRes.uncommitted_count);
            commitBtn.textContent = dirty ? '📦 Commit ●' : '📦 Commit';
        }
        if (timeEl && stRes) {
            const ticks = Number(stRes.time_ticks ?? 0);
            const mpt = Number(stRes.time_per_tick_minutes ?? 5) || 5;
            const startH = Number(stRes.clock_start_hour ?? 8);
            const startM = Number(stRes.clock_start_minute ?? 0);
            const total = Math.round(startH * 60 + startM + ticks * mpt);
            const hh = String(Math.floor((total % 1440) / 60)).padStart(2, '0');
            const mm = String(total % 60).padStart(2, '0');
            timeEl.textContent = `🕐 ${hh}:${mm}`;
        }
    }
    async function refreshTopbar(cachedState) {
        try {
            const stPromise = cachedState
                ? Promise.resolve(cachedState)
                : fetch('/api/state').then(r => r.ok ? r.json() : null).catch(() => null);
            const [stRes, scRes] = await Promise.all([
                stPromise,
                fetch('/api/scenario/status').then(r => r.ok ? r.json() : null).catch(() => null),
            ]);
            applyTopbarState(stRes, scRes);
        }
        catch (_) { /* best-effort */ }
    }
    async function loadQuickSettings() {
        const rawEl = document.getElementById('shared-set-show-raw-llm');
        const autoReplyEl = document.getElementById('shared-set-commons-auto-reply');
        const baseEl = document.getElementById('shared-set-api-base');
        const modelEl = document.getElementById('shared-set-model');
        const keyEl = document.getElementById('shared-set-api-key');
        const statusEl = document.getElementById('shared-settings-status');
        if (statusEl)
            statusEl.textContent = '';
        const cfg = getGlobalConfig();
        if (cfg) {
            if (typeof cfg.ready === 'function') {
                try {
                    await cfg.ready();
                }
                catch (_) { /* ignore */ }
            }
            if (rawEl)
                rawEl.checked = Boolean(cfg.showRawLLM);
            if (autoReplyEl)
                autoReplyEl.checked = Boolean(cfg.commonsAutoReplyOnMessage);
            if (baseEl)
                baseEl.value = cfg.apiBase || 'http://localhost:1234/v1';
            if (modelEl)
                modelEl.value = cfg.model || 'glm-4-9b-0414';
            if (keyEl)
                keyEl.value = cfg.apiKey || 'not-needed';
            return;
        }
        const [rawVal, autoVal, baseVal, modelVal, keyVal] = await Promise.all([
            readConfigValue('show_raw_llm', 'false'),
            readConfigValue('commons_auto_reply_on_message', 'false'),
            readConfigValue('api_base', 'http://localhost:1234/v1'),
            readConfigValue('model', 'glm-4-9b-0414'),
            readConfigValue('api_key', 'not-needed'),
        ]);
        if (rawEl)
            rawEl.checked = rawVal === 'true';
        if (autoReplyEl)
            autoReplyEl.checked = autoVal === 'true';
        if (baseEl)
            baseEl.value = baseVal;
        if (modelEl)
            modelEl.value = modelVal;
        if (keyEl)
            keyEl.value = keyVal;
    }
    async function saveQuickSettings() {
        const rawEl = document.getElementById('shared-set-show-raw-llm');
        const autoReplyEl = document.getElementById('shared-set-commons-auto-reply');
        const baseEl = document.getElementById('shared-set-api-base');
        const modelEl = document.getElementById('shared-set-model');
        const keyEl = document.getElementById('shared-set-api-key');
        const statusEl = document.getElementById('shared-settings-status');
        const showRaw = Boolean(rawEl?.checked);
        const autoReply = Boolean(autoReplyEl?.checked);
        const apiBase = baseEl?.value.trim() || 'http://localhost:1234/v1';
        const model = modelEl?.value.trim() || 'glm-4-9b-0414';
        const apiKey = keyEl?.value.trim() || 'not-needed';
        const cfg = getGlobalConfig();
        if (cfg) {
            cfg.showRawLLM = showRaw;
            cfg.commonsAutoReplyOnMessage = autoReply;
            cfg.apiBase = apiBase;
            cfg.model = model;
            cfg.apiKey = apiKey;
            if (typeof cfg.save === 'function') {
                await cfg.save();
            }
        }
        else {
            await Promise.all([
                writeConfigValue('show_raw_llm', showRaw ? 'true' : 'false'),
                writeConfigValue('commons_auto_reply_on_message', autoReply ? 'true' : 'false'),
                writeConfigValue('api_base', apiBase),
                writeConfigValue('model', model),
                writeConfigValue('api_key', apiKey),
            ]);
        }
        if (statusEl) {
            statusEl.textContent = 'Saved';
        }
    }
    function initSharedSettingsModal() {
        const modal = document.getElementById('shared-settings-modal');
        const openBtn = document.getElementById('shared-settings-btn');
        const closeBtn = document.getElementById('shared-settings-close');
        const cancelBtn = document.getElementById('shared-settings-cancel');
        const saveBtn = document.getElementById('shared-settings-save');
        if (!modal || !openBtn)
            return;
        const closeModal = () => {
            modal.style.display = 'none';
        };
        openBtn.addEventListener('click', () => {
            void loadQuickSettings().then(() => {
                modal.style.display = 'flex';
            });
        });
        closeBtn?.addEventListener('click', closeModal);
        cancelBtn?.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal)
                closeModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.style.display !== 'none') {
                closeModal();
            }
        });
        saveBtn?.addEventListener('click', async () => {
            saveBtn.disabled = true;
            try {
                await saveQuickSettings();
                closeModal();
            }
            catch (e) {
                const statusEl = document.getElementById('shared-settings-status');
                if (statusEl) {
                    statusEl.textContent = `Save failed: ${e instanceof Error ? e.message : String(e)}`;
                }
            }
            finally {
                saveBtn.disabled = false;
            }
        });
    }
    function initSharedTopbar() {
        const commitBtn = document.getElementById('shared-commit-btn');
        if (commitBtn) {
            commitBtn.addEventListener('click', async () => {
                commitBtn.disabled = true;
                const prev = commitBtn.textContent;
                commitBtn.textContent = '💾 Committing...';
                try {
                    const res = await fetch('/api/scenario/commit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({}),
                    });
                    if (!res.ok)
                        throw new Error(`HTTP ${res.status}`);
                    await refreshTopbar();
                }
                catch (e) {
                    commitBtn.textContent = prev || '📦 Commit';
                    alert(`Commit failed: ${e instanceof Error ? e.message : String(e)}`);
                }
                finally {
                    commitBtn.disabled = false;
                }
            });
        }
        const restartBtn = document.getElementById('shared-restart-btn');
        if (restartBtn) {
            restartBtn.addEventListener('click', async () => {
                if (!window.confirm('Restart scenario? This will reset all world state.')) {
                    return;
                }
                restartBtn.disabled = true;
                const prev = restartBtn.textContent;
                restartBtn.textContent = '⏳ Resetting...';
                try {
                    const res = await fetch('/api/reset', { method: 'POST' });
                    if (!res.ok)
                        throw new Error(`HTTP ${res.status}`);
                    const data = await res.json().catch(() => null);
                    if (data && data.status === 'error') {
                        throw new Error(String(data.error || 'Reset failed'));
                    }
                    window.location.reload();
                }
                catch (e) {
                    restartBtn.textContent = prev || '🔄 Restart';
                    restartBtn.disabled = false;
                    alert(`Restart failed: ${e instanceof Error ? e.message : String(e)}`);
                }
            });
        }
        initSharedSettingsModal();
        // Event-driven refresh instead of a 10s idle poll:
        // reuse worldState updates when available, otherwise listen to /api/events SSE.
        let refreshTimer = null;
        const scheduleRefresh = (cachedState) => {
            if (refreshTimer !== null)
                window.clearTimeout(refreshTimer);
            refreshTimer = window.setTimeout(() => {
                refreshTimer = null;
                void refreshTopbar(cachedState);
            }, 350);
        };
        const ws = window.worldState;
        void refreshTopbar(ws?.data || undefined);
        if (ws && typeof ws.on === 'function') {
            ws.on('update', (data) => scheduleRefresh(data));
        }
        else if (typeof EventSource !== 'undefined') {
            try {
                const es = new EventSource('/api/events');
                es.addEventListener('world_changed', () => scheduleRefresh());
                es.onmessage = () => scheduleRefresh();
                window.addEventListener('beforeunload', () => { try {
                    es.close();
                }
                catch (_) { } });
            }
            catch (_) { /* ignore SSE fallback errors */ }
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSharedTopbar);
    }
    else {
        initSharedTopbar();
    }
})();
