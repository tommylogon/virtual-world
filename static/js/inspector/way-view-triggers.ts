/**
 * InspectorWayViewTriggers — Trigger extraction for way inspector
 * Extracted from way-view.js for modularity.
 *
 * @module inspector/way-view-triggers — trigger extraction for the way inspector
 * @contributes InspectorWayViewTriggers: pull a way's trigger edges into the inspector's trigger list
 * @powers showing a way's triggers in the way inspector
 * @relates consumed by way-view; complements inspector/trigger-helpers
 * @docs docs/virtualWorld/Rules Engine/Triggers & Effects.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// NOTE: ExtractedTrigger is declared *below* on purpose — a leading type-only
// statement makes tsc drop this file's leading JSDoc, and js_module_index.py
// reads @module out of the emitted .js. Keep a value declaration first.
const InspectorWayViewTriggers = (() => {
    const api = {} as {
        _extractTriggersFromEdges(nodeId: string): ExtractedTrigger[];
    };

    api._extractTriggersFromEdges = function (nodeId: string): ExtractedTrigger[] {
        const triggers: ExtractedTrigger[] = [];
        if (!worldState.graph?.edges) return triggers;
        for (const edge of worldState.graph.edges) {
            if (edge.source !== nodeId || edge.type !== 'triggers') continue;
            const edgeProps = edge.properties || {};
            const effects = edgeProps.effects?.length > 0
                ? edgeProps.effects
                : (edgeProps.effect_type
                    ? [{ type: edgeProps.effect_type, params: edgeProps.effect_params || {} }]
                    : []);
            let conditions = edgeProps.conditions || {};
            if (Array.isArray(conditions) || !conditions.operator) {
                const logic = edgeProps.conditions_logic || 'and';
                conditions = Array.isArray(conditions) && conditions.length > 0
                    ? { operator: logic, conditions }
                    : {};
            }
            triggers.push({
                trigger_type: edgeProps.trigger_type || 'on_examine',
                effects,
                target_name: edgeProps.target_name || '',
                target_state: edgeProps.target_state || '',
                conditions,
                fail_message: edgeProps.fail_message || ''
            });
        }
        return triggers;
    };

    return api;
})();

(window as unknown as { InspectorWayViewTriggers: typeof InspectorWayViewTriggers })
    .InspectorWayViewTriggers = InspectorWayViewTriggers;

interface ExtractedTrigger {
    trigger_type: string;
    effects: unknown[];
    target_name: string;
    target_state: string;
    conditions: unknown;
    success_message?: string;
    fail_message?: string;
}
