/**
 * InspectorWayViewTriggers — Trigger extraction for way inspector
 * Extracted from way-view.js for modularity.
 */
window.InspectorWayViewTriggers = (() => {
    const T = {};

    T._extractTriggersFromEdges = function(nodeId) {
        const triggers = [];
        if (!worldState.graph?.edges) return triggers;
        for (const edge of worldState.graph.edges) {
            if (edge.source !== nodeId || edge.type !== 'triggers') continue;
            const ep = edge.properties || {};
            const effects = ep.effects?.length > 0
                ? ep.effects
                : (ep.effect_type
                    ? [{ type: ep.effect_type, params: ep.effect_params || {} }]
                    : []);
            let conditions = ep.conditions || {};
            if (Array.isArray(conditions) || !conditions.operator) {
                const logic = ep.conditions_logic || 'and';
                conditions = Array.isArray(conditions) && conditions.length > 0
                    ? { operator: logic, conditions }
                    : {};
            }
            triggers.push({
                trigger_type: ep.trigger_type || 'on_examine',
                effects,
                target_name: ep.target_name || '',
                target_state: ep.target_state || '',
                conditions,
                success_message: ep.success_message || '',
                fail_message: ep.fail_message || ''
            });
        }
        return triggers;
    };

    return T;
})();
