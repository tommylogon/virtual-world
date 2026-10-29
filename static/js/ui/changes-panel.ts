/**
 * changes-panel.js — Changes-since-source panel (task-373)
 *
 * Shows the server-side diff (live world vs scenario source) grouped by
 * Rooms / Items / Ways / Players, with per-group Commit (merge live → source)
 * and Discard (restore source → live, undo-protected). Entry: the 🌀 "Changes"
 * button in the scenario dropdown / toolbar area.
 *
 * Wire: GET /api/scenario/diff → groups
 *       POST /api/scenario/diff/apply {commit:[...]|discard:[...]}
 *
 * @module ui/changes-panel — changes-since-source panel
 * @contributes ChangesPanel: live-vs-source diff grouped by kind, with per-group Commit / Discard
 * @powers Recent edits / undo — reviewing and committing edits back into the scenario source (task-373)
 * @relates uses /api/scenario/diff + /api/scenario/diff/apply; opened from the scenario toolbar
 * @docs docs/virtualWorld/Scenario Workflows & UI Audit.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const ChangesPanel = (() => {
  'use strict';

  let _cache: DiffResponse | null = null; // last diff response (for re-render after apply)

  const GROUP_META: Record<string, { emoji: string; label: string; kind: string }> = {
    added_areas:    { emoji: '🏠', label: 'Rooms added',    kind: 'add' },
    removed_areas:  { emoji: '🏠', label: 'Rooms removed',  kind: 'del' },
    changed_areas:  { emoji: '🏠', label: 'Rooms changed',  kind: 'chg' },
    added_items:    { emoji: '📦', label: 'Items added',    kind: 'add' },
    removed_items:  { emoji: '📦', label: 'Items removed',  kind: 'del' },
    changed_items:  { emoji: '📦', label: 'Items changed',  kind: 'chg' },
    added_ways:     { emoji: '🚪', label: 'Ways added',     kind: 'add' },
    removed_ways:   { emoji: '🚪', label: 'Ways removed',   kind: 'del' },
    changed_ways:   { emoji: '🚪', label: 'Ways changed',   kind: 'chg' },
    added_players:  { emoji: '🧍', label: 'Players added',  kind: 'add' },
    removed_players:{ emoji: '🧍', label: 'Players removed',kind: 'del' },
  };

  // group → section for the per-group commit/discard keys
  const SECTION_OF = (key: string): string | null => {
    if (key.includes('_area')) return 'areas';
    if (key.includes('_item')) return 'items';
    if (key.includes('_way')) return 'ways';
    if (key.includes('_player')) return 'players';
    return null;
  };

  async function fetchDiff(): Promise<DiffResponse> {
    return (await ApiClient.getScenarioDiff()) as DiffResponse;
  }

  async function apply(commit: string[] = [], discard: string[] = []): Promise<{ error?: string }> {
    const data = await ApiClient.applyScenarioDiff(commit, discard);
    if (data.error) throw new Error(data.error);
    if (window.worldState) worldState.fetch();
    // ScenarioStatus is not declared in types/globals.d.ts (shared hub), so the
    // optional presence check goes through a local cast.
    const status = (window as unknown as { ScenarioStatus?: { refresh(): void } }).ScenarioStatus;
    if (status) status.refresh();
    return data;
  }

  async function open() {
    let data = _cache;
    if (!data) {
      data = await fetchDiff();
      _cache = data;
    }
    render(data);
  }

  function render(data: DiffResponse) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    const box = document.createElement('div');
    box.className = 'modal-window';
    box.style.cssText = 'width:640px;max-width:92vw;max-height:85vh;display:flex;flex-direction:column;';

    const groups: Record<string, string[]> = data.groups || {};
    const source = data.source || '';
    const anyDiff = Object.values(groups).some(list => Array.isArray(list) && list.length > 0);

    // Construct modal contents via DOM elements
    const head = document.createElement('div');
    head.className = 'modal-head';
    const h3 = document.createElement('h3');
    h3.style.cssText = 'margin:0;font-size:15px;';
    h3.textContent = '🔄 Changes since source';
    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close-btn';
    closeBtn.id = 'cp-close';
    closeBtn.textContent = '✕';
    head.append(h3, closeBtn);

    const sourceSub = document.createElement('div');
    sourceSub.style.cssText = 'font-size:10px;color:var(--text-muted);padding-bottom:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    sourceSub.title = source;
    const sourceLabel = source ? (source.split(/[\\/]/).pop() || '') : 'none - commit first';
    sourceSub.textContent = `Source: ${sourceLabel}`;

    box.append(head, sourceSub);

    if (!source) {
      const emptyDiv = document.createElement('div');
      emptyDiv.style.cssText = 'padding:12px 0;color:var(--text-dim);font-size:12px;';
      emptyDiv.textContent = 'No scenario source yet - use 💾 Commit Scenario first.';
      box.appendChild(emptyDiv);
    } else if (!anyDiff) {
      const matchDiv = document.createElement('div');
      matchDiv.style.cssText = 'padding:12px 0;color:#3fb950;font-size:12px;';
      matchDiv.textContent = '✅ No drift - the live world matches the source.';
      box.appendChild(matchDiv);
    } else {
      // group rows
      const listDiv = document.createElement('div');
      listDiv.style.cssText = 'overflow-y:auto;flex:1;';
      let lastSection: string | null = null;
      for (const [key, names] of Object.entries(groups)) {
        if (!Array.isArray(names) || names.length === 0) continue;
        const meta = GROUP_META[key] || { emoji: '📄', label: key, kind: 'chg' };
        const section = SECTION_OF(key) || 'other';
        if (lastSection !== null && section !== lastSection && section !== 'other') {
          const sep = document.createElement('div');
          sep.style.cssText = 'border-top:1px solid var(--border);margin:8px 0;';
          listDiv.appendChild(sep);
        }
        lastSection = section;
        const color = meta.kind === 'add' ? '#3fb950' : meta.kind === 'del' ? '#f85149' : '#e3b341';
        const short = names.length > 4 ? names.slice(0, 4).join(', ') + '…' : names.join(', ');

        const row = document.createElement('div');
        row.style.cssText = 'padding:4px 2px;';

        const rowHeader = document.createElement('div');
        rowHeader.style.cssText = 'display:flex;align-items:center;gap:6px;';

        const emojiSpan = document.createElement('span');
        emojiSpan.style.cssText = 'flex-shrink:0;';
        emojiSpan.textContent = meta.emoji;

        const labelSpan = document.createElement('span');
        labelSpan.style.cssText = `color:${color};font-weight:600;font-size:12px;`;
        labelSpan.textContent = meta.label;

        const countBadge = document.createElement('span');
        countBadge.className = 'state-badge';
        countBadge.style.cssText = `font-size:9px;background:${color}22;color:${color};border:1px solid ${color};padding:1px 6px;border-radius:4px;`;
        countBadge.textContent = String(names.length);

        rowHeader.append(emojiSpan, labelSpan, countBadge);

        const namesDiv = document.createElement('div');
        namesDiv.style.cssText = 'font-size:10px;color:var(--text-muted);padding-left:22px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
        namesDiv.title = short;
        namesDiv.textContent = short;

        row.append(rowHeader, namesDiv);
        listDiv.appendChild(row);
      }
      box.appendChild(listDiv);

      // per-section action buttons
      const sections = ['areas', 'items', 'ways', 'players'];
      const present = sections.filter(s => Object.keys(groups).some(k => SECTION_OF(k) === s && Array.isArray(groups[k]) && groups[k].length > 0));
      if (present.length > 0) {
        const actionRow = document.createElement('div');
        actionRow.style.cssText = 'border-top:1px solid var(--border);padding-top:8px;margin-top:4px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;';

        const commitLabel = document.createElement('span');
        commitLabel.style.cssText = 'font-size:10px;color:var(--text-dim);';
        commitLabel.textContent = 'Commit section:';
        actionRow.appendChild(commitLabel);

        for (const s of present) {
          const btn = document.createElement('button');
          btn.className = 'btn btn-sm btn-green cp-commit';
          btn.dataset.section = s;
          btn.style.cssText = 'font-size:10px;padding:2px 10px;';
          btn.textContent = `💾 ${s.charAt(0).toUpperCase() + s.slice(1)}`;
          actionRow.appendChild(btn);
        }

        const discardLabel = document.createElement('span');
        discardLabel.style.cssText = 'font-size:10px;color:var(--text-dim);margin-left:8px;';
        discardLabel.textContent = 'Discard section:';
        actionRow.appendChild(discardLabel);

        for (const s of present) {
          const btn = document.createElement('button');
          btn.className = 'btn btn-sm btn-red cp-discard';
          btn.dataset.section = s;
          btn.style.cssText = 'font-size:10px;padding:2px 10px;';
          btn.textContent = `↩️ ${s.charAt(0).toUpperCase() + s.slice(1)}`;
          actionRow.appendChild(btn);
        }
        box.appendChild(actionRow);
      }
    }

    // footer: full commit + refresh
    const footer = document.createElement('div');
    footer.style.cssText = 'display:flex;justify-content:space-between;padding-top:10px;border-top:1px solid var(--border);margin-top:8px;';
    const refreshBtnEl = document.createElement('button');
    refreshBtnEl.className = 'btn btn-sm btn-ghost';
    refreshBtnEl.id = 'cp-refresh';
    refreshBtnEl.textContent = '🔄 Refresh';
    footer.appendChild(refreshBtnEl);

    if (source && anyDiff) {
      const commitAllBtn = document.createElement('button');
      commitAllBtn.className = 'btn btn-sm btn-green';
      commitAllBtn.id = 'cp-commit-all';
      commitAllBtn.textContent = '💾 Commit All';
      footer.appendChild(commitAllBtn);
    }
    box.appendChild(footer);
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    const close = () => overlay.remove();
    box.querySelector<HTMLElement>('#cp-close')!.onclick = close;
    overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) close(); });
    const escHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); document.removeEventListener('keydown', escHandler); close(); }
    };
    document.addEventListener('keydown', escHandler);

    const refreshBtn = box.querySelector<HTMLElement>('#cp-refresh');
    if (refreshBtn) refreshBtn.onclick = async () => {
      _cache = await fetchDiff();
      close();
      render(_cache);
    };

    const commitAll = box.querySelector<HTMLElement>('#cp-commit-all');
    if (commitAll) commitAll.onclick = async () => {
      try {
        await apply(['areas', 'items', 'ways', 'players'], []);
        toastInfo('All changes committed to source.');
        _cache = await fetchDiff();
        close(); render(_cache);
      } catch (e) { toastError('Commit failed: ' + (e instanceof Error ? e.message : String(e))); }
    };

    box.querySelectorAll<HTMLElement>('.cp-commit').forEach(btn => {
      btn.onclick = async () => {
        const section = btn.dataset.section || '';
        try {
          await apply([section], []);
          toastInfo('Committed ' + section + ' changes to source.');
          _cache = await fetchDiff();
          close(); render(_cache);
        } catch (e) { toastError('Commit failed: ' + (e instanceof Error ? e.message : String(e))); }
      };
    });
    box.querySelectorAll<HTMLElement>('.cp-discard').forEach(btn => {
      btn.onclick = async () => {
        const section = btn.dataset.section || '';
        const ok = await (window as any).Dialog?.confirm?.({
          title: 'Discard Changes',
          message: 'Discard live ' + section + ' changes and restore from source? (undoable)',
          danger: true
        });
        if (!ok) return;
        try {
          await apply([], [section]);
          toastInfo('Restored ' + section + ' from source.');
          _cache = await fetchDiff();
          close(); render(_cache);
        } catch (e) { toastError('Discard failed: ' + (e instanceof Error ? e.message : String(e))); }
      };
    });

    _cache = data; // keep for re-render
  }

  return { open, fetchDiff, apply };
})();
(window as unknown as { ChangesPanel: typeof ChangesPanel }).ChangesPanel = ChangesPanel;

/**
 * Type declarations live BELOW the first value statement on purpose: TypeScript
 * drops a file's leading JSDoc when the first statement is type-only, and
 * `tools/js_module_index.py` reads `@module` out of the emitted .js.
 */

/** Shape of GET /api/scenario/diff. */
interface DiffResponse {
  groups?: Record<string, string[]>;
  source?: string;
  error?: string;
  [key: string]: unknown;
}
