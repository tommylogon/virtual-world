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
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const InspectorTemplateSync = (() => {
  const esc = (text?: string | null) => (text || '').replace(/"/g, '&quot;').replace(/'/g, '\\\'');

  /**
   * The library-template endpoints this module calls are not on the
   * `ApiClient` shape in types/globals.d.ts, and that file is a shared hub
   * under concurrent edit, so the wider surface is declared locally.
   */
  function _api(): TemplateSyncApi {
    return ApiClient as unknown as TemplateSyncApi;
  }

  // Per-type world-payload builders and diff sections.
  const CONFIG: Record<string, TemplateSyncConfig> = {};

  /**
   * Register the payload builder + sections for a node type so the helpers below
   * can fetch the world payload and show the right comparison.
   * @param type - 'way' | 'area' | 'character'
   * @param cfg
   */
  function register(type: string, cfg: TemplateSyncConfig) {
    CONFIG[type] = cfg;
  }

  /**
   * Build the footer/footer-row HTML: template selector + refresh button.
   * @param type - node type key
   * @param nodeId - graph node id
   * @param props - node properties (for library_id)
   * @returns HTML for the selector + refresh button
   */
  function renderTemplateRow(type: string, nodeId: string, props?: Record<string, unknown> | null): string {
    const libId = (props && props.library_id) as string || '';
    const brokenFrom = (props && props.template_broken_from) as string || '';
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
   * @param type - node type key ('way' | 'area' | 'character')
   * @param nodeId - graph node id
   */
  async function breakTemplateLink(type: string, nodeId: string) {
    const node = worldState.getNode(nodeId);
    if (!node) { toastInfo('Node not found.'); return; }
    const was = (node.properties && node.properties.library_id) || '';
    if (!was) { toastInfo('This node is not linked to a template.'); return; }
    if (!window.confirm(
      `Stop syncing "${node.name || nodeId}" from library template "${was}"?\n\n` +
      'The node keeps everything it has now. It will simply stop taking updates ' +
      'from the template.'
    )) return;

    const data = await _api().breakTemplateLink(nodeId);
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
  const _libCache: Record<string, { at: number; data: Record<string, TemplateSyncLibraryEntry> }> = {}; // typeKey -> { at, data }
  const _LIB_TTL = 30000;

  /**
   * Populate a type's template selector dropdown from its library registry.
   * @param type - 'way' | 'area' | 'character'
   * @param nodeId - graph node id
   */
  async function populateSelector(type: string, nodeId: string) {
    const escaped = esc(nodeId);
    const input = document.getElementById(`${type}-lib-template-${escaped}`) as HTMLInputElement | null;
    if (!input) return;
    const list = document.getElementById(`${type}-lib-template-${escaped}-opts`);
    const current = input.value || (worldState.getNode(nodeId)?.properties?.library_id) || '';
    const typeKey = type === 'way' ? 'ways' : `${type}s`;
    let libData: Record<string, TemplateSyncLibraryEntry> = {};
    try {
      const cached = _libCache[typeKey];
      if (cached && Date.now() - cached.at < _LIB_TTL) {
        libData = cached.data;
      } else {
        libData = await _api().getLibraryType(typeKey);
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
   * @param type - 'way' | 'area' | 'character'
   * @param nodeId - graph node id
   */
  async function refreshFromLibrary(type: string, nodeId: string) {
    const cfg = CONFIG[type];
    if (!cfg) { toastError(`No refresh config for type "${type}".`); return; }

    const node = worldState.getNode(nodeId);
    if (!node) { toastInfo('Node not found — cannot refresh.'); return; }

    const select = document.getElementById(`${type}-lib-template-${esc(nodeId)}`) as HTMLInputElement | null;
    const libId = (select && select.value) || node.properties?.library_id || '';
    if (!libId) { toastInfo('No library template selected — cannot refresh.'); return; }

    let libEntry: TemplateSyncLibraryEntry = {};
    try {
      const libData = await _api().getLibraryType(type === 'way' ? 'ways' : `${type}s`);
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

    const data = await _api().refreshFromLibrary(nodeId, result.sections || [], libId, result.entries);
    if (data.error) { toastError(data.error); return; }
    await worldState.fetch();
    if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
    events.log(`Refreshed "${node.name}" from library: ${(data.applied || []).join(', ')}`, 'system-msg');
  }

  return { register, renderTemplateRow, populateSelector, refreshFromLibrary, breakTemplateLink };
})();
(window as unknown as { InspectorTemplateSync: typeof InspectorTemplateSync }).InspectorTemplateSync = InspectorTemplateSync;

/**
 * Type declarations live BELOW the first value statement on purpose: TypeScript
 * drops a file's leading JSDoc when the first statement is type-only, and
 * `tools/js_module_index.py` reads `@module` out of the emitted .js.
 */

/** One entry of a library registry (name is the only field this file reads). */
interface TemplateSyncLibraryEntry {
    name?: string;
    [key: string]: unknown;
}

/** What `register()` stores per node type. */
interface TemplateSyncConfig {
    buildWorldPayload(nodeId: string, node: unknown): unknown;
    sections: Array<{ key: string; label: string }>;
    title?: string;
}

/** The ApiClient endpoints this module needs beyond the declared shared shape. */
interface TemplateSyncApi {
    getLibraryType(typeKey: string): Promise<Record<string, TemplateSyncLibraryEntry>>;
    refreshFromLibrary(nodeId: string, sections: unknown, libId: string,
                       entries: unknown): Promise<{ error?: string; applied?: string[] }>;
    breakTemplateLink(nodeId: string): Promise<{ error?: string; was_linked?: boolean }>;
}
