/**
 * TemplateSync — shared "Library Template" footer pattern for node inspectors.
 *
 * Mirrors the item inspector's template-selector + Refresh-from-Library flow
 * (task-295) so ways, areas, and characters are treated the same way:
 *
 *   ┌──────────────────────────────────────────────────────────┐
 *   │ [ (no template) ▾ ] [🔄 Refresh from Library] [📚 Save]   │
 *   └──────────────────────────────────────────────────────────┘
 *
 * The selector lists every entry in the node type's library registry, preselects
 * the node's current `library_id`, and Refresh shows the DiffModal (only checked
 * sections overwrite) before calling /api/library/refresh-to-world.
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
    const sid = `${type}-lib-template-${esc(nodeId)}`;
    return `<select id="${sid}" title="Library template this node syncs against" style="flex:1;min-width:140px;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">
        <option value="">(no template)</option>
        ${libId ? `<option value="${esc(libId)}" selected>${esc(libId)}</option>` : ''}
      </select>
      <button class="btn btn-sm btn-green" onclick="InspectorTemplateSync.refreshFromLibrary('${type}','${esc(nodeId)}')">🔄 Refresh from Library</button>`;
  }

  /**
   * Populate a type's template selector dropdown from its library registry.
   * @param {string} type - 'way' | 'area' | 'character'
   * @param {string} nodeId - graph node id
   */
  async function populateSelector(type, nodeId) {
    const escaped = esc(nodeId);
    const select = document.getElementById(`${type}-lib-template-${escaped}`);
    if (!select) return;
    const current = select.value || (worldState.getNode(nodeId)?.properties?.library_id) || '';
    let libData = {};
    try { libData = await ApiClient.getLibraryType(type === 'way' ? 'ways' : `${type}s`); } catch (e) { /* ignore */ }
    let html = '<option value="">(no template)</option>';
    for (const [id, entry] of Object.entries(libData)) {
      const label = (entry && entry.name) ? `${entry.name} (${id})` : id;
      html += `<option value="${esc(id)}">${esc(label)}</option>`;
    }
    select.innerHTML = html;
    if (current) select.value = current;
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
    if (!result || !result.sections.length) return;

    const data = await ApiClient.refreshFromLibrary(nodeId, result.sections, libId);
    if (data.error) { toastError(data.error); return; }
    await worldState.fetch();
    if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
    events.log(`Refreshed "${node.name}" from library: ${(data.applied || []).join(', ')}`, 'system-msg');
  }

  return { register, renderTemplateRow, populateSelector, refreshFromLibrary };
})();
