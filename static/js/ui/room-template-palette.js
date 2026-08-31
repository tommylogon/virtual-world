/**
 * room-template-palette.js — New Room from Template (task-381)
 *
 * Lists library areas (data/library/areas/*) as room templates. Picking one
 * creates a fresh area from the template via POST /api/build/area (env +
 * description + tags), then optionally imports its template items into the
 * room. The new room is NOT connected to anything — use the graph to wire
 * ways to it.
 */
window.RoomTemplatePalette = (() => {
  'use strict';

  async function open() {
    let lib = {};
    try {
      lib = await ApiClient.getLibraryType('areas');
    } catch (e) {
      toastError('Could not load library areas.');
      return;
    }
    const entries = Object.entries(lib);
    if (entries.length === 0) {
      toastInfo('No area templates in the library yet — save an area with 📚 Save to Library first.');
      return;
    }

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    const box = document.createElement('div');
    box.className = 'modal-window';
    box.style.cssText = 'width:520px;max-width:92vw;max-height:80vh;display:flex;flex-direction:column;';

    let html = '<div class="modal-head"><h3 style="margin:0;font-size:15px;">🏗️ New Room from Template</h3>'
      + '<button class="modal-close-btn" id="rp-close">✕</button></div>'
      + '<div style="font-size:10px;color:var(--text-dim);margin-bottom:8px;">' + entries.length + ' library area templates. Pick one to spawn a fresh room (not wired to anything yet).</div>'
      + '<div style="overflow-y:auto;flex:1;">';

    entries.sort((a, b) => String(b[0]).localeCompare(String(a[0])));
    for (const [id, entry] of entries) {
      const name = (entry && entry.name) || id;
      const desc = (entry && entry.description) || '';
      const env = (entry && entry.environment) || {};
      const items = (entry && Array.isArray(entry.items) ? entry.items : []);
      html += '<div style="padding:6px 4px;border-bottom:1px solid var(--border);">'
        + '<div style="display:flex;align-items:center;gap:6px;">'
        + '<span>🏠</span>'
        + '<div style="flex:1;min-width:0;">'
        + '<div style="font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + esc(name) + ' <span style="font-size:9px;color:var(--text-muted);">(' + esc(id) + ')</span></div>'
        + '<div style="font-size:10px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + esc(desc) + '">' + esc(desc) + '</div>'
        + '<div style="font-size:9px;color:var(--text-dim);">' + items.length + ' items' + (env.light ? ' · light ' + env.light : '') + (env.temperature ? ' · ' + env.temperature + '°C' : '') + '</div>'
        + '</div>'
        + '<button class="btn btn-sm btn-blue" data-id="' + esc(id) + '" style="font-size:9px;padding:2px 10px;">➕ Spawn</button>'
        + '</div></div>';
    }
    html += '</div>';

    box.innerHTML = html;
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    const close = () => overlay.remove();
    box.querySelector('#rp-close').onclick = close;
    overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) close(); });
    const escHandler = (e) => { if (e.key === 'Escape') { e.preventDefault(); document.removeEventListener('keydown', escHandler); close(); } };
    document.addEventListener('keydown', escHandler);

    box.querySelectorAll('button[data-id]').forEach((btn) => {
      btn.onclick = async () => {
        const id = btn.dataset.id;
        const entry = lib[id] || {};
        const name = (entry.name || id).replace(/\s+/g, ' ').trim();
        let finalName = name;
        // de-dupe: append " (2)" etc if an area with that name exists
        let suffix = 2;
        const existingNames = new Set(Object.keys(worldState.areas || {}).map(s => s.toLowerCase()));
        while (existingNames.has(finalName.toLowerCase())) {
          finalName = `${name} (${suffix++})`;
        }
        const env = entry.environment || {};
        try {
          const res = await ApiClient.post('/api/build/area', {
            name: finalName,
            description: entry.description || '',
            light: env.light ?? 'normal',
            temperature: env.temperature ?? 21,
            air: env.air ?? 'fresh',
            smell: env.smell ?? 'neutral',
            noise: env.noise ?? 'quiet',
            tags: entry.tags || [],
          });
          if (res.error) throw new Error(res.error);
          // import template items via legacy build-item (each placed in the room)
          const items = Array.isArray(entry.items) ? entry.items : [];
          let placed = 0;
          for (const item of items) {
            if (!item || !item.name) continue;
            const ires = await ApiClient.post('/api/build/item', {
              name: String(item.name),
              area: finalName,
              description: item.description || '',
              actions: item.actions || 'examine,take,use',
              uses: item.uses ?? -1,
              weight: item.weight ?? 0.1,
              tags: item.tags || [],
            });
            if (!ires.error) placed++;
          }
          worldState.fetch();
          if (typeof toastInfo === 'function') toastInfo(`Room "${finalName}" spawned${placed ? ` with ${placed} template items` : ''}.`);
          try { events.log(`🏗️ Spawned room "${finalName}" from template "${id}".`, 'system-msg'); } catch (e) {}
          close();
        } catch (e) {
          toastError('Spawn failed: ' + (e.message || e));
        }
      };
    });
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  return { open };
})();
