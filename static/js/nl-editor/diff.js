"use strict";
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
 * @docs docs/virtualWorld/dev_tasks/done/graph/task-387-natural-language-editor-mode.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.NLEditorDiff = (() => {
    'use strict';
    const RESERVED = new Set(['properties', 'name', 'id', 'type', 'kind']);
    const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
    const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    /** The effective property map of a patch (nested `properties` + flat keys). */
    function patchProps(patch) {
        const props = {};
        if (!isObj(patch))
            return props;
        if (isObj(patch.properties))
            Object.assign(props, patch.properties);
        for (const [key, value] of Object.entries(patch)) {
            if (RESERVED.has(key))
                continue;
            props[key] = value;
        }
        return props;
    }
    /** Pre-state properties for a node: staged creation wins, else the live node. */
    function baseProps(nodeId, nodes, creations) {
        const key = String(nodeId || '').toLowerCase();
        const created = (creations || {})[key];
        if (isObj(created) && isObj(created.properties))
            return created.properties;
        const live = (nodes || {})[key];
        return isObj(live) && isObj(live.properties) ? live.properties : {};
    }
    /** Flatten one patch key into leaf changes (dicts are diffed key-by-key). */
    function diffPairs(key, before, after) {
        if (isObj(before) || isObj(after)) {
            const b = isObj(before) ? before : {};
            const a = isObj(after) ? after : {};
            const out = [];
            for (const sub of new Set([...Object.keys(b), ...Object.keys(a)])) {
                if (same(b[sub], a[sub]))
                    continue;
                out.push({ key: `${key}.${sub}`, before: b[sub], after: a[sub] });
            }
            return out;
        }
        if (same(before, after))
            return [];
        return [{ key, before, after }];
    }
    /** All leaf changes a patch makes to one node. */
    function nodeDiff(nodeId, patch, nodes, creations) {
        const before = baseProps(nodeId, nodes, creations);
        const changes = [];
        for (const [key, value] of Object.entries(patchProps(patch))) {
            changes.push(...diffPairs(key, before[key], value));
        }
        return changes;
    }
    /** Describe an op's effect: kind, target id(s), and leaf property changes. */
    function opDiff(op, context = {}) {
        const nodes = context.nodes || {};
        const creations = context.creations || {};
        const type = isObj(op) ? op.type : undefined;
        const payload = (isObj(op) && isObj(op.payload) ? op.payload : {});
        if (type === 'create_node' || type === 'create_character') {
            const node = (isObj(payload.node) ? payload.node : payload);
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
            const ids = (Array.isArray(payload.matched_ids) ? payload.matched_ids : []);
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
        if (type === 'update_player') {
            const charId = payload.character || payload.character_id || payload.name;
            return {
                kind: 'update-player',
                id: charId,
                changes: playerDiff(charId, payload.patch, context.players || {}, nodes),
            };
        }
        if (type === 'spawn_library_item') {
            return { kind: 'spawn', id: payload.library_id, target: payload.parent_id, changes: [] };
        }
        if (type === 'attach') {
            return { kind: 'attach', from: payload.from_id, to: payload.to_id, relation: payload.relation || 'in', changes: [] };
        }
        if (type === 'detach') {
            return { kind: 'detach', from: payload.from_id, to: payload.to_id, relation: payload.relation || 'in', changes: [] };
        }
        if (type === 'connect_areas') {
            return { kind: 'connect', from: payload.area_a_id, to: payload.area_b_id, way: payload.way_name || payload.way_id, changes: [] };
        }
        if (type === 'create_trigger') {
            const trig = isObj(payload.trigger) ? payload.trigger : {};
            return { kind: 'trigger', id: payload.owner_id, label: trig.trigger_type || 'trigger', changes: [] };
        }
        if (type === 'rename_character') {
            return { kind: 'rename', id: payload.character || payload.character_id, label: payload.new_name || payload.name, changes: [] };
        }
        return { kind: 'other', changes: [] };
    }
    /** Resolve a player record from context.players by name or player_<name> node id. */
    function resolvePlayerRecord(charId, players, nodes) {
        if (!isObj(players))
            return {};
        const rawKey = String(charId || '').trim();
        if (!rawKey)
            return {};
        if (isObj(players[rawKey]))
            return players[rawKey];
        const lower = rawKey.toLowerCase();
        const stripped = lower.startsWith('player_') ? lower.slice(7).replace(/_/g, ' ') : lower;
        for (const [k, v] of Object.entries(players)) {
            if (!isObj(v))
                continue;
            const kLow = k.toLowerCase();
            const vName = String(v.name || '').toLowerCase();
            if (kLow === lower || kLow === stripped || vName === lower || vName === stripped) {
                return v;
            }
        }
        const node = (nodes || {})[lower];
        if (isObj(node) && typeof node.name === 'string' && isObj(players[node.name])) {
            return players[node.name];
        }
        return {};
    }
    /** Field-level diff for an update_player patch (schedule, goals, obligations, memories, relationship, emotion). */
    function playerDiff(charId, patch, players, nodes) {
        if (!isObj(patch))
            return [];
        const before = resolvePlayerRecord(charId, players, nodes);
        const changes = [];
        for (const [key, value] of Object.entries(patch)) {
            if (key === 'relationship' && isObj(value)) {
                const target = String(value.target || '?');
                const rels = isObj(before.relationships) ? before.relationships : {};
                const prevRel = isObj(rels[target]) ? rels[target] : undefined;
                changes.push({ key: `relationship.${target}`, before: prevRel?.closeness, after: value.closeness });
            }
            else if (key === 'remove_relationship') {
                const target = String(value || '?');
                const rels = isObj(before.relationships) ? before.relationships : {};
                changes.push({ key: `relationship.${target}`, before: rels[target] ?? 'linked', after: undefined });
            }
            else if (key === 'emotion' && isObj(value)) {
                const dim = String(value.name || '?');
                const emos = isObj(before.emotions) ? before.emotions : {};
                changes.push({ key: `emotion.${dim}`, before: emos[dim], after: `+${value.delta ?? 0}` });
            }
            else {
                const prev = before[key];
                if (!same(prev, value)) {
                    changes.push({ key, before: prev, after: value });
                }
            }
        }
        return changes;
    }
    function formatValue(value) {
        if (value === undefined)
            return '—';
        if (value === null)
            return 'null';
        if (typeof value === 'string')
            return value.length > 40 ? `${value.slice(0, 37)}…` : value;
        if (typeof value === 'object') {
            const text = JSON.stringify(value);
            return text.length > 40 ? `${text.slice(0, 37)}…` : text;
        }
        return String(value);
    }
    function formatChanges(changes) {
        return (changes || []).map(c => `${c.key}: ${formatValue(c.before)} → ${formatValue(c.after)}`);
    }
    /** Flat preview lines for the staged tray, capped at *limit* leaf changes. */
    function summaryLines(op, context = {}, limit = 4) {
        const diff = opDiff(op, context);
        if (diff.kind === 'create')
            return [`+ create ${diff.id || 'node'}`];
        if (diff.kind === 'delete')
            return [`− delete ${diff.id || 'node'}`];
        if (diff.kind === 'library')
            return [`library ${diff.registry || '?'}: upsert ${diff.id || '?'}`];
        if (diff.kind === 'library-delete')
            return [`library ${diff.registry || '?'}: delete ${diff.id || '?'}`];
        if (diff.kind === 'spawn')
            return [`+ spawn ${diff.id || 'item'} into ${diff.target || 'area'}`];
        if (diff.kind === 'attach')
            return [`+ attach ${diff.from || '?'} -> ${diff.to || '?'} (${diff.relation || 'in'})`];
        if (diff.kind === 'detach')
            return [`− detach ${diff.from || '?'} from ${diff.to || '?'} (${diff.relation || 'in'})`];
        if (diff.kind === 'connect')
            return [`+ connect ${diff.from || '?'} <-> ${diff.to || '?'} via ${diff.way || 'way'}`];
        if (diff.kind === 'trigger')
            return [`+ trigger (${diff.label || '?'}) on ${diff.id || 'node'}`];
        if (diff.kind === 'rename')
            return [`rename ${diff.id || 'character'} -> ${diff.label || '?'}`];
        let changes;
        if (diff.kind === 'bulk') {
            changes = [];
            for (const target of diff.targets || []) {
                changes.push(...formatChanges(target.changes).map(text => `${target.id}: ${text}`));
            }
        }
        else {
            changes = formatChanges(diff.changes);
        }
        if (!changes.length)
            return ['(no property change — will no-op)'];
        if (changes.length <= limit)
            return changes;
        return [...changes.slice(0, limit), `+${changes.length - limit} more`];
    }
    return { opDiff, diffPairs, nodeDiff, playerDiff, patchProps, baseProps, formatChanges, formatValue, summaryLines };
})();
