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
(window as unknown as { ScenarioHealth: unknown }).ScenarioHealth = (() => {
  'use strict';


  let _cache: ScenarioSummary[] | null = null;

  async function open() {
    let list = _cache;
    if (!list) {
      const resp = await fetch('/api/scenarios');
      list = await resp.json() as ScenarioSummary[];
      _cache = list;
    }
    render(list);
  }

  function render(list: ScenarioSummary[]) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    const box = document.createElement('div');
    box.className = 'modal-window';
    box.style.cssText = 'width:700px;max-width:94vw;max-height:82vh;display:flex;flex-direction:column;';

    const totalIssues = list.reduce((acc: number, s: ScenarioSummary) => acc + ((s.health && s.health.issues) || 0), 0);
    const broken = list.filter((s: ScenarioSummary) => s.health && !s.health.ok).length;
    let html = '<div class="modal-head"><h3 style="margin:0;font-size:15px;">🩺 Scenario health</h3>'
      + '<button class="modal-close-btn" id="sh-close">✕</button></div>'
      + '<div style="font-size:10px;color:var(--text-dim);margin-bottom:8px;">' + list.length + ' scenarios · '
      + (totalIssues === 0 ? '<span style="color:#3fb950;">all clean (file-level)</span>' : '<span style="color:#e3b341;">' + totalIssues + ' file-level issues</span>')
      + (broken ? ' · <span style="color:#f85149;">' + broken + ' unparseable</span>' : '')
      + '</div>';

    html += '<div style="overflow-y:auto;flex:1;">';
    for (const s of list) {
      const h = s.health || {};
      const issues = h.issues || 0;
      const color = !h.ok ? '#f85149' : issues > 0 ? '#e3b341' : '#3fb950';
      const badge = !h.ok ? '⚠ unparseable' : issues > 0 ? `⚠ ${issues} issue${issues === 1 ? '' : 's'}` : '✓ clean';
      const age = s.modified ? ageStr(Number(s.modified)) : '';
      html += '<div style="padding:6px 4px;border-bottom:1px solid var(--border);">'
        + '<div style="display:flex;align-items:center;gap:6px;">'
        + '<span style="flex-shrink:0;">📄</span>'
        + '<div style="flex:1;min-width:0;">'
        + '<div style="font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + esc(s.name) + '</div>'
        + '<div style="font-size:9px;color:var(--text-muted);">' + (s.areas || 0) + ' rooms · ' + (s.players || 0) + ' players · ' + fmtSize(Number(s.size)) + (age ? ' · ' + age : '') + '</div>'
        + (issues > 0 ? '<div style="font-size:9px;color:' + color + ';padding-top:1px;">'
            + (h.dangling_trigger_targets ? '🔗 ' + h.dangling_trigger_targets + ' dangling trigger target(s) · ' : '')
            + (h.ways_missing_description ? '🚪 ' + h.ways_missing_description + ' way(s) no description · ' : '')
            + (h.areas_missing_description ? '🏠 ' + h.areas_missing_description + ' area(s) no description' : '')
            + '</div>' : '')
        + '</div>'
        + '<span class="state-badge" style="font-size:9px;background:' + color + '22;color:' + color + ';border:1px solid ' + color + ';padding:1px 6px;border-radius:4px;font-weight:600;flex-shrink:0;">' + badge + '</span>'
        + '<button class="btn btn-sm btn-ghost" data-open="' + esc(s.name) + '" style="font-size:9px;flex-shrink:0;">Open</button>'
        + '</div></div>';
    }
    html += '</div>';
    html += '<div style="padding-top:8px;border-top:1px solid var(--border);margin-top:6px;display:flex;justify-content:space-between;align-items:center;">'
      + '<span style="font-size:9px;color:var(--text-muted);">File-level scan only — open a scenario and run 🧩 Audit for deep trigger validation.</span>'
      + '<button class="btn btn-sm btn-ghost" id="sh-refresh">🔄 Refresh</button></div>';

    box.innerHTML = html;
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    const close = () => overlay.remove();
    box.querySelector<HTMLElement>('#sh-close')!.onclick = close;
    overlay.addEventListener('mousedown', (e: MouseEvent) => { if (e.target === overlay) close(); });
    const escHandler = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.preventDefault(); document.removeEventListener('keydown', escHandler); close(); } };
    document.addEventListener('keydown', escHandler);

    const refreshBtn = box.querySelector<HTMLElement>('#sh-refresh');
    if (refreshBtn) refreshBtn.onclick = async () => {
      _cache = null;
      close();
      open();
    };

    box.querySelectorAll<HTMLButtonElement>('button[data-open]').forEach((btn) => {
      btn.onclick = async () => {
        close();
        if ((window as unknown as { ScenarioManager?: { open?: () => void } }).ScenarioManager) (window as unknown as { ScenarioManager: { open?: () => void } }).ScenarioManager.open?.();  // full manager handles load+audit
      };
    });
  }

  function ageStr(ts: number) {
    const days = (Date.now() / 1000 - ts) / 86400;
    if (days < 1) return 'today';
    if (days < 30) return Math.round(days) + 'd ago';
    if (days < 365) return Math.round(days / 30) + 'mo ago';
    return (days / 365).toFixed(1) + 'y ago';
  }

  function fmtSize(bytes: number) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(0) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  }

  function esc(s: unknown) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  return { open };
})();


// NOTE: this shape declaration sits AFTER the first value statement on purpose.
// A leading `interface`/`type` makes TypeScript drop the file's leading JSDoc
// block from the emitted .js, and tools/js_module_index.py reads the `@module`
// tag out of that emitted .js.
interface ScenarioSummary {
  name?: string;
  size?: number | string;
  modified?: number | string;
  areas?: number;
  players?: number;
  health?: {
    ok?: boolean;
    issues?: number;
    dangling_trigger_targets?: number;
    ways_missing_description?: number;
    areas_missing_description?: number;
  };
}
