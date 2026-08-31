/**
 * staging.js — Staging buffer for Natural-Language Editor (task-387).
 *
 * Buffers graph operations locally until the user approves and applies them.
 * No live graph changes happen until explicit Apply.
 */

window.NLEditorStaging = (() => {
    'use strict';

    class StagingBuffer {
        constructor() {
            this.ops = [];
            this.listeners = [];
        }

        onChange(callback) {
            this.listeners.push(callback);
        }

        _notify() {
            for (const cb of this.listeners) {
                try { cb(this.ops); } catch (e) { console.error('Staging listener error:', e); }
            }
        }

        /** Generate a deterministic, unique node ID */
        mintId(kind, name) {
            const cleanKind = (kind || 'item').toLowerCase().trim();
            const cleanName = (name || 'entity').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'node';
            const randSuffix = Math.random().toString(36).substring(2, 6);
            return `${cleanKind}_${cleanName}_${randSuffix}`;
        }

        /** Mint an operation ID */
        _mintOpId() {
            return `op_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
        }

        /** Add an operation to the staging buffer */
        addOp(type, payload, summary) {
            const op = {
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
        removeOp(opId) {
            const initialLen = this.ops.length;
            this.ops = this.ops.filter(op => op.id !== opId);
            if (this.ops.length !== initialLen) {
                this._notify();
                return true;
            }
            return false;
        }

        /** Replace an op's payload in place (inline tweaker). */
        updateOp(opId, payload) {
            const op = this.ops.find(o => o.id === opId);
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
        getStagedCreations() {
            const creations = {};
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
            const deletions = new Set();
            for (const op of this.ops) {
                if (op.type === 'delete_node' && op.payload.node_id) {
                    deletions.add(op.payload.node_id.toLowerCase());
                }
            }
            return deletions;
        }

        /** Get map of staged patches: id -> merged properties patch */
        getStagedUpdates() {
            const updates = {};
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
            const edges = [];
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
        async apply(opFilter = null) {
            const targets = opFilter ? this.ops.filter(o => opFilter.has(o.id)) : this.ops;
            if (targets.length === 0) return { success: true, appliedCount: 0 };

            const opsPayload = targets.map(op => ({ type: op.type, payload: op.payload }));
            let batch;
            try {
                batch = await ApiClient.post('/api/graph/batch', { ops: opsPayload });
            } catch (e) {
                batch = null;
            }
            if (batch && typeof batch.status === 'string') {
                await this._refreshWorld();
                const errs = (batch.errors || []).map(er => {
                    if (typeof er === 'string') return er;
                    const label = er.type || 'op';
                    const name = targets[er.index]?.summary || `#${er.index}`;
                    return `${name} (${label}): ${er.error}`;
                });
                this._clearApplied(opFilter);
                this._notify();
                return {
                    success: batch.status === 'success',
                    appliedCount: (batch.applied || []).length,
                    errors: errs
                };
            }

            // ── Fallback: per-op replay (stale server, no atomic undo) ──
            const errors = [];
            let appliedCount = 0;

            const creates = targets.filter(o => o.type === 'create_node' || o.type === 'spawn_library_item' || o.type === 'connect_areas');
            const updates = targets.filter(o => o.type === 'update_node' || o.type === 'link_to_library');
            const edges = targets.filter(o => o.type === 'attach' || o.type === 'detach');
            const deletes = targets.filter(o => o.type === 'delete_node');
            const sortedOps = [...creates, ...updates, ...edges, ...deletes];

            for (const op of sortedOps) {
                try {
                    switch (op.type) {
                        case 'create_node': {
                            const nodeData = op.payload.node || op.payload;
                            const res = await ApiClient.createNode({
                                id: nodeData.id,
                                type: nodeData.type || nodeData.kind || 'item',
                                name: nodeData.name,
                                properties: nodeData.properties || {}
                            });
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedCount++;
                            break;
                        }
                        case 'spawn_library_item': {
                            const p = op.payload;
                            const parentNode = (typeof worldState?.getNode === 'function' ? worldState.getNode(p.parent_id) : null)
                                || (typeof worldState?.getNodeByIdentifier === 'function' ? worldState.getNodeByIdentifier(p.parent_id) : null);
                            let target;
                            if (parentNode?.type === 'area') target = { type: 'area', name: parentNode.name };
                            else if (parentNode?.type === 'character') target = { type: 'character', id: parentNode.id };
                            else if (parentNode?.type === 'item') target = { type: 'container', id: parentNode.id };
                            else target = { type: 'area', name: p.parent_id };
                            const res = await ApiClient.placeItemFromLibrary(target, p.library_id);
                            // custom rename (place route has no rename)
                            if (!res?.error && p.rename && res?.node_id) {
                                await ApiClient.updateNode(res.node_id, { name: p.rename });
                            }
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedCount++;
                            break;
                        }
                        case 'connect_areas': {
                            const p = op.payload;
                            const wayRes = await ApiClient.createNode({
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
                            await ApiClient.createEdge(p.area_a_id, p.way_id, 'connection', { direction: dirA, visible_in_direction: '' });
                            await ApiClient.createEdge(p.way_id, p.area_b_id, 'connection', { direction: dirB });
                            await ApiClient.createEdge(p.area_b_id, p.way_id, 'connection', { direction: dirB, visible_in_direction: '' });
                            await ApiClient.createEdge(p.way_id, p.area_a_id, 'connection', { direction: dirA });
                            appliedCount++;
                            break;
                        }
                        case 'update_node': {
                            const p = op.payload;
                            const patch = this._nodePatch(p.patch || {});
                            const ok = await ApiClient.updateNode(p.node_id, patch);
                            if (!ok) errors.push(`${op.summary}: node update rejected`);
                            else appliedCount++;
                            break;
                        }
                        case 'link_to_library': {
                            const p = op.payload;
                            const ok = await ApiClient.updateNode(p.node_id, { properties: { template_id: p.library_id } });
                            if (!ok) errors.push(`${op.summary}: link rejected`);
                            else appliedCount++;
                            break;
                        }
                        case 'attach': {
                            const p = op.payload;
                            const res = await ApiClient.createEdge(p.from_id, p.to_id, p.relation || 'in', p.properties || {});
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedCount++;
                            break;
                        }
                        case 'detach': {
                            const p = op.payload;
                            const res = await ApiClient.deleteEdge(p.from_id, p.to_id, p.relation || 'in');
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedCount++;
                            break;
                        }
                        case 'delete_node': {
                            const p = op.payload;
                            const res = await ApiClient.deleteNode(p.node_id);
                            if (res?.error) errors.push(`${op.summary}: ${res.error}`);
                            else appliedCount++;
                            break;
                        }
                    }
                } catch (err) {
                    errors.push(`${op.summary}: ${err.message}`);
                }
            }

            await this._refreshWorld();
            this._clearApplied(opFilter);
            this._notify();
            return {
                success: errors.length === 0,
                appliedCount,
                errors
            };
        }

        /** Remove applied ops only; with a filter, keep the unchecked ones. */
        _clearApplied(opFilter) {
            if (opFilter) {
                this.ops = this.ops.filter(o => !opFilter.has(o.id));
            } else {
                this.ops = [];
            }
        }

        /** Wrap an NL-editor flat property patch for the PATCH route. */
        _nodePatch(patch) {
            if ('properties' in patch || 'name' in patch || 'id' in patch) return patch;
            return { properties: patch };
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
