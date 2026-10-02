/**
 * NodeBadges — compact emoji indicators for graph node labels.
 * Trait badges (mechanics) appear before tag-library icons; both are capped
 * to keep labels readable at default zoom.
 *
 * Skip badges when GraphNetwork.loadGraphData already encodes the trait via
 * node color/border (see NODE_GRAPH_VISUALS below).
 *
 * @module graph/node-badges — compact label indicators
 * @contributes NodeBadges: mechanic badges + tag-library icons in node labels, formatLabel(), legendHtml()
 * @powers the at-a-glance emoji badges on graph nodes (capped so labels stay readable)
 * @relates used by GraphNetwork.buildNodeConfig; reads the tag library
 * @docs docs/virtualWorld/Library System/Tags System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// Named `NodeBadgesModule` rather than assigning straight to `window.NodeBadges`
// so the module keeps a real type and self-references resolve to it.
const NodeBadgesModule = {
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
    collectTraitBadges(nodeData: GraphNodeData | null | undefined): Badge[] {
        if (!nodeData) return [];
        switch (nodeData.type) {
            case 'way': return NodeBadgesModule._wayBadges(nodeData);
            case 'item': return NodeBadgesModule._itemBadges(nodeData);
            case 'character': return NodeBadgesModule._characterBadges(nodeData);
            case 'area': return NodeBadgesModule._areaBadges(nodeData);
            default: return [];
        }
    },

    /**
     * Build the vis-network label: trait emojis + tag icons + name.
     * @param {Object} nodeData
     * @param {Array<{icon:string}>} [tagMeta]
     * @returns {string}
     */
    formatLabel(nodeData: GraphNodeData | null | undefined, tagMeta?: TagMeta[]): string {
        let name = nodeData?.name || '';
        // Fall back to id only when name is genuinely empty; if the "name" is
        // just an auto-generated id (e.g. "item_knife_1"), strip the type
        // prefix so the label reads "knife" instead of a raw id.
        if (!name && nodeData?.id) {
            name = nodeData.id.replace(/^(area|item|way|character|trigger|logic_trigger)_/, '');
        }
        if (!name) name = '?';
        const traits = NodeBadgesModule.collectTraitBadges(nodeData)
            .slice(0, NodeBadgesModule.MAX_TRAIT_BADGES)
            .map((b: Badge) => b.emoji)
            .join('');
        const tags = (tagMeta || [])
            .slice(0, NodeBadgesModule.MAX_TAG_ICONS)
            .map((m: TagMeta) => m.icon)
            .join('');
        const prefix = traits + tags;
        return prefix ? `${prefix} ${name}` : name;
    },

    /** Plain-text lines for tooltips describing active trait badges. */
    traitTooltipLines(nodeData: GraphNodeData): string[] {
        return NodeBadgesModule.collectTraitBadges(nodeData).map((b: Badge) => `${b.emoji} ${b.title}`);
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
            <div class="legend-row"><span style="font-size:11px;">🌑🏢</span><span style="font-size:9px;"> dark area / not on the ground storey</span></div>
            <div style="font-size:9px;color:var(--text-muted);margin-top:4px;">Way/item state (open, locked, lit…) uses node color — see legend above.</div>`;
    },

    _push(badges: Badge[], seen: Set<string>, entry: Badge | null | undefined) {
        if (!entry || seen.has(entry.title)) return;
        seen.add(entry.title);
        badges.push(entry);
    },

    _normalizeTags(props: Record<string, any> | null | undefined): string[] {
        let tags = props?.tags || [];
        if (typeof tags === 'string') tags = tags.split(',').map((t: string) => t.trim()).filter(Boolean);
        return Array.isArray(tags) ? tags.map((t: any) => String(t).toLowerCase()) : [];
    },

    _triggerCount(nodeId: string | undefined): number {
        const edges = worldState?.graph?.edges || [];
        return edges.filter((e: { type?: string; source?: string; target?: string }) =>
            e.type === 'triggers' && (e.source === nodeId || e.target === nodeId)).length;
    },

    _wayBadges(nodeData: GraphNodeData): Badge[] {
        const props = nodeData.properties || {};
        const badges: Badge[] = [];
        const seen = new Set<string>();

        const req = String(props.requires || '').toLowerCase();
        if ((NodeBadgesModule.WAY_REQUIRES as Record<string, Badge>)[req]) {
            NodeBadgesModule._push(badges, seen, (NodeBadgesModule.WAY_REQUIRES as Record<string, Badge>)[req]);
        }

        const needsOpen = props.needs_open || {};
        if (needsOpen.enabled) {
            const skill = needsOpen.skill || 'Athletics';
            const dc = needsOpen.dc ?? 15;
            NodeBadgesModule._push(badges, seen, { emoji: '💪', title: `Skill check to open (${skill} DC ${dc})` });
        }

        // one_way: blue border on the triangle — no ➡️ badge
        if (props.see_through) NodeBadgesModule._push(badges, seen, { emoji: '👁', title: 'See-through (view beyond)' });
        if (props.auto_close) NodeBadgesModule._push(badges, seen, { emoji: '🔄', title: 'Auto-closes after use' });

        const maxSize = String(props.max_size || '').toLowerCase();
        if (maxSize && maxSize !== 'none' && (NodeBadgesModule.MAX_SIZE as Record<string, Badge>)[maxSize]) {
            NodeBadgesModule._push(badges, seen, (NodeBadgesModule.MAX_SIZE as Record<string, Badge>)[maxSize]);
        }

        return badges;
    },

    _itemBadges(nodeData: GraphNodeData): Badge[] {
        const props = nodeData.properties || {};
        const badges: Badge[] = [];
        const seen = new Set<string>();
        const tags = NodeBadgesModule._normalizeTags(props);

        // current_state (lit/broken/depleted/locked): node color or tooltip — no emoji

        if (tags.includes('container')) NodeBadgesModule._push(badges, seen, { emoji: '🧰', title: 'Container' });
        if ((props.equip_slots || []).length > 0) NodeBadgesModule._push(badges, seen, { emoji: '👕', title: 'Equippable' });

        const triggerCount = NodeBadgesModule._triggerCount(nodeData.id);
        if (triggerCount > 0) {
            NodeBadgesModule._push(badges, seen, {
                emoji: '⚡',
                title: triggerCount === 1 ? 'Has trigger' : `Has ${triggerCount} triggers`,
            });
        }

        return badges;
    },

    _characterBadges(nodeData: GraphNodeData): Badge[] {
        const name = nodeData.name as string | undefined;
        const player = (worldState as NodeState | undefined)?.players?.[name as string];
        const badges: Badge[] = [];
        const seen = new Set<string>();

        let controlMode = 'llm';
        if (typeof eventStream !== 'undefined' && eventStream.getControlMode) {
            controlMode = eventStream.getControlMode(name as string);
        } else if (player?.simple_npc) {
            controlMode = 'npc';
        }

        if (controlMode === 'npc') NodeBadgesModule._push(badges, seen, { emoji: '🤖', title: 'Scripted NPC' });
        else if (controlMode === 'human') NodeBadgesModule._push(badges, seen, { emoji: '👤', title: 'Human-controlled' });
        else NodeBadgesModule._push(badges, seen, { emoji: '🧠', title: 'LLM agent' });

        if (player) {
            const state = (player.state || '').toLowerCase();
            if (state === 'dead') NodeBadgesModule._push(badges, seen, { emoji: '💀', title: 'Dead' });
            else if (state === 'unconscious') NodeBadgesModule._push(badges, seen, { emoji: '😴', title: 'Unconscious' });

            const activity = (player.activity as { type?: string } | undefined)?.type || player.activity;
            if (activity === 'sleep') NodeBadgesModule._push(badges, seen, { emoji: '💤', title: 'Sleeping' });
        }

        return badges;
    },

    _areaBadges(nodeData: GraphNodeData): Badge[] {
        const props = nodeData.properties || {};
        const badges: Badge[] = [];
        const seen = new Set<string>();

        // `floor` is a storey index (0 ground, 1 up, -1 down, unbounded). A
        // non-numeric value is a save written before the ground material moved to
        // `properties.surface`; it counts as ground rather than a storey called
        // "dirt".
        const parsed = Number(props.floor ?? 0);
        const floor = Number.isFinite(parsed) ? Math.round(parsed) : 0;
        if (floor !== 0) {
            NodeBadgesModule._push(badges, seen, {
                emoji: floor > 0 ? '🏢' : '🕳️',
                title: floor > 0 ? `Floor ${floor}` : `Floor ${floor} (below ground)`,
            });
        }

        const light = props.environment?.light;
        if (typeof light === 'number' && light <= 20) {
            NodeBadgesModule._push(badges, seen, { emoji: '🌑', title: 'Very dark' });
        } else if (typeof light === 'string' && ['dark', 'pitch black', 'dim'].includes(light.toLowerCase())) {
            NodeBadgesModule._push(badges, seen, { emoji: '🌑', title: 'Dark area' });
        }

        const triggerCount = NodeBadgesModule._triggerCount(nodeData.id);
        if (triggerCount > 0) {
            NodeBadgesModule._push(badges, seen, {
                emoji: '⚡',
                title: triggerCount === 1 ? 'Area trigger' : `${triggerCount} area triggers`,
            });
        }

        return badges;
    },
};

(window as unknown as { NodeBadges: typeof NodeBadgesModule }).NodeBadges = NodeBadgesModule;

// `eventStream` has no ambient declaration, and this module is loaded before
// it in some graph-only pages, so it is read defensively through the window.
const eventStream = (window as unknown as {
    eventStream?: EventStreamLike;
}).eventStream as EventStreamLike;

// Type declarations sit below the first value statement on purpose: TypeScript
// drops a file's leading JSDoc when the first statement is type-only, which
// would strip the `@module` header `tools/js_module_index.py` reads.
interface Badge {
    emoji: string;
    title: string;
}

interface TagMeta {
    icon: string;
    [key: string]: unknown;
}

interface GraphNodeData {
    id?: string;
    name?: string;
    type?: string;
    properties?: Record<string, any>;
    [key: string]: unknown;
}

interface NodeState {
    graph?: { edges?: Array<{ type?: string; source?: string; target?: string }> };
    players?: Record<string, {
        state?: string;
        simple_npc?: boolean;
        activity?: { type?: string } | string;
    }>;
    [key: string]: unknown;
}

interface EventStreamLike {
    getControlMode?: (name: string) => string;
}
