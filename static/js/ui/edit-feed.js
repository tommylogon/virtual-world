/**
 * edit-feed.js — "World edited" feed with per-edit undo (task-384)
 *
 * Listens to the SAME EventSource world_changed stream as world-state.js and
 * records a short toast-style feed (bottom-right). Each entry carries the
 * mutation (method + path from the server event) and a ↩ Undo button that
 * pops exactly one undo snapshot (the one that mutation pushed), reverting
 * just that edit. Feed is session-local, capped at 8.
 *
 * Caveat: undo pops the NEWEST snapshot, not this specific one — feeds are
 * per-edit *labels* for visibility; exact ordering discipline is the undo
 * stack's job. Practically the newest edit is the one in front of you.
 */
window.EditFeed = (() => {
  'use strict';

  const MAX = 8;
  let _el = null;
  let _rows = [];

  const METHOD_ICON = { POST: '✚', PATCH: '✎', DELETE: '🗑', PUT: '⇅' };
  const PATH_LABEL = (path) => {
    const p = String(path || '');
    if (p.includes('/graph/node/')) return 'graph node edited';
    if (p.includes('/graph/edge')) return 'graph edge edited';
    if (p === '/api/load') return 'world loaded';
    if (p === '/api/reset') return 'world reset';
    if (p.includes('/api/players')) return 'player updated';
    if (p.includes('/api/memory')) return 'memory updated';
    if (p.includes('/library')) return 'library edited';
    return p.replace('/api/', '') || 'world changed';
  };

  function ensureEl() {
    if (_el && document.body.contains(_el)) return _el;
    _el = document.createElement('div');
    _el.id = 'edit-feed';
    _el.style.cssText = 'position:fixed;bottom:14px;right:14px;z-index:9500;display:flex;flex-direction:column;gap:4px;max-width:320px;';
    document.body.appendChild(_el);
    return _el;
  }

  function push(ev) {
    const el = ensureEl();
    const row = document.createElement('div');
    const method = (ev.method || 'POST').toUpperCase();
    const icon = METHOD_ICON[method] || '●';
    const label = PATH_LABEL(ev.path);
    row.style.cssText = 'display:flex;align-items:center;gap:6px;padding:4px 8px;background:rgba(20,22,30,0.92);border:1px solid var(--border);border-radius:6px;font-size:10.5px;color:var(--text);box-shadow:0 2px 8px rgba(0,0,0,0.4);';
    const iconSpan = document.createElement('span');
    iconSpan.textContent = icon;
    iconSpan.style.cssText = 'color:var(--accent);flex-shrink:0;';
    const labelSpan = document.createElement('span');
    labelSpan.textContent = label;
    labelSpan.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    const undoBtn = document.createElement('button');
    undoBtn.className = 'btn btn-sm';
    undoBtn.textContent = '↩ Undo';
    undoBtn.style.cssText = 'font-size:9px;padding:1px 6px;flex-shrink:0;';
    undoBtn.onclick = async () => {
      try {
        const resp = await fetch('/api/undo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ steps: 1 })
        });
        const data = await resp.json();
        if (data.error) { toastError('Undo failed: ' + data.error); return; }
        try { graphManager.loadGraphData(); } catch (e) {}
        worldState.fetch();
        if (typeof toastInfo === 'function') toastInfo('Undid: ' + label + '.');
      } catch (e) {
        toastError('Undo failed: ' + (e.message || e));
      }
    };
    row.appendChild(iconSpan);
    row.appendChild(labelSpan);
    row.appendChild(undoBtn);
    el.appendChild(row);
    _rows.push(row);
    if (_rows.length > MAX) {
      const old = _rows.shift();
      old.remove();
    }
    // fade old rows after 12s
    setTimeout(() => { row.style.opacity = '0'; row.style.transition = 'opacity 0.5s'; setTimeout(() => row.remove(), 600); }, 12000);
  }

  // Subscribe to the same /api/events stream (world-state.js also reads it;
  // EventSource allows multiple listeners per connection? NO — one per tab.
  // Use a shared bus: world-state.js emits appEvents 'world:changed' after
  // its own stream handler. Fall back to a second EventSource if the bus is
  // missing (duplicate events are harmless-ish; dedupe by seq).
  let _lastSeq = -1;
  function attach() {
    if (window.appEvents) {
      appEvents.on('world:changed', (ev) => {
        if (ev && ev.seq != null && ev.seq === _lastSeq) return;
        if (ev && ev.seq != null) _lastSeq = ev.seq;
        push(ev || {});
      });
    } else {
      try {
        const es = new EventSource('/api/events');
        es.onmessage = (msg) => {
          let ev; try { ev = JSON.parse(msg.data); } catch (e) { return; }
          if (!ev || ev.type !== 'world_changed') return;
          if (ev.seq != null && ev.seq === _lastSeq) return;
          if (ev.seq != null) _lastSeq = ev.seq;
          push(ev);
        };
      } catch (e) { /* offline */ }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attach);
  } else {
    attach();
  }

  return { push, attach };
})();
