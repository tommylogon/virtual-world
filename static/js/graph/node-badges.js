/**
 * NodeBadges — compact emoji indicators for graph node labels.
 * Trait badges (mechanics) appear before tag-library icons; both are capped
 * to keep labels readable at default zoom.
 *
 * Skip badges when GraphNetwork.loadGraphData already encodes the trait via
 * node color/border (see NODE_GRAPH_VISUALS below).
 *
 * @module NodeBadges
 */
window.NodeBadges = {
    MAX_TRAIT_BADGES: 5,
    MAX_TAG_ICONS: 2,

    /** States/styles drawn on the node shape — no duplicate emoji on the label. */
    NODE_GRAPH_VISUALS: {
        way: ['open', 'closed', 'locked', 'hidden', 'blocked', 'broken', 'one_way_border'],
        item: ['lit', 'broken', 'depleted'],
    },

    WAY_REQUIRES: {
        jump: { emoji: '🦘', title: 'Jump passage (jump <dir>)' },
        climb: { emoji: '🧗', title: 'Climb passage (climb <dir>)' },
        crawl: { emoji: '🐛', title: 'Crawl passage (auto-crawl on go)' },
    },

    MAX_SIZE: {
        tiny: { emoji: '🐜', title: 'Max size: tiny' },
        small: { emoji: '🐀', title: 'Max size: small' },
        normal: { emoji: '📏', title: 'Max size: normal' },
        huge: { emoji: '🐘', title: 'Max size: huge' },
        giant: { emoji: '🦣', title: 'Max size: giant' },
        titanic: { emoji: '🐋', title: 'Max size: titanic' },
    },

    /**
     * @param {Object} nodeData
     * @returns {Array<{emoji:string, title:string}>}
     */
    collectTraitBadges(nodeData) {
        if (!nodeData) return [];
        switch (nodeData.type) {
            case 'way': return NodeBadges._wayBadges(nodeData);
            case 'item': return NodeBadges._itemBadges(nodeData);
            case 'character': return NodeBadges._characterBadges(nodeData);
            case 'area': return NodeBadges._areaBadges(nodeData);
            default: return [];
        }
    },

    /**
     * Build the vis-network label: trait emojis + tag icons + name.
     * @param {Object} nodeData
     * @param {Array<{icon:string}>} [tagMeta]
     * @returns {string}
     */
    formatLabel(nodeData, tagMeta) {
        const name = nodeData?.name || nodeData?.id || '?';
        const traits = NodeBadges.collectTraitBadges(nodeData)
            .slice(0, NodeBadges.MAX_TRAIT_BADGES)
            .map(b => b.emoji)
            .join('');
        const tags = (tagMeta || [])
            .slice(0, NodeBadges.MAX_TAG_ICONS)
            .map(m => m.icon)
            .join('');
        const prefix = traits + tags;
        return prefix ? `${prefix} ${name}` : name;
    },

    /** Plain-text lines for tooltips describing active trait badges. */
    traitTooltipLines(nodeData) {
        return NodeBadges.collectTraitBadges(nodeData).map(b => `${b.emoji} ${b.title}`);
    },

    /** HTML fragment for the graph legend. */
    legendHtml() {
        return `<div style="font-size:9px;color:var(--text-muted);margin:6px 0 2px;">Label badges:</div>
            <div class="legend-row"><span style="font-size:11px;">🦘🧗🐛</span><span style="font-size:9px;"> jump / climb / crawl</span></div>
            <div class="legend-row"><span style="font-size:11px;">💪</span><span style="font-size:9px;"> skill check to open</span></div>
            <div class="legend-row"><span style="font-size:11px;">🔄👁</span><span style="font-size:9px;"> auto-close / see-through</span></div>
            <div class="legend-row"><span style="font-size:11px;">🐜🐀📏🐘</span><span style="font-size:9px;"> max passage size</span></div>
            <div class="legend-row"><span style="font-size:11px;">🧰⚡</span><span style="font-size:9px;"> container / triggers</span></div>
            <div class="legend-row"><span style="font-size:11px;">🤖🧠👤</span><span style="font-size:9px;"> NPC / LLM / human</span></div>
            <div class="legend-row"><span style="font-size:11px;">🌑🏢</span><span style="font-size:9px;"> dark area / non-ground floor</span></div>
            <div style="font-size:9px;color:var(--text-muted);margin-top:4px;">Way/item state (open, locked, lit…) uses node color — see legend above.</div>`;
    },

    _push(badges, seen, entry) {
        if (!entry || seen.has(entry.title)) return;
        seen.add(entry.title);
        badges.push(entry);
    },

    _normalizeTags(props) {
        let tags = props?.tags || [];
        if (typeof tags === 'string') tags = tags.split(',').map(t => t.trim()).filter(Boolean);
        return Array.isArray(tags) ? tags.map(t => String(t).toLowerCase()) : [];
    },

    _triggerCount(nodeId) {
        const edges = worldState?.graph?.edges || [];
        return edges.filter(e => e.type === 'triggers' && (e.source === nodeId || e.target === nodeId)).length;
    },

    _wayBadges(nodeData) {
        const props = nodeData.properties || {};
        const badges = [];
        const seen = new Set();

        const req = (props.requires || '').toLowerCase();
        if (NodeBadges.WAY_REQUIRES[req]) NodeBadges._push(badges, seen, NodeBadges.WAY_REQUIRES[req]);

        const needsOpen = props.needs_open || {};
        if (needsOpen.enabled) {
            const skill = needsOpen.skill || 'Athletics';
            const dc = needsOpen.dc ?? 15;
            NodeBadges._push(badges, seen, { emoji: '💪', title: `Skill check to open (${skill} DC ${dc})` });
        }

        // one_way: blue border on the triangle — no ➡️ badge
        if (props.see_through) NodeBadges._push(badges, seen, { emoji: '👁', title: 'See-through (view beyond)' });
        if (props.auto_close) NodeBadges._push(badges, seen, { emoji: '🔄', title: 'Auto-closes after use' });

        const maxSize = (props.max_size || '').toLowerCase();
        if (maxSize && maxSize !== 'none' && NodeBadges.MAX_SIZE[maxSize]) {
            NodeBadges._push(badges, seen, NodeBadges.MAX_SIZE[maxSize]);
        }

        return badges;
    },

    _itemBadges(nodeData) {
        const props = nodeData.properties || {};
        const badges = [];
        const seen = new Set();
        const tags = NodeBadges._normalizeTags(props);

        // current_state (lit/broken/depleted/locked): node color or tooltip — no emoji

        if (tags.includes('container')) NodeBadges._push(badges, seen, { emoji: '🧰', title: 'Container' });
        if ((props.equip_slots || []).length > 0) NodeBadges._push(badges, seen, { emoji: '👕', title: 'Equippable' });

        const triggerCount = NodeBadges._triggerCount(nodeData.id);
        if (triggerCount > 0) {
            NodeBadges._push(badges, seen, {
                emoji: '⚡',
                title: triggerCount === 1 ? 'Has trigger' : `Has ${triggerCount} triggers`,
            });
        }

        return badges;
    },

    _characterBadges(nodeData) {
        const name = nodeData.name;
        const player = worldState?.players?.[name];
        const badges = [];
        const seen = new Set();

        let controlMode = 'llm';
        if (typeof eventStream !== 'undefined' && eventStream.getControlMode) {
            controlMode = eventStream.getControlMode(name);
        } else if (player?.simple_npc) {
            controlMode = 'npc';
        }

        if (controlMode === 'npc') NodeBadges._push(badges, seen, { emoji: '🤖', title: 'Scripted NPC' });
        else if (controlMode === 'human') NodeBadges._push(badges, seen, { emoji: '👤', title: 'Human-controlled' });
        else NodeBadges._push(badges, seen, { emoji: '🧠', title: 'LLM agent' });

        if (player) {
            const state = (player.state || '').toLowerCase();
            if (state === 'dead') NodeBadges._push(badges, seen, { emoji: '💀', title: 'Dead' });
            else if (state === 'unconscious') NodeBadges._push(badges, seen, { emoji: '😴', title: 'Unconscious' });

            const activity = player.activity?.type || player.activity;
            if (activity === 'sleep') NodeBadges._push(badges, seen, { emoji: '💤', title: 'Sleeping' });
        }

        return badges;
    },

    _areaBadges(nodeData) {
        const props = nodeData.properties || {};
        const badges = [];
        const seen = new Set();

        const floor = props.floor ?? 0;
        if (floor !== 0) {
            NodeBadges._push(badges, seen, {
                emoji: floor > 0 ? '🏢' : '🕳️',
                title: floor > 0 ? `Floor ${floor}` : `Basement ${floor}`,
            });
        }

        const light = props.environment?.light;
        if (typeof light === 'number' && light <= 20) {
            NodeBadges._push(badges, seen, { emoji: '🌑', title: 'Very dark' });
        } else if (typeof light === 'string' && ['dark', 'pitch black', 'dim'].includes(light.toLowerCase())) {
            NodeBadges._push(badges, seen, { emoji: '🌑', title: 'Dark area' });
        }

        const triggerCount = NodeBadges._triggerCount(nodeData.id);
        if (triggerCount > 0) {
            NodeBadges._push(badges, seen, {
                emoji: '⚡',
                title: triggerCount === 1 ? 'Area trigger' : `${triggerCount} area triggers`,
            });
        }

        return badges;
    },
};
