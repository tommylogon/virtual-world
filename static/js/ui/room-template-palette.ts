/**
 * room-template-palette.js — New Room from Template (task-381)
 *
 * Lists library areas (data/library/areas/*) as room templates. Picking one
 * creates a fresh area from the template via POST /api/build/area (env +
 * description + tags), then optionally imports its template items into the
 * room. The new room is NOT connected to anything — use the graph to wire
 * ways to it.
 *
 * @module ui/room-template-palette — New Room from Template
 * @contributes RoomTemplatePalette: list library areas, create a room from one (+ optional template items)
 * @powers starting a room from an authored library area (task-381)
 * @relates POST /api/build/area; the new room is left unconnected for you to wire up
 * @docs docs/virtualWorld/World Building/Rooms & Areas.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(window as unknown as { RoomTemplatePalette: unknown }).RoomTemplatePalette = (() => {
  'use strict';

/**
 * ApiClient's generic HTTP surface; the declared global only lists named
 * wrappers. A function, not a captured const, so ApiClient is still read at
 * call time exactly as the original did from inside `open`.
 */
function api() {
  return ApiClient as unknown as {
    getLibraryType(kind: string): Promise<Record<string, AreaTemplate>>;
    post(path: string, body: unknown): Promise<{ error?: string }>;
  };
}

  async function open() {
    let lib: Record<string, AreaTemplate> = {};
    try {
      lib = await api().getLibraryType('areas');
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

    const head = document.createElement('div');
    head.className = 'modal-head';
    const h3 = document.createElement('h3');
    h3.style.cssText = 'margin:0;font-size:15px;';
    h3.textContent = '🏗️ New Room from Template';
    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close-btn';
    closeBtn.id = 'rp-close';
    closeBtn.textContent = '✕';
    head.append(h3, closeBtn);

    const sub = document.createElement('div');
    sub.style.cssText = 'font-size:10px;color:var(--text-dim);margin-bottom:8px;';
    sub.textContent = `${entries.length} library area templates. Pick one to spawn a fresh room (not wired to anything yet).`;

    const listDiv = document.createElement('div');
    listDiv.style.cssText = 'overflow-y:auto;flex:1;';

    entries.sort((a, b) => String(b[0]).localeCompare(String(a[0])));
    for (const [id, entry] of entries) {
      const name = (entry && entry.name) || id;
      const desc = (entry && entry.description) || '';
      const env = (entry && entry.environment) || {};
      const items = (entry && Array.isArray(entry.items) ? entry.items : []);

      const row = document.createElement('div');
      row.style.cssText = 'padding:6px 4px;border-bottom:1px solid var(--border);';

      const innerRow = document.createElement('div');
      innerRow.style.cssText = 'display:flex;align-items:center;gap:6px;';

      const iconSpan = document.createElement('span');
      iconSpan.textContent = '🏠';

      const detailsCol = document.createElement('div');
      detailsCol.style.cssText = 'flex:1;min-width:0;';

      const nameEl = document.createElement('div');
      nameEl.style.cssText = 'font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
      nameEl.append(name, ' ');
      const idSpan = document.createElement('span');
      idSpan.style.cssText = 'font-size:9px;color:var(--text-muted);';
      idSpan.textContent = `(${id})`;
      nameEl.appendChild(idSpan);

      const descEl = document.createElement('div');
      descEl.style.cssText = 'font-size:10px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
      descEl.title = desc;
      descEl.textContent = desc;

      const metaEl = document.createElement('div');
      metaEl.style.cssText = 'font-size:9px;color:var(--text-dim);';
      metaEl.textContent = `${items.length} items${env.light ? ' · light ' + env.light : ''}${env.temperature ? ' · ' + env.temperature + '°C' : ''}`;

      detailsCol.append(nameEl, descEl, metaEl);

      const spawnBtn = document.createElement('button');
      spawnBtn.className = 'btn btn-sm btn-blue';
      spawnBtn.dataset.id = id;
      spawnBtn.style.cssText = 'font-size:9px;padding:2px 10px;';
      spawnBtn.textContent = '➕ Spawn';

      innerRow.append(iconSpan, detailsCol, spawnBtn);
      row.appendChild(innerRow);
      listDiv.appendChild(row);
    }

    box.append(head, sub, listDiv);
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    const close = () => overlay.remove();
    box.querySelector<HTMLElement>('#rp-close')!.onclick = close;
    overlay.addEventListener('mousedown', (e: MouseEvent) => { if (e.target === overlay) close(); });
    const escHandler = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.preventDefault(); document.removeEventListener('keydown', escHandler); close(); } };
    document.addEventListener('keydown', escHandler);

    box.querySelectorAll<HTMLButtonElement>('button[data-id]').forEach((btn) => {
      btn.onclick = async () => {
        const id = btn.dataset.id || '';
        const entry = lib[id] || {};
        const name = String(entry.name || id).replace(/\s+/g, ' ').trim();
        let finalName = name;
        // de-dupe: append " (2)" etc if an area with that name exists
        let suffix = 2;
        const existingNames = new Set(Object.keys(worldState.areas || {}).map((s: string) => s.toLowerCase()));
        while (existingNames.has(finalName.toLowerCase())) {
          finalName = `${name} (${suffix++})`;
        }
        const env = entry.environment || {};
        try {
          const res = await api().post('/api/build/area', {
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
            const ires = await api().post('/api/build/item', {
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
          toastError('Spawn failed: ' + (e instanceof Error ? e.message : String(e)));
        }
      };
    });
  }

  return { open };
})();


// NOTE: the shape declarations below are deliberately AFTER the first value
// statement. A leading `interface`/`type` makes TypeScript drop the file's
// leading JSDoc block from the emitted .js, and tools/js_module_index.py reads
// the `@module` tag out of that emitted .js.
type AreaTemplate = {
  name?: string;
  description?: string;
  environment?: Record<string, unknown>;
  items?: Array<Record<string, unknown>>;
  tags?: unknown[];
};
