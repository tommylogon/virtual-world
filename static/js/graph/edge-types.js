/**
 * EdgeTypes — shared edge type configuration for the graph
 * Central place for edge type names, colors, icons, and valid source/target combos.
 * Load this before graph-manager.js in index.html.
 */
window.EdgeTypes = {
    // All edge types with display metadata
    ALL: {
        'connection': { label: 'Connection', icon: '🔗', color: '#4ec9b0', desc: 'Area ↔ Area (via door)' },
        'in':          { label: 'In', icon: '📥', color: '#ffffff', desc: 'Item inside a room or container' },
        'on':          { label: 'On', icon: '📄', color: '#58a6ff', desc: 'Item resting on a surface' },
        'under':       { label: 'Under', icon: '⬇️', color: '#8b5cf6', desc: 'Item hidden beneath something' },
        'behind':      { label: 'Behind', icon: '⬅️', color: '#8b5cf6', desc: 'Item obscured behind something' },
        'beside':      { label: 'Beside', icon: '↔️', color: '#58a6ff', desc: 'Item next to something' },
        'at':          { label: 'At', icon: '📍', color: '#ffffff', desc: 'Item loosely positioned near' },
        'carrying':    { label: 'Carrying', icon: '🎒', color: '#6e7681', desc: 'Item in a character\'s inventory' },
        'equipped':    { label: 'Equipped', icon: '⚔️', color: '#d29922', desc: 'Worn or held by a character' },
        'grappled':    { label: 'Grappled', icon: '⛓️', color: '#d50000', desc: 'Character holds another (grappler → target)' },
        'unlocks':     { label: 'Unlocks', icon: '🔓', color: '#3fb950', desc: 'Item unlocks a door' },
        'triggers':    { label: 'Triggers', icon: '⚡', color: '#e3b341', desc: 'Node triggers an action' },
        'requires':    { label: 'Requires', icon: '🔒', color: '#f85149', desc: 'Door requires a condition' },
    },

    // Legacy aliases — map old names to new for display
    LEGACY_MAP: {
        'location': 'in',
        'carried_by': 'carrying',
        'contains': 'in',
    },

    /** Resolve an edge type to its display config (handles legacy names) */
    getConfig(type) {
        const resolved = this.LEGACY_MAP[type] || type;
        return this.ALL[resolved] || { label: type, icon: '🔗', color: '#30363d', desc: '' };
    },

    /** Get the canonical type name (handles legacy aliases) */
    resolve(type) {
        return this.LEGACY_MAP[type] || type;
    },

    /** Get edge types valid for creating a new edge from a given node type */
    validForSource(nodeType) {
        if (nodeType === 'item') {
            return ['in', 'on', 'under', 'behind', 'beside', 'at', 'carrying', 'equipped', 'unlocks', 'triggers'];
        }
        if (nodeType === 'area') {
            return ['triggers'];
        }
        if (nodeType === 'way') {
            return ['triggers'];
        }
        if (nodeType === 'character') {
            return ['triggers'];
        }
        return ['triggers'];
    },

    /** Get valid target node types for a given edge type */
    validTargets(edgeType) {
        switch (edgeType) {
            case 'connection': return ['area'];
            case 'in': return ['area', 'item'];
            case 'on': return ['item'];
            case 'under': return ['item'];
            case 'behind': return ['item'];
            case 'beside': return ['item'];
            case 'at': return ['area', 'item'];
            case 'carrying': return ['character'];
            case 'equipped': return ['character'];
            case 'unlocks': return ['way'];
            case 'triggers': return ['area', 'item', 'way', 'character'];
            case 'requires': return ['area', 'item', 'way', 'character'];
            default: return ['area', 'item', 'way', 'character'];
        }
    },
};
