/**
 * tools.js — Tool catalog and Overlay Graph View for Natural-Language Editor (task-387).
 *
 * Implements the 20 catalog tools with an OverlayGraphView that seamlessly
 * merges live worldState with uncommitted staged operations.
 */

window.NLEditorTools = (() => {
    'use strict';

    /**
     * OverlayGraphView merges live world graph with uncommitted staged operations.
     */
    class OverlayGraphView {
        constructor(stagingBuffer) {
            this.staging = stagingBuffer;
        }

        getNode(nodeId) {
            if (!nodeId) return null;
            const nid = String(nodeId).toLowerCase();
            const deletions = this.staging.getStagedDeletions();
            if (deletions.has(nid)) return null;

            const creations = this.staging.getStagedCreations();
            if (creations[nid]) {
                const node = { ...creations[nid] };
                const updates = this.staging.getStagedUpdates();
                if (updates[nid]) {
                    node.properties = { ...(node.properties || {}), ...updates[nid] };
                }
                return node;
            }

            const liveNode = typeof worldState !== 'undefined' && worldState?.getNode ? worldState.getNode(nid) : null;
            if (liveNode) {
                const node = JSON.parse(JSON.stringify(liveNode));
                const updates = this.staging.getStagedUpdates();
                if (updates[nid]) {
                    node.properties = { ...(node.properties || {}), ...updates[nid] };
                }
                return node;
            }
            return null;
        }

        searchNodes(query = '', kind = null, tags = null) {
            const q = (query || '').toLowerCase().trim();
            const filterKind = kind ? kind.toLowerCase() : null;
            const tagSet = Array.isArray(tags) ? new Set(tags.map(t => t.toLowerCase())) : null;
            const deletions = this.staging.getStagedDeletions();
            const results = [];
            const seenIds = new Set();

            // 1. Search staged creations
            const creations = this.staging.getStagedCreations();
            for (const [id, node] of Object.entries(creations)) {
                if (seenIds.has(id) || deletions.has(id)) continue;
                if (filterKind && (node.type || 'item').toLowerCase() !== filterKind) continue;
                const name = (node.name || '').toLowerCase();
                if (!q || id.includes(q) || name.includes(q)) {
                    seenIds.add(id);
                    results.push({
                        id: node.id,
                        name: node.name,
                        type: node.type || 'item',
                        tags: node.properties?.tags || [],
                        short_desc: (node.properties?.description || '').slice(0, 80),
                        staged: true
                    });
                }
            }

            // 2. Search live nodes
            const liveNodes = typeof worldState !== 'undefined' && worldState?.graph?.nodes ? worldState.graph.nodes : {};
            for (const [id, rawNode] of Object.entries(liveNodes)) {
                const nid = id.toLowerCase();
                if (seenIds.has(nid) || deletions.has(nid)) continue;
                const nodeType = (rawNode.type || '').toLowerCase();
                if (filterKind && nodeType !== filterKind) continue;

                const name = (rawNode.name || '').toLowerCase();
                const desc = (rawNode.properties?.description || '').toLowerCase();
                const nodeTags = (rawNode.properties?.tags || []).map(t => String(t).toLowerCase());

                if (tagSet && !tagSet.some(t => nodeTags.includes(t))) continue;

                if (!q || nid.includes(q) || name.includes(q) || desc.includes(q)) {
                    seenIds.add(nid);
                    results.push({
                        id: rawNode.id,
                        name: rawNode.name,
                        type: rawNode.type,
                        tags: rawNode.properties?.tags || [],
                        short_desc: (rawNode.properties?.description || '').slice(0, 80),
                        staged: false
                    });
                }
            }

            return results.slice(0, 15);
        }

        listWorldSummary() {
            const lines = ['### World Summary (Overlay):'];
            const areas = [];
            const liveNodes = typeof worldState !== 'undefined' && worldState?.graph?.nodes ? worldState.graph.nodes : {};
            const creations = this.staging.getStagedCreations();
            const deletions = this.staging.getStagedDeletions();

            const allNodes = { ...liveNodes, ...creations };
            for (const [id, node] of Object.entries(allNodes)) {
                const nid = id.toLowerCase();
                if (deletions.has(nid)) continue;
                if (node.type === 'area') {
                    const tagStr = (node.properties?.tags || []).join(', ');
                    areas.push(`- Area [${node.name}] (id: ${node.id}${node.staged ? ', STAGED' : ''})${tagStr ? ` [tags: ${tagStr}]` : ''}`);
                }
            }
            if (areas.length === 0) lines.push('(No areas found in world)');
            else lines.push(...areas);

            const stagedOps = this.staging.getOps();
            if (stagedOps.length > 0) {
                lines.push(`\nPending Staged Ops (${stagedOps.length}):`);
                stagedOps.forEach((op, idx) => lines.push(`  ${idx + 1}. [${op.type}] ${op.summary}`));
            }
            return lines.join('\n');
        }
    }

    /**
     * OpenAI-compatible Tool Definitions
     */
    const TOOL_DEFINITIONS = [
        {
            type: 'function',
            function: {
                name: 'search_graph_nodes',
                description: 'Search for existing or staged areas, items, ways, or characters by name, keyword, or tag.',
                parameters: {
                    type: 'object',
                    properties: {
                        query: { type: 'string', description: 'Search term to match name, id, or description' },
                        kind: { type: 'string', enum: ['area', 'item', 'way', 'character', 'logic_trigger'], description: 'Optional node type filter' },
                        tags: { type: 'array', items: { type: 'string' }, description: 'Optional list of required tags' }
                    }
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'get_node',
                description: 'Get the full details, properties, triggers, and state of a node (from live world or staging).',
                parameters: {
                    type: 'object',
                    properties: {
                        node_id: { type: 'string', description: 'The unique ID of the node to inspect' }
                    },
                    required: ['node_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'search_library_items',
                description: 'Search the curated Item Library to find reusable templates before creating from scratch.',
                parameters: {
                    type: 'object',
                    properties: {
                        query: { type: 'string', description: 'Keyword to search item templates (e.g. "lantern", "sword", "key")' },
                        tags: { type: 'array', items: { type: 'string' }, description: 'Optional tags filter' }
                    }
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'get_library_item',
                description: 'Get the full template schema and trigger configuration for an item in the library.',
                parameters: {
                    type: 'object',
                    properties: {
                        item_id: { type: 'string', description: 'The library item ID (e.g. "antique_gas_lamp")' }
                    },
                    required: ['item_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'search_library_tags',
                description: 'Search available system tags to ensure you only use registered tags and mechanic enums.',
                parameters: {
                    type: 'object',
                    properties: {
                        query: { type: 'string', description: 'Tag keyword (e.g. "light", "weapon", "container")' }
                    }
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'list_world_summary',
                description: 'Get a concise summary of all rooms, landmarks, and currently staged operations.',
                parameters: { type: 'object', properties: {} }
            }
        },
        {
            type: 'function',
            function: {
                name: 'search_library_areas',
                description: 'Search the curated Area Library for reusable room templates before creating from scratch.',
                parameters: {
                    type: 'object',
                    properties: {
                        query: { type: 'string', description: 'Keyword for area templates (e.g. "tavern", "store", "dungeon")' },
                        tags: { type: 'array', items: { type: 'string' }, description: 'Optional tags filter' }
                    }
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'get_library_area',
                description: 'Get the full template schema (environment, exits, items) of a library area.',
                parameters: {
                    type: 'object',
                    properties: { area_id: { type: 'string', description: 'Library area id (e.g. "bath_room")' } },
                    required: ['area_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'search_library_characters',
                description: 'Search the curated Character Library for reusable cast members before creating from scratch.',
                parameters: {
                    type: 'object',
                    properties: {
                        query: { type: 'string', description: 'Keyword for character templates (e.g. "guard", "shopkeeper")' },
                        tags: { type: 'array', items: { type: 'string' }, description: 'Optional tags filter' }
                    }
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'get_library_character',
                description: 'Get the full template schema (stats, vitals, skills, personality, inventory) of a library character.',
                parameters: {
                    type: 'object',
                    properties: { char_id: { type: 'string', description: 'Library character id' } },
                    required: ['char_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'list_library_summary',
                description: 'Get a concise summary of each library registry (items, areas, characters, ways) and their counts.',
                parameters: { type: 'object', properties: {} }
            }
        },
        {
            type: 'function',
            function: {
                name: 'link_to_library',
                description: 'Stage linking an existing live node to a library template (template sync then tracks it).',
                parameters: {
                    type: 'object',
                    properties: {
                        node_id: { type: 'string', description: 'Live graph node id' },
                        library_id: { type: 'string', description: 'Library template id' },
                        registry_type: { type: 'string', enum: ['items', 'areas', 'ways', 'characters'], description: 'Which registry (default items)' }
                    },
                    required: ['node_id', 'library_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'create_node',
                description: 'Stage creation of a new world entity (area, item, character, or logic_trigger). Must search library first if creating an item.',
                parameters: {
                    type: 'object',
                    properties: {
                        kind: { type: 'string', enum: ['area', 'item', 'character', 'logic_trigger'], description: 'The kind of entity' },
                        name: { type: 'string', description: 'Display name' },
                        properties: {
                            type: 'object',
                            description: 'Entity properties including description, tags, current_state, weight, actions, triggers'
                        }
                    },
                    required: ['kind', 'name']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'spawn_library_item',
                description: 'Stage instantiation of a curated item from the library into a parent area or container.',
                parameters: {
                    type: 'object',
                    properties: {
                        library_id: { type: 'string', description: 'Library item ID to spawn' },
                        parent_id: { type: 'string', description: 'Target area or container node ID where item will be placed' },
                        rename: { type: 'string', description: 'Optional custom name' },
                        relation: { type: 'string', enum: ['in', 'on', 'under', 'behind', 'beside', 'at'], description: 'Spatial relationship (default: "in")' },
                        overrides: { type: 'object', description: 'Optional property overrides' }
                    },
                    required: ['library_id', 'parent_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'populate_area',
                description: 'Stage a whole themed furnishing pass for an area in ONE call: several themed items, an NPC, and the area ambience, all reviewable in the staging tray. Use when the user asks to "furnish", "fill", "dress", or "turn into" a room. Theme pack keys: apothecary, kitchen, garden, study, smithy, warehouse, shrine, bedroom, generic.',
                parameters: {
                    type: 'object',
                    properties: {
                        area_id: { type: 'string', description: 'The area node ID to populate' },
                        theme: { type: 'string', description: 'Theme pack key (apothecary, kitchen, garden, study, smithy, warehouse, shrine, bedroom, generic)' },
                        item_count: { type: 'integer', description: 'Max items to stage (default: all in the theme pack, 2-12)' },
                        include_npc: { type: 'boolean', description: 'Stage the theme NPC too (default true)' },
                        area_env: { type: 'boolean', description: 'Also update the area ambience (smell/air) (default true)' }
                    },
                    required: ['area_id', 'theme']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'update_node',
                description: 'Stage a partial update/patch to an existing or staged node properties.',
                parameters: {
                    type: 'object',
                    properties: {
                        node_id: { type: 'string', description: 'Node ID to update' },
                        patch: { type: 'object', description: 'Key-value map of properties to update (e.g. description, triggers, tags)' }
                    },
                    required: ['node_id', 'patch']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'delete_node',
                description: 'Stage deletion of an entity from the world.',
                parameters: {
                    type: 'object',
                    properties: {
                        node_id: { type: 'string', description: 'Node ID to delete' }
                    },
                    required: ['node_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'attach',
                description: 'Stage a spatial connection placing an item/entity into/onto another node.',
                parameters: {
                    type: 'object',
                    properties: {
                        from_id: { type: 'string', description: 'The entity being placed (e.g. item)' },
                        to_id: { type: 'string', description: 'The parent target container/surface/area' },
                        relation: { type: 'string', enum: ['in', 'on', 'under', 'behind', 'beside', 'at'], description: 'Spatial relation' }
                    },
                    required: ['from_id', 'to_id', 'relation']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'detach',
                description: 'Stage removal of a spatial relationship edge between two nodes.',
                parameters: {
                    type: 'object',
                    properties: {
                        from_id: { type: 'string', description: 'Source node ID' },
                        to_id: { type: 'string', description: 'Target node ID' },
                        relation: { type: 'string', description: 'Edge relation type' }
                    },
                    required: ['from_id', 'to_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'connect_areas',
                description: 'Stage a passage/doorway connecting two areas (creates way node and 4 bidirectional connection edges).',
                parameters: {
                    type: 'object',
                    properties: {
                        area_a_id: { type: 'string', description: 'First area node ID' },
                        area_b_id: { type: 'string', description: 'Second area node ID' },
                        way_name: { type: 'string', description: 'Name of the door/pathway (e.g. "Oak Door", "Hidden Passage")' },
                        direction_a: { type: 'string', description: 'Exit direction shown in area A (default "north")' },
                        direction_b: { type: 'string', description: 'Exit direction shown in area B (default "south")' },
                        properties: { type: 'object', description: 'Optional way properties (e.g. current_state: "closed" / "locked")' }
                    },
                    required: ['area_a_id', 'area_b_id', 'way_name']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'unstage_op',
                description: 'Remove a specific uncommitted operation from the staging buffer.',
                parameters: {
                    type: 'object',
                    properties: {
                        op_id: { type: 'string', description: 'The operation ID to remove' }
                    },
                    required: ['op_id']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'clear_staged',
                description: 'Clear all pending operations from the staging buffer.',
                parameters: { type: 'object', properties: {} }
            }
        },
        {
            type: 'function',
            function: {
                name: 'request_clarification',
                description: 'Ask the user a multiple-choice question when authoring intent or target reference is ambiguous.',
                parameters: {
                    type: 'object',
                    properties: {
                        question: { type: 'string', description: 'The clear clarifying question for the user' },
                        options: { type: 'array', items: { type: 'string' }, description: '2 to 4 quick-choice buttons for the user to select' }
                    },
                    required: ['question', 'options']
                }
            }
        }
    ];

    // ─────────────────────── Mechanic inference (task-387) ───────────────────────
    // When the model creates an item, common-sense mechanics are bound from the
    // name so e.g. a "glowing crystal" actually lights the room and a "roast
    // chicken" can be eaten — without asking the model to know every detail.
    const _ACTIONS_BASE = 'examine,take,use';

    function _appendAction(actions, action) {
        const list = Array.isArray(actions) ? actions.join(',') : (actions || _ACTIONS_BASE);
        const parts = list.split(',').map(s => s.trim()).filter(Boolean);
        if (!parts.includes(action)) parts.push(action);
        return parts.join(',');
    }

    function inferMechanics(kind, name, props) {
        if (kind !== 'item') return props;
        const p = Object.assign({}, props);
        p.tags = Array.isArray(p.tags) ? [...p.tags] : [];
        const hasTag = t => p.tags.includes(t);
        const nameL = String(name || '').toLowerCase();

        // 💡 Light sources — engine counts tag light_source + lit/on state.
        if (/(candle|lamp|lantern|torch|brazier|hearth|fire|flame|sconce|wisp|glowing|crystal|lamp|glow)/.test(nameL) && !hasTag('light_source')) {
            p.tags.push('light_source');
            if (p.light_level === undefined) {
                p.light_level = /(fire|flame|torch|brazier|hearth|lantern|bonfire|campfire)/.test(nameL) ? 'bright' : 'dim';
            }
            if (/(glow|glowing|lit|burning|ember|alight)/.test(nameL) && p.current_state === undefined) {
                p.current_state = 'lit';
            }
        }
        // 🔊 Sound sources.
        if (/(violin|harp|bell|chime|music box|gramophone|organ|drum|singing|humming|whispering|chant)/.test(nameL) && !hasTag('sound_source')) {
            p.tags.push('sound_source');
            if (p.sound_level === undefined) p.sound_level = 1;
            if (p.sound_pattern === undefined) {
                const subj = /(violin|harp|organ|music box|gramophone)/.test(nameL) ? 'music' : 'sound';
                p.sound_pattern = `a soft ${subj} of ${name.toLowerCase()}`;
            }
        }
        // 🔥 Heat sources.
        if (/(heat|stove|oven|furnace|brazier|hearth|forge|kiln|fireplace)/.test(nameL) && !hasTag('heat_source')) {
            p.tags.push('heat_source');
        }
        // 🍗 Food / 🍷 drink / 📖 read / 🔑 use actions.
        if (/(chicken|roast|turkey|meat|steak|bread|cake|pie|soup|stew|fish|apple|cheese|honey|pastry|sausage|ham|egg|sandwich|biscuit)/.test(nameL)) {
            p.actions = _appendAction(p.actions, 'eat');
        }
        if (/(wine|ale|mead|tea|coffee|water|milk|potion|whiskey|brandy|brew|juice|elixir|cider)/.test(nameL)) {
            p.actions = _appendAction(p.actions, 'drink');
        }
        if (/(book|tome|scroll|letter|note|journal|diary|map|ledger|letter)/.test(nameL)) {
            p.actions = _appendAction(p.actions, 'read');
        }
        if (/(key(ring)?|bolt cutter|picklock|lockpick)/.test(nameL)) {
            p.actions = _appendAction(p.actions, 'use');
        }
        // ⚔️ Weapons / 🛡 armor+clothing.
        if (/(sword|axe|dagger|knife|bow|spear|hammer|mace|rapier|blade|staff|scythe|halberd)/.test(nameL)) {
            if (!hasTag('weapon')) p.tags.push('weapon');
            if (p.damage === undefined) p.damage = '1d6';
        }
        if (/(shield|armor|helm|helmet|cloak|robe|boots|gloves|coat|cuirass|gambeson)/.test(nameL)) {
            if (!hasTag('armor') && !hasTag('clothing')) p.tags.push(/(shield|armor|helm|helmet|cuirass|gambeson)/.test(nameL) ? 'armor' : 'clothing');
            if (p.defense === undefined) p.defense = 1;
        }

        if (p.tags.length === 0) delete p.tags;
        return p;
    }

    // ─────────────────── populate_area theme packs (task-387) ───────────────────
    // Cohesive furnishing passes: a named theme stages themed items + one NPC
    // + area ambience in a single tool call, all reviewable in the staging tray.
    const THEME_PACKS = {
        apothecary: {
            label: 'Apothecary', area: { environment: { smell: 'herbal', air: 'fresh' } },
            npc: { name: 'Apothecary', description: 'A precise herbalist behind a curved counter.', personality: 'Quietly judgmental, exacting about dosages, secretly kind.' },
            items: [
                ['herb drying rack', { tags: ['container'], weight: 8 }],
                ['mortar and pestle', { weight: 1.2 }],
                ['apothecary cabinet', { tags: ['container'], weight: 12 }],
                ['brass balance scale', { weight: 2 }],
                ['herbal notes book', { weight: 0.4 }],
                ['potion shelf', { tags: ['container'], weight: 9 }],
                ['candle of beeswax', { tags: ['container'], weight: 0.2 }],
                ['bundle of dried herbs', { weight: 0.3 }]
            ]
        },
        kitchen: {
            label: 'Kitchen', area: { environment: { smell: 'woodsmoke and bread', air: 'warm' } },
            npc: { name: 'Cook', description: 'A flour-dusted cook tending the stove.', personality: 'Cheerful and gruff, strong opinions about seasoning.' },
            items: [
                ['wooden worktable', { tags: ['container'], weight: 14 }],
                ['cast iron pot', { weight: 6 }],
                ['loaf of bread', { weight: 0.8 }],
                ['spice shelf', { tags: ['container'], weight: 5 }],
                ['stew pot', { weight: 6 }],
                ['cooking knife', { weight: 0.4 }],
                ['hanging herbs', { weight: 0.2 }],
                ['hearth fire', { weight: 0.5 }]
            ]
        },
        garden: {
            label: 'Garden', area: { environment: { smell: 'blooming flowers', air: 'fresh' } },
            npc: { name: 'Gardener', description: 'A patient gardener knee-deep in soil.', personality: 'Terse about weeds, endlessly generous with seeds.' },
            items: [
                ['flowerbed', { tags: ['container'], weight: 10 }],
                ['watering can', { weight: 1.5 }],
                ['garden trowel', { weight: 0.4 }],
                ['stone birdbath', { weight: 12 }],
                ['garden lantern', { weight: 1.2 }],
                ['crate of vegetables', { tags: ['container'], weight: 8 }]
            ]
        },
        study: {
            label: 'Study', area: { environment: { smell: 'old paper and wax', air: 'still' } },
            npc: { name: 'Scholar', description: 'A weary scholar surrounded by open books.', personality: 'Brilliant, absent-minded, allergic to small talk.' },
            items: [
                ['writing desk', { tags: ['container'], weight: 15 }],
                ['leather tome', { weight: 1.4 }],
                ['reading candle', { weight: 0.3 }],
                ['inkwell', { weight: 0.4 }],
                ['scroll tube', { weight: 0.5 }],
                ['bookcase', { tags: ['container'], weight: 18 }],
                ['quill set', { weight: 0.2 }]
            ]
        },
        smithy: {
            label: 'Smithy', area: { environment: { smell: 'charcoal and hot iron', air: 'hot' } },
            npc: { name: 'Blacksmith', description: 'A broad-shouldered smith resting an anvil.', personality: 'Laconic with strangers, exacting about steel.' },
            items: [
                ['anvil', { weight: 40 }],
                ['charcoal brazier', { weight: 8 }],
                ['quench trough', { weight: 20 }],
                ['hammer', { weight: 3 }],
                ['coal shovel', { weight: 2 }],
                ['tool rack', { tags: ['container'], weight: 10 }]
            ]
        },
        warehouse: {
            label: 'Warehouse', area: { environment: { smell: 'dust and timber', air: 'dry' } },
            npc: { name: 'Warehouse Foreman', description: 'A foreman checking a cargo manifest.', personality: 'Pragmatic, suspicious of anything unlisted.' },
            items: [
                ['crate', { tags: ['container'], weight: 15 }],
                ['barrel', { tags: ['container'], weight: 20 }],
                ['sack', { tags: ['container'], weight: 5 }],
                ['grain sack', { weight: 12 }],
                ['hand cart', { weight: 22 }],
                ['oil lamp', { weight: 0.6 }]
            ]
        },
        shrine: {
            label: 'Shrine', area: { environment: { smell: 'incense and cold stone', air: 'still' } },
            npc: { name: 'Candlekeeper', description: 'A robed acolyte maintaining the shrine.', personality: 'Soft-spoken, generous with quiet blessings.' },
            items: [
                ['offering bowl', { weight: 4 }],
                ['tall candle', { weight: 0.8 }],
                ['incense burner', { weight: 1 }],
                ['prayer book', { weight: 0.5 }],
                ['glowing crystal', { weight: 1 }],
                ['worn prayer mat', { weight: 2 }]
            ]
        },
        bedroom: {
            label: 'Bedroom', area: { environment: { smell: 'lavender and old linen', air: 'pristine' } },
            npc: { name: 'Maid', description: 'A quiet maid smoothing a bedsheet.', personality: 'Discreet, observant, slightly superstitious.' },
            items: [
                ['bed', { tags: ['container'], weight: 30 }],
                ['nightstand', { tags: ['container'], weight: 8 }],
                ['oil lamp', { weight: 0.6 }],
                ['linen chest', { tags: ['container'], weight: 12 }],
                ['mirror', { weight: 6 }],
                ['bedside candle', { weight: 0.2 }]
            ]
        },
        generic: {
            label: 'Generic furnishings', area: null,
            npc: { name: 'Resident', description: 'A local resident.', personality: 'Friendly but unremarkable.' },
            items: [
                ['wooden table', { tags: ['container'], weight: 12 }],
                ['shelf', { tags: ['container'], weight: 9 }],
                ['oil lamp', { weight: 0.6 }],
                ['crate', { tags: ['container'], weight: 8 }],
                ['basket', { tags: ['container'], weight: 2 }],
                ['bottle', { weight: 0.3 }]
            ]
        }
    };

    function buildThemePack(themeKey, itemCount) {
        const pack = THEME_PACKS[themeKey] || THEME_PACKS[themeKey.replace(/s$/, '')] || null;
        if (!pack) return null;
        const count = Math.max(2, Math.min(12, parseInt(itemCount, 10) || (pack.items.length || 6)));
        return Object.assign({}, pack, {
            items: pack.items.slice(0, count).map(([name, props]) => ({ kind: 'item', name, properties: props || {} }))
        });
    }

    /**
     * Tool execution router
     */
    class ToolRouter {
        constructor(stagingBuffer) {
            this.staging = stagingBuffer;
            this.overlay = new OverlayGraphView(stagingBuffer);
        }

        /** The node currently selected in the graph/inspector, if any. */
        _selectedNode() {
            try {
                const view = (typeof VW !== 'undefined' && VW?.inspector) ? VW.inspector._currentView : null;
                if (view && view.type === 'node' && view.id && typeof worldState?.getNode === 'function') {
                    return worldState.getNode(view.id) || null;
                }
            } catch (e) { /* ignore */ }
            return null;
        }

        /** Fill a missing node_id from the user's current selection (task-387
         *  "this node" awareness: type "add a chest to this room" with the
         *  room selected and the agent can target it without a name). */
        _resolveNodeId(nodeId) {
            if (nodeId) return nodeId;
            const sel = this._selectedNode();
            return sel ? sel.id : null;
        }

        async execute(toolName, args = {}, context = {}) {
            try {
                switch (toolName) {
                    case 'search_graph_nodes': {
                        const results = this.overlay.searchNodes(args.query, args.kind, args.tags);
                        return { count: results.length, matches: results };
                    }
                    case 'get_node': {
                        const nodeId = this._resolveNodeId(args.node_id);
                        const node = this.overlay.getNode(nodeId);
                        if (!node) return { error: `Node '${args.node_id}' not found in world or staging.` };
                        return node;
                    }
                    case 'search_library_items': {
                        const q = (args.query || '').toLowerCase().trim();
                        try {
                            const res = await ApiClient.get('/api/library/items');
                            let items = Array.isArray(res) ? res : (res?.items ? Object.values(res.items) : []);
                            if (q) {
                                items = items.filter(it =>
                                    (it.name || '').toLowerCase().includes(q) ||
                                    (it.id || '').toLowerCase().includes(q) ||
                                    (it.description || '').toLowerCase().includes(q)
                                );
                            }
                            const compact = items.slice(0, 10).map(it => ({
                                id: it.id,
                                name: it.name,
                                tags: it.tags || [],
                                description: (it.description || '').slice(0, 80)
                            }));
                            return { count: compact.length, items: compact };
                        } catch (e) {
                            return { count: 0, items: [], error: e.message };
                        }
                    }
                    case 'get_library_item': {
                        try {
                            const res = await ApiClient.get('/api/library/items');
                            const items = Array.isArray(res) ? res : (res?.items || {});
                            const item = Array.isArray(items)
                                ? items.find(it => it.id === args.item_id)
                                : items[args.item_id];
                            if (!item) return { error: `Library item '${args.item_id}' not found.` };
                            return item;
                        } catch (e) {
                            return { error: e.message };
                        }
                    }
                    case 'search_library_tags': {
                        try {
                            const res = await ApiClient.get('/api/tags/search?q=' + encodeURIComponent(args.query || ''));
                            return { count: (res || []).length, tags: (res || []).slice(0, 15) };
                        } catch (e) {
                            return { count: 0, tags: [], error: e.message };
                        }
                    }
                    case 'list_world_summary': {
                        return { summary: this.overlay.listWorldSummary() };
                    }
                    case 'search_library_areas': {
                        const q = (args.query || '').toLowerCase().trim();
                        try {
                            const res = await ApiClient.get('/api/library/areas');
                            let areas = Array.isArray(res) ? res : Object.values(res || {});
                            if (q) {
                                areas = areas.filter(a =>
                                    (a.name || '').toLowerCase().includes(q) ||
                                    (a.id || '').toLowerCase().includes(q) ||
                                    (a.description || '').toLowerCase().includes(q)
                                );
                            }
                            const compact = areas.slice(0, 10).map(a => ({
                                id: a.id, name: a.name, tags: a.tags || [],
                                description: (a.description || '').slice(0, 80)
                            }));
                            return { count: compact.length, areas: compact };
                        } catch (e) {
                            return { count: 0, areas: [], error: e.message };
                        }
                    }
                    case 'get_library_area': {
                        try {
                            const res = await ApiClient.get('/api/library/areas');
                            const areas = Array.isArray(res) ? res : Object.values(res || {});
                            const area = areas.find(a => String(a.id) === args.area_id);
                            if (!area) return { error: `Library area '${args.area_id}' not found.` };
                            return area;
                        } catch (e) {
                            return { error: e.message };
                        }
                    }
                    case 'search_library_characters': {
                        const q = (args.query || '').toLowerCase().trim();
                        try {
                            const res = await ApiClient.get('/api/library/characters');
                            let chars = Array.isArray(res) ? res : Object.values(res || {});
                            if (q) {
                                chars = chars.filter(c =>
                                    (c.name || '').toLowerCase().includes(q) ||
                                    (c.id || '').toLowerCase().includes(q) ||
                                    (c.personality || '').toLowerCase().includes(q)
                                );
                            }
                            const compact = chars.slice(0, 10).map(c => ({
                                id: c.id, name: c.name, tags: c.tags || [],
                                description: (c.personality || '').slice(0, 80)
                            }));
                            return { count: compact.length, characters: compact };
                        } catch (e) {
                            return { count: 0, characters: [], error: e.message };
                        }
                    }
                    case 'get_library_character': {
                        try {
                            const res = await ApiClient.get('/api/library/characters');
                            const chars = Array.isArray(res) ? res : Object.values(res || {});
                            const char = chars.find(c => String(c.id) === args.char_id);
                            if (!char) return { error: `Library character '${args.char_id}' not found.` };
                            return char;
                        } catch (e) {
                            return { error: e.message };
                        }
                    }
                    case 'list_library_summary': {
                        try {
                            const res = await ApiClient.get('/api/library/entities');
                            const parts = [];
                            for (const [t, info] of Object.entries(res || {})) parts.push(`${t}: ${info?.count ?? '?'}`);
                            return { summary: `Library registries — ${parts.join(', ')}.` };
                        } catch (e) {
                            return { summary: 'Library summary unavailable.', error: e.message };
                        }
                    }
                    case 'link_to_library': {
                        const nodeId = this._resolveNodeId(args.node_id);
                        const node = this.overlay.getNode(nodeId);
                        if (!node) return { error: `Node '${args.node_id}' not found.` };
                        const op = this.staging.addOp('link_to_library', {
                            node_id: nodeId,
                            library_id: args.library_id,
                            registry_type: args.registry_type || 'items'
                        }, `Link "${node.name || nodeId}" to library ${args.registry_type || 'items'}/${args.library_id}`);
                        return { staged: true, op_id: op.id, summary: op.summary };
                    }
                    case 'create_node': {
                        const kind = args.kind || 'item';
                        const name = args.name || 'Unnamed';
                        const nodeId = this.staging.mintId(kind, name);
                        const nodeData = {
                            id: nodeId,
                            type: kind,
                            name,
                            // Mechanic inference binds light/sound/heat tags and
                            // eat/drink/read actions from the name automatically.
                            properties: inferMechanics(kind, name, args.properties || {})
                        };
                        const op = this.staging.addOp('create_node', { node: nodeData }, `Create ${kind} "${name}" [id: ${nodeId}]`);
                        return { staged: true, op_id: op.id, node_id: nodeId, summary: op.summary };
                    }
                    case 'spawn_library_item': {
                        const parentId = this._resolveNodeId(args.parent_id);
                        const targetNode = this.overlay.getNode(parentId);
                        if (!targetNode) return { error: `Parent target node '${args.parent_id}' does not exist.` };
                        const op = this.staging.addOp('spawn_library_item', {
                            library_id: args.library_id,
                            parent_id: parentId,
                            rename: args.rename,
                            relation: args.relation || 'in',
                            overrides: args.overrides
                        }, `Spawn library item "${args.library_id}" into "${targetNode.name || parentId}"`);
                        return { staged: true, op_id: op.id, summary: op.summary };
                    }
                    case 'populate_area': {
                        const area = this.overlay.getNode(args.area_id);
                        if (!area || area.type !== 'area') return { error: `Area '${args.area_id}' not found or not an area.` };
                        const themeKey = String(args.theme || '').toLowerCase().trim();
                        const pack = buildThemePack(themeKey, args.item_count);
                        if (!pack) {
                            return { error: `Unknown theme '${args.theme}'. Available: ${Object.keys(THEME_PACKS).join(', ')}` };
                        }
                        const staged = [];
                        for (const def of pack.items) {
                            const nodeId = this.staging.mintId(def.kind, def.name);
                            const props = inferMechanics(def.kind, def.name, def.properties || {});
                            this.staging.addOp('create_node',
                                { node: { id: nodeId, type: def.kind, name: def.name, properties: props } },
                                `Create item "${def.name}" [id: ${nodeId}]`);
                            this.staging.addOp('attach',
                                { from_id: nodeId, to_id: area.id, relation: def.relation || 'in' },
                                `Place "${def.name}" ${def.relation || 'in'} "${area.name}"`);
                            staged.push({ id: nodeId, name: def.name });
                        }
                        if (pack.npc && args.include_npc !== false) {
                            const npcId = this.staging.mintId('character', pack.npc.name);
                            this.staging.addOp('create_node',
                                { node: { id: npcId, type: 'character', name: pack.npc.name,
                                          properties: { personality: pack.npc.personality || '', description: pack.npc.description || '' } } },
                                `Create character "${pack.npc.name}" [id: ${npcId}]`);
                            this.staging.addOp('attach',
                                { from_id: npcId, to_id: area.id, relation: 'in' },
                                `Place "${pack.npc.name}" in "${area.name}"`);
                            staged.push({ id: npcId, name: pack.npc.name });
                        }
                        if (pack.area && args.area_env !== false) {
                            const env = Object.assign({}, (area.properties || {}).environment || {}, pack.area.environment || {});
                            this.staging.addOp('update_node',
                                { node_id: area.id, patch: { properties: { environment: env } } },
                                `Set "${area.name}" ambience (${Object.keys(pack.area.environment || {}).join(', ') || 'theme'})`);
                        }
                        return {
                            staged: staged.length,
                            area: area.name,
                            theme: themeKey,
                            items: staged,
                            summary: `Staged ${staged.length} themed entities for "${area.name}" (${pack.label || themeKey}).`
                        };
                    }
                    case 'update_node': {
                        const nodeId = this._resolveNodeId(args.node_id);
                        const node = this.overlay.getNode(nodeId);
                        if (!node) return { error: `Node '${args.node_id}' not found.` };
                        const op = this.staging.addOp('update_node', {
                            node_id: nodeId,
                            patch: args.patch
                        }, `Update "${node.name || nodeId}" properties`);
                        return { staged: true, op_id: op.id, summary: op.summary };
                    }
                    case 'delete_node': {
                        const nodeId = this._resolveNodeId(args.node_id);
                        const node = this.overlay.getNode(nodeId);
                        if (!node) return { error: `Node '${args.node_id}' not found.` };
                        const op = this.staging.addOp('delete_node', {
                            node_id: nodeId
                        }, `Delete ${node.type || 'node'} "${node.name || nodeId}"`);
                        return { staged: true, op_id: op.id, summary: op.summary };
                    }
                    case 'attach': {
                        const fromNode = this.overlay.getNode(args.from_id);
                        const toNode = this.overlay.getNode(args.to_id);
                        if (!fromNode) return { error: `Source entity '${args.from_id}' not found.` };
                        if (!toNode) return { error: `Target container '${args.to_id}' not found.` };
                        const op = this.staging.addOp('attach', {
                            from_id: args.from_id,
                            to_id: args.to_id,
                            relation: args.relation || 'in',
                            properties: args.properties || {}
                        }, `Attach "${fromNode.name || args.from_id}" ${args.relation || 'in'} "${toNode.name || args.to_id}"`);
                        return { staged: true, op_id: op.id, summary: op.summary };
                    }
                    case 'detach': {
                        const op = this.staging.addOp('detach', {
                            from_id: args.from_id,
                            to_id: args.to_id,
                            relation: args.relation || 'in'
                        }, `Detach ${args.from_id} from ${args.to_id}`);
                        return { staged: true, op_id: op.id, summary: op.summary };
                    }
                    case 'connect_areas': {
                        const areaA = this.overlay.getNode(args.area_a_id);
                        const areaB = this.overlay.getNode(args.area_b_id);
                        if (!areaA || areaA.type !== 'area') return { error: `Area '${args.area_a_id}' not found.` };
                        if (!areaB || areaB.type !== 'area') return { error: `Area '${args.area_b_id}' not found.` };
                        const wayId = this.staging.mintId('way', args.way_name || 'Door');
                        const op = this.staging.addOp('connect_areas', {
                            way_id: wayId,
                            area_a_id: args.area_a_id,
                            area_b_id: args.area_b_id,
                            way_name: args.way_name || 'Door',
                            direction_a: args.direction_a,
                            direction_b: args.direction_b,
                            properties: args.properties || {}
                        }, `Connect "${areaA.name}" <-> "${areaB.name}" via "${args.way_name}" [way_id: ${wayId}]`);
                        return { staged: true, op_id: op.id, way_id: wayId, summary: op.summary };
                    }
                    case 'unstage_op': {
                        const success = this.staging.removeOp(args.op_id);
                        return { unstage_success: success, remaining: this.staging.getOps().length };
                    }
                    case 'clear_staged': {
                        this.staging.clear();
                        return { cleared: true };
                    }
                    case 'request_clarification': {
                        if (typeof context.onClarify === 'function') {
                            context.onClarify(args.question, args.options || []);
                        }
                        return { suspended_for_user_choice: true, question: args.question, options: args.options };
                    }
                    default:
                        return { error: `Unknown tool: ${toolName}` };
                }
            } catch (err) {
                return { error: `Tool execution failed: ${err.message}` };
            }
        }
    }

    return { OverlayGraphView, TOOL_DEFINITIONS, ToolRouter };
})();
