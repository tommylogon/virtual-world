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
 */
window.ChangesPanel = (() => {
  'use strict';

  let _cache = null; // last diff response (for re-render after apply)

  const GROUP_META = {
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
  const SECTION_OF = (key) => {
    if (key.includes('_area')) return 'areas';
    if (key.includes('_item')) return 'items';
    if (key.includes('_way')) return 'ways';
    if (key.includes('_player')) return 'players';
    return null;
  };

  async function fetchDiff() {
    const resp = await fetch('/api/scenario/diff');
    return resp.json();
  }

  async function apply(commit = [], discard = []) {
    const resp = await fetch('/api/scenario/diff/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ commit, discard }),
    });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    if (window.worldState) worldState.fetch();
    if (window.ScenarioStatus) ScenarioStatus.refresh();
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

  function render(data) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    const box = document.createElement('div');
    box.className = 'modal-window';
    box.style.cssText = 'width:640px;max-width:92vw;max-height:85vh;display:flex;flex-direction:column;';

    const groups = data.groups || {};
    const source = data.source || '';
    const anyDiff = Object.values(groups).some(list => Array.isArray(list) && list.length > 0);

    let body = '<div class="modal-head"><h3 style="margin:0;font-size:15px;">🔄 Changes since source</h3>'
      + '<button class="modal-close-btn" id="cp-close">✕</button></div>'
      + '<div style="font-size:10px;color:var(--text-muted);padding-bottom:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escAttr(source) + '">Source: ' + (source ? escAttr(source.split(/[\\/]/).pop()) : 'none — commit first') + '</div>';

    if (!source) {
      body += '<div style="padding:12px 0;color:var(--text-dim);font-size:12px;">No scenario source yet — use 💾 Commit Scenario first.</div>';
    } else if (!anyDiff) {
      body += '<div style="padding:12px 0;color:#3fb950;font-size:12px;">✅ No drift — the live world matches the source.</div>';
    } else {
      // group rows
      body += '<div style="overflow-y:auto;flex:1;">';
      let lastSection = null;
      for (const [key, names] of Object.entries(groups)) {
        if (!Array.isArray(names) || names.length === 0) continue;
        const meta = GROUP_META[key] || { emoji: '📄', label: key, kind: 'chg' };
        const section = SECTION_OF(key) || 'other';
        if (lastSection !== null && section !== lastSection && section !== 'other') {
          body += '<div style="border-top:1px solid var(--border);margin:8px 0;"></div>';
        }
        lastSection = section;
        const color = meta.kind === 'add' ? '#3fb950' : meta.kind === 'del' ? '#f85149' : '#e3b341';
        const short = names.length > 4 ? names.slice(0, 4).join(', ') + '…' : names.join(', ');
        body += '<div style="padding:4px 2px;">'
          + '<div style="display:flex;align-items:center;gap:6px;">'
          + '<span style="flex-shrink:0;">' + meta.emoji + '</span>'
          + '<span style="color:' + color + ';font-weight:600;font-size:12px;">' + meta.label + '</span>'
          + '<span class="state-badge" style="font-size:9px;background:' + color + '22;color:' + color + ';border:1px solid ' + color + ';padding:1px 6px;border-radius:4px;">' + names.length + '</span>'
          + '</div>'
          + '<div style="font-size:10px;color:var(--text-muted);padding-left:22px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escAttr(short) + '">' + escAttr(short) + '</div>'
          + '</div>';
      }
      body += '</div>';

      // per-section action buttons
      const sections = ['areas', 'items', 'ways', 'players'];
      const present = sections.filter(s => Object.keys(groups).some(k => SECTION_OF(k) === s && Array.isArray(groups[k]) && groups[k].length > 0));
      if (present.length > 0) {
        body += '<div style="border-top:1px solid var(--border);padding-top:8px;margin-top:4px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">';
        body += '<span style="font-size:10px;color:var(--text-dim);">Commit section:</span>';
        for (const s of present) {
          body += '<button class="btn btn-sm btn-green cp-commit" data-section="' + s + '" style="font-size:10px;padding:2px 10px;">💾 ' + s.charAt(0).toUpperCase() + s.slice(1) + '</button>';
        }
        body += '<span style="font-size:10px;color:var(--text-dim);margin-left:8px;">Discard section:</span>';
        for (const s of present) {
          body += '<button class="btn btn-sm btn-red cp-discard" data-section="' + s + '" style="font-size:10px;padding:2px 10px;">↩️ ' + s.charAt(0).toUpperCase() + s.slice(1) + '</button>';
        }
        body += '</div>';
      }
    }

    // footer: full commit + refresh
    body += '<div style="display:flex;justify-content:space-between;padding-top:10px;border-top:1px solid var(--border);margin-top:8px;">'
      + '<button class="btn btn-sm btn-ghost" id="cp-refresh">🔄 Refresh</button>'
      + (source && anyDiff ? '<button class="btn btn-sm btn-green" id="cp-commit-all">💾 Commit All</button>' : '')
      + '</div>';

    box.innerHTML = body;
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    const close = () => overlay.remove();
    box.querySelector('#cp-close').onclick = close;
    overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) close(); });
    const escHandler = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); document.removeEventListener('keydown', escHandler); close(); }
    };
    document.addEventListener('keydown', escHandler);

    const refreshBtn = box.querySelector('#cp-refresh');
    if (refreshBtn) refreshBtn.onclick = async () => {
      _cache = await fetchDiff();
      close();
      render(_cache);
    };

    const commitAll = box.querySelector('#cp-commit-all');
    if (commitAll) commitAll.onclick = async () => {
      try {
        await apply(['areas', 'items', 'ways', 'players'], []);
        toastInfo('All changes committed to source.');
        _cache = await fetchDiff();
        close(); render(_cache);
      } catch (e) { toastError('Commit failed: ' + e.message); }
    };

    box.querySelectorAll('.cp-commit').forEach(btn => {
      btn.onclick = async () => {
        const section = btn.dataset.section;
        try {
          await apply([section], []);
          toastInfo('Committed ' + section + ' changes to source.');
          _cache = await fetchDiff();
          close(); render(_cache);
        } catch (e) { toastError('Commit failed: ' + e.message); }
      };
    });
    box.querySelectorAll('.cp-discard').forEach(btn => {
      btn.onclick = async () => {
        const section = btn.dataset.section;
        if (!confirm('Discard live ' + section + ' changes and restore from source? (undoable)')) return;
        try {
          await apply([], [section]);
          toastInfo('Restored ' + section + ' from source.');
          _cache = await fetchDiff();
          close(); render(_cache);
        } catch (e) { toastError('Discard failed: ' + e.message); }
      };
    });

    _cache = data; // keep for re-render
  }

  function escAttr(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  return { open, fetchDiff, apply };
})();
