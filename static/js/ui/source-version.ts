/**
 * Warn an open editor tab when its served frontend files change on disk.
 * The page embeds the fingerprint at render time; the endpoint returns the
 * current fingerprint without caching.
 *
 * @module ui/source-version - warn editor tabs when served files change on disk
 * @contributes polls /api/client-version and shows a reload notice when changed
 * @powers source-refresh-notice banner in the editor
 * @relates templates/index.html
 * @docs none
 */
(() => {
    const loadedVersion = document.body?.dataset.clientVersion;
    if (!loadedVersion) return;

    let noticeShown = false;
    let checkRunning = false;

    function showRefreshNotice() {
        if (noticeShown || document.getElementById('source-refresh-notice')) return;
        noticeShown = true;

        const notice = document.createElement('div');
        notice.id = 'source-refresh-notice';
        notice.setAttribute('role', 'alert');
        notice.setAttribute('aria-live', 'assertive');
        notice.style.cssText = [
            'position:fixed', 'top:12px', 'left:50%', 'transform:translateX(-50%)',
            'z-index:20000', 'display:flex', 'align-items:center', 'gap:12px',
            'max-width:calc(100vw - 24px)', 'padding:10px 14px', 'border-radius:8px',
            'border:1px solid #d29922', 'background:#2b2415', 'color:#f0e6cc',
            'box-shadow:0 4px 18px rgba(0,0,0,.45)', 'font:13px system-ui,sans-serif'
        ].join(';');

        const message = document.createElement('span');
        message.textContent = 'App source changed. Refresh this page to load the update.';

        const refresh = document.createElement('button');
        refresh.type = 'button';
        refresh.textContent = 'Refresh now';
        refresh.style.cssText = 'border:0;border-radius:5px;padding:6px 10px;background:#d29922;color:#17130b;font-weight:700;cursor:pointer;';
        refresh.addEventListener('click', () => window.location.reload());

        const dismiss = document.createElement('button');
        dismiss.type = 'button';
        dismiss.textContent = 'Dismiss';
        dismiss.setAttribute('aria-label', 'Dismiss refresh notice');
        dismiss.style.cssText = 'border:0;background:transparent;color:inherit;cursor:pointer;';
        dismiss.addEventListener('click', () => notice.remove());

        notice.append(message, refresh, dismiss);
        document.body.appendChild(notice);
    }

    async function checkVersion() {
        if (noticeShown || checkRunning || document.hidden) return;
        checkRunning = true;
        try {
            const response = await fetch('/api/client-version', { cache: 'no-store' });
            if (!response.ok) return;
            const current = await response.json();
            if (current?.version && current.version !== loadedVersion) showRefreshNotice();
        } catch (_error) {
            // Keep the editor usable if the version endpoint is temporarily unavailable.
        } finally {
            checkRunning = false;
        }
    }

    window.setInterval(() => { void checkVersion(); }, 15000);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) void checkVersion();
    });
    window.addEventListener('focus', () => { void checkVersion(); });
})();
