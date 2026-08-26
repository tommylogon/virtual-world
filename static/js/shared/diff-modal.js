/**
 * DiffModal — Reusable conflict-resolution modal for world→library sync.
 *
 * Shows section-by-section comparison between current (library) and incoming (world).
 * User picks which sections to update, saves as duplicate, or cancels.
 *
 * Usage:
 *   const result = await DiffModal.show(currentLibEntry, worldPayload, sections, options);
 *   // result = null (cancel), { action: 'update', sections: [...] },
 *   //           { action: 'duplicate', name: '...', id: '...', sections: [...] }
 *
 * Sections format:
 *   [{ key: 'description', label: 'Description' }, ...]
 */
const diffModalTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.DiffModal = (() => {
  const esc = (text) => (text || '').replace(/"/g, '&quot;');

  // True for values that should be treated as "no data": null/undefined,
  // blank string, or empty array/object.
  function isEmptyValue(value) {
    if (value === null || value === undefined) return true;
    if (typeof value === 'string') return value.trim() === '';
    if (Array.isArray(value)) return value.length === 0;
    if (typeof value === 'object') return Object.keys(value).length === 0;
    return false;
  }

  function canonicalize(value) {
    if (value === null || value === undefined) return value;
    if (Array.isArray(value)) return value.map(canonicalize);
    if (typeof value === 'object') {
      const out = {};
      for (const k of Object.keys(value).sort()) out[k] = canonicalize(value[k]);
      return out;
    }
    return value;
  }

  function compareValues(a, b) {
    const ca = canonicalize(a);
    const cb = canonicalize(b);
    const sa = ca === undefined || ca === null ? '' : JSON.stringify(ca);
    const sb = cb === undefined || cb === null ? '' : JSON.stringify(cb);
    return sa !== sb;
  }

  function truncate(val, len = 5000) {
    if (val === undefined || val === null) return '(empty)';
    let s = typeof val === 'object' ? JSON.stringify(val) : String(val);
    return s.length > len ? s.substring(0, len) + '...' : s;
  }

  function diffCell(key, label, current, incoming, isDiff, clobber = false, clobberTip = '') {
    const cur = truncate(current);
    const inc = truncate(incoming);
    let inner;
    const needsScroll = (typeof incoming === 'object' && incoming !== null) ||
                     (cur.length > 50 || inc.length > 50);
    if (needsScroll) {
      inner = `<pre class="diff-cell scroll" title="Full JSON value">${esc(cur)} → ${esc(inc)}</pre>`;
    } else {
      inner = `<div class="diff-cell-inline">${esc(cur)} → ${esc(inc)}</div>`;
    }
    // A "clobber" is when one side has data and the other is empty — enable
    // applying by default would erase the data side. Left unchecked as a warning.
    const toggleState = clobber ? '' : (isDiff ? 'checked' : '');
    const toggleDisabled = clobber ? '' : '';
    return `<div class="diff-section" data-key="${key}" ${isDiff ? 'style="background:rgba(136,255,136,0.05);"' : ''}>
      <input type="checkbox" class="diff-section-toggle" data-key="${key}" ${toggleState} ${toggleDisabled} style="margin:0;" title="${esc(clobberTip)}">
      <div style="font-weight:${isDiff ? '600' : '400'};color:${isDiff ? (clobber ? '#e3b341' : 'var(--text)') : 'var(--text-muted)'};">${esc(label)}${clobber ? ' ⚠' : ''}</div>
      <div style="color:${isDiff ? (clobber ? '#e3b341' : '#88ff88') : 'var(--text-muted)'};font-size:10px;${isDiff ? '' : 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'}">${inner}</div>
    </div>`;
  }

  /**
   * Show the diff modal. Returns a promise.
   * @param {object} current — library entry (the one on disk)
   * @param {object} incoming — world payload (what we're saving)
   * @param {Array<{key:string,label:string}>} sections — section definitions
   * @param {object} options — { title, name, onDuplicate }
   * @returns {Promise<null|{action:string,sections:string[],name?:string,id?:string}>}
   */
  function show(current, incoming, sections, options = {}) {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay';

      const toWorld = options.direction === 'to-world';
      const clobberTip = toWorld
        ? 'This field is empty in the library but has data in the world — applying would erase it.'
        : 'This field has data in the library but is empty in the world — applying would erase it.';

      const modal = document.createElement('div');
      const diffs = sections.map(s => {
        const isDifferent = compareValues(current?.[s.key], incoming?.[s.key]);
        const clobber = toWorld
          ? isDifferent && !isEmptyValue(incoming?.[s.key]) && isEmptyValue(current?.[s.key])
          : isDifferent && !isEmptyValue(current?.[s.key]) && isEmptyValue(incoming?.[s.key]);
        return { ...s, isDifferent, clobber };
      });
      const hasDiffs = diffs.some(d => d.isDifferent);

      let html = `<div class="modal-head">
        <h3 style="margin:0;font-size:15px;">${esc(options.title || 'Save to Library')}</h3>
        <button class="modal-close-btn" id="diff-modal-cancel">✕</button>
      </div>`;

      if (!hasDiffs) {
        html += `<p style="padding:12px 0;color:var(--text-muted);font-size:13px;">
          No changes detected — the library entry is already up to date.
        </p>
        <div style="display:flex;gap:8px;justify-content:flex-end;padding-top:12px;border-top:1px solid var(--border);">
          <button class="btn btn-sm" id="diff-modal-close">OK</button>
        </div>`;
      } else if (options.readOnly) {
        html += `<p style="font-size:12px;color:var(--text-muted);margin-bottom:12px;">
          Comparing library entry <strong>${esc(options.name || '')}</strong> with the world copy.
          Select a section to see both values. (Read-only)
        </p>`;

        html += `<div style="display:grid;grid-template-columns:auto 1fr 1fr;gap:6px;font-size:11px;margin-bottom:8px;padding:6px 0;border-bottom:1px solid var(--border);color:var(--text-muted);font-weight:600;">
          <div></div>
          <div>Section</div>
          <div>Library → World</div>
        </div>`;

        diffs.forEach(s => {
          html += diffCell(s.key, s.label, current?.[s.key], incoming?.[s.key], s.isDifferent, s.clobber, clobberTip);
        });

        html += `<div style="display:flex;gap:8px;justify-content:flex-end;padding-top:12px;border-top:1px solid var(--border);margin-top:8px;">
          <button class="btn btn-sm" id="diff-modal-close-bottom">Close</button>
        </div>`;
      } else {
        html += `<p style="font-size:12px;color:var(--text-muted);margin-bottom:12px;">
          The library entry <strong>${esc(options.name || '')}</strong> already exists with different values.
          Select which sections to update, or save as a new entry.
        </p>`;

        html += `<div style="display:grid;grid-template-columns:auto 1fr 1fr;gap:6px;font-size:11px;margin-bottom:8px;padding:6px 0;border-bottom:1px solid var(--border);color:var(--text-muted);font-weight:600;">
          <div></div>
          <div>Section</div>
          <div>Library → World</div>
        </div>`;

        diffs.forEach(s => {
          html += diffCell(s.key, s.label, current?.[s.key], incoming?.[s.key], s.isDifferent, s.clobber, clobberTip);
        });

        html += `<div style="display:flex;gap:8px;justify-content:space-between;padding-top:12px;border-top:1px solid var(--border);margin-top:8px;">
          <div style="display:flex;gap:8px;">
            <button class="btn btn-sm btn-yellow" id="diff-modal-duplicate">📋 Save as Duplicate</button>
          </div>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-sm" id="diff-modal-cancel-bottom">Cancel</button>
            <button class="btn btn-sm btn-green" id="diff-modal-update">Update Selected</button>
          </div>
        </div>`;
      }

      window.Lit.render(diffModalTag`${window.Lit.unsafeHTML(html)}`, modal);
      overlay.appendChild(modal);
      document.body.appendChild(overlay);

      const cleanup = () => {
        if (overlay.parentNode) document.body.removeChild(overlay);
      };

      document.getElementById('diff-modal-cancel').onclick = () => { cleanup(); resolve(null); };
      const cancelBtn = document.getElementById('diff-modal-cancel-bottom');
      if (cancelBtn) cancelBtn.onclick = () => { cleanup(); resolve(null); };
      const closeBtn = document.getElementById('diff-modal-close');
      if (closeBtn) closeBtn.onclick = () => { cleanup(); resolve(null); };
      const closeBottomBtn = document.getElementById('diff-modal-close-bottom');
      if (closeBottomBtn) closeBottomBtn.onclick = () => { cleanup(); resolve(null); };

      const updateBtn = document.getElementById('diff-modal-update');
      if (updateBtn) {
        updateBtn.onclick = () => {
          const toggles = modal.querySelectorAll('.diff-section-toggle');
          const selected = [];
          toggles.forEach(t => { if (t.checked) selected.push(t.dataset.key); });
          cleanup();
          resolve({ action: 'update', sections: selected });
        };
      }

      const dupeBtn = document.getElementById('diff-modal-duplicate');
      if (dupeBtn) {
        dupeBtn.onclick = () => {
          const newName = prompt('Enter a name for the duplicate entry:', (options.name || '') + ' (copy)');
          if (!newName) return;
          cleanup();
          const newId = newName.toLowerCase().replace(/[^a-z0-9_]+/g, '_');
          const toggles = modal.querySelectorAll('.diff-section-toggle');
          const selected = [];
          toggles.forEach(t => { if (t.checked) selected.push(t.dataset.key); });
          resolve({ action: 'duplicate', name: newName, id: newId, sections: selected });
        };
      }
    });
  }

  return { show };
})();
