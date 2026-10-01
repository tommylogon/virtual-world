/**
 * TemplateSync — shared "Library Template" footer pattern for node inspectors.
 *
 * Mirrors the item inspector's template-selector + Refresh-from-Library flow
 * (task-295) so ways, areas, and characters are treated the same way:
 *
 *   ┌──────────────────────────────────────────────────────────┐
 *   │ [ (no template) ▾ ] [🔄 Refresh from Library] [🔗 Break] │
 *   └──────────────────────────────────────────────────────────┘
 *
 * The selector lists every entry in the node type's library registry, preselects
 * the node's current `library_id`, and Refresh shows the DiffModal (only checked
 * sections overwrite) before calling /api/library/refresh-to-world.
 *
 * **Break Link** is the other half and only appears when the node actually has a
 * link: it unbinds the node and keeps its data, so a hand-fixed copy stays fixed
 * (task-289/317 — this was missing, which made "mine now" unexpressible).
 *
 * @module shared/template-sync — the "Library Template" footer pattern
 * @contributes InspectorTemplateSync: template selector + Refresh-from-Library (via DiffModal) + Break Link + Save
 * @powers keeping ways/areas/characters in sync with their library templates (task-295, task-289, task-317)
 * @relates used by the node inspectors; calls /api/library/refresh-to-world and /api/library/break-template-link
 * @docs docs/virtualWorld/Library System/Library 2.0 - Unified Library Design.md
 */
window.InspectorTemplateSync = (() => {
  const esc = (text) => (text || '').replace(/"/g, '&quot;').replace(/'/g, '\\\'');

  // Per-type world-payload builders and diff sections.
  const CONFIG = {};

  /**
   * Register the payload builder + sections for a node type so the helpers below
   * can fetch the world payload and show the right comparison.
   * @param {string} type - 'way' | 'area' | 'character'
   * @param {{ buildWorldPayload: function(string):object, sections: Array<{key,label}>, title: string }} cfg
   */
  function register(type, cfg) {
    CONFIG[type] = cfg;
  }

  /**
   * Build the footer/footer-row HTML: template selector + refresh button.
   * @param {string} type - node type key
   * @param {string} nodeId - graph node id
   * @param {object} props - node properties (for library_id)
   * @returns {string} HTML for the selector + refresh button
   */
  function renderTemplateRow(type, nodeId, props) {
    const libId = (props && props.library_id) || '';
    const brokenFrom = (props && props.template_broken_from) || '';
    const sid = `${type}-lib-template-${esc(nodeId)}`;
    const sidList = sid + '-opts';
    // Break Link appears only when there IS a link. Offering it on an unlinked
    // node would be a button that can only ever report "nothing to break".
    // The "was linked to" line is provenance from a previous break, so an author
    // can still see where this copy came from after it stopped syncing.
    const breakBtn = libId
      ? `<button class="btn btn-sm" style="background:#5a1a1a;border-color:#8a2a2a;color:#ff9b9b;" onclick="InspectorTemplateSync.breakTemplateLink('${type}','${esc(nodeId)}')" title="Stop syncing this node from its template. Its current data is kept exactly as it is.">🔗 Break Link</button>`
      : '';
    const wasLinked = !libId && brokenFrom
      ? `<div style="flex-basis:100%;font-size:9px;color:var(--text-muted);">was linked to <code>${esc(brokenFrom)}</code> — this copy no longer syncs</div>`
      : '';
    return `<input id="${sid}" list="${sidList}" placeholder="Search or pick a library template..." value="${esc(libId)}" title="Library template this node syncs against — type to search" style="flex:1;min-width:140px;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;" />
      <datalist id="${sidList}"></datalist>
      <button class="btn btn-sm btn-green" onclick="InspectorTemplateSync.refreshFromLibrary('${type}','${esc(nodeId)}')">🔄 Refresh from Library</button>
      ${breakBtn}${wasLinked}`;
  }

  /**
   * Break the template link: the node stops syncing, and keeps every value it
   * has. This is the operation task-289/317 were missing entirely — without it,
   * an author who fixed a placed copy by hand had no way to say so, and the
   * next Refresh would quietly undo the fix.
   * @param {string} type - node type key ('way' | 'area' | 'character')
   * @param {string} nodeId - graph node id
   */
  async function breakTemplateLink(type, nodeId) {
    const node = worldState.getNode(nodeId);
    if (!node) { toastInfo('Node not found.'); return; }
    const was = (node.properties && node.properties.library_id) || '';
    if (!was) { toastInfo('This node is not linked to a template.'); return; }
    if (!window.confirm(
      `Stop syncing "${node.name || nodeId}" from library template "${was}"?\n\n` +
      'The node keeps everything it has now. It will simply stop taking updates ' +
      'from the template.'
    )) return;

    const data = await ApiClient.breakTemplateLink(nodeId);
    if (data && data.error) { toastError(data.error); return; }
    await worldState.fetch();
    if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
    if (data && data.was_linked) {
      events.log(`Unlinked "${node.name || nodeId}" from library template "${was}". Data kept.`, 'system-msg');
    }
  }

  // Per-type library registry cache with a short TTL: populateSelector runs
  // on every inspector re-render; without a cache each re-render refetched the
  // whole registry (characters, ways, areas).
  const _libCache = {}; // typeKey -> { at, data }
  const _LIB_TTL = 30000;

  /**
   * Populate a type's template selector dropdown from its library registry.
   * @param {string} type - 'way' | 'area' | 'character'
   * @param {string} nodeId - graph node id
   */
  async function populateSelector(type, nodeId) {
    const escaped = esc(nodeId);
    const input = document.getElementById(`${type}-lib-template-${escaped}`);
    if (!input) return;
    const list = document.getElementById(`${type}-lib-template-${escaped}-opts`);
    const current = input.value || (worldState.getNode(nodeId)?.properties?.library_id) || '';
    const typeKey = type === 'way' ? 'ways' : `${type}s`;
    let libData = {};
    try {
      const cached = _libCache[typeKey];
      if (cached && Date.now() - cached.at < _LIB_TTL) {
        libData = cached.data;
      } else {
        libData = await ApiClient.getLibraryType(typeKey);
        _libCache[typeKey] = { at: Date.now(), data: libData };
      }
    } catch (e) { /* ignore */ }
    if (list) {
      let html = '';
      for (const [id, entry] of Object.entries(libData)) {
        const label = (entry && entry.name) ? `${entry.name} (${id})` : id;
        html += `<option value="${esc(id)}">${esc(label)}</option>`;
      }
      list.innerHTML = html;
    }
    if (current && !input.value) input.value = current;
  }

  /**
   * Open the DiffModal comparing the selected library entry vs the world copy,
   * then send the checked sections to refresh-to-world. Mirrors item-view.
   * @param {string} type - 'way' | 'area' | 'character'
   * @param {string} nodeId - graph node id
   */
  async function refreshFromLibrary(type, nodeId) {
    const cfg = CONFIG[type];
    if (!cfg) { toastError(`No refresh config for type "${type}".`); return; }

    const node = worldState.getNode(nodeId);
    if (!node) { toastInfo('Node not found — cannot refresh.'); return; }

    const select = document.getElementById(`${type}-lib-template-${esc(nodeId)}`);
    const libId = (select && select.value) || node.properties?.library_id || '';
    if (!libId) { toastInfo('No library template selected — cannot refresh.'); return; }

    let libEntry = {};
    try {
      const libData = await ApiClient.getLibraryType(type === 'way' ? 'ways' : `${type}s`);
      libEntry = libData[libId] || {};
    } catch (e) { /* ignore */ }
    if (!Object.keys(libEntry).length) {
      toastInfo('No library entry found. Save to library first.');
      return;
    }

    const worldPayload = cfg.buildWorldPayload(nodeId, node);
    if (!worldPayload) { toastError('Could not build world payload.'); return; }

    const result = await DiffModal.show(libEntry, worldPayload, cfg.sections, {
      title: cfg.title || `Refresh ${type} from Library`,
      name: node.name || nodeId,
      // Refresh = applying library (current) onto the world copy (incoming) —
      // so `to-world` direction protects world data from empty library values.
      direction: 'to-world'
    });
    const hasWhole = (result.sections && result.sections.length) > 0;
    const hasEntries = result.entries && Object.keys(result.entries).length > 0;
    if (!hasWhole && !hasEntries) return;

    const data = await ApiClient.refreshFromLibrary(nodeId, result.sections || [], libId, result.entries);
    if (data.error) { toastError(data.error); return; }
    await worldState.fetch();
    if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
    events.log(`Refreshed "${node.name}" from library: ${(data.applied || []).join(', ')}`, 'system-msg');
  }

  return { register, renderTemplateRow, populateSelector, refreshFromLibrary, breakTemplateLink };
})();
