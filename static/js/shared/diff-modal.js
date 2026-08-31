/**
 * DiffModal — Reusable conflict-resolution modal for world↔library sync.
 *
 * Shows a section-by-section comparison between the current (on-disk library)
 * entry and the incoming (world) payload. The user picks which sections to
 * update, saves as a duplicate, or cancels.
 *
 * Per-entry upgrade (v2):
 *   Sections can opt into per-entry granularity by setting `perEntry: true`.
 *   Such sections render as an expandable group whose rows are individual
 *   entries (a memory, an item, a condition, one relationship, etc.) with
 *   their own checkboxes plus an `all of category` toggle. This lets you
 *   carry over just a few memories or items instead of clobbering the whole
 *   category.
 *
 * Usage:
 *   const result = await DiffModal.show(currentLibEntry, worldPayload, sections, options);
 *   // result = null (cancel)
 *   //        | { action: 'update',    sections: [...], entries: {...} }
 *   //        | { action: 'duplicate', name, id, sections: [...], entries: {...} }
 *
 *   `sections`  — whole-section keys to apply.
 *   `entries`   — { key: [entryKey, ...] } per-entry selection for
 *                 perEntry sections that are only partially selected.
 *
 * Sections format:
 *   [{ key: 'description', label: 'Description' },
 *    { key: 'memories',    label: 'Memories', perEntry: true }]
 *
 * Entry identifiers: for object sections (relationships, conditions, equipped,
 * vitals, ...) the identifier is the object key; for array sections (memories,
 * items) it is `id` when present, else `name`.
 */
const diffModalTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.DiffModal = (() => {
  const esc = (text) => (text || '').replace(/"/g, '&quot;');

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

  // Compact human-readable summary for one entry value. The label line already
  // shows the entry's text/name, so this shows the *metadata* instead of dumping
  // the full JSON object (which made memory/relationship diff rows unreadable).
  function entrySummary(val) {
    if (val === undefined || val === null) return '(empty)';
    if (typeof val === 'string') return truncate(val, 120);
    if (typeof val !== 'object') return truncate(String(val), 60);
    if (typeof val.text === 'string') {
      const parts = ['⭐' + (val.importance ?? '?')];
      if (Array.isArray(val.tags) && val.tags.length) parts.push('#' + val.tags.join(' #'));
      const emos = (Array.isArray(val.memory_emotions) && val.memory_emotions.length)
        ? val.memory_emotions
        : (val.emotion && val.emotion.label ? [val.emotion] : []);
      if (emos.length) parts.push(emos.map(e => String(e.label || '') + (e.intensity ? ':' + e.intensity : '')).join(', '));
      if (val.location) parts.push('📍' + val.location);
      if (val.source) parts.push(val.source);
      return truncate(parts.join(' · '), 160) || '(no metadata)';
    }
    if (typeof val.name === 'string') return truncate(String(val.name), 60);
    // Compact fallback for relationship/condition/equipped objects.
    return truncate(JSON.stringify(val), 200);
  }

  // ── Per-entry helpers ──────────────────────────────────────────────

  // Object sections use their own key; array sections match by `id` first and
  // fall back to a normalized content signature, so a runtime memory and its
  // library copy (which may carry a different regenerated random id) still line
  // up as one "changed"/"same" row instead of a +add/−remove pair.
  function idKeyOf(item) {
    if (item && typeof item === 'object') {
      if (item.id != null && item.id !== '') return String(item.id);
      if (item.name != null && item.name !== '') return 'name:' + String(item.name);
    }
    return null;
  }
  function contentKeyOf(item) {
    if (item && typeof item === 'object' && typeof item.text === 'string' && item.text.trim()) {
      return 'text:' + item.text.toLowerCase().replace(/\s+/g, ' ').trim();
    }
    return null;
  }
  // Selection key carried by the checkbox / matched by applyEntrySelection.
  function selKeyOf(item) {
    const id = idKeyOf(item);
    if (id !== null) return id;
    return contentKeyOf(item);
  }

  function toEntryList(value) {
    if (Array.isArray(value)) return value.map((item, i) => ({ key: selKeyOf(item) ?? i, data: item }));
    if (value && typeof value === 'object') return Object.keys(value).map((k) => ({ key: k, data: value[k] }));
    return [];
  }

  // A section is eligible for per-entry editing only when every entry has an
  // individually addressable key (object keys, or array entries with id/name/text).
  function perEntryEligible(value) {
    if (Array.isArray(value)) {
      if (value.length === 0) return false;
      return value.every((v) => selKeyOf(v) !== null);
    }
    if (value && typeof value === 'object') return Object.keys(value).length > 0;
    return false;
  }

  function entryLabel(key, data) {
    if (data && typeof data === 'object') {
      if (typeof data.text === 'string') return truncate(data.text, 90);
      if (typeof data.name === 'string') return truncate(data.name, 40);
      if (typeof data.id === 'string') return truncate(data.id, 24);
    }
    return truncate(key, 40);
  }

  // Content equality ignoring identity/derived fields (id, embedding), so a
  // memory that is identical except for its random id reads as "same", and an
  // embedding that gets regenerated does not force "changed".
  function contentEquals(a, b) {
    const strip = (v) => {
      if (Array.isArray(v)) return v.map(strip);
      if (v && typeof v === 'object') {
        const o = {};
        for (const k of Object.keys(v)) { if (k === 'id' || k === 'embedding') continue; o[k] = strip(v[k]); }
        return o;
      }
      return v;
    };
    const sa = JSON.stringify(strip(a) ?? '');
    const sb = JSON.stringify(strip(b) ?? '');
    return sa === sb;
  }

  // Two-pass per-entry diff: pair by id, then pair the leftovers by content.
  function entryDiff(current, incoming) {
    const cList = toEntryList(current);
    const iList = toEntryList(incoming);
    const usedC = new Array(cList.length).fill(false);
    const usedI = new Array(iList.length).fill(false);
    const rows = [];

    const pairBy = (keyFn) => {
      cList.forEach((cEle, ci) => {
        if (usedC[ci]) return;
        const ck = keyFn(cEle.data);
        if (ck === null) return;
        const ii = iList.findIndex((iEle, i) => !usedI[i] && keyFn(iEle.data) === ck);
        if (ii < 0) return;
        usedC[ci] = true;
        usedI[ii] = true;
        const inc = iList[ii].data;
        rows.push({ key: selKeyOf(inc), current: cEle.data, incoming: inc, status: contentEquals(cEle.data, inc) ? 'same' : 'changed' });
      });
    };

    pairBy(idKeyOf);
    pairBy(contentKeyOf);

    cList.forEach((cEle, ci) => {
      if (!usedC[ci]) rows.push({ key: selKeyOf(cEle.data), current: cEle.data, incoming: undefined, status: 'removed' });
    });
    iList.forEach((iEle, i) => {
      if (!usedI[i]) rows.push({ key: selKeyOf(iEle.data), current: undefined, incoming: iEle.data, status: 'added' });
    });
    return rows;
  }

  const STATUS_COLOR = { same: 'var(--text-muted)', added: '#88ff88', removed: '#ff7b7b', changed: '#e3b341' };
  const STATUS_LABEL = { same: '=', added: '+', removed: '−', changed: '~' };

  function statusBadge(status) {
    return '<span class="pe-status" style="color:' + STATUS_COLOR[status] + ';font-weight:700;min-width:14px;text-align:center;display:inline-block;" title="' + status + '">'
      + (STATUS_LABEL[status] || '') + '</span>';
  }

  // Render an expandable per-entry group for one section.
  // `toWorld` (lib→world) marks entries that exist in the library but are
  // missing/different in the world as the ones to copy over; the save direction
  // (world→lib) marks entries that exist in the world as the ones to carry over.
  function perEntryGroup(key, label, current, incoming, ro, toWorld) {
    const rows = entryDiff(current, incoming);
    const changedCount = rows.filter((r) => r.status === 'changed').length;
    const addedCount = rows.filter((r) => r.status === 'added').length;
    const removedCount = rows.filter((r) => r.status === 'removed').length;
    const changedAny = changedCount + addedCount + removedCount > 0;
    const isApplyable = (st) => toWorld ? (st === 'changed' || st === 'removed') : (st === 'changed' || st === 'added');
    const defaultChecked = rows.some((r) => isApplyable(r.status) && r.status !== 'same');

    let rowHtml = '';
    rows.forEach((r) => {
      const selectable = !ro && isApplyable(r.status) && r.status !== 'same';
      const checked = selectable ? 'checked' : '';
      const labelText = entryLabel(r.key, r.incoming === undefined ? r.current : r.incoming);
      const cell = '<div class="diff-cell-inline" style="font-size:10px;">'
        + esc(entrySummary(r.current)) + ' <span style="color:var(--text-muted)">→</span> ' + esc(entrySummary(r.incoming))
        + '</div>';
      rowHtml += '<div class="pe-row" style="display:grid;grid-template-columns:auto 16px 1fr;gap:8px;align-items:start;padding:3px 0;border-bottom:1px solid var(--border);">'
        + '<input type="checkbox" class="pe-entry" data-key="' + esc(key) + '" data-entry="' + esc(r.key) + '" ' + checked + ' '
          + (ro ? 'disabled' : 'style="margin:0;"') + '>',
      rowHtml += statusBadge(r.status);
      rowHtml += '<div style="min-width:0;"><div style="font-size:11px;font-weight:500;">' + esc(labelText) + '</div>' + cell + '</div>';
      rowHtml += '</div>';
    });

    const open = changedAny ? '' : 'hidden';

    return '<div class="diff-section pe" data-key="' + esc(key) + '" '
      + (changedAny ? 'style="background:rgba(136,255,136,0.05);"' : '') + '>'
      + '<div class="pe-head" style="display:flex;align-items:center;gap:6px;cursor:pointer;">'
      + '<input type="checkbox" class="diff-section-toggle" data-key="' + esc(key) + '" ' + (defaultChecked ? 'checked' : '') + ' '
        + (ro ? 'disabled' : 'style="margin:0;"') + ' title="Apply the whole category">'
      + '<span class="pe-chevron" style="color:var(--text-muted);font-size:10px;transform:rotate(90deg);">▶</span>'
      + '<span style="font-weight:600;color:var(--text);">' + esc(label) + '</span>'
      + '<span style="margin-left:auto;font-size:10px;color:var(--text-muted);">'
      + (changedAny
          ? changedCount + ' chg · ' + addedCount + ' add · ' + removedCount + ' rem'
          : rows.length + ' entries unchanged')
      + '</span>'
      + '</div>'
      + '<div class="pe-body" ' + open + ' style="padding:0 0 4px 22px;margin-top:4px;">'
      + '<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text-muted);margin-bottom:4px;">'
      + '<label style="display:flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" class="pe-all" data-key="' + esc(key) + '" ' + (ro ? 'disabled' : '') + '> Select all ' + rows.length + ' entries</label>'
      + '<span style="margin-left:auto;font-size:10px;">' + (toWorld ? 'Entries present in the library are pre-selected to copy onto the world.' : 'Changed/added world entries are pre-selected.') + '</span>'
      + '</div>'
      + rowHtml
      + '</div>'
      + '</div>';
  }

  function diffCell(key, label, current, incoming, isDiff, clobber = false, clobberTip = '') {
    const cur = truncate(current);
    const inc = truncate(incoming);
    let inner;
    const needsScroll = (typeof incoming === 'object' && incoming !== null) ||
                     (cur.length > 50 || inc.length > 50);
    if (needsScroll) {
      inner = '<pre class="diff-cell scroll" title="Full JSON value">' + esc(cur) + ' → ' + esc(inc) + '</pre>';
    } else {
      inner = '<div class="diff-cell-inline">' + esc(cur) + ' → ' + esc(inc) + '</div>';
    }
    const toggleState = clobber ? '' : (isDiff ? 'checked' : '');
    return '<div class="diff-section" data-key="' + key + '" ' + (isDiff ? 'style="background:rgba(136,255,136,0.05);"' : '') + '>'
      + '<input type="checkbox" class="diff-section-toggle" data-key="' + key + '" ' + toggleState + ' style="margin:0;" title="' + esc(clobberTip) + '">'
      + '<div style="font-weight:' + (isDiff ? '600' : '400') + ';color:' + (isDiff ? (clobber ? '#e3b341' : 'var(--text)') : 'var(--text-muted)') + ';">' + esc(label) + (clobber ? ' ⚠' : '') + '</div>'
      + '<div style="color:' + (isDiff ? (clobber ? '#e3b341' : '#88ff88') : 'var(--text-muted)') + ';font-size:10px;' + (isDiff ? '' : 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;') + '">' + inner + '</div>'
      + '</div>';
  }

  function show(current, incoming, sections, options = {}) {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay';

      const toWorld = options.direction === 'to-world';
      const clobberTip = toWorld
        ? 'This field is empty in the library but has data in the world — applying would erase it.'
        : 'This field has data in the library but is empty in the world — applying would erase it.';

      const modal = document.createElement('div');
      modal.className = 'modal-window';
      const diffs = sections.map((s) => {
        const isDifferent = compareValues(current?.[s.key], incoming?.[s.key]);
        const clobber = toWorld
          ? isDifferent && !isEmptyValue(incoming?.[s.key]) && isEmptyValue(current?.[s.key])
          : isDifferent && !isEmptyValue(current?.[s.key]) && isEmptyValue(incoming?.[s.key]);
        const isPerEntry = !!s.perEntry && perEntryEligible(incoming?.[s.key]);
        return Object.assign({}, s, { isDifferent, clobber, isPerEntry });
      });
      const hasDiffs = diffs.some((d) => d.isDifferent);

      let html = '<div class="modal-head">'
        + '<h3 style="margin:0;font-size:15px;">' + esc(options.title || 'Save to Library') + '</h3>'
        + '<button class="modal-close-btn" id="diff-modal-cancel">✕</button>'
        + '</div>';

      if (!hasDiffs) {
        html += '<p style="padding:12px 0;color:var(--text-muted);font-size:13px;">'
          + 'No changes detected — the library entry is already up to date.'
          + '</p>'
          + '<div style="display:flex;gap:8px;justify-content:flex-end;padding-top:12px;border-top:1px solid var(--border);">'
          + '<button class="btn btn-sm" id="diff-modal-close">OK</button>'
          + '</div>';
      } else {
        html += '<p style="font-size:12px;color:var(--text-muted);margin-bottom:12px;">'
          + (options.readOnly
              ? 'Comparing library entry <strong>' + esc(options.name || '') + '</strong> with the world copy. Expand a category and select an entry to inspect it. (Read-only)'
              : 'The library entry <strong>' + esc(options.name || '') + '</strong> already exists with different values. Check whole sections, or expand a category to pick individual memories/items. Otherwise save as a new entry.') + '</p>';

        diffs.forEach((s) => {
          if (s.isPerEntry) {
            html += perEntryGroup(s.key, s.label, current?.[s.key], incoming?.[s.key], options.readOnly, toWorld);
          } else {
            html += diffCell(s.key, s.label, current?.[s.key], incoming?.[s.key], s.isDifferent, s.clobber, clobberTip);
          }
        });

        html += '<div style="display:flex;gap:8px;justify-content:' + (options.readOnly ? 'flex-end' : 'space-between') + ';padding-top:12px;border-top:1px solid var(--border);margin-top:8px;">';
        if (!options.readOnly) {
          html += '<div style="display:flex;gap:8px;"><button class="btn btn-sm btn-yellow" id="diff-modal-duplicate">📋 Save as Duplicate</button></div>';
        }
        html += '<div style="display:flex;gap:8px;">'
          + '<button class="btn btn-sm" id="diff-modal-cancel-bottom">' + (options.readOnly ? 'Close' : 'Cancel') + '</button>'
          + (options.readOnly ? '' : '<button class="btn btn-sm btn-green" id="diff-modal-update">Update Selected</button>')
          + '</div></div>';
      }

      window.Lit.render(window.Lit.unsafeHTML(html), modal);
      overlay.appendChild(modal);
      document.body.appendChild(overlay);

      // Escape + click-on-backdrop close, matching the app's other modals.
      const escClose = (e) => { if (e.key === 'Escape') { e.preventDefault(); cleanup(); resolve(null); } };
      const cleanup = () => { document.removeEventListener('keydown', escClose); if (overlay.parentNode) document.body.removeChild(overlay); };
      document.addEventListener('keydown', escClose);
      overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) { cleanup(); resolve(null); } });

      document.getElementById('diff-modal-cancel').onclick = () => { cleanup(); resolve(null); };
      const cancelBtn = document.getElementById('diff-modal-cancel-bottom');
      if (cancelBtn) cancelBtn.onclick = () => { cleanup(); resolve(null); };
      const closeBtn = document.getElementById('diff-modal-close');
      if (closeBtn) closeBtn.onclick = () => { cleanup(); resolve(null); };

      // Wire per-group expand/collapse + whole/all toggles.
      modal.querySelectorAll('.pe').forEach((group) => {
        const head = group.querySelector('.pe-head');
        const chevron = group.querySelector('.pe-chevron');
        const body = group.querySelector('.pe-body');
        const sectionToggle = group.querySelector('.diff-section-toggle');
        const allToggle = group.querySelector('.pe-all');
        if (head) {
          head.onclick = (ev) => {
            if (ev.target && (ev.target === sectionToggle || (ev.target.tagName === 'INPUT'))) return;
            const hidden = body.hasAttribute('hidden');
            body.toggleAttribute('hidden');
            chevron.style.transform = hidden ? 'rotate(90deg)' : 'rotate(0deg)';
          };
        }
        if (sectionToggle && !sectionToggle.disabled) {
          sectionToggle.onchange = () => {
            const on = sectionToggle.checked;
            group.querySelectorAll('.pe-entry').forEach((e) => { e.checked = on; });
            if (allToggle) allToggle.checked = on;
          };
        }
        if (allToggle && !allToggle.disabled) {
          allToggle.onchange = () => {
            group.querySelectorAll('.pe-entry').forEach((e) => { e.checked = allToggle.checked; });
          };
        }
      });

      const collectResult = (action, extra) => {
        const selected = [];
        const entries = {};
        modal.querySelectorAll('.pe').forEach((group) => {
          const key = group.dataset.key;
          const sectionToggle = group.querySelector('.diff-section-toggle');
          if (sectionToggle && sectionToggle.checked) {
            if (!selected.includes(key)) selected.push(key);
            return;
          }
          const checked = [];
          group.querySelectorAll('.pe-entry').forEach((e) => { if (e.checked) checked.push(e.dataset.entry); });
          if (checked.length > 0) entries[key] = checked;
        });
        modal.querySelectorAll('.diff-section:not(.pe) .diff-section-toggle').forEach((t) => {
          if (t.checked && !selected.includes(t.dataset.key)) selected.push(t.dataset.key);
        });
        const base = { action, sections: selected, entries };
        return extra ? Object.assign(base, extra) : base;
      };

      const updateBtn = document.getElementById('diff-modal-update');
      if (updateBtn) {
        updateBtn.onclick = () => { cleanup(); resolve(collectResult('update')); };
      }

      const dupeBtn = document.getElementById('diff-modal-duplicate');
      if (dupeBtn) {
        dupeBtn.onclick = () => {
          const newName = prompt('Enter a name for the duplicate entry:', (options.name || '') + ' (copy)');
          if (!newName) return;
          cleanup();
          const newId = newName.toLowerCase().replace(/[^a-z0-9_]+/g, '_');
          resolve(collectResult('duplicate', { name: newName, id: newId }));
        };
      }
    });
  }

  // Apply a per-entry selection onto a base value. Symmetric for save (world→
  // lib) and refresh (lib→world): `current` is the existing value, `incoming`
  // the source carrying the selected entries, `selKeys` the chosen entry keys.
  function applyEntrySelection(current, incoming, selKeys) {
    if (!incoming || !selKeys || selKeys.length === 0) return current;
    if (Array.isArray(incoming)) {
      const selSet = new Set(selKeys);
      let out = Array.isArray(current) ? current.slice() : [];
      const findPartner = (inc) => {
        const id = idKeyOf(inc);
        if (id !== null) {
          const idx = out.findIndex((x) => idKeyOf(x) === id);
          if (idx >= 0) return idx;
        }
        const ck = contentKeyOf(inc);
        if (ck !== null) {
          const idx = out.findIndex((x) => contentKeyOf(x) === ck);
          if (idx >= 0) return idx;
        }
        return -1;
      };
      for (const inc of incoming) {
        const sk = selKeyOf(inc);
        if (sk === null || !selSet.has(sk)) continue;
        const idx = findPartner(inc);
        if (idx >= 0) {
          // Preserve the existing row's id so future syncs keep matching by id.
          out[idx] = (out[idx] && out[idx].id != null && out[idx].id !== '')
            ? Object.assign({}, inc, { id: out[idx].id })
            : inc;
        } else {
          out.push(inc);
        }
      }
      return out;
    }
    if (incoming && typeof incoming === 'object') {
      const out = current && typeof current === 'object' && !Array.isArray(current) ? Object.assign({}, current) : {};
      for (const k of selKeys) {
        if (incoming[k] !== undefined) out[k] = incoming[k];
      }
      return out;
    }
    return incoming;
  }

  return { show, applyEntrySelection };
})();
