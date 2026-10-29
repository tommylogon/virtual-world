"use strict";
/**
 * scenario-health.js — Scenario health dashboard (task-385)
 *
 * Lists every data/scenarios/*.json with a file-level health scan (parseable,
 * trigger-edge counts, dangling trigger targets, missing way/area
 * descriptions) plus size/age/area/player stats. Click a row's "Open" to load
 * it via ScenarioManager semantics, "Audit" to run the full trigger validator
 * on a throwaway load.
 *
 * Wire: GET /api/scenarios (now carries health), POST /api/scenarios/<name>
 * for open, GET /api/triggers/validate for the live audit.
 *
 * @module ui/scenario-health — scenario health dashboard
 * @contributes ScenarioHealth: per-file health scan (parse, trigger edges, dangling targets, missing text) + stats
 * @powers spotting a broken scenario before you load it (task-385)
 * @relates uses /api/scenarios + /api/triggers/validate; Open follows ScenarioManager semantics
 * @docs docs/virtualWorld/Scenario Workflows & UI Audit.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.ScenarioHealth = (() => {
    'use strict';
    let _cache = null;
    async function open() {
        let list = _cache;
        if (!list) {
            list = (await ApiClient.listScenarios());
            _cache = list;
        }
        render(list);
    }
    function render(list) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        const box = document.createElement('div');
        box.className = 'modal-window';
        box.style.cssText = 'width:700px;max-width:94vw;max-height:82vh;display:flex;flex-direction:column;';
        const totalIssues = list.reduce((acc, s) => acc + ((s.health && s.health.issues) || 0), 0);
        const broken = list.filter((s) => s.health && !s.health.ok).length;
        const head = document.createElement('div');
        head.className = 'modal-head';
        const h3 = document.createElement('h3');
        h3.style.cssText = 'margin:0;font-size:15px;';
        h3.textContent = '🩺 Scenario health';
        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close-btn';
        closeBtn.id = 'sh-close';
        closeBtn.textContent = '✕';
        head.append(h3, closeBtn);
        const sub = document.createElement('div');
        sub.style.cssText = 'font-size:10px;color:var(--text-dim);margin-bottom:8px;';
        sub.append(`${list.length} scenarios · `);
        const issueSpan = document.createElement('span');
        if (totalIssues === 0) {
            issueSpan.style.color = '#3fb950';
            issueSpan.textContent = 'all clean (file-level)';
        }
        else {
            issueSpan.style.color = '#e3b341';
            issueSpan.textContent = `${totalIssues} file-level issues`;
        }
        sub.appendChild(issueSpan);
        if (broken) {
            const brokenSpan = document.createElement('span');
            brokenSpan.style.color = '#f85149';
            brokenSpan.textContent = `${broken} unparseable`;
            sub.append(' · ', brokenSpan);
        }
        box.append(head, sub);
        const listDiv = document.createElement('div');
        listDiv.style.cssText = 'overflow-y:auto;flex:1;';
        for (const s of list) {
            const h = s.health || {};
            const issues = h.issues || 0;
            const color = !h.ok ? '#f85149' : issues > 0 ? '#e3b341' : '#3fb950';
            const badge = !h.ok ? '⚠ unparseable' : issues > 0 ? `⚠ ${issues} issue${issues === 1 ? '' : 's'}` : '✓ clean';
            const age = s.modified ? ageStr(Number(s.modified)) : '';
            const row = document.createElement('div');
            row.style.cssText = 'padding:6px 4px;border-bottom:1px solid var(--border);';
            const innerRow = document.createElement('div');
            innerRow.style.cssText = 'display:flex;align-items:center;gap:6px;';
            const iconSpan = document.createElement('span');
            iconSpan.style.cssText = 'flex-shrink:0;';
            iconSpan.textContent = '📄';
            const detailsCol = document.createElement('div');
            detailsCol.style.cssText = 'flex:1;min-width:0;';
            const nameEl = document.createElement('div');
            nameEl.style.cssText = 'font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            nameEl.textContent = s.name || '';
            const metaEl = document.createElement('div');
            metaEl.style.cssText = 'font-size:9px;color:var(--text-muted);';
            metaEl.textContent = `${s.areas || 0} rooms · ${s.players || 0} players · ${fmtSize(Number(s.size))}${age ? ' · ' + age : ''}`;
            detailsCol.append(nameEl, metaEl);
            if (issues > 0) {
                const issuesEl = document.createElement('div');
                issuesEl.style.cssText = `font-size:9px;color:${color};padding-top:1px;`;
                const bits = [];
                if (h.dangling_trigger_targets)
                    bits.push(`🔗 ${h.dangling_trigger_targets} dangling trigger target(s)`);
                if (h.ways_missing_description)
                    bits.push(`🚪 ${h.ways_missing_description} way(s) no description`);
                if (h.areas_missing_description)
                    bits.push(`🏠 ${h.areas_missing_description} area(s) no description`);
                issuesEl.textContent = bits.join(' · ');
                detailsCol.appendChild(issuesEl);
            }
            const badgeSpan = document.createElement('span');
            badgeSpan.className = 'state-badge';
            badgeSpan.style.cssText = `font-size:9px;background:${color}22;color:${color};border:1px solid ${color};padding:1px 6px;border-radius:4px;font-weight:600;flex-shrink:0;`;
            badgeSpan.textContent = badge;
            const openBtn = document.createElement('button');
            openBtn.className = 'btn btn-sm btn-ghost';
            openBtn.dataset.open = s.name || '';
            openBtn.style.cssText = 'font-size:9px;flex-shrink:0;';
            openBtn.textContent = 'Open';
            innerRow.append(iconSpan, detailsCol, badgeSpan, openBtn);
            row.appendChild(innerRow);
            listDiv.appendChild(row);
        }
        box.appendChild(listDiv);
        const footer = document.createElement('div');
        footer.style.cssText = 'padding-top:8px;border-top:1px solid var(--border);margin-top:6px;display:flex;justify-content:space-between;align-items:center;';
        const footNote = document.createElement('span');
        footNote.style.cssText = 'font-size:9px;color:var(--text-muted);';
        footNote.textContent = 'File-level scan only - open a scenario and run 🧩 Audit for deep trigger validation.';
        const refreshBtnEl = document.createElement('button');
        refreshBtnEl.className = 'btn btn-sm btn-ghost';
        refreshBtnEl.id = 'sh-refresh';
        refreshBtnEl.textContent = '🔄 Refresh';
        footer.append(footNote, refreshBtnEl);
        box.appendChild(footer);
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        const close = () => overlay.remove();
        box.querySelector('#sh-close').onclick = close;
        overlay.addEventListener('mousedown', (e) => { if (e.target === overlay)
            close(); });
        const escHandler = (e) => { if (e.key === 'Escape') {
            e.preventDefault();
            document.removeEventListener('keydown', escHandler);
            close();
        } };
        document.addEventListener('keydown', escHandler);
        const refreshBtn = box.querySelector('#sh-refresh');
        if (refreshBtn)
            refreshBtn.onclick = async () => {
                _cache = null;
                close();
                open();
            };
        box.querySelectorAll('button[data-open]').forEach((btn) => {
            btn.onclick = async () => {
                close();
                if (window.ScenarioManager)
                    window.ScenarioManager.open?.(); // full manager handles load+audit
            };
        });
    }
    function ageStr(ts) {
        const days = (Date.now() / 1000 - ts) / 86400;
        if (days < 1)
            return 'today';
        if (days < 30)
            return Math.round(days) + 'd ago';
        if (days < 365)
            return Math.round(days / 30) + 'mo ago';
        return (days / 365).toFixed(1) + 'y ago';
    }
    function fmtSize(bytes) {
        if (bytes < 1024)
            return bytes + ' B';
        if (bytes < 1048576)
            return (bytes / 1024).toFixed(0) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }
    return { open };
})();
