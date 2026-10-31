"use strict";
/**
 * trigger-def.js - Pure trigger definition converters and normalizer.
 *
 * Provides pure conversions between engine trigger definitions and graph
 * representation, with zero DOM or visual dependencies:
 *   - normalizeConditions() - single canonical normalizer for condition trees
 *   - triggerToGraph() / triggersToGraph() - layout definitions into graph nodes and wires
 *   - compileToTriggers() / compileToEngine() - compile graph nodes and wires back to definitions
 *   - triggerDefFromEdge() / triggersFromGraphEdges() - extract definitions from graph edges
 *
 * @module shared/trigger-def - trigger definition converters
 * @contributes TriggerDef.normalizeConditions + triggerToGraph + compileToTriggers + triggerDefFromEdge
 * @powers pure trigger compilation and round-trip conversion without DOM dependencies
 * @relates shared/trigger-graph.js re-exports these onto TriggerGraph
 * @docs docs/virtualWorld/Rules Engine/Triggers & Effects.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
globalThis.TriggerDef = (() => {
    'use strict';
    // ─── Condition Normalization & Flattening (task-901) ───
    /**
     * Canonical condition tree normalizer.
     * Converts raw condition shapes (bare condition, array of leaves, nested logic tree)
     * into a standard logical tree shape: { operator: 'and'|'or'|'not', conditions: [...] }
     * or {} when empty.
     */
    function normalizeConditions(raw, defaultLogic = 'and') {
        if (!raw)
            return {};
        // Bare condition leaf without operator wrapper
        if (typeof raw === 'object' && !Array.isArray(raw) && !raw.operator && raw.type) {
            return { operator: defaultLogic || 'and', conditions: [raw] };
        }
        // Array of conditions
        if (Array.isArray(raw)) {
            if (!raw.length)
                return {};
            return { operator: defaultLogic || 'and', conditions: raw };
        }
        // Logical group node ({ operator, conditions }) or envelope ({ conditions })
        if (typeof raw === 'object' && raw.conditions && Array.isArray(raw.conditions)) {
            const op = raw.operator ? String(raw.operator).toLowerCase() : (defaultLogic || 'and');
            if (!raw.conditions.length)
                return {};
            return { operator: op, conditions: raw.conditions };
        }
        if (typeof raw === 'object' && raw.operator) {
            const op = String(raw.operator).toLowerCase();
            const children = Array.isArray(raw.conditions) ? raw.conditions : [];
            if (!children.length)
                return {};
            return { operator: op, conditions: children };
        }
        return {};
    }
    /** True when a tree is just a flat AND of leaf conditions (or a bare leaf list). */
    function treeIsFlat(tree) {
        if (!tree || typeof tree !== 'object')
            return true;
        if (Array.isArray(tree))
            return tree.every((c) => treeIsFlat(c));
        if (tree.operator) {
            if (tree.operator !== 'and')
                return false;
            return (tree.conditions || []).every((c) => treeIsFlat(c));
        }
        return true;
    }
    /** Flatten an engine condition tree to its leaf conditions in order. */
    function flattenConditions(tree) {
        if (!tree)
            return [];
        if (Array.isArray(tree))
            return tree.flatMap((c) => flattenConditions(c));
        if (typeof tree !== 'object')
            return [];
        if (tree.operator)
            return (tree.conditions || []).flatMap((c) => flattenConditions(c));
        return [tree];
    }
    function conditionToGraphProps(cond) {
        if (!cond || !cond.type)
            return { condition_type: 'skill_check', skill: 'Athletics', dc: 10 };
        const t = cond.type;
        const props = { condition_type: t };
        const numeric = ['area_temp', 'vital', 'vital_above', 'vital_below', 'uses_reached', 'uses_above', 'temperature_below', 'temperature_above'];
        if (['skill_check', 'save_throw'].includes(t)) {
            props.dc = cond.dc || (t === 'save_throw' ? 12 : 10);
            if (cond.skill)
                props.skill = cond.skill;
            if (cond.stat)
                props.skill = cond.stat;
        }
        if (numeric.includes(t))
            props.operator = cond.operator || 'lt';
        if (t === 'eq') {
            if (cond.target)
                props.target = cond.target;
            if (cond.value != null)
                props.value = String(cond.value);
        }
        else if (t === 'in_area') {
            if (cond.area)
                props.area = cond.area;
            if (cond.target)
                props.target = cond.target;
        }
        else if (t === 'tick_since_state')
            props.min_ticks = cond.min_ticks ?? 0;
        else if (t === 'proximity')
            props.max_areas = cond.max_areas ?? 0;
        else if (t === 'has_item') {
            if (cond.item)
                props.item = cond.item;
            if (cond.target)
                props.target = cond.target;
        }
        else if (t === 'has_trait' || t === 'has_tag') {
            if (cond.value != null)
                props.value = String(cond.value);
        }
        else if (t === 'area_has_status') {
            if (cond.status_type)
                props.status_type = cond.status_type;
            if (cond.target)
                props.target = cond.target;
        }
        else if (t === 'item_relationship') {
            if (cond.relation)
                props.relation = cond.relation;
            if (cond.direction)
                props.direction = cond.direction;
            if (cond.target)
                props.target = cond.target;
        }
        else if (t === 'npc_emotion_is') {
            if (cond.emotion)
                props.emotion = cond.emotion;
            if (cond.operator)
                props.operator = cond.operator;
            if (cond.value != null)
                props.value = String(cond.value);
        }
        else if (t === 'npc_is_hidden') {
            props.value = String(cond.value !== false);
        }
        else if (t === 'character_has_tag') {
            if (cond.tag)
                props.tag = cond.tag;
            if (cond.target)
                props.target = cond.target;
        }
        else {
            if (cond.value != null)
                props.value = String(cond.value);
            if (cond.target)
                props.target = cond.target;
        }
        return props;
    }
    function buildConditionFromNode(node) {
        const cond = { type: node.props.condition_type || 'skill_check' };
        const p = node.props;
        if (cond.type === 'skill_check') {
            cond.skill = p.skill || 'Athletics';
            cond.dc = parseInt(p.dc) || 10;
        }
        else if (cond.type === 'save_throw') {
            cond.stat = p.skill || 'DEX';
            cond.dc = parseInt(p.dc) || 12;
            cond.target = p.target || 'self';
        }
        else if (cond.type === 'state_equals') {
            cond.target = p.target || 'self';
            cond.value = p.value || '';
        }
        else if (cond.type === 'eq') {
            cond.target = p.target || 'npc_state';
            cond.value = p.value || '';
        }
        else if (cond.type === 'in_area') {
            cond.area = p.area || '';
            cond.target = p.target || 'npc';
        }
        else if (cond.type === 'tick_since_state') {
            cond.min_ticks = parseInt(p.min_ticks) || 0;
        }
        else if (cond.type === 'proximity') {
            cond.max_areas = parseInt(p.max_areas) || 0;
        }
        else if (cond.type === 'random_chance') {
            cond.chance = p.chance !== undefined ? parseFloat(p.chance) : (p.value !== undefined && p.value !== '' ? parseFloat(p.value) : 0.5);
        }
        else if (['area_temp', 'vital', 'vital_above', 'vital_below'].includes(cond.type)) {
            cond.operator = p.operator || 'lt';
            cond.value = p.value !== undefined && p.value !== '' ? p.value : '';
            if (p.stat)
                cond.stat = p.stat;
            if (p.target)
                cond.target = p.target;
        }
        else if (cond.type === 'is_equipped') {
            cond.item = p.item || p.value || '';
            if (p.target)
                cond.target = p.target;
        }
        else if (cond.type === 'area_has_status') {
            cond.status_type = p.status_type || p.value || '';
            if (p.target)
                cond.target = p.target;
        }
        else if (cond.type === 'item_relationship') {
            cond.relation = p.relation || 'in';
            if (p.direction)
                cond.direction = p.direction;
            if (p.target)
                cond.target = p.target;
        }
        else if (cond.type === 'npc_emotion_is') {
            cond.emotion = p.emotion || '';
            cond.operator = p.operator || 'eq';
            if (p.value !== undefined && p.value !== '')
                cond.value = p.value;
        }
        else if (cond.type === 'npc_is_hidden') {
            cond.value = (p.value === true || p.value === 'true');
        }
        else if (cond.type === 'character_has_tag') {
            cond.tag = p.tag || p.value || '';
            cond.target = p.target || 'self';
        }
        else {
            if (p.value !== undefined && p.value !== '')
                cond.value = p.value;
            if (p.target)
                cond.target = p.target;
            if (p.skill)
                cond.skill = p.skill;
            if (p.dc)
                cond.dc = parseInt(p.dc);
            if (p.item)
                cond.item = p.item;
            if (p.operator)
                cond.operator = p.operator;
            if (p.stat)
                cond.stat = p.stat;
        }
        return cond;
    }
    function _outWires(wires, nodeId, ...sockets) {
        return (wires || []).filter((w) => w && w.from && w.from[0] === nodeId && sockets.includes(w.from[1]));
    }
    function _normalizeEffectParams(type, params) {
        const p = { ...params };
        delete p.effect_type;
        ['symptoms', 'extra_conditions', 'succ_json', 'fail_json'].forEach(k => {
            if (typeof p[k] === 'string') {
                const s = p[k].trim();
                if (!s) {
                    delete p[k];
                    return;
                }
                try {
                    p[k] = JSON.parse(s);
                }
                catch (e) {
                    delete p[k];
                }
            }
        });
        if (type === 'save') {
            const branch = (side) => {
                if (Array.isArray(p[side === 'succ' ? 'on_success' : 'on_fail']) && p[side + '_json'] === undefined && p[side + '_type'] === undefined) {
                    return p[side === 'succ' ? 'on_success' : 'on_fail'];
                }
                const j = typeof p[side + '_json'] === 'object' ? p[side + '_json'] : undefined;
                if (Array.isArray(j))
                    return j;
                const t = p[side + '_type'] || 'none';
                if (t === 'none')
                    return [];
                if (t === 'message')
                    return p[side + '_msg'] ? [{ type: 'message', params: { message: p[side + '_msg'] } }] : [];
                if (t === 'apply_condition') {
                    const bp = { condition: p[side + '_cond'] || '', target: 'self' };
                    if (p[side + '_dur'] !== undefined && p[side + '_dur'] !== '')
                        bp.duration = parseInt(p[side + '_dur']) || 0;
                    if (p[side + '_src'])
                        bp.source = p[side + '_src'];
                    if (p[side + '_src_type'])
                        bp.source_type = p[side + '_src_type'];
                    return [{ type: 'apply_condition', params: bp }];
                }
                if (t === 'damage')
                    return [{ type: 'damage', params: { amount: parseInt(p[side + '_dmg']) || 5, target: 'self' } }];
                return [];
            };
            const out = { dc: parseInt(p.save_dc) || 12, on_success: branch('succ'), on_fail: branch('fail') };
            if (p.save_mode === 'skill')
                out.skill = p.save_skill || 'Athletics';
            else
                out.stat = p.save_stat || 'WIS';
            if (p.save_dc === undefined && Array.isArray(p.on_success)) {
                return { ...p };
            }
            return out;
        }
        if (type === 'apply_condition' || type === 'remove_condition') {
            const by = p.target_by;
            if (!by || by === 'self') {
                p.target = 'self';
                delete p.target_by;
                delete p.target_value;
            }
            else if (by === 'all_in_area') {
                delete p.target_value;
                delete p.target;
            }
            else {
                p.target_value = p.target_value ?? p.target ?? '';
                delete p.target;
            }
        }
        if (type === 'set_hidden' || type === 'set_way_view') {
            if (p.hidden !== undefined)
                p.hidden = (p.hidden === true || p.hidden === 'true');
            if (p.see_through !== undefined)
                p.see_through = (p.see_through === true || p.see_through === 'true');
        }
        if (type === 'apply_trait' && (p.param === 'true' || p.param === 'false' || p.param === '')) {
            p.param = p.param === 'false' ? false : true;
        }
        if (type === 'spawn_item' && p.into === 'area')
            delete p.into;
        Object.keys(p).forEach(k => { if (p[k] === '' || p[k] === undefined)
            delete p[k]; });
        return p;
    }
    function _traceGroupCondition(nodeId, wires, nodes, seen) {
        if (!seen)
            seen = new Set();
        const node = nodes.find((n) => n.id === nodeId);
        const op = (node && node.props && node.props.operator) || 'and';
        const children = [];
        const cw = wires.find((w) => w.from[0] === nodeId && w.from[1] === 'child');
        let cur = cw ? cw.to[0] : null;
        while (cur && !seen.has(cur)) {
            seen.add(cur);
            const cn = nodes.find((n) => n.id === cur);
            if (!cn)
                break;
            if (cn.type === 'group')
                children.push(_traceGroupCondition(cur, wires, nodes, seen));
            else if (cn.type === 'condition')
                children.push(buildConditionFromNode(cn));
            else
                break;
            const nw = wires.find(w => w.from[0] === cur && w.from[1] === 'output_yes');
            cur = nw ? nw.to[0] : null;
        }
        return { operator: op, conditions: children };
    }
    function _traceGraph(nodeId, wires, nodes, seen) {
        const empty = { effects: [], conditions: [], fail_message: '', problems: [] };
        if (!seen)
            seen = new Set();
        if (seen.has(nodeId)) {
            return { ...empty, problems: ['Cycle detected in the graph; the loop was not followed.'] };
        }
        seen.add(nodeId);
        const node = nodes.find((n) => n.id === nodeId);
        if (!node)
            return empty;
        if (node.type === 'condition') {
            const conds = [buildConditionFromNode(node)];
            const label = conds[0]?.type || 'condition';
            const yesOuts = _outWires(wires, nodeId, 'output_yes');
            const yesBranches = yesOuts.map((w) => _traceGraph(w.to[0], wires, nodes, new Set(seen)));
            const ye = {
                effects: yesBranches.flatMap((b) => b.effects),
                conditions: yesBranches.flatMap((b) => b.conditions),
                fail_message: yesBranches.map((b) => b.fail_message).find(Boolean) || '',
                problems: yesBranches.flatMap((b) => b.problems)
            };
            let failMessage = '';
            const problems = [...ye.problems];
            const noOuts = _outWires(wires, nodeId, 'output_no');
            if (noOuts.length) {
                let kept = '';
                for (const w of noOuts) {
                    const ne = _traceGraph(w.to[0], wires, nodes, new Set(seen));
                    const msgs = ne.effects.filter((e) => e.type === 'message');
                    if (ne.conditions.length) {
                        problems.push(`Condition "${label}" NO branch chains another condition; the engine supports only a single NO message.`);
                    }
                    if (ne.effects.length === 1 && msgs.length === 1 && msgs[0].params?.message) {
                        if (!kept)
                            kept = msgs[0].params.message;
                        else
                            problems.push(`Condition "${label}" has ${noOuts.length} NO branches; only one NO message is compiled.`);
                    }
                    else if (ne.effects.length > 0) {
                        problems.push(`Condition "${label}" NO branch has ${ne.effects.length} effect(s); the engine supports only a single NO message.`);
                    }
                    problems.push(...ne.problems);
                }
                failMessage = kept;
            }
            return {
                effects: ye.effects,
                conditions: [...conds, ...ye.conditions],
                fail_message: failMessage || ye.fail_message || '',
                problems,
            };
        }
        if (node.type === 'group') {
            const groupCond = _traceGroupCondition(nodeId, wires, nodes);
            const label = groupCond.operator;
            const noOuts = _outWires(wires, nodeId, 'output_no');
            let failMessage = '';
            const problems = [];
            if (noOuts.length) {
                for (const w of noOuts) {
                    const ne = _traceGraph(w.to[0], wires, nodes, new Set(seen));
                    const msgs = ne.effects.filter((e) => e.type === 'message');
                    if (ne.conditions.length) {
                        problems.push(`Group "${label}" NO branch chains another condition; the engine supports only a single NO message.`);
                    }
                    if (ne.effects.length === 1 && msgs.length === 1 && msgs[0].params?.message) {
                        if (!failMessage)
                            failMessage = msgs[0].params.message;
                        else
                            problems.push(`Group "${label}" has ${noOuts.length} NO branches; only one NO message is compiled.`);
                    }
                    else if (ne.effects.length > 0) {
                        problems.push(`Group "${label}" NO branch has ${ne.effects.length} effect(s); the engine supports only a single NO message.`);
                    }
                    problems.push(...ne.problems);
                }
            }
            const yesOuts = _outWires(wires, nodeId, 'output_yes');
            const yesBranches = yesOuts.map((w) => _traceGraph(w.to[0], wires, nodes, new Set(seen)));
            return {
                effects: yesBranches.flatMap((b) => b.effects),
                conditions: [groupCond, ...yesBranches.flatMap((b) => b.conditions)],
                fail_message: failMessage || yesBranches.map((b) => b.fail_message).find(Boolean) || '',
                problems: problems.concat(yesBranches.flatMap((b) => b.problems)),
            };
        }
        if (node.type === 'effect') {
            const eff = { type: node.props.effect_type || 'message', params: _normalizeEffectParams(node.props.effect_type || 'message', node.props) };
            const next = _outWires(wires, nodeId, 'output', 'right')
                .map((w) => _traceGraph(w.to[0], wires, nodes, new Set(seen)));
            return {
                effects: [eff, ...next.flatMap((b) => b.effects)],
                conditions: next.flatMap((b) => b.conditions),
                fail_message: next.map((b) => b.fail_message).find(Boolean) || '',
                problems: next.flatMap((b) => b.problems),
            };
        }
        return empty;
    }
    const TRIGGER_STATE_KEYS = ['id', 'name', 'once', 'fired', 'cooldown', 'success_message', 'target_name', 'target_state'];
    function _carriedTriggerState(props) {
        const out = {};
        for (const key of TRIGGER_STATE_KEYS) {
            const value = props[key];
            if (value !== undefined && value !== null && value !== '')
                out[key] = value;
        }
        return out;
    }
    /** Compile one trigger root node and everything attached into a single definition. */
    function compileRoot(triggerNode, graph) {
        const props = triggerNode.props || {};
        const tt = props.trigger_type || 'on_use';
        const carried = _carriedTriggerState(props);
        const tw = (graph.wires || []).find((w) => w.from[0] === triggerNode.id && (w.from[1] === 'output' || w.from[1] === 'right'));
        if (!tw) {
            const empty = { ...carried, trigger_type: tt, effects: [{ type: 'message', params: { message: '' } }], conditions: {} };
            empty.target_name = props.target_tag || '';
            empty.target_state = props.target_state || '';
            return empty;
        }
        const traced = _traceGraph(tw.to[0], graph.wires, graph.nodes);
        const problems = [...(traced.problems || [])];
        const condTree = normalizeConditions(traced.conditions.length === 1 && traced.conditions[0]?.operator
            ? traced.conditions[0]
            : traced.conditions);
        const result = {
            ...carried,
            trigger_type: tt,
            effects: traced.effects.length ? traced.effects : [{ type: 'message', params: { message: '' } }],
            conditions: condTree,
        };
        result.target_name = props.target_tag || '';
        result.target_state = props.target_state || '';
        if (traced.fail_message)
            result.fail_message = traced.fail_message;
        if (problems.length)
            result.compile_error = problems.join(' ');
        return result;
    }
    /** Compile every trigger root in the graph in visual order. */
    function compileToTriggers(graph) {
        if (!graph?.nodes)
            return [];
        return graph.nodes
            .filter((n) => n.type === 'trigger')
            .map((n) => compileRoot(n, graph));
    }
    /** The first trigger root's definition, for single-trigger callers. */
    function compileToEngine(graph) {
        const all = compileToTriggers(graph);
        return all.length ? all[0] : null;
    }
    /** Lay one trigger definition out as a graph block. */
    function triggerToGraph(triggerDef, opts) {
        const t = triggerDef || {};
        const prefix = (opts && opts.idPrefix) || '';
        const x0 = (opts && opts.xOffset) || 0;
        const y0 = (opts && opts.yOffset) || 0;
        const nodes = [];
        const wires = [];
        let nextNodeSeq = 0;
        const nodeId = () => `${prefix}n${nextNodeSeq++}`;
        const wireId = () => `${prefix}w${wires.length}`;
        const types = Array.isArray(t.trigger_type) ? t.trigger_type : [t.trigger_type || 'on_use'];
        const tnode = nodeId();
        const triggerProps = {
            trigger_type: types,
            target_tag: t.target_name || t.target_tag || '',
            target_state: t.target_state || '',
        };
        if (t.id)
            triggerProps.id = t.id;
        if (t.name)
            triggerProps.name = t.name;
        if (t.once !== undefined)
            triggerProps.once = !!t.once;
        if (t.fired !== undefined)
            triggerProps.fired = !!t.fired;
        if (t.cooldown !== undefined && t.cooldown !== '')
            triggerProps.cooldown = t.cooldown;
        if (t.success_message)
            triggerProps.success_message = t.success_message;
        nodes.push({ id: tnode, type: 'trigger', x: x0 + 50, y: y0 + 50, props: triggerProps });
        // Normalize conditions through the single normalization function (task-901)
        const normalized = normalizeConditions(t.conditions);
        let topEntries;
        if (treeIsFlat(normalized)) {
            topEntries = flattenConditions(normalized);
        }
        else if (normalized.operator === 'and') {
            topEntries = normalized.conditions || [];
        }
        else if (normalized.operator) {
            topEntries = [normalized];
        }
        else {
            topEntries = [];
        }
        const layoutEntry = (entry, from, x, y) => {
            if (entry && typeof entry === 'object' && !Array.isArray(entry) && entry.operator) {
                const gnode = nodeId();
                nodes.push({ id: gnode, type: 'group', x, y, props: { operator: entry.operator } });
                wires.push({ id: wireId(), from, to: [gnode, 'input'] });
                let childFrom = [gnode, 'child'];
                (entry.conditions || []).forEach((c, i) => {
                    childFrom = layoutEntry(c, childFrom, x + 240, y + 40 + i * 120);
                });
                return [gnode, 'output_yes'];
            }
            const cnode = nodeId();
            nodes.push({ id: cnode, type: 'condition', x, y, props: conditionToGraphProps(entry) });
            wires.push({ id: wireId(), from, to: [cnode, 'input'] });
            return [cnode, 'output_yes'];
        };
        const effects = t.effects || [];
        let attachFrom = [tnode, 'output'];
        let lastCond = null;
        topEntries.forEach((c, i) => {
            attachFrom = layoutEntry(c, attachFrom, x0 + 50, y0 + 180 + i * 120);
            lastCond = attachFrom[0];
        });
        for (let i = 0; i < effects.length; i++) {
            const eff = effects[i];
            const enode = nodeId();
            nodes.push({
                id: enode, type: 'effect',
                x: x0 + 50 + (topEntries.length ? 220 : 0),
                y: y0 + 180 + i * 120,
                props: { effect_type: eff.type || 'message', ...(eff.params || {}) },
            });
            wires.push({ id: wireId(), from: attachFrom, to: [enode, 'input'] });
            if (effects.length > 1 && i < effects.length - 1) {
                attachFrom = [enode, 'output'];
            }
        }
        if (t.fail_message && lastCond) {
            const fnode = nodeId();
            nodes.push({
                id: fnode, type: 'effect', x: x0 + 330, y: y0 + 180 + topEntries.length * 120,
                props: { effect_type: 'message', message: t.fail_message },
            });
            wires.push({ id: wireId(), from: [lastCond, 'output_no'], to: [fnode, 'input'] });
        }
        return { nodes, wires };
    }
    /** Lay every definition on one diagram, one block per trigger. */
    function triggersToGraph(triggerDefs) {
        const defs = Array.isArray(triggerDefs) ? triggerDefs : [];
        const nodes = [];
        const wires = [];
        let y = 0;
        defs.forEach((def, i) => {
            const block = triggerToGraph(def, { idPrefix: `t${i}_`, yOffset: y });
            nodes.push(...block.nodes);
            wires.push(...block.wires);
            const lowest = block.nodes.reduce((m, n) => Math.max(m, n.y), y);
            y = lowest + 240;
        });
        return { nodes, wires };
    }
    function engineToFormData(compiled) {
        if (!compiled) {
            return {
                effects: [{ type: 'message', params: {} }],
                conditions: {},
            };
        }
        return {
            trigger_type: compiled.trigger_type,
            effects: compiled.effects || [{ type: 'message', params: {} }],
            conditions: compiled.conditions || {},
            target_name: compiled.target_name || '',
            target_state: compiled.target_state || '',
            fail_message: compiled.fail_message || '',
        };
    }
    const TRIGGER_FIELDS = ['id', 'name', 'trigger_type', 'effects', 'effect_type',
        'effect_params', 'condition', 'conditions', 'conditions_logic', 'target_name',
        'target_tag', 'target_state', 'success_message', 'fail_message', 'once',
        'fired', 'cooldown'];
    function _looksLikeTrigger(value) {
        return !!value && typeof value === 'object' && !Array.isArray(value)
            && TRIGGER_FIELDS.some((key) => key in value);
    }
    function _unwrapSingleKey(value, scalar) {
        for (let i = 0; i < 8; i++) {
            if (!value || typeof value !== 'object' || Array.isArray(value))
                return value;
            const keys = Object.keys(value);
            if (keys.length !== 1 || _looksLikeTrigger(value))
                return value;
            const inner = value[keys[0]];
            if (!scalar && !(inner && typeof inner === 'object'))
                return value;
            value = inner;
        }
        return value;
    }
    function normalizeTriggerEntry(entry) {
        const unwrapped = _unwrapSingleKey(entry);
        if (!unwrapped || typeof unwrapped !== 'object' || Array.isArray(unwrapped))
            return null;
        const out = { ...unwrapped };
        for (const key of ['trigger_type', 'effects', 'conditions', 'condition']) {
            if (out[key] && typeof out[key] === 'object' && !Array.isArray(out[key])) {
                out[key] = _unwrapSingleKey(out[key], true);
            }
        }
        let effects = out.effects;
        if (effects && typeof effects === 'object' && !Array.isArray(effects))
            effects = [effects];
        if (Array.isArray(effects)) {
            const fixed = effects
                .map((effect) => _unwrapSingleKey(effect))
                .filter((effect) => effect && typeof effect === 'object' && !Array.isArray(effect) && effect.type);
            if (fixed.length)
                out.effects = fixed;
            else
                delete out.effects;
        }
        if (out.conditions === '' || out.conditions === null)
            delete out.conditions;
        return out;
    }
    function normalizeTriggerList(value) {
        if (value === undefined || value === null)
            return [];
        const unwrapped = _unwrapSingleKey(value);
        const raw = Array.isArray(unwrapped) ? unwrapped : (Array.isArray(value) ? value : [unwrapped]);
        return raw
            .map((entry) => normalizeTriggerEntry(entry))
            .filter((entry) => !!entry);
    }
    function _nodeById(nodes, id) {
        if (!nodes || id === undefined || id === null)
            return null;
        const wanted = String(id).toLowerCase();
        if (Array.isArray(nodes)) {
            return nodes.find((n) => n && String(n.id).toLowerCase() === wanted) || null;
        }
        if (nodes[id])
            return nodes[id];
        for (const key of Object.keys(nodes)) {
            if (key.toLowerCase() === wanted)
                return nodes[key];
        }
        return null;
    }
    function triggerDefFromEdge(edge, nodes) {
        const target = edge && edge.target;
        const node = _nodeById(nodes, target);
        const nodeProps = (node && node.properties) || {};
        const edgeProps = (edge && edge.properties) || {};
        const pick = (key) => {
            const e = edgeProps[key];
            if (e !== undefined && e !== null && e !== '')
                return e;
            const n = nodeProps[key];
            return (n === undefined) ? undefined : n;
        };
        const rawEffects = pick('effects');
        const effects = (Array.isArray(rawEffects) && rawEffects.length)
            ? rawEffects
            : (pick('effect_type')
                ? [{ type: pick('effect_type'), params: pick('effect_params') || {} }]
                : []);
        let rawConditions = pick('conditions');
        const singular = pick('condition');
        const empty = rawConditions === undefined || rawConditions === null || rawConditions === ''
            || (Array.isArray(rawConditions) && rawConditions.length === 0);
        if (empty)
            rawConditions = singular ? [singular] : [];
        const logic = pick('conditions_logic') || 'and';
        const conditions = normalizeConditions(rawConditions, logic);
        const def = {
            trigger_type: pick('trigger_type') || 'on_examine',
            effects,
            conditions,
            target_name: pick('target_name') || '',
            target_state: pick('target_state') || '',
            success_message: pick('success_message') || '',
            fail_message: pick('fail_message') || '',
        };
        const ownId = pick('id');
        if (target)
            def.id = target;
        else if (ownId !== undefined && ownId !== '')
            def.id = ownId;
        for (const key of ['name', 'once', 'fired', 'cooldown']) {
            const value = pick(key);
            if (value !== undefined && value !== null && value !== '')
                def[key] = value;
        }
        return def;
    }
    function triggerDefFromProperty(entry) {
        const normalized = normalizeTriggerEntry(entry);
        if (!normalized)
            return null;
        return triggerDefFromEdge({ source: '', target: normalized.id, type: 'triggers', properties: normalized }, null);
    }
    function triggersFromGraphEdges(edges, nodes, sourceId) {
        const out = [];
        const seen = new Set();
        const lower = sourceId == null || sourceId === '' ? null : String(sourceId).toLowerCase();
        if (sourceId) {
            const source = _nodeById(nodes, sourceId);
            const raw = source && source.properties ? source.properties.triggers : null;
            for (const entry of normalizeTriggerList(raw)) {
                const def = triggerDefFromProperty(entry);
                if (!def)
                    continue;
                if (def.id) {
                    if (seen.has(def.id))
                        continue;
                    seen.add(def.id);
                }
                out.push(def);
            }
        }
        for (const edge of (edges || [])) {
            if (!edge || edge.type !== 'triggers')
                continue;
            if (lower != null && String(edge.source).toLowerCase() !== lower)
                continue;
            if (edge.target && seen.has(edge.target))
                continue;
            const def = triggerDefFromEdge(edge, nodes);
            if (def && def.id)
                seen.add(def.id);
            out.push(def);
        }
        return out;
    }
    function compileError(compiled) {
        return compiled && compiled.compile_error ? compiled.compile_error : '';
    }
    return {
        normalizeConditions,
        treeIsFlat,
        flattenConditions,
        conditionToGraphProps,
        buildConditionFromNode,
        traceGroupCondition: _traceGroupCondition,
        compileRoot,
        compileToTriggers,
        compileToEngine,
        compileError,
        triggerToGraph,
        triggersToGraph,
        engineToFormData,
        normalizeTriggerEntry,
        normalizeTriggerList,
        triggerDefFromEdge,
        triggerDefFromProperty,
        triggersFromGraphEdges,
    };
})();
if (typeof globalThis.module !== 'undefined' && globalThis.module.exports) {
    globalThis.module.exports = globalThis.TriggerDef;
}
