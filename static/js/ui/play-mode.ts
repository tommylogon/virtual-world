/**
 * play-mode.ts - Unity-style transient simulation sandbox with clean revert on stop (task-885).
 *
 * Provides PlayMode controller:
 *   - Play Mode (▶ Play): snapshots authored state, runs simulation/turns freely in a transient sandbox.
 *   - Stop (⏹ Stop): discards all simulation state and restores the pre-play authored baseline.
 *   - Updates topbar button, PLAYING badge, and body.play-mode-active styles.
 */

interface PlayModeStatusResponse {
    play_mode: boolean;
    has_snapshot: boolean;
    status?: string;
    error?: string;
}

const PlayMode = (() => {
    'use strict';

    let _isPlaying = false;
    let _busy = false;

    function getBtn(): HTMLButtonElement | null {
        return document.getElementById('play-mode-btn') as HTMLButtonElement | null;
    }

    function getBadge(): HTMLElement | null {
        return document.getElementById('play-mode-badge');
    }

    function updateUI(isPlaying: boolean) {
        _isPlaying = isPlaying;
        const btn = getBtn();
        if (btn) {
            if (isPlaying) {
                btn.textContent = '⏹ Stop';
                btn.className = 'btn btn-sm btn-red';
                btn.title = 'Stop Play Mode and revert simulation back to authored checkpoint';
            } else {
                btn.textContent = '▶ Play';
                btn.className = 'btn btn-sm btn-green';
                btn.title = 'Enter Play Mode: run simulation in a transient sandbox and revert on stop';
            }
        }

        const badge = getBadge();
        if (badge) {
            badge.style.display = isPlaying ? 'inline-block' : 'none';
        }

        document.body.classList.toggle('play-mode-active', isPlaying);

        const scStatus = (window as any).ScenarioStatus;
        if (scStatus && typeof scStatus.refresh === 'function') {
            scStatus.refresh().catch(() => {});
        }
    }

    async function enter(): Promise<boolean> {
        if (_busy) return _isPlaying;
        _busy = true;
        try {
            const resp = await fetch('/api/play_mode/enter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            const data = (await resp.json()) as PlayModeStatusResponse;
            if (data.error) throw new Error(data.error);

            updateUI(true);
            const tInfo = (window as any).toastInfo;
            if (typeof tInfo === 'function') {
                tInfo('Entered Play Mode. Simulation is running in sandbox.');
            }
            const ev = (window as any).events;
            if (ev && typeof ev.log === 'function') {
                ev.log('▶ Play Mode active - simulation sandbox running.', 'system-msg');
            }
            return true;
        } catch (e) {
            console.error('[PlayMode] enter failed:', e);
            const tErr = (window as any).toastError;
            if (typeof tErr === 'function') {
                tErr('Could not enter Play Mode: ' + (e instanceof Error ? e.message : String(e)));
            }
            return false;
        } finally {
            _busy = false;
        }
    }

    async function stop(): Promise<boolean> {
        if (_busy) return _isPlaying;
        _busy = true;
        try {
            // If the autonomous agent loop is active, stop it first
            const ag = (window as any).agent;
            if (ag && ag.isRunning && typeof ag.stop === 'function') {
                try { ag.stop(); } catch (err) {}
            }

            const resp = await fetch('/api/play_mode/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            const data = (await resp.json()) as PlayModeStatusResponse;
            if (data.error) throw new Error(data.error);

            updateUI(false);

            // Refresh live world state back to restored authored snapshot
            const ws = (window as any).worldState;
            if (ws && typeof ws.fetch === 'function') {
                await ws.fetch(true);
            }

            const tInfo = (window as any).toastInfo;
            if (typeof tInfo === 'function') {
                tInfo('Exited Play Mode. Simulation state reverted to authored baseline.');
            }
            const ev = (window as any).events;
            if (ev && typeof ev.log === 'function') {
                ev.log('⏹ Stopped Play Mode - world restored to authored checkpoint.', 'system-msg');
            }
            return true;
        } catch (e) {
            console.error('[PlayMode] stop failed:', e);
            const tErr = (window as any).toastError;
            if (typeof tErr === 'function') {
                tErr('Could not stop Play Mode: ' + (e instanceof Error ? e.message : String(e)));
            }
            return false;
        } finally {
            _busy = false;
        }
    }

    async function toggle(): Promise<void> {
        if (_isPlaying) {
            await stop();
        } else {
            await enter();
        }
    }

    async function checkStatus(): Promise<void> {
        try {
            const resp = await fetch('/api/play_mode/status');
            const data = (await resp.json()) as PlayModeStatusResponse;
            updateUI(Boolean(data && data.play_mode));
        } catch (e) {
            // Server may not support endpoint yet or be offline
        }
    }

    function init() {
        checkStatus();
        const ws = (window as any).worldState;
        if (ws && typeof ws.on === 'function') {
            ws.on('update', (data?: any) => {
                if (data && typeof data.is_play_mode === 'boolean' && data.is_play_mode !== _isPlaying) {
                    updateUI(data.is_play_mode);
                }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 0);
    }

    return {
        isActive: () => _isPlaying,
        enter,
        stop,
        toggle,
        updateUI,
        checkStatus,
    };
})();

(window as any).PlayMode = PlayMode;
