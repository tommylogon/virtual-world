/**
 * diff.js — property-level diff for staged NL-editor ops (task-461).
 *
 * A staged op shows a summary line; this turns it into the concrete property
 * changes it will make ("traits.dark_vision: — → true"), diffed against the
 * live/staged pre-state, so a wrong or empty patch is visible before Apply.
 *
 * Pure: the caller supplies the node maps, so it is unit-testable without DOM.
 *
 * @module nl-editor/diff — property-level diff for staged ops
 * @contributes NLEditorDiff: opDiff(), diffPairs(), formatChanges(), summaryLines()
 * @powers NL editor — the staged-ops tray's per-op diff preview
 * @relates read by ui.js when rendering staged rows
 * @docs docs/virtualWorld/dev_tasks/inprogress/graph/task-461-nl-editor-validation-gate-and-apply-time-property-diff.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

interface NlEditorDiffWindowSurface { NLEditorDiff: unknown }

(window as unknown as NlEditorDiffWindowSurface).NLEditorDiff = (() => {
    'use strict';

    const RESERVED = new Set(['properties', 'name', 'id', 'type', 'kind']);
    const isObj = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
    const same = (a: unknown, b: unknown): boolean => JSON.stringify(a) === JSON.stringify(b);

    /** The effective property map of a patch (nested `properties` + flat keys). */
    function patchProps(patch: unknown): Record<string, unknown> {
        const props: Record<string, unknown> = {};
        if (!isObj(patch)) return props;
        if (isObj(patch.properties)) Object.assign(props, patch.properties);
        for (const [key, value] of Object.entries(patch)) {
            if (RESERVED.has(key)) continue;
            props[key] = value;
        }
        return props;
    }

    /** Pre-state properties for a node: staged creation wins, else the live node. */
    function baseProps(nodeId: unknown, nodes: Record<string, unknown>, creations: Record<string, unknown>): Record<string, unknown> {
        const key = String(nodeId || '').toLowerCase();
        const created = (creations || {})[key];
        if (isObj(created) && isObj(created.properties)) return created.properties;
        const live = (nodes || {})[key];
        return isObj(live) && isObj(live.properties) ? live.properties : {};
    }

    /** Flatten one patch key into leaf changes (dicts are diffed key-by-key). */
    function diffPairs(key: string, before: unknown, after: unknown): PropertyChange[] {
        if (isObj(before) || isObj(after)) {
            const b = isObj(before) ? before : {};
            const a = isObj(after) ? after : {};
            const out: PropertyChange[] = [];
            for (const sub of new Set([...Object.keys(b), ...Object.keys(a)])) {
                if (same(b[sub], a[sub])) continue;
                out.push({ key: `${key}.${sub}`, before: b[sub], after: a[sub] });
            }
            return out;
        }
        if (same(before, after)) return [];
        return [{ key, before, after }];
    }

    /** All leaf changes a patch makes to one node. */
    function nodeDiff(nodeId: unknown, patch: unknown, nodes: Record<string, unknown>, creations: Record<string, unknown>): PropertyChange[] {
        const before = baseProps(nodeId, nodes, creations);
        const changes: PropertyChange[] = [];
        for (const [key, value] of Object.entries(patchProps(patch))) {
            changes.push(...diffPairs(key, before[key], value));
        }
        return changes;
    }

    /** Describe an op's effect: kind, target id(s), and leaf property changes. */
    function opDiff(op: unknown, context: DiffContext = {}): OpDiff {
        const nodes = context.nodes || {};
        const creations = context.creations || {};
        const type = isObj(op) ? op.type : undefined;
        const payload = (isObj(op) && isObj(op.payload) ? op.payload : {}) as Record<string, unknown>;

        if (type === 'create_node') {
            const node = (isObj(payload.node) ? payload.node : payload) as Record<string, unknown>;
            return { kind: 'create', id: node.id, label: node.name, changes: [] };
        }
        if (type === 'delete_node') {
            return { kind: 'delete', id: payload.node_id, changes: [] };
        }
        if (type === 'update_node') {
            return {
                kind: 'update',
                id: payload.node_id,
                changes: nodeDiff(payload.node_id, payload.patch, nodes, creations),
            };
        }
        if (type === 'update_matching_nodes') {
            const ids = (Array.isArray(payload.matched_ids) ? payload.matched_ids : []) as string[];
            return {
                kind: 'bulk',
                targets: ids.map(id => ({
                    id,
                    changes: nodeDiff(id, payload.patch, nodes, creations),
                })),
            };
        }
        if (type === 'library_upsert') {
            return { kind: 'library', id: payload.id, registry: payload.registry_type, changes: [] };
        }
        if (type === 'library_delete') {
            return { kind: 'library-delete', id: payload.id, registry: payload.registry_type, changes: [] };
        }
        return { kind: 'other', changes: [] };
    }

    function formatValue(value: unknown): string {
        if (value === undefined) return '—';
        if (value === null) return 'null';
        if (typeof value === 'string') return value.length > 40 ? `${value.slice(0, 37)}…` : value;
        if (typeof value === 'object') {
            const text = JSON.stringify(value);
            return text.length > 40 ? `${text.slice(0, 37)}…` : text;
        }
        return String(value);
    }

    function formatChanges(changes: PropertyChange[] | undefined | null): string[] {
        return (changes || []).map(c => `${c.key}: ${formatValue(c.before)} → ${formatValue(c.after)}`);
    }

    /** Flat preview lines for the staged tray, capped at *limit* leaf changes. */
    function summaryLines(op: unknown, context: DiffContext = {}, limit = 4): string[] {
        const diff = opDiff(op, context);
        if (diff.kind === 'create') return [`+ create ${diff.id || 'node'}`];
        if (diff.kind === 'delete') return [`− delete ${diff.id || 'node'}`];
        if (diff.kind === 'library') return [`library ${diff.registry || '?'}: upsert ${diff.id || '?'}`];
        if (diff.kind === 'library-delete') return [`library ${diff.registry || '?'}: delete ${diff.id || '?'}`];

        let changes: string[];
        if (diff.kind === 'bulk') {
            changes = [];
            for (const target of diff.targets || []) {
                changes.push(...formatChanges(target.changes).map(text => `${target.id}: ${text}`));
            }
        } else {
            changes = formatChanges(diff.changes);
        }
        if (!changes.length) return ['(no property change — will no-op)'];
        if (changes.length <= limit) return changes;
        return [...changes.slice(0, limit), `+${changes.length - limit} more`];
    }

    return { opDiff, diffPairs, nodeDiff, patchProps, baseProps, formatChanges, formatValue, summaryLines };
})();

/* ── types ──
 * Declared at the BOTTOM on purpose: tsc drops a file's leading JSDoc when the
 * first statement is type-only, and js_module_index.py reads `@module` out of
 * the emitted .js. An `interface` above the IIFE would strip it. */

/** One leaf property change: `key`, its pre-state and its post-state. */
interface PropertyChange {
    key: string;
    before: unknown;
    after: unknown;
}

/** Caller-supplied maps: live nodes and staged creations, both keyed by id. */
interface DiffContext {
    nodes?: Record<string, unknown>;
    creations?: Record<string, unknown>;
}

/** The per-kind result of opDiff(), discriminated on `kind`. */
type OpDiff =
    | { kind: 'create'; id: unknown; label: unknown; changes: PropertyChange[] }
    | { kind: 'delete'; id: unknown; changes: PropertyChange[] }
    | { kind: 'update'; id: unknown; changes: PropertyChange[] }
    | { kind: 'bulk'; targets: Array<{ id: string; changes: PropertyChange[] }> }
    | { kind: 'library'; id: unknown; registry: unknown; changes: PropertyChange[] }
    | { kind: 'library-delete'; id: unknown; registry: unknown; changes: PropertyChange[] }
    | { kind: 'other'; changes: PropertyChange[] };
