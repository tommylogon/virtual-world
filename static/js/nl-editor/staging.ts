/**
 * staging.js — Staging buffer for Natural-Language Editor (task-387).
 *
 * Buffers graph operations locally until the user approves and applies them.
 * No live graph changes happen until explicit Apply.
 *
 * @module nl-editor/staging — the staged-ops buffer
 * @contributes NLEditorStaging: buffer graph ops until explicit Apply; approve/reject per op
 * @powers NL editor — safe, reversible NL edits — nothing touches the graph until you apply
 * @relates consumed by index.js + ghosts.js; applied through the graph API
 * @docs docs/virtualWorld/dev_tasks/done/graph/task-387-natural-language-editor-mode.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

(window as unknown as { NLEditorStaging: unknown }).NLEditorStaging = (() => {
    'use strict';

    /**
     * The HTTP surface this buffer needs. `globals.d.ts` declares only the
     * named ApiClient wrappers converted code makes, and this file is the
     * first converted caller of createNode/createEdge/deleteEdge/deleteNode/
     * placeItemFromLibrary. A function, not a captured const, so ApiClient is
     * still read at call time exactly as the original did from inside methods.
     */
    function api() {
        return ApiClient as unknown as {
            post(path: string, body: unknown): Promise<any>;
            createNode(data: unknown): Promise<any>;
            createEdge(from: string, to: string, type: string, props?: unknown): Promise<any>;
            deleteEdge(from: string, to: string, type: string): Promise<any>;
            deleteNode(nodeId: string): Promise<any>;
            updateNode(nodeId: string, changes: unknown): Promise<any>;
            placeItemFromLibrary(target: unknown, libraryId: string): Promise<any>;
        };
    }

    class StagingBuffer {
        /** Staged graph operations, in the order they were queued. */
        declare ops: StagedOp[];
        /** Subscribers notified after every mutation; each gets the op list. */
        declare listeners: Array<(ops: StagedOp[]) => void>;

        constructor() {
            this.ops = [];
            this.listeners = [];
        }

        onChange(callback: (ops: StagedOp[]) => void) {
            this.listeners.push(callback);
        }

        _notify() {
            for (const cb of this.listeners) {
                try { cb(this.ops); } catch (e) { console.error('Staging listener error:', e); }
            }
        }

        /** Generate a deterministic, unique node ID */
        mintId(kind?: string, name?: string) {
            const cleanKind = (kind || 'item').toLowerCase().trim();
            const cleanName = (name || 'entity').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'node';
            const randSuffix = Math.random().toString(36).substring(2, 6);
            return `${cleanKind}_${cleanName}_${randSuffix}`;
        }

        /** Mint an operation ID */
        _mintOpId(): string {
            return `op_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
        }

        /** Add an operation to the staging buffer */
        addOp(type: string, payload: StagedOpPayload, summary?: string): StagedOp {
            const op: StagedOp = {
                id: this._mintOpId(),
                type,
                payload,
                summary: summary || `${type}: ${JSON.stringify(payload).slice(0, 50)}`,
                timestamp: Date.now()
            };
            this.ops.push(op);
            this._notify();
            return op;
        }

        /** Remove a specific staged operation */
        removeOp(opId: string) {
            const initialLen = this.ops.length;
            this.ops = this.ops.filter((op: StagedOp) => op.id !== opId);
            if (this.ops.length !== initialLen) {
                this._notify();
                return true;
            }
            return false;
        }

        /** Replace an op's payload in place (inline tweaker). */
        updateOp(opId: string, payload: StagedOpPayload) {
            const op = this.ops.find((o: StagedOp) => o.id === opId);
            if (!op) return false;
            op.payload = payload;
            op.summary = `${op.type}: ${JSON.stringify(payload).slice(0, 50)}`;
            op.updatedAt = Date.now();
            this._notify();
            return true;
        }

        /** Clear all staged operations */
        clear() {
            this.ops = [];
            this._notify();
        }

        /** Get all currently staged operations */
        getOps() {
            return [...this.ops];
        }

        /** Get dictionary of uncommitted created nodes: id -> node object */
        getStagedCreations(): Record<string, Record<string, unknown>> {
            const creations: Record<string, Record<string, unknown>> = {};
            for (const op of this.ops) {
                if (op.type === 'create_node' || op.type === 'spawn_library_item') {
                    const node = op.payload.node || op.payload;
                    if (node?.id) {
                        creations[node.id.toLowerCase()] = {
                            id: node.id,
                            type: node.type || node.kind || 'item',
                            name: node.name || node.id,
                            properties: node.properties || {},
                            staged: true
                        };
                    }
                } else if (op.type === 'connect_areas') {
                    const wayId = op.payload.way_id || op.payload.id;
                    if (wayId) {
                        creations[wayId.toLowerCase()] = {
                            id: wayId,
                            type: 'way',
                            name: op.payload.way_name || 'Door',
                            properties: op.payload.properties || {},
                            staged: true
                        };
                    }
                }
            }
            return creations;
        }

        /** Get set of node IDs staged for deletion */
        getStagedDeletions() {
            const deletions = new Set<string>();
            for (const op of this.ops) {
                if (op.type === 'delete_node' && op.payload.node_id) {
                    deletions.add(op.payload.node_id.toLowerCase());
                }
            }
            return deletions;
        }

        /** Get map of staged patches: id -> merged properties patch */
        getStagedUpdates() {
            const updates: Record<string, Record<string, unknown>> = {};
            for (const op of this.ops) {
                if (op.type === 'update_node' && op.payload.node_id) {
                    const nid = op.payload.node_id.toLowerCase();
                    updates[nid] = Object.assign(updates[nid] || {}, op.payload.patch || {});
                }
            }
            return updates;
        }

        /** Get staged relation edges */
        getStagedEdges() {
            const edges: StagedEdge[] = [];
            for (const op of this.ops) {
                if (op.type === 'attach') {
                    edges.push({
                        source: op.payload.from_id,
                        target: op.payload.to_id,
                        type: op.payload.relation || 'in',
                        properties: op.payload.properties || {},
                        staged: true
                    });
                } else if (op.type === 'connect_areas') {
                    const wayId = op.payload.way_id;
                    const areaA = op.payload.area_a_id;
                    const areaB = op.payload.area_b_id;
                    if (wayId && areaA && areaB) {
                        edges.push({ source: wayId, target: areaA, type: 'connection', properties: {}, staged: true });
                        edges.push({ source: areaA, target: wayId, type: 'connection', properties: {}, staged: true });
                        edges.push({ source: wayId, target: areaB, type: 'connection', properties: {}, staged: true });
                        edges.push({ source: areaB, target: wayId, type: 'connection', properties: {}, staged: true });
                    }
                }
            }
            return edges;
        }

        /**
         * Apply all staged operations.
         *
         * Primary path: one `POST /api/graph/batch` call — the server replays
         * the ops in topological order and records exactly ONE undo snapshot,
         * so a single Undo reverts the whole Apply (task-387).
         * Fallback: replay per-op against the live APIs (no atomic undo) for
         * servers predating the batch endpoint.
         *
         * @param {Set<string>|null} opFilter - apply only these op ids; the
         *        unchecked ops stay staged for later (selective apply).
         */
        async apply(opFilter: Set<string> | null = null) {
            const targets: StagedOp[] = opFilter ? this.ops.filter((o: StagedOp) => opFilter.has(o.id)) : this.ops;
            if (targets.length === 0) return { success: true, appliedCount: 0 };

            const opsPayload = targets.map((op: StagedOp) => ({ type: op.type, payload: op.payload }));
            let batch: any;
            try {
                batch = await api().post('/api/graph/batch', { ops: opsPayload, strict_validation: true });
            } catch (e) {
                batch = null;
            }
            if (batch && batch.status === 'invalid') {
                // task-461: the validation gate refused the batch — nothing was
                // applied; keep every op staged and surface the findings.
                const issues = batch.validation || [];
                const messages = (batch.errors || issues)
                    .map((er: any) => er.message || er.error || String(er))
                    .filter(Boolean);
                return {
                    success: false,
                    invalid: true,
                    appliedCount: 0,
                    remaining: this.ops.length,
                    validation: issues,
                    errors: messages.length ? messages : ['Validation failed.'],
                };
            }
            if (batch && typeof batch.status === 'string') {
                await this._refreshWorld();
                // Remove ONLY the ops the server reports as applied. A `partial`
                // batch means the rest failed; they must stay staged so the user
                // can fix and retry them rather than losing them silently.
                const appliedIds = new Set<string>();
                for (const entry of (batch.applied || [])) {
                    const op = targets[entry.index];
                    if (op) appliedIds.add(op.id);
                }
                const errs = (batch.errors || []).map((er: any) => {
                    if (typeof er === 'string') return er;
                    const label = er.type || 'op';
                    const name = targets[er.index]?.summary || `#${er.index}`;
                    return `${name} (${label}): ${er.error}`;
                });
                this._removeOps(appliedIds);
                this._notify();
                return {
                    success: batch.status === 'success',
                    appliedCount: appliedIds.size,
                    remaining: this.ops.length,
                    errors: errs
                };
            }

            // ── Fallback: per-op replay (stale server, no atomic undo) ──
            const errors: string[] = [];
            const appliedIds = new Set<string>();

            const creates = targets.filter((o: StagedOp) => o.type === 'create_node' || o.type === 'spawn_library_item' || o.type === 'connect_areas');
            const updates = targets.filter((o: StagedOp) => o.type === 'update_node' || o.type === 'link_to_library');
            const edges = targets.filter((o: StagedOp) => o.type === 'attach' || o.type === 'detach');
            const deletes = targets.filter((o: StagedOp) => o.type === 'delete_node');
            const sortedOps = [...creates, ...updates, ...edges, ...deletes];

            for (const op of sortedOps) {
                try {
                    switch (op.type) {
                        case 'create_node': {
                            const nodeData = op.payload.node || op.payload;
                            const res = await api().createNode({
                                id: nodeData.id,
                                type: nodeData.type || nodeData.kind || 'item',
                                name: nodeData.name,
                                properties: nodeData.properties || {}
                            });
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedIds.add(op.id);
                            break;
                        }
                        case 'spawn_library_item': {
                            const p = op.payload;
                            const parentNode = (typeof worldState?.getNode === 'function' ? worldState.getNode(p.parent_id) : null)
                                || (typeof worldState?.getNodeByIdentifier === 'function' ? worldState.getNodeByIdentifier(p.parent_id) : null);
                            let target: { type: string; name?: unknown; id?: unknown };
                            if (parentNode?.type === 'area') target = { type: 'area', name: parentNode.name };
                            else if (parentNode?.type === 'character') target = { type: 'character', id: parentNode.id };
                            else if (parentNode?.type === 'item') target = { type: 'container', id: parentNode.id };
                            else target = { type: 'area', name: p.parent_id };
                            const res = await api().placeItemFromLibrary(target, p.library_id);
                            // custom rename (place route has no rename)
                            if (!res?.error && p.rename && res?.node_id) {
                                await api().updateNode(res.node_id, { name: p.rename });
                            }
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedIds.add(op.id);
                            break;
                        }
                        case 'connect_areas': {
                            const p = op.payload;
                            const wayRes = await api().createNode({
                                id: p.way_id,
                                type: 'way',
                                name: p.way_name || 'Door',
                                properties: p.properties || {}
                            });
                            if (wayRes?.error) {
                                errors.push(`${op.summary} (way): ${wayRes.error}`);
                                break;
                            }
                            const dirA = p.direction_a || 'north';
                            const dirB = p.direction_b || 'south';
                            // Canonical pattern: area→way (direction + visible),
                            // way→area (direction only).
                            await api().createEdge(p.area_a_id, p.way_id, 'connection', { direction: dirA, visible_in_direction: '' });
                            await api().createEdge(p.way_id, p.area_b_id, 'connection', { direction: dirB });
                            await api().createEdge(p.area_b_id, p.way_id, 'connection', { direction: dirB, visible_in_direction: '' });
                            await api().createEdge(p.way_id, p.area_a_id, 'connection', { direction: dirA });
                            appliedIds.add(op.id);
                            break;
                        }
                        case 'update_node': {
                            const p = op.payload;
                            const patch = this._nodePatch(p.patch || {});
                            const ok = await api().updateNode(p.node_id, patch);
                            if (!ok) errors.push(`${op.summary}: node update rejected`);
                            else appliedIds.add(op.id);
                            break;
                        }
                        case 'update_matching_nodes': {
                            // Only the batch endpoint understands bulk selectors;
                            // never drop the op silently on a stale server.
                            errors.push(`${op.summary}: bulk update needs the batch endpoint`);
                            break;
                        }
                        case 'library_upsert':
                        case 'library_delete': {
                            errors.push(`${op.summary}: library editing needs the batch endpoint`);
                            break;
                        }
                        case 'link_to_library': {
                            const p = op.payload;
                            const ok = await api().updateNode(p.node_id, { properties: { template_id: p.library_id } });
                            if (!ok) errors.push(`${op.summary}: link rejected`);
                            else appliedIds.add(op.id);
                            break;
                        }
                        case 'attach': {
                            const p = op.payload;
                            const res = await api().createEdge(p.from_id, p.to_id, p.relation || 'in', p.properties || {});
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedIds.add(op.id);
                            break;
                        }
                        case 'detach': {
                            const p = op.payload;
                            const res = await api().deleteEdge(p.from_id, p.to_id, p.relation || 'in');
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedIds.add(op.id);
                            break;
                        }
                        case 'delete_node': {
                            const p = op.payload;
                            const res = await api().deleteNode(p.node_id);
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedIds.add(op.id);
                            break;
                        }
                    }
                } catch (err) {
                    errors.push(`${op.summary}: ${err instanceof Error ? err.message : String(err)}`);
                }
            }

            await this._refreshWorld();
            this._removeOps(appliedIds);
            this._notify();
            return {
                success: errors.length === 0,
                appliedCount: appliedIds.size,
                remaining: this.ops.length,
                errors
            };
        }

        /** Remove only the ops that actually applied; failures stay staged. */
        _removeOps(opIds: Set<string> | null | undefined) {
            if (!opIds || opIds.size === 0) return;
            this.ops = this.ops.filter((o: StagedOp) => !opIds.has(o.id));
        }

        /** Wrap an NL-editor flat property patch for the PATCH route.
         *  Mirrors the batch route's folding: a top-level `name` is a rename,
         *  every other flat key becomes a property. */
        _nodePatch(patch: Record<string, any>): Record<string, any> {
            if ('properties' in patch || 'id' in patch) return patch;
            const rest: Record<string, any> = { ...patch };
            const out: Record<string, any> = {};
            if (typeof rest.name === 'string') { out.name = rest.name; delete rest.name; }
            if (Object.keys(rest).length) out.properties = rest;
            return out;
        }

        async _refreshWorld() {
            try {
                if (typeof worldState !== 'undefined' && worldState?.fetch) {
                    await worldState.fetch();
                }
            } catch (e) { /* world refresh failure must not fail the apply */ }
        }
    }

    return { StagingBuffer };
})();


// NOTE: these shape declarations sit AFTER the first value statement on purpose.
// A leading `interface`/`type` makes TypeScript drop the file's leading JSDoc
// block from the emitted .js, and tools/js_module_index.py reads the `@module`
// tag out of that emitted .js.

/**
 * An op payload is free-form JSON produced by the NL editor (node/edge/patch
 * shapes, library refs, spawn targets). Its keys are read by name throughout
 * `apply`, so the honest type here is an open record rather than a guess at a
 * closed union.
 */
type StagedOpPayload = Record<string, any>;

interface StagedOp {
    id: string;
    type: string;
    payload: StagedOpPayload;
    summary: string;
    timestamp: number;
    updatedAt?: number;
}

interface StagedEdge {
    source: unknown;
    target: unknown;
    type: string;
    properties: unknown;
    staged?: boolean;
}
