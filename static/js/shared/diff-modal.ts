/**
 * DiffModal - V3 Hybrid Merge Workbench for world <-> library sync.
 *
 * @module shared/diff-modal - world <-> library conflict resolution
 * @contributes DiffModal.show(current, incoming, sections, options) -> update / duplicate / cancel, with per-entry & per-axis smart merge
 * @powers choosing exactly which library sections, entries, or object axes overwrite a world node while protecting world-only seed items
 * @relates used by template-sync, library-browser, inspector/helpers, and item-library refresh flows
 * @docs docs/virtualWorld/Library System/diff-modal.md
 *
 * V3 Hybrid Merge Workbench:
 *   - Fluid widescreen layout (clamp/vh, sticky header/KPI bar/dry-run footer)
 *   - Hides identical (=) sections, entries, and axes by default with a KPI toggle
 *   - Inline word-level diff (-old / +new) for prose fields and memory text
 *   - Full untruncated memory text with metadata pills and #tag facet chips
 *   - World-only / target-only items (especially seed memories) protected as
 *     Keep Safe by default unless explicitly unlocked and marked for removal
 *   - Per-axis Smart Merge for structured objects (relationships, stats, skills)
 *   - Clear direction banner (Library -> World vs World -> Library), dry-run
 *     summary preview, and UndoHistory refresh hook on Apply
 *
 * Usage (backward compatible):
 *   const result = await DiffModal.show(currentLibEntry, worldPayload, sections, options);
 *   // result = null (cancel)
 *   //        | { action: 'update',    sections: [...], entries: {...} }
 *   //        | { action: 'duplicate', name, id, sections: [...], entries: {...} }
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(window as unknown as DiffModalWindowSurface).DiffModal = (() => {
  const esc = (text: unknown): string => String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  const PROSE_KEYS = new Set([
    'personality', 'description', 'base_description', 'appearance',
    'backstory', 'notes', 'summary', 'behavior_notes',
  ]);
  const STRUCTURED_OBJECT_KEYS = new Set([
    'stats', 'skills', 'relationships', 'vitals', 'decay_rates', 'conditions', 'equipped',
  ]);

  function isPlainObject(value: unknown): value is Record<string, unknown> {
    return !!value && typeof value === 'object' && !Array.isArray(value);
  }

  function isEmptyValue(value: unknown): boolean {
    if (value === null || value === undefined) return true;
    if (typeof value === 'string') return value.trim() === '';
    if (Array.isArray(value)) return value.length === 0;
    if (typeof value === 'object') return Object.keys(value).length === 0;
    return false;
  }

  function canonicalize(value: unknown): unknown {
    if (value === null || value === undefined) return value;
    if (Array.isArray(value)) return (value as unknown[]).map(canonicalize);
    if (typeof value === 'object') {
      const out: Record<string, unknown> = {};
      for (const k of Object.keys(value as object).sort()) {
        out[k] = canonicalize((value as Record<string, unknown>)[k]);
      }
      return out;
    }
    return value;
  }

  function compareValues(a: unknown, b: unknown): boolean {
    const ca = canonicalize(a);
    const cb = canonicalize(b);
    const sa = ca === undefined || ca === null ? '' : JSON.stringify(ca);
    const sb = cb === undefined || cb === null ? '' : JSON.stringify(cb);
    return sa !== sb;
  }

  function formatValue(val: unknown): string {
    if (val === undefined) return '(missing)';
    if (val === null) return '(null)';
    if (typeof val === 'string') return val === '' ? '(empty)' : val;
    if (typeof val === 'object') return JSON.stringify(val, null, 2);
    return String(val);
  }

  function formatCompact(val: unknown): string {
    if (val === undefined) return '(missing)';
    if (val === null) return '(null)';
    if (typeof val === 'string') return val === '' ? '(empty)' : val;
    if (typeof val === 'object') return JSON.stringify(val);
    return String(val);
  }

  function isSeedMemory(item: unknown): boolean {
    if (!isPlainObject(item)) return false;
    if (String(item.source || '').toLowerCase() === 'seed') return true;
    if (item.seed === true) return true;
    if (Array.isArray(item.tags) && item.tags.some((t) => String(t).toLowerCase() === 'seed')) return true;
    return false;
  }

  function isMemoryObject(item: unknown): item is Record<string, unknown> {
    return isPlainObject(item) && typeof item.text === 'string';
  }

  function isProseValue(key: string, a: unknown, b: unknown): boolean {
    if ((a !== undefined && a !== null && typeof a !== 'string') ||
        (b !== undefined && b !== null && typeof b !== 'string')) {
      return false;
    }
    const sa = typeof a === 'string' ? a : '';
    const sb = typeof b === 'string' ? b : '';
    if (!sa && !sb) return false;
    if (PROSE_KEYS.has(key)) return true;
    return sa.length > 24 || sb.length > 24 || /\s/.test(sa) || /\s/.test(sb);
  }

  // ── Word-level diff (LCS) ─────────────────────────────────────────

  function wordDiff(oldText: string, newText: string): WordDiffChunk[] {
    const a = (oldText || '').split(/(\s+)/).filter((t) => t.length > 0);
    const b = (newText || '').split(/(\s+)/).filter((t) => t.length > 0);
    if (a.length === 0 && b.length === 0) return [];
    if (a.length === 0) return [{ type: 'add', text: newText }];
    if (b.length === 0) return [{ type: 'del', text: oldText }];

    // Guard against quadratic blowup on huge texts: fall back to prefix/suffix diff.
    if (a.length * b.length > 180000) {
      let p = 0;
      while (p < a.length && p < b.length && a[p] === b[p]) p++;
      let s = 0;
      while (s < a.length - p && s < b.length - p && a[a.length - 1 - s] === b[b.length - 1 - s]) s++;
      const chunks: WordDiffChunk[] = [];
      if (p > 0) chunks.push({ type: 'same', text: a.slice(0, p).join('') });
      const midA = a.slice(p, a.length - s).join('');
      const midB = b.slice(p, b.length - s).join('');
      if (midA) chunks.push({ type: 'del', text: midA });
      if (midB) chunks.push({ type: 'add', text: midB });
      if (s > 0) chunks.push({ type: 'same', text: a.slice(a.length - s).join('') });
      return chunks;
    }

    const n = a.length;
    const m = b.length;
    const dp = new Int32Array((n + 1) * (m + 1));
    const stride = m + 1;
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        if (a[i] === b[j]) {
          dp[i * stride + j] = 1 + dp[(i + 1) * stride + (j + 1)];
        } else {
          const down = dp[(i + 1) * stride + j];
          const right = dp[i * stride + (j + 1)];
          dp[i * stride + j] = down >= right ? down : right;
        }
      }
    }

    const raw: WordDiffChunk[] = [];
    let i = 0;
    let j = 0;
    while (i < n && j < m) {
      if (a[i] === b[j]) {
        raw.push({ type: 'same', text: a[i] });
        i++;
        j++;
      } else if (dp[(i + 1) * stride + j] >= dp[i * stride + (j + 1)]) {
        raw.push({ type: 'del', text: a[i] });
        i++;
      } else {
        raw.push({ type: 'add', text: b[j] });
        j++;
      }
    }
    while (i < n) raw.push({ type: 'del', text: a[i++] });
    while (j < m) raw.push({ type: 'add', text: b[j++] });

    const merged: WordDiffChunk[] = [];
    for (const c of raw) {
      const prev = merged[merged.length - 1];
      if (prev && prev.type === c.type) {
        prev.text += c.text;
      } else {
        merged.push({ type: c.type, text: c.text });
      }
    }
    return merged;
  }

  function renderWordDiffHtml(oldText: string, newText: string): string {
    const chunks = wordDiff(oldText, newText);
    if (!chunks.length) return '<span class="dm-muted">(empty)</span>';
    return chunks.map((c) => {
      if (c.type === 'del') return '<del class="dm-word-del">' + esc(c.text) + '</del>';
      if (c.type === 'add') return '<ins class="dm-word-add">' + esc(c.text) + '</ins>';
      return '<span>' + esc(c.text) + '</span>';
    }).join('');
  }

  // ── Per-entry helpers ──────────────────────────────────────────────

  function idKeyOf(item: unknown): string | null {
    if (item && typeof item === 'object') {
      const o = item as Record<string, unknown>;
      if (o.id != null && o.id !== '') return String(o.id);
      if (o.name != null && o.name !== '') return 'name:' + String(o.name);
    }
    return null;
  }

  function contentKeyOf(item: unknown): string | null {
    if (item && typeof item === 'object' && typeof (item as Record<string, unknown>).text === 'string'
        && String((item as Record<string, unknown>).text).trim()) {
      const text = String((item as Record<string, unknown>).text);
      return 'text:' + text.toLowerCase().replace(/\s+/g, ' ').trim();
    }
    return null;
  }

  function selKeyOf(item: unknown): string | null {
    const id = idKeyOf(item);
    if (id !== null) return id;
    return contentKeyOf(item);
  }

  function toEntryList(value: unknown): EntryListItem[] {
    if (Array.isArray(value)) return (value as unknown[]).map((item, i) => ({ key: selKeyOf(item) ?? i, data: item }));
    if (value && typeof value === 'object') {
      const o = value as Record<string, unknown>;
      return Object.keys(o).map((k) => ({ key: k, data: o[k] }));
    }
    return [];
  }

  function perEntryEligible(value: unknown): boolean {
    if (Array.isArray(value)) {
      if (value.length === 0) return false;
      return value.every((v) => selKeyOf(v) !== null);
    }
    if (value && typeof value === 'object') return Object.keys(value as object).length > 0;
    return false;
  }

  function entryLabel(key: unknown, data: unknown): string {
    if (data && typeof data === 'object') {
      const o = data as Record<string, unknown>;
      if (typeof o.text === 'string') return o.text;
      if (typeof o.name === 'string') return String(o.name);
      if (typeof o.id === 'string') return String(o.id);
    }
    return String(key ?? '');
  }

  function contentEquals(a: unknown, b: unknown): boolean {
    const strip = (v: unknown): unknown => {
      if (Array.isArray(v)) return (v as unknown[]).map(strip);
      if (v && typeof v === 'object') {
        const src = v as Record<string, unknown>;
        const o: Record<string, unknown> = {};
        for (const k of Object.keys(src).sort()) {
          if (k === 'id' || k === 'embedding') continue;
          o[k] = strip(src[k]);
        }
        return o;
      }
      return v;
    };
    const sa = JSON.stringify(strip(a) ?? '');
    const sb = JSON.stringify(strip(b) ?? '');
    return sa === sb;
  }

  // Two-pass per-entry diff: pair by id (or object key), then pair leftovers by content.
  // Preserves `current` and `incoming` parameter positions for backward compatibility.
  function entryDiff(current: unknown, incoming: unknown): DiffModalDiffRow[] {
    const isObjSection = (!Array.isArray(current) && current && typeof current === 'object')
      || (!Array.isArray(incoming) && incoming && typeof incoming === 'object');
    const cList = toEntryList(current);
    const iList = toEntryList(incoming);
    const usedC = new Array(cList.length).fill(false);
    const usedI = new Array(iList.length).fill(false);
    const rows: DiffModalDiffRow[] = [];

    const rowKeyOf = (entry: EntryListItem): string | null => {
      if (isObjSection && typeof entry.key === 'string') return entry.key;
      return selKeyOf(entry.data) ?? (entry.key != null ? String(entry.key) : null);
    };

    const pairBy = (keyFn: (entry: EntryListItem) => string | null) => {
      cList.forEach((cEntry, ci) => {
        if (usedC[ci]) return;
        const ck = keyFn(cEntry);
        if (ck === null) return;
        const ii = iList.findIndex((iEntry, i) => !usedI[i] && keyFn(iEntry) === ck);
        if (ii < 0) return;
        usedC[ci] = true;
        usedI[ii] = true;
        const inc = iList[ii].data;
        rows.push({
          key: rowKeyOf(iList[ii]),
          current: cEntry.data,
          incoming: inc,
          status: contentEquals(cEntry.data, inc) ? 'same' : 'changed',
        });
      });
    };

    if (isObjSection) {
      pairBy((entry) => (typeof entry.key === 'string' ? entry.key : null));
    } else {
      pairBy((entry) => idKeyOf(entry.data));
      pairBy((entry) => contentKeyOf(entry.data));
    }

    cList.forEach((cEntry, ci) => {
      if (!usedC[ci]) rows.push({ key: rowKeyOf(cEntry), current: cEntry.data, incoming: undefined, status: 'removed' });
    });
    iList.forEach((iEntry, i) => {
      if (!usedI[i]) rows.push({ key: rowKeyOf(iEntry), current: undefined, incoming: iEntry.data, status: 'added' });
    });
    return rows;
  }

  // ── Scoped V3 Styles ──────────────────────────────────────────────

  function ensureStyles(): void {
    if (typeof document === 'undefined' || !document.head) return;
    if (document.getElementById('diff-modal-v3-styles')) return;
    const style = document.createElement('style');
    style.id = 'diff-modal-v3-styles';
    style.textContent = `
      .modal-window.diff-modal-v3 {
        width: clamp(680px, 92vw, 1380px);
        max-width: 96vw;
        max-height: 92vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        padding: 0;
        box-sizing: border-box;
      }
      .dm-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 14px 20px;
        border-bottom: 1px solid var(--border);
        background: var(--bg-card);
        flex-shrink: 0;
      }
      .dm-head-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; min-width: 0; }
      .dm-dir-badge {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 600;
        border: 1px solid var(--border);
      }
      .dm-dir-to-world { background: rgba(88, 166, 255, 0.14); color: #79c0ff; border-color: rgba(88, 166, 255, 0.4); }
      .dm-dir-to-lib { background: rgba(63, 185, 80, 0.14); color: #7ee787; border-color: rgba(63, 185, 80, 0.4); }
      .dm-ro-badge {
        padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 600;
        background: rgba(255,255,255,0.08); color: var(--text-muted);
      }
      .dm-toolbar {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 10px 20px;
        border-bottom: 1px solid var(--border);
        background: rgba(0, 0, 0, 0.16);
        flex-shrink: 0;
      }
      .dm-kpi-strip { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
      .dm-kpi-pill {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600;
        background: var(--bg-inset, rgba(255,255,255,0.04));
        border: 1px solid var(--border); color: var(--text-muted);
        cursor: pointer; user-select: none;
      }
      .dm-kpi-pill:hover { border-color: var(--accent, #58a6ff); color: var(--text); }
      .dm-kpi-pill.active {
        background: rgba(88, 166, 255, 0.18); border-color: var(--accent, #58a6ff); color: var(--text);
      }
      .dm-kpi-pill.dm-kpi-safe.active { background: rgba(227, 179, 65, 0.16); border-color: #e3b341; color: #f2cc60; }
      .dm-kpi-pill.dm-kpi-new.active { background: rgba(63, 185, 80, 0.16); border-color: #3fb950; color: #7ee787; }
      .dm-kpi-pill.dm-kpi-chg.active { background: rgba(210, 153, 34, 0.16); border-color: #d29922; color: #e3b341; }
      .dm-facet-bar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
      .dm-facet-chip {
        padding: 3px 9px; border-radius: 6px; font-size: 11px; font-weight: 500;
        background: rgba(255,255,255,0.04); border: 1px solid var(--border); color: var(--text);
        cursor: pointer;
      }
      .dm-facet-chip:hover { border-color: var(--accent, #58a6ff); }
      .dm-facet-chip.active { background: rgba(88, 166, 255, 0.2); border-color: var(--accent, #58a6ff); }
      .dm-search {
        margin-left: auto; min-width: 180px; max-width: 280px; flex: 1;
        padding: 4px 10px; font-size: 11.5px; border-radius: 6px;
        background: var(--bg-input, rgba(0,0,0,0.25)); border: 1px solid var(--border); color: var(--text);
      }
      .dm-body {
        flex: 1; overflow-y: auto; padding: 14px 20px; display: flex; flex-direction: column; gap: 10px;
      }
      .dm-body.dm-hide-same .dm-row-same,
      .dm-body.dm-hide-same .dm-section-same,
      .dm-body.dm-hide-same .dm-axis-same {
        display: none !important;
      }
      .dm-hidden-filter { display: none !important; }
      .dm-section-card {
        border: 1px solid var(--border); border-radius: 8px; background: rgba(255,255,255,0.02);
        overflow: hidden;
      }
      .dm-section-card.dm-has-diff { border-color: rgba(88, 166, 255, 0.28); }
      .dm-sec-head {
        display: flex; align-items: center; gap: 8px; padding: 9px 12px;
        background: rgba(255,255,255,0.03); border-bottom: 1px solid var(--border);
      }
      .dm-sec-head.pe-head { cursor: pointer; }
      .dm-sec-body { padding: 10px 12px; }
      .dm-word-diff {
        font-size: 12.5px; line-height: 1.55; white-space: pre-wrap; word-break: break-word;
        padding: 8px 10px; border-radius: 6px; background: rgba(0,0,0,0.22); border: 1px solid var(--border);
      }
      .dm-word-del {
        background: rgba(248, 81, 73, 0.22); color: #ffa198; text-decoration: line-through;
        padding: 0 2px; border-radius: 3px;
      }
      .dm-word-add {
        background: rgba(63, 185, 80, 0.22); color: #7ee787; text-decoration: none;
        padding: 0 2px; border-radius: 3px;
      }
      .dm-pe-row {
        display: grid; grid-template-columns: auto 22px 1fr; gap: 10px; align-items: start;
        padding: 8px 6px; border-bottom: 1px solid var(--border);
      }
      .dm-pe-row:last-child { border-bottom: none; }
      .dm-pe-row.dm-row-safe { background: rgba(227, 179, 65, 0.05); }
      .dm-mem-text {
        font-size: 12.5px; line-height: 1.5; white-space: pre-wrap; word-break: break-word;
        color: var(--text); margin-bottom: 4px;
      }
      .dm-meta-pills { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; font-size: 10.5px; color: var(--text-muted); }
      .dm-pill {
        padding: 1px 6px; border-radius: 999px; border: 1px solid var(--border);
        background: rgba(255,255,255,0.04); font-size: 10px;
      }
      .dm-pill-seed { background: rgba(63, 185, 80, 0.14); border-color: rgba(63, 185, 80, 0.4); color: #7ee787; }
      .dm-pill-safe { background: rgba(227, 179, 65, 0.16); border-color: rgba(227, 179, 65, 0.45); color: #f2cc60; }
      .dm-pill-remove { background: rgba(248, 81, 73, 0.18); border-color: rgba(248, 81, 73, 0.5); color: #ffa198; }
      .dm-safe-toggle {
        padding: 2px 8px; border-radius: 6px; font-size: 10.5px; font-weight: 600; cursor: pointer;
        border: 1px solid rgba(227, 179, 65, 0.45); background: rgba(227, 179, 65, 0.14); color: #f2cc60;
      }
      .dm-safe-toggle.dm-unlocked {
        border-color: rgba(248, 81, 73, 0.55); background: rgba(248, 81, 73, 0.2); color: #ffa198;
      }
      .dm-axis-table {
        width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 11.5px;
        background: rgba(0,0,0,0.16); border-radius: 6px; overflow: hidden;
      }
      .dm-axis-table th, .dm-axis-table td {
        padding: 5px 8px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: middle;
      }
      .dm-axis-table th { font-size: 10px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }
      .dm-axis-choice {
        display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden;
      }
      .dm-axis-btn {
        padding: 2px 8px; font-size: 10.5px; border: none; background: transparent; color: var(--text-muted); cursor: pointer;
      }
      .dm-axis-btn.active-target { background: rgba(227, 179, 65, 0.2); color: #f2cc60; font-weight: 600; }
      .dm-axis-btn.active-source { background: rgba(63, 185, 80, 0.22); color: #7ee787; font-weight: 600; }
      .dm-foot {
        display: flex; flex-direction: column; gap: 8px;
        padding: 12px 20px; border-top: 1px solid var(--border); background: var(--bg-card); flex-shrink: 0;
      }
      .dm-dry-run {
        font-size: 11.5px; color: var(--text-muted); padding: 6px 10px; border-radius: 6px;
        background: rgba(88, 166, 255, 0.08); border: 1px solid rgba(88, 166, 255, 0.22);
      }
      .dm-foot-actions { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
      .dm-muted { color: var(--text-muted); }
    `;
    document.head.appendChild(style);
  }

  // ── V3 Model Builder (direction-normalized to source vs target) ────

  // Given DiffModal.show(current, incoming, sections, options):
  // - In 'to-world': current = Library (source), incoming = World (target)
  // - In 'to-lib' (default): current = Library (target), incoming = World (source)
  function normalizeEntryRow(r: DiffModalDiffRow, toWorld: boolean): NormalizedEntryRow {
    const targetVal = toWorld ? r.incoming : r.current;
    const sourceVal = toWorld ? r.current : r.incoming;
    let bucket: NormalizedBucket;
    if (r.status === 'same') {
      bucket = 'same';
    } else if (r.status === 'changed') {
      bucket = 'changed';
    } else if (toWorld) {
      // r.status === 'removed' => in current (Library), missing in incoming (World) => 'new'
      // r.status === 'added' => in incoming (World), missing in current (Library) => 'target-only'
      bucket = r.status === 'removed' ? 'new' : 'target-only';
    } else {
      // r.status === 'added' => in incoming (World), missing in current (Library) => 'new'
      // r.status === 'removed' => in current (Library), missing in incoming (World) => 'target-only'
      bucket = r.status === 'added' ? 'new' : 'target-only';
    }
    const sample = sourceVal !== undefined ? sourceVal : targetVal;
    const seed = isSeedMemory(sample) || isSeedMemory(targetVal);
    const isStructuredObj = !isMemoryObject(sample) && (isPlainObject(targetVal) || isPlainObject(sourceVal));
    const tags: string[] = [];
    const tagSrc = isPlainObject(sample) && Array.isArray(sample.tags) ? sample.tags : [];
    for (const t of tagSrc) tags.push(String(t));
    if (isPlainObject(targetVal) && Array.isArray(targetVal.tags)) {
      for (const t of targetVal.tags) {
        const s = String(t);
        if (!tags.includes(s)) tags.push(s);
      }
    }
    return {
      key: String(r.key ?? ''),
      rawStatus: r.status,
      bucket,
      targetVal,
      sourceVal,
      seed,
      isStructuredObj,
      tags,
    };
  }

  function buildAxisRows(targetObj: Record<string, unknown> | undefined,
                         sourceObj: Record<string, unknown> | undefined): AxisDiffRow[] {
    const t = targetObj || {};
    const s = sourceObj || {};
    const keys = Array.from(new Set([...Object.keys(t), ...Object.keys(s)]));
    return keys.map((ak) => {
      const hasT = Object.prototype.hasOwnProperty.call(t, ak) && t[ak] !== undefined;
      const hasS = Object.prototype.hasOwnProperty.call(s, ak) && s[ak] !== undefined;
      const tv = hasT ? t[ak] : undefined;
      const sv = hasS ? s[ak] : undefined;
      let bucket: NormalizedBucket;
      if (hasT && hasS) {
        bucket = compareValues(tv, sv) ? 'changed' : 'same';
      } else if (hasS && !hasT) {
        bucket = 'new';
      } else {
        bucket = 'target-only';
      }
      // Smart Merge default:
      // - 'new' (missing in target, present in source): adopt from source ('source')
      // - 'changed' (live runtime value in target vs source): keep target ('target')
      // - 'target-only': keep target ('target')
      // - 'same': 'target'
      const defaultPick: 'target' | 'source' = bucket === 'new' ? 'source' : 'target';
      return { axis: ak, bucket, targetVal: tv, sourceVal: sv, defaultPick };
    });
  }

  // ── Rendering Helpers ─────────────────────────────────────────────

  function renderMemoryMetadata(item: unknown, isTargetOnly: boolean, seed: boolean): string {
    if (!isPlainObject(item)) return '';
    const pills: string[] = [];
    if (seed) pills.push('<span class="dm-pill dm-pill-seed">🌱 Seed</span>');
    if (isTargetOnly) pills.push('<span class="dm-pill dm-pill-safe">🛡️ World-Only</span>');
    if (item.importance !== undefined && item.importance !== null) {
      pills.push('<span class="dm-pill">⭐ ' + esc(item.importance) + '</span>');
    }
    if (Array.isArray(item.tags)) {
      for (const t of item.tags) pills.push('<span class="dm-pill">#' + esc(t) + '</span>');
    }
    const emos = (Array.isArray(item.memory_emotions) && item.memory_emotions.length)
      ? item.memory_emotions as Record<string, unknown>[]
      : (isPlainObject(item.emotion) && item.emotion.label ? [item.emotion] : []);
    if (emos.length) {
      const emoStr = emos.map((e) => String(e.label || '') + (e.intensity ? ':' + e.intensity : '')).join(', ');
      pills.push('<span class="dm-pill">' + esc(emoStr) + '</span>');
    }
    if (item.location) pills.push('<span class="dm-pill">📍 ' + esc(item.location) + '</span>');
    if (item.source) pills.push('<span class="dm-pill">' + esc(item.source) + '</span>');
    return pills.length ? '<div class="dm-meta-pills">' + pills.join('') + '</div>' : '';
  }

  function renderAxisTable(sectionKey: string, entryKey: string, axes: AxisDiffRow[],
                           ro: boolean | undefined, targetLabel: string, sourceLabel: string): string {
    let rowsHtml = '';
    for (const ax of axes) {
      const sameCls = ax.bucket === 'same' ? 'dm-axis-same' : '';
      const badge = ax.bucket === 'same' ? '=' : (ax.bucket === 'new' ? '+' : (ax.bucket === 'target-only' ? '🛡️' : '~'));
      const tActive = ax.defaultPick === 'target' ? 'active-target' : '';
      const sActive = ax.defaultPick === 'source' ? 'active-source' : '';
      const disabledAttr = (ro || ax.bucket === 'same' || ax.bucket === 'target-only') ? 'disabled' : '';
      rowsHtml += '<tr class="dm-axis-row ' + sameCls + '" data-section="' + esc(sectionKey) + '" data-entry="' + esc(entryKey) + '" data-axis="' + esc(ax.axis) + '" data-bucket="' + ax.bucket + '" data-pick="' + ax.defaultPick + '">'
        + '<td><code>' + esc(ax.axis) + '</code> <span class="dm-muted">' + badge + '</span></td>'
        + '<td><code>' + esc(formatCompact(ax.targetVal)) + '</code></td>'
        + '<td><code>' + esc(formatCompact(ax.sourceVal)) + '</code></td>'
        + '<td>'
        + '<div class="dm-axis-choice">'
        + '<button type="button" class="dm-axis-btn ' + tActive + '" data-choice="target" ' + disabledAttr + '>Keep ' + esc(targetLabel) + '</button>'
        + '<button type="button" class="dm-axis-btn ' + sActive + '" data-choice="source" ' + disabledAttr + '>Use ' + esc(sourceLabel) + '</button>'
        + '</div>'
        + '</td>'
        + '</tr>';
    }
    return '<table class="dm-axis-table">'
      + '<thead><tr><th>Axis</th><th>' + esc(targetLabel) + '</th><th>' + esc(sourceLabel) + '</th><th>Merge</th></tr></thead>'
      + '<tbody>' + rowsHtml + '</tbody>'
      + '</table>';
  }

  function renderPerEntryGroup(sec: DiffSectionState, current: unknown, incoming: unknown,
                               ro: boolean | undefined, toWorld: boolean): {
    html: string;
    counts: Record<NormalizedBucket, number>;
    seedCount: number;
    tags: string[];
  } {
    const rawRows = entryDiff(current, incoming);
    const normRows = rawRows.map((r) => normalizeEntryRow(r, toWorld));
    const counts: Record<NormalizedBucket, number> = { changed: 0, new: 0, 'target-only': 0, same: 0 };
    let seedCount = 0;
    const tagSet = new Set<string>();
    normRows.forEach((nr) => {
      counts[nr.bucket]++;
      if (nr.seed && nr.bucket === 'target-only') seedCount++;
      nr.tags.forEach((t) => tagSet.add(t));
    });

    const targetLabel = toWorld ? 'World' : 'Library';
    const sourceLabel = toWorld ? 'Library' : 'World';
    const hasChanges = (counts.changed + counts.new + counts['target-only']) > 0;
    const sameSecCls = hasChanges ? 'dm-has-diff' : 'dm-section-same';

    let rowHtml = '';
    for (const nr of normRows) {
      const isSame = nr.bucket === 'same';
      const isTargetOnly = nr.bucket === 'target-only';
      const rowCls = [
        'dm-pe-row',
        isSame ? 'dm-row-same' : '',
        isTargetOnly ? 'dm-row-safe' : '',
      ].filter(Boolean).join(' ');

      const sample = nr.sourceVal !== undefined ? nr.sourceVal : nr.targetVal;
      const isMem = isMemoryObject(sample) || isMemoryObject(nr.targetVal);
      const searchText = [
        nr.key,
        isMem && isPlainObject(sample) ? String(sample.text || '') : '',
        isMem && isPlainObject(nr.targetVal) ? String(nr.targetVal.text || '') : '',
        nr.tags.join(' '),
      ].join(' ').toLowerCase();

      // Left control:
      // - For 'changed' / 'new': checkbox `.pe-entry` (checked by default)
      // - For 'target-only': safety lock button `.dm-safe-toggle` (Keep Safe by default)
      // - For 'same': disabled checkbox
      let ctrlHtml = '';
      if (isTargetOnly) {
        ctrlHtml = '<button type="button" class="dm-safe-toggle" data-key="' + esc(sec.key) + '" data-entry="' + esc(nr.key) + '" data-seed="' + (nr.seed ? '1' : '0') + '" data-state="safe" '
          + (ro ? 'disabled' : '') + ' title="World-only item is protected by default. Click to unlock and mark for removal.">'
          + '🛡️ Keep Safe</button>';
      } else {
        const checked = !ro && !isSame ? 'checked' : '';
        ctrlHtml = '<input type="checkbox" class="pe-entry" data-key="' + esc(sec.key) + '" data-entry="' + esc(nr.key) + '" ' + checked + ' '
          + (ro || isSame ? 'disabled' : '') + ' style="margin:3px 0 0 0;">';
      }

      const badgeMap: Record<NormalizedBucket, string> = {
        same: '<span style="color:var(--text-muted);font-weight:700;" title="Identical">=</span>',
        new: '<span style="color:#7ee787;font-weight:700;" title="New from ' + sourceLabel + '">+</span>',
        'target-only': '<span style="color:#f2cc60;font-weight:700;" title="Only in ' + targetLabel + ' (Keep Safe)">🛡️</span>',
        changed: '<span style="color:#e3b341;font-weight:700;" title="Changed">~</span>',
      };

      let bodyHtml = '';
      if (isMem) {
        const tText = isPlainObject(nr.targetVal) ? String(nr.targetVal.text || '') : '';
        const sText = isPlainObject(nr.sourceVal) ? String(nr.sourceVal.text || '') : '';
        if (nr.bucket === 'changed' && tText && sText) {
          bodyHtml += '<div class="dm-mem-text dm-word-diff">' + renderWordDiffHtml(tText, sText) + '</div>';
        } else {
          const displayText = sText || tText;
          bodyHtml += '<div class="dm-mem-text">' + esc(displayText) + '</div>';
        }
        bodyHtml += renderMemoryMetadata(sample, isTargetOnly, nr.seed);
      } else if (nr.isStructuredObj && nr.bucket !== 'same') {
        const axes = buildAxisRows(
          isPlainObject(nr.targetVal) ? nr.targetVal : undefined,
          isPlainObject(nr.sourceVal) ? nr.sourceVal : undefined,
        );
        bodyHtml += '<div style="font-weight:600;font-size:12px;">' + esc(nr.key) + '</div>';
        bodyHtml += renderAxisTable(sec.key, nr.key, axes, ro, targetLabel, sourceLabel);
      } else {
        const label = entryLabel(nr.key, sample);
        bodyHtml += '<div style="font-weight:600;font-size:12px;">' + esc(label) + '</div>';
        if (!isSame) {
          bodyHtml += '<div style="font-size:11px;color:var(--text-muted);margin-top:2px;">'
            + '<span>' + esc(formatCompact(nr.targetVal)) + '</span>'
            + ' <span>-></span> '
            + '<span style="color:var(--text);">' + esc(formatCompact(nr.sourceVal)) + '</span>'
            + '</div>';
        }
      }

      rowHtml += '<div class="' + rowCls + '" data-bucket="' + nr.bucket + '" data-seed="' + (nr.seed ? '1' : '0') + '" data-tags="' + esc(nr.tags.join(',')) + '" data-search="' + esc(searchText) + '">'
        + ctrlHtml
        + '<div style="text-align:center;">' + badgeMap[nr.bucket] + '</div>'
        + '<div style="min-width:0;">' + bodyHtml + '</div>'
        + '</div>';
    }

    const summaryParts: string[] = [];
    if (counts.changed) summaryParts.push(counts.changed + ' chg');
    if (counts.new) summaryParts.push(counts.new + ' new');
    if (counts['target-only']) summaryParts.push(counts['target-only'] + ' protected');
    if (counts.same) summaryParts.push(counts.same + ' same');

    const html = '<div class="diff-section pe dm-section-card ' + sameSecCls + '" data-key="' + esc(sec.key) + '">'
      + '<div class="dm-sec-head pe-head">'
      + '<input type="checkbox" class="diff-section-toggle" data-key="' + esc(sec.key) + '" '
      + (ro ? 'disabled' : '') + ' title="Replace entire ' + esc(sec.label) + ' section (overwrites ' + targetLabel + '-only items)">'
      + '<span class="pe-chevron" style="color:var(--text-muted);font-size:10px;transform:rotate(' + (hasChanges ? '90deg' : '0deg') + ');">▶</span>'
      + '<span style="font-weight:600;color:var(--text);">' + esc(sec.label) + '</span>'
      + '<span style="margin-left:auto;font-size:11px;color:var(--text-muted);">' + (summaryParts.join(' · ') || 'empty') + '</span>'
      + '</div>'
      + '<div class="pe-body dm-sec-body" ' + (hasChanges ? '' : 'hidden') + '>'
      + '<div style="display:flex;align-items:center;gap:8px;font-size:11px;color:var(--text-muted);margin-bottom:6px;">'
      + '<label style="display:flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" class="pe-all" data-key="' + esc(sec.key) + '" ' + (ro ? 'disabled' : '') + '> Select all applyable</label>'
      + '<span style="margin-left:auto;font-size:10.5px;">' + esc(targetLabel) + '-only items stay Keep Safe unless unlocked.</span>'
      + '</div>'
      + rowHtml
      + '</div>'
      + '</div>';

    return { html, counts, seedCount, tags: Array.from(tagSet) };
  }

  function renderSimpleSection(sec: DiffSectionState, current: unknown, incoming: unknown,
                               ro: boolean | undefined, toWorld: boolean): {
    html: string;
    bucket: NormalizedBucket;
  } {
    const targetVal = toWorld ? incoming : current;
    const sourceVal = toWorld ? current : incoming;
    const targetLabel = toWorld ? 'World' : 'Library';
    const sourceLabel = toWorld ? 'Library' : 'World';
    const isDiff = sec.isDifferent;
    const bucket: NormalizedBucket = !isDiff
      ? 'same'
      : (isEmptyValue(targetVal) && !isEmptyValue(sourceVal) ? 'new' : 'changed');
    const sameCls = isDiff ? 'dm-has-diff' : 'dm-section-same';
    const checked = !ro && isDiff && !sec.clobber ? 'checked' : '';

    // Check if this is a structured object (e.g. stats, skills) eligible for per-axis smart merge
    const isObjMerge = isDiff && (STRUCTURED_OBJECT_KEYS.has(sec.key) || (isPlainObject(targetVal) && isPlainObject(sourceVal)));

    let contentHtml = '';
    if (!isDiff) {
      contentHtml = '<div class="dm-muted" style="font-size:11.5px;">Identical: <code>' + esc(formatCompact(targetVal)) + '</code></div>';
    } else if (isObjMerge && (isPlainObject(targetVal) || isPlainObject(sourceVal))) {
      const axes = buildAxisRows(
        isPlainObject(targetVal) ? targetVal : undefined,
        isPlainObject(sourceVal) ? sourceVal : undefined,
      );
      contentHtml = '<div class="dm-obj-merge" data-key="' + esc(sec.key) + '">'
        + renderAxisTable(sec.key, '__section__', axes, ro, targetLabel, sourceLabel)
        + '</div>';
    } else if (isProseValue(sec.key, targetVal, sourceVal)) {
      contentHtml = '<div class="dm-word-diff">'
        + renderWordDiffHtml(typeof targetVal === 'string' ? targetVal : formatValue(targetVal),
                             typeof sourceVal === 'string' ? sourceVal : formatValue(sourceVal))
        + '</div>';
    } else {
      contentHtml = '<div style="font-size:12px;display:flex;flex-wrap:wrap;gap:6px;align-items:baseline;">'
        + '<span class="dm-word-del">' + esc(formatValue(targetVal)) + '</span>'
        + '<span class="dm-muted">-></span>'
        + '<span class="dm-word-add">' + esc(formatValue(sourceVal)) + '</span>'
        + '</div>';
    }

    const warnBadge = sec.clobber
      ? '<span class="dm-pill dm-pill-safe" title="Source is empty while ' + targetLabel + ' has data">⚠ Empty in ' + sourceLabel + '</span>'
      : '';

    const html = '<div class="diff-section dm-section-card ' + sameCls + (isObjMerge ? ' dm-obj-section' : '') + '" data-key="' + esc(sec.key) + '" data-bucket="' + bucket + '" data-search="' + esc((sec.label + ' ' + sec.key).toLowerCase()) + '">'
      + '<div class="dm-sec-head">'
      + '<input type="checkbox" class="diff-section-toggle" data-key="' + esc(sec.key) + '" ' + checked + ' ' + (ro ? 'disabled' : '') + '>'
      + '<span style="font-weight:600;color:var(--text);">' + esc(sec.label) + '</span>'
      + warnBadge
      + '<span style="margin-left:auto;font-size:11px;color:var(--text-muted);">' + (isDiff ? (bucket === 'new' ? '+ New' : '~ Changed') : '= Identical') + '</span>'
      + '</div>'
      + '<div class="dm-sec-body">' + contentHtml + '</div>'
      + '</div>';

    return { html, bucket };
  }

  // ── Show Modal ────────────────────────────────────────────────────

  function show(current: DiffEntry, incoming: DiffEntry, sections: DiffModalDiffSection[],
                options: DiffOptions = {}): Promise<DiffModalDiffResult | null> {
    return new Promise((resolve) => {
      ensureStyles();
      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay';

      const toWorld = options.direction === 'to-world';
      const modal = document.createElement('div');
      modal.className = 'modal-window diff-modal-v3';

      const diffs: DiffSectionState[] = sections.map((s: DiffModalDiffSection) => {
        const isDifferent = compareValues(current?.[s.key], incoming?.[s.key]);
        const clobber = toWorld
          ? isDifferent && !isEmptyValue(incoming?.[s.key]) && isEmptyValue(current?.[s.key])
          : isDifferent && !isEmptyValue(current?.[s.key]) && isEmptyValue(incoming?.[s.key]);
        const isPerEntry = !!s.perEntry && (perEntryEligible(incoming?.[s.key]) || perEntryEligible(current?.[s.key]));
        return Object.assign({}, s, { isDifferent, clobber, isPerEntry });
      });
      const hasDiffs = diffs.some((d) => d.isDifferent);

      const dirBadge = toWorld
        ? '<span class="dm-dir-badge dm-dir-to-world">Library -> World</span>'
        : '<span class="dm-dir-badge dm-dir-to-lib">World -> Library</span>';
      const roBadge = options.readOnly ? '<span class="dm-ro-badge">Read-Only</span>' : '';

      let html = '<div class="dm-head">'
        + '<div class="dm-head-left">'
        + '<h3 style="margin:0;font-size:15px;">' + esc(options.title || (toWorld ? 'Refresh from Library' : 'Save to Library')) + '</h3>'
        + (options.name ? '<span style="font-size:12.5px;color:var(--text-muted);"><strong>' + esc(options.name) + '</strong></span>' : '')
        + dirBadge + roBadge
        + '</div>'
        + '<button class="modal-close-btn" id="diff-modal-cancel">✕</button>'
        + '</div>';

      if (!hasDiffs) {
        html += '<div class="dm-body">'
          + '<p style="padding:16px 0;color:var(--text-muted);font-size:13px;">No changes detected - both copies are already identical.</p>'
          + '</div>'
          + '<div class="dm-foot"><div class="dm-foot-actions" style="justify-content:flex-end;">'
          + '<button class="btn btn-sm" id="diff-modal-close">OK</button>'
          + '</div></div>';
      } else {
        const totals: Record<NormalizedBucket, number> = { changed: 0, new: 0, 'target-only': 0, same: 0 };
        let totalSeeds = 0;
        const allTags = new Set<string>();
        const sectionHtmlParts: string[] = [];

        diffs.forEach((s) => {
          if (s.isPerEntry) {
            const res = renderPerEntryGroup(s, current?.[s.key], incoming?.[s.key], options.readOnly, toWorld);
            sectionHtmlParts.push(res.html);
            totals.changed += res.counts.changed;
            totals.new += res.counts.new;
            totals['target-only'] += res.counts['target-only'];
            totals.same += res.counts.same;
            totalSeeds += res.seedCount;
            res.tags.forEach((t) => allTags.add(t));
          } else {
            const res = renderSimpleSection(s, current?.[s.key], incoming?.[s.key], options.readOnly, toWorld);
            sectionHtmlParts.push(res.html);
            totals[res.bucket]++;
          }
        });

        const tagChipsHtml = Array.from(allTags).slice(0, 12).map((t) =>
          '<button type="button" class="dm-facet-chip dm-tag-chip" data-tag="' + esc(t) + '">#' + esc(t) + '</button>'
        ).join('');

        html += '<div class="dm-toolbar">'
          + '<div class="dm-kpi-strip">'
          + '<button type="button" class="dm-kpi-pill active" data-filter="all">All Changes</button>'
          + '<button type="button" class="dm-kpi-pill dm-kpi-chg" data-filter="changed">~ ' + totals.changed + ' Conflicts</button>'
          + '<button type="button" class="dm-kpi-pill dm-kpi-new" data-filter="new">+ ' + totals.new + ' New</button>'
          + '<button type="button" class="dm-kpi-pill dm-kpi-safe" data-filter="target-only">🛡️ ' + totals['target-only'] + ' ' + (toWorld ? 'World-Only' : 'Library-Only') + '</button>'
          + '<button type="button" class="dm-kpi-pill" id="dm-toggle-same" title="Toggle identical (=) items">= ' + totals.same + ' Identical (Hidden)</button>'
          + '<input type="search" class="dm-search" id="dm-search-input" placeholder="Filter fields, memories, tags...">'
          + '</div>'
          + '<div class="dm-facet-bar">'
          + (totalSeeds > 0 ? '<button type="button" class="dm-facet-chip" id="dm-keep-all-seed">🛡️ Keep all Seed (' + totalSeeds + ')</button>' : '')
          + (totals['target-only'] > 0 ? '<button type="button" class="dm-facet-chip" id="dm-keep-all-safe">🛡️ Keep all ' + (toWorld ? 'World-Only' : 'Target-Only') + '</button>' : '')
          + tagChipsHtml
          + '</div>'
          + '</div>';

        html += '<div class="dm-body dm-hide-same" id="dm-body">' + sectionHtmlParts.join('') + '</div>';

        html += '<div class="dm-foot">'
          + '<div class="dm-dry-run" id="dm-dry-run-summary">Calculating merge plan...</div>'
          + '<div class="dm-foot-actions">';
        if (!options.readOnly) {
          html += '<div style="display:flex;gap:8px;"><button class="btn btn-sm btn-yellow" id="diff-modal-duplicate">📋 Save as Duplicate</button></div>';
        }
        html += '<div style="display:flex;gap:8px;">'
          + '<button class="btn btn-sm" id="diff-modal-cancel-bottom">' + (options.readOnly ? 'Close' : 'Cancel') + '</button>'
          + (options.readOnly ? '' : '<button class="btn btn-sm btn-green" id="diff-modal-update">Apply Selected</button>')
          + '</div></div></div>';
      }

      window.Lit.render(window.Lit.unsafeHTML(html), modal);
      overlay.appendChild(modal);
      document.body.appendChild(overlay);

      const escClose = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.preventDefault(); cleanup(); resolve(null); } };
      const cleanup = () => { document.removeEventListener('keydown', escClose); if (overlay.parentNode) document.body.removeChild(overlay); };
      document.addEventListener('keydown', escClose);
      overlay.addEventListener('mousedown', (e: MouseEvent) => { if (e.target === overlay) { cleanup(); resolve(null); } });

      const cancelTop = document.getElementById('diff-modal-cancel');
      if (cancelTop) cancelTop.onclick = () => { cleanup(); resolve(null); };
      const cancelBtn = document.getElementById('diff-modal-cancel-bottom');
      if (cancelBtn) cancelBtn.onclick = () => { cleanup(); resolve(null); };
      const closeBtn = document.getElementById('diff-modal-close');
      if (closeBtn) closeBtn.onclick = () => { cleanup(); resolve(null); };

      const collectResult = (action: DiffAction, extra?: Record<string, unknown>): DiffModalDiffResult => {
        const selected: string[] = [];
        const entries: Record<string, EntrySelectionSpec> = {};

        (modal.querySelectorAll('.pe') as NodeListOf<HTMLElement>).forEach((group) => {
          const key = group.dataset.key as string;
          const sectionToggle = group.querySelector('.diff-section-toggle') as HTMLInputElement | null;
          if (sectionToggle && sectionToggle.checked) {
            if (!selected.includes(key)) selected.push(key);
            return;
          }
          const checkedKeys: string[] = [];
          (group.querySelectorAll('.pe-entry') as NodeListOf<HTMLInputElement>)
            .forEach((e) => { if (e.checked && e.dataset.entry) checkedKeys.push(e.dataset.entry); });

          const removeKeys: string[] = [];
          (group.querySelectorAll('.dm-safe-toggle') as NodeListOf<HTMLButtonElement>)
            .forEach((b) => { if (b.dataset.state === 'remove' && b.dataset.entry) removeKeys.push(b.dataset.entry); });

          const axesMap: Record<string, string[]> = {};
          (group.querySelectorAll('.dm-axis-row') as NodeListOf<HTMLElement>).forEach((row) => {
            if (row.dataset.pick === 'source' && row.dataset.entry && row.dataset.axis) {
              if (!axesMap[row.dataset.entry]) axesMap[row.dataset.entry] = [];
              axesMap[row.dataset.entry].push(row.dataset.axis);
            }
          });

          const hasAxes = Object.keys(axesMap).length > 0;
          const hasRemove = removeKeys.length > 0;
          if (hasAxes || hasRemove) {
            const spec: EntrySelectionObject = { keys: checkedKeys };
            if (hasAxes) spec.axes = axesMap;
            if (hasRemove) spec.remove = removeKeys;
            entries[key] = spec;
          } else if (checkedKeys.length > 0) {
            entries[key] = checkedKeys;
          }
        });

        (modal.querySelectorAll('.diff-section:not(.pe)') as NodeListOf<HTMLElement>).forEach((secEl) => {
          const key = secEl.dataset.key as string;
          const t = secEl.querySelector('.diff-section-toggle') as HTMLInputElement | null;
          if (t && t.checked) {
            const axisRows = secEl.querySelectorAll('.dm-axis-row') as NodeListOf<HTMLElement>;
            if (axisRows.length > 0) {
              const sourceAxes: string[] = [];
              let hasTargetPick = false;
              axisRows.forEach((row) => {
                if (row.dataset.bucket === 'same') return;
                if (row.dataset.pick === 'source' && row.dataset.axis) sourceAxes.push(row.dataset.axis);
                else if (row.dataset.pick === 'target') hasTargetPick = true;
              });
              if (hasTargetPick && sourceAxes.length > 0) {
                entries[key] = sourceAxes;
              } else if (!hasTargetPick && sourceAxes.length > 0) {
                if (!selected.includes(key)) selected.push(key);
              }
            } else if (!selected.includes(key)) {
              selected.push(key);
            }
          }
        });

        const base: DiffModalDiffResult = { action, sections: selected, entries };
        return extra ? Object.assign(base, extra) : base;
      };

      const updateDryRun = () => {
        const dryEl = document.getElementById('dm-dry-run-summary');
        if (!dryEl) return;
        const res = collectResult('update');
        const wholeCount = res.sections.length;
        let entryAdds = 0;
        let axisCount = 0;
        let removeCount = 0;
        for (const k of Object.keys(res.entries)) {
          const v = res.entries[k];
          if (Array.isArray(v)) {
            entryAdds += v.length;
          } else if (v && typeof v === 'object') {
            entryAdds += (v.keys || []).length;
            removeCount += (v.remove || []).length;
            for (const ek of Object.keys(v.axes || {})) axisCount += (v.axes?.[ek] || []).length;
          }
        }
        const safeCount = modal.querySelectorAll('.dm-safe-toggle[data-state="safe"]').length;
        const parts: string[] = [];
        parts.push(wholeCount + ' section' + (wholeCount === 1 ? '' : 's'));
        if (entryAdds > 0) parts.push(entryAdds + ' entr' + (entryAdds === 1 ? 'y' : 'ies'));
        if (axisCount > 0) parts.push(axisCount + ' smart-merge ax' + (axisCount === 1 ? 'is' : 'es'));
        parts.push(safeCount + ' Keep Safe');
        if (removeCount > 0) parts.push(removeCount + ' marked for removal');
        dryEl.textContent = 'Dry-run summary: ' + parts.join(' · ');
      };

      // Filter & Search state
      let activeFilter = 'all';
      let activeTag = '';
      let searchTerm = '';

      const applyFilters = () => {
        const bodyEl = document.getElementById('dm-body');
        if (!bodyEl) return;
        (bodyEl.querySelectorAll('.dm-pe-row') as NodeListOf<HTMLElement>).forEach((row) => {
          const bucket = row.dataset.bucket || '';
          const tags = (row.dataset.tags || '').split(',').filter(Boolean);
          const text = row.dataset.search || '';
          const matchBucket = activeFilter === 'all' || bucket === activeFilter;
          const matchTag = !activeTag || tags.includes(activeTag);
          const matchSearch = !searchTerm || text.includes(searchTerm);
          row.classList.toggle('dm-hidden-filter', !(matchBucket && matchTag && matchSearch));
        });
        (bodyEl.querySelectorAll('.diff-section:not(.pe)') as NodeListOf<HTMLElement>).forEach((sec) => {
          const bucket = sec.dataset.bucket || '';
          const text = sec.dataset.search || '';
          const matchBucket = activeFilter === 'all' || bucket === activeFilter;
          const matchSearch = !searchTerm || text.includes(searchTerm);
          const matchTag = !activeTag;
          sec.classList.toggle('dm-hidden-filter', !(matchBucket && matchTag && matchSearch));
        });
      };

      // KPI filter pills
      (modal.querySelectorAll('.dm-kpi-pill[data-filter]') as NodeListOf<HTMLButtonElement>).forEach((pill) => {
        pill.onclick = () => {
          activeFilter = pill.dataset.filter || 'all';
          (modal.querySelectorAll('.dm-kpi-pill[data-filter]') as NodeListOf<HTMLButtonElement>)
            .forEach((p) => p.classList.toggle('active', p === pill));
          applyFilters();
        };
      });

      const sameToggle = document.getElementById('dm-toggle-same');
      if (sameToggle) {
        sameToggle.onclick = () => {
          const bodyEl = document.getElementById('dm-body');
          if (!bodyEl) return;
          const nowHidden = bodyEl.classList.toggle('dm-hide-same');
          sameToggle.classList.toggle('active', !nowHidden);
          sameToggle.textContent = sameToggle.textContent?.replace(/\((Hidden|Shown)\)/, nowHidden ? '(Hidden)' : '(Shown)') || '';
        };
      }

      const searchInput = document.getElementById('dm-search-input') as HTMLInputElement | null;
      if (searchInput) {
        searchInput.oninput = () => {
          searchTerm = searchInput.value.trim().toLowerCase();
          applyFilters();
        };
      }

      // Tag facet chips
      (modal.querySelectorAll('.dm-tag-chip') as NodeListOf<HTMLButtonElement>).forEach((chip) => {
        chip.onclick = () => {
          const tag = chip.dataset.tag || '';
          activeTag = activeTag === tag ? '' : tag;
          (modal.querySelectorAll('.dm-tag-chip') as NodeListOf<HTMLButtonElement>)
            .forEach((c) => c.classList.toggle('active', c.dataset.tag === activeTag));
          applyFilters();
        };
      });

      // Bulk Keep Safe chips
      const keepSeedsBtn = document.getElementById('dm-keep-all-seed');
      if (keepSeedsBtn) {
        keepSeedsBtn.onclick = () => {
          (modal.querySelectorAll('.dm-safe-toggle[data-seed="1"]') as NodeListOf<HTMLButtonElement>).forEach((b) => {
            b.dataset.state = 'safe';
            b.classList.remove('dm-unlocked');
            b.textContent = '🛡️ Keep Safe';
          });
          updateDryRun();
        };
      }
      const keepAllSafeBtn = document.getElementById('dm-keep-all-safe');
      if (keepAllSafeBtn) {
        keepAllSafeBtn.onclick = () => {
          (modal.querySelectorAll('.dm-safe-toggle') as NodeListOf<HTMLButtonElement>).forEach((b) => {
            b.dataset.state = 'safe';
            b.classList.remove('dm-unlocked');
            b.textContent = '🛡️ Keep Safe';
          });
          updateDryRun();
        };
      }

      // Wire safety lock toggles
      (modal.querySelectorAll('.dm-safe-toggle') as NodeListOf<HTMLButtonElement>).forEach((btn) => {
        btn.onclick = () => {
          if (btn.disabled) return;
          const isSafe = btn.dataset.state !== 'remove';
          btn.dataset.state = isSafe ? 'remove' : 'safe';
          btn.classList.toggle('dm-unlocked', isSafe);
          btn.textContent = isSafe ? '🗑 Mark Remove' : '🛡️ Keep Safe';
          updateDryRun();
        };
      });

      // Wire per-axis buttons
      (modal.querySelectorAll('.dm-axis-row') as NodeListOf<HTMLElement>).forEach((row) => {
        const btns = row.querySelectorAll('.dm-axis-btn') as NodeListOf<HTMLButtonElement>;
        btns.forEach((btn) => {
          btn.onclick = () => {
            if (btn.disabled) return;
            const choice = btn.dataset.choice === 'source' ? 'source' : 'target';
            row.dataset.pick = choice;
            btns.forEach((b) => {
              b.classList.toggle('active-target', choice === 'target' && b.dataset.choice === 'target');
              b.classList.toggle('active-source', choice === 'source' && b.dataset.choice === 'source');
            });
            updateDryRun();
          };
        });
      });

      // Wire per-group expand/collapse + whole/all toggles
      (modal.querySelectorAll('.pe') as NodeListOf<HTMLElement>).forEach((group) => {
        const head = group.querySelector('.pe-head') as HTMLElement | null;
        const chevron = group.querySelector('.pe-chevron') as HTMLElement;
        const body = group.querySelector('.pe-body') as HTMLElement;
        const sectionToggle = group.querySelector('.diff-section-toggle') as HTMLInputElement | null;
        const allToggle = group.querySelector('.pe-all') as HTMLInputElement | null;
        if (head) {
          head.onclick = (ev: MouseEvent) => {
            if (ev.target && (ev.target === sectionToggle || ((ev.target as HTMLElement).tagName === 'INPUT'))) return;
            const hidden = body.hasAttribute('hidden');
            body.toggleAttribute('hidden');
            chevron.style.transform = hidden ? 'rotate(90deg)' : 'rotate(0deg)';
          };
        }
        if (sectionToggle && !sectionToggle.disabled) {
          sectionToggle.onchange = () => {
            const on = sectionToggle.checked;
            (group.querySelectorAll('.pe-entry') as NodeListOf<HTMLInputElement>).forEach((e) => {
              if (!e.disabled) e.checked = on;
            });
            if (allToggle) allToggle.checked = on;
            updateDryRun();
          };
        }
        if (allToggle && !allToggle.disabled) {
          allToggle.onchange = () => {
            (group.querySelectorAll('.pe-entry') as NodeListOf<HTMLInputElement>).forEach((e) => {
              if (!e.disabled) e.checked = allToggle.checked;
            });
            updateDryRun();
          };
        }
        (group.querySelectorAll('.pe-entry') as NodeListOf<HTMLInputElement>).forEach((cb) => {
          cb.onchange = () => updateDryRun();
        });
      });

      (modal.querySelectorAll('.diff-section:not(.pe) .diff-section-toggle') as NodeListOf<HTMLInputElement>).forEach((cb) => {
        cb.onchange = () => updateDryRun();
      });

      updateDryRun();

      const updateBtn = document.getElementById('diff-modal-update');
      if (updateBtn) {
        updateBtn.onclick = () => {
          const result = collectResult('update');
          try {
            const uh = (window as unknown as { UndoHistory?: { snapshot?: (label: string) => void; refresh?: () => void } }).UndoHistory;
            if (uh && typeof uh.snapshot === 'function') uh.snapshot('DiffModal Apply');
          } catch (_e) { /* ignore */ }
          cleanup();
          resolve(result);
        };
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

  // Apply a per-entry (and optional per-axis / remove) selection onto a base value.
  // Backward compatible with plain string[] selKeys as well as EntrySelectionObject.
  function applyEntrySelection(current: unknown, incoming: unknown,
                               selSpec: EntrySelectionSpec | null | undefined): unknown {
    if (!incoming || !selSpec) return current;
    const isSpecObj = !Array.isArray(selSpec) && typeof selSpec === 'object';
    const selKeys = Array.isArray(selSpec) ? selSpec : (selSpec.keys || []);
    const axesMap = isSpecObj ? (selSpec.axes || {}) : {};
    const removeSet = new Set<string>(isSpecObj ? (selSpec.remove || []) : []);
    if (selKeys.length === 0 && Object.keys(axesMap).length === 0 && removeSet.size === 0) {
      return current;
    }

    if (Array.isArray(incoming)) {
      const selSet = new Set(selKeys);
      let out: unknown[] = Array.isArray(current) ? (current as unknown[]).slice() : [];
      if (removeSet.size > 0) {
        out = out.filter((item) => {
          const sk = selKeyOf(item);
          return sk === null || !removeSet.has(sk);
        });
      }
      const findPartner = (inc: unknown): number => {
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
      for (const inc of incoming as unknown[]) {
        const sk = selKeyOf(inc);
        if (sk === null) continue;
        if (selSet.has(sk)) {
          const idx = findPartner(inc);
          if (idx >= 0) {
            const priorId = (out[idx] as Record<string, unknown> | undefined)?.id;
            out[idx] = (out[idx] && priorId != null && priorId !== '')
              ? Object.assign({}, inc, { id: priorId })
              : inc;
          } else {
            out.push(inc);
          }
        } else if (axesMap[sk] && isPlainObject(inc)) {
          const idx = findPartner(inc);
          if (idx >= 0 && isPlainObject(out[idx])) {
            const merged = Object.assign({}, out[idx] as Record<string, unknown>);
            for (const ak of axesMap[sk]) {
              if (inc[ak] !== undefined) merged[ak] = inc[ak];
            }
            out[idx] = merged;
          }
        }
      }
      return out;
    }

    if (incoming && typeof incoming === 'object') {
      const src = incoming as Record<string, unknown>;
      const out: Record<string, unknown> = current && typeof current === 'object' && !Array.isArray(current)
        ? Object.assign({}, current as Record<string, unknown>) : {};
      for (const rk of removeSet) {
        delete out[rk];
      }
      for (const k of selKeys) {
        if (src[k] !== undefined) out[k] = src[k];
      }
      for (const k of Object.keys(axesMap)) {
        if (isPlainObject(src[k])) {
          const baseEntry = isPlainObject(out[k]) ? Object.assign({}, out[k] as Record<string, unknown>) : {};
          for (const ak of axesMap[k]) {
            if ((src[k] as Record<string, unknown>)[ak] !== undefined) {
              baseEntry[ak] = (src[k] as Record<string, unknown>)[ak];
            }
          }
          out[k] = baseEntry;
        }
      }
      return out;
    }
    return incoming;
  }

  return {
    show,
    applyEntrySelection,
    wordDiff,
    entryDiff,
    isSeedMemory,
    buildAxisRows,
  };
})();

// ────────────────────────── local types ──────────────────────────
// Declared after the IIFE so the leading JSDoc block stays the first thing in
// the emitted .js and `@module` remains discoverable.

type DiffEntry = Record<string, unknown>;

interface DiffModalDiffSection {
    key: string;
    label: string;
    perEntry?: boolean;
}

interface DiffSectionState extends DiffModalDiffSection {
    isDifferent: boolean;
    clobber: boolean;
    isPerEntry: boolean;
}

type DiffStatus = 'same' | 'added' | 'removed' | 'changed';
type NormalizedBucket = 'same' | 'changed' | 'new' | 'target-only';

interface DiffModalDiffRow {
    key: string | number | null;
    current: unknown;
    incoming: unknown;
    status: DiffStatus;
}

interface NormalizedEntryRow {
    key: string;
    rawStatus: DiffStatus;
    bucket: NormalizedBucket;
    targetVal: unknown;
    sourceVal: unknown;
    seed: boolean;
    isStructuredObj: boolean;
    tags: string[];
}

interface AxisDiffRow {
    axis: string;
    bucket: NormalizedBucket;
    targetVal: unknown;
    sourceVal: unknown;
    defaultPick: 'target' | 'source';
}

interface WordDiffChunk {
    type: 'same' | 'del' | 'add';
    text: string;
}

interface EntryListItem {
    key: string | number;
    data: unknown;
}

interface EntrySelectionObject {
    keys: string[];
    axes?: Record<string, string[]>;
    remove?: string[];
}

type EntrySelectionSpec = string[] | EntrySelectionObject;

type DiffAction = 'update' | 'duplicate';

interface DiffModalDiffResult {
    action: DiffAction;
    sections: string[];
    entries: Record<string, EntrySelectionSpec>;
    name?: string;
    id?: string;
}

interface DiffOptions {
    title?: string;
    name?: string;
    readOnly?: boolean;
    direction?: string;
}

interface DiffModalWindowSurface { DiffModal: unknown }
