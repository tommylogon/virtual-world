/**
 * GraphNodeOps — node and edge CRUD operations for the graph
 * Provides create, delete, duplicate operations for graph nodes and edges.
 * Extracted from graph-manager.js. References the global graphManager singleton.
 *
 * @module GraphNodeOps
 */
// Lazy lit-html tag: window.Lit is only available at call time (deferred module
// bootstrap), not at parse time. Unique per file so top-level consts never collide.
const graphNodeOpsTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.GraphNodeOps = {
    /**
     * Shows a confirmation modal with yes/no buttons.
     */
    _showConfirmModal(message, title) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            const titleHtml = title || 'Confirm';
            window.Lit.render(graphNodeOpsTag`
                <div class="modal-window" style="width:400px;max-width:90vw;">
                    <div class="modal-head"><h3 style="margin:0;font-size:14px;">${titleHtml}</h3></div>
                    <div style="padding:0 20px 16px;font-size:12px;color:var(--text);">${window.Lit.unsafeHTML(message)}</div>
                    <div style="padding:12px 20px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end;">
                        <button class="btn btn-sm btn-ghost" id="modal-cancel-btn">Cancel</button>
                        <button class="btn btn-sm" style="background:var(--red);color:#fff;" id="modal-confirm-btn">Delete</button>
                    </div>
                </div>`, overlay);
            document.body.appendChild(overlay);
            const cleanup = () => { overlay.remove(); };
            overlay.querySelector('#modal-cancel-btn').onclick = () => { cleanup(); resolve(false); };
            overlay.querySelector('#modal-confirm-btn').onclick = () => { cleanup(); resolve(true); };
            overlay.addEventListener('click', (e) => { if (e.target === overlay) { cleanup(); resolve(false); } });
        });
    },

    /**
     * Shows a yes/no modal for duplicate-related choices.
     */
    _showDuplicateChoiceModal(question, title) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            const titleHtml = title || 'Duplicate Options';
            window.Lit.render(graphNodeOpsTag`
                <div class="modal-window" style="width:440px;max-width:90vw;">
                    <div class="modal-head"><h3 style="margin:0;font-size:14px;">${titleHtml}</h3></div>
                    <div style="padding:0 20px 16px;font-size:12px;color:var(--text);">${window.Lit.unsafeHTML(question)}</div>
                    <div style="padding:12px 20px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end;">
                        <button class="btn btn-sm btn-ghost" id="dup-no-btn">No</button>
                        <button class="btn btn-sm" style="background:var(--primary);color:#fff;" id="dup-yes-btn">Yes</button>
                    </div>
                </div>`, overlay);
            document.body.appendChild(overlay);
            const cleanup = () => { overlay.remove(); };
            overlay.querySelector('#dup-no-btn').onclick = () => { cleanup(); resolve(false); };
            overlay.querySelector('#dup-yes-btn').onclick = () => { cleanup(); resolve(true); };
            overlay.addEventListener('click', (e) => { if (e.target === overlay) { cleanup(); resolve(false); } });
        });
    },

    /**
     * Shows a modal for entering a duplicate node name.
     */
    _showDuplicateNameModal(originalName, defaultName) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            window.Lit.render(graphNodeOpsTag`
                <div class="modal-window" style="width:420px;max-width:90vw;">
                    <div class="modal-head"><h3 style="margin:0;font-size:14px;">Rename Duplicate</h3></div>
                    <div style="padding:0 20px 16px;font-size:12px;color:var(--text);">
                        Enter a name for <strong>${originalName}</strong>:<br>
                        <input type="text" id="dup-name-input" .value=${defaultName} style="width:100%;margin-top:8px;padding:6px 8px;font-size:12px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text);box-sizing:border-box;" />
                    </div>
                    <div style="padding:12px 20px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end;">
                        <button class="btn btn-sm btn-ghost" id="dup-cancel-btn">Cancel</button>
                        <button class="btn btn-sm" style="background:var(--primary);color:#fff;" id="dup-ok-btn">OK</button>
                    </div>
                </div>`, overlay);
            document.body.appendChild(overlay);
            const cleanup = () => { overlay.remove(); };
            overlay.querySelector('#dup-cancel-btn').onclick = () => { cleanup(); resolve(null); };
            overlay.querySelector('#dup-ok-btn').onclick = () => {
                const value = document.getElementById('dup-name-input')?.value || null;
                cleanup();
                resolve(value);
            };
            overlay.addEventListener('click', (e) => { if (e.target === overlay) { cleanup(); resolve(null); } });
            // Focus and select the input
            setTimeout(() => {
                const input = document.getElementById('dup-name-input');
                if (input) { input.focus(); input.select(); }
            }, 50);
        });
    },

    async deleteNode(nodeId) {
        const confirmed = await this._showConfirmModal(
            'Delete <strong>' + nodeId + '</strong> and all its connections?',
            'Delete Node'
        );
        if (!confirmed) return;
        const data = await ApiClient.deleteNode(nodeId);
        if (data.status === 'success') {
            events.log('Node deleted.', 'system-msg');
            hideInspectorPanel();
            worldState.fetch();
        } else {
            events.log(`Error: ${data.error}`, 'error-msg');
        }
    },

    /**
     * Deletes a graph edge between two nodes via the API.
     * Confirms with the user before proceeding.
     *
     * @param {string} source - The source node identifier
     * @param {string} target - The target node identifier
     * @param {string} edgeType - The edge type (connection, unlocks, triggers)
     */
    async deleteEdge(source, target, edgeType) {
        const confirmed = await this._showConfirmModal(
            'Delete edge <strong>' + source + ' &rarr; ' + target + '</strong>?',
            'Delete Edge'
        );
        if (!confirmed) return;
        const data = await ApiClient.deleteEdge(source, target, edgeType);
        if (data.status === 'success') {
            events.log('Edge deleted.', 'system-msg');
            hideInspectorPanel();
            worldState.fetch();
        } else {
            events.log(`Error: ${data.error}`, 'error-msg');
        }
    },

    /** Build a deduplicated list of unique IDs from an array of objects. */
    _uniqueIds(arr) {
        const seen = new Set();
        const result = [];
        for (const obj of arr) {
            const id = typeof obj === 'string' ? obj : obj.id || obj.target || obj.source;
            if (id && !seen.has(id)) {
                seen.add(id);
                result.push(id);
            }
        }
        return result;
    },

    /**
     * Duplicates a graph node including all its edges.
     * Prompts for the new node name, then shows modals for each category
     * of related element to decide whether to duplicate it too.
     *
     * @param {string} nodeId - The identifier of the node to duplicate
     */
    async duplicateNode(nodeId) {
        const nodeData = graphManager.nodes.get(nodeId);
        if (!nodeData) return;
        const newName = await this._showDuplicateNameModal(
            nodeData.name || nodeId,
            (nodeData.name || nodeId) + '_copy'
        );
        if (!newName?.trim()) return;
        const trimmedName = newName.trim();

        // Characters are real players: they need a Player object registered
        // (world.players) plus a player_<name> graph node, not just a bare node.
        if (nodeData.type === 'character') {
            try {
                const nodeNameOf = (nm) => `player_${nm.replace(/\s+/g, '_')}`;
                const nameTaken = (nm) => !!worldState.players?.[nm] || graphManager.nodes.has(nodeNameOf(nm));
                // Auto-append a numeric suffix if the chosen name collides with an
                // existing player, so we never silently overwrite an existing character.
                let charName = trimmedName;
                let charSuffix = 1;
                while (nameTaken(charName)) {
                    charSuffix++;
                    charName = `${trimmedName}_${charSuffix}`;
                }
                if (charName !== trimmedName) {
                    events.log(`Duplicate name "${trimmedName}" was taken — creating as "${charName}" instead.`, 'system-msg');
                }
                const res = await ApiClient.createCharacter(charName);
                if (res.error) {
                    events.log(`Duplicate failed: ${res.error}`, 'error-msg');
                    return;
                }
                const newId = nodeNameOf(charName);
                // Copy the original character's design data (appearance, personality,
                // tags, traits, NPC config) — createCharacter only makes a bare name.
                const origPlayer = worldState.players?.[nodeData.name];
                if (origPlayer) {
                    const copy = {};
                    ['description', 'base_description', 'personality', 'traits', 'tags',
                     'stats', 'skills', 'equipped', 'npc_behavior',
                     'npc_action_interval', 'simple_npc'].forEach(key => {
                        if (origPlayer[key] !== undefined && origPlayer[key] !== null) copy[key] = origPlayer[key];
                    });
                    if (Object.keys(copy).length > 0) {
                        await ApiClient.updateCharacter(charName, copy);
                    }
                }
                await this._copyEdgesWithModals(nodeId, newId, nodeData.type);
                if (origPlayer?.current_area) {
                    await ApiClient.movePlayerToRoom(charName, origPlayer.current_area);
                }
                events.log(`Duplicated "${nodeData.name}" as "${charName}" with edges.`, 'system-msg');
                worldState.fetch();
            } catch (err) {
                console.error('Character duplicate error:', err);
                events.log(`Duplicate failed: ${err.message}`, 'error-msg');
            }
            return;
        }

        // Resolve a unique id/name. If the derived id is already taken, auto-append
        // a numeric suffix instead of dead-ending on an "already exists" error.
        const idFromName = (nm) => `${nodeData.type}_${nm.replace(/\s+/g, '_')}`.toLowerCase();
        let copyName = trimmedName;
        let newId = idFromName(copyName);
        let copySuffix = 1;
        while (graphManager.nodes.has(newId)) {
            copySuffix++;
            copyName = `${trimmedName}_${copySuffix}`;
            newId = idFromName(copyName);
        }
        if (copyName !== trimmedName) {
            events.log(`Duplicate name "${trimmedName}" was taken — creating as "${copyName}" instead.`, 'system-msg');
        }
        // Create the duplicate node. If the backend still 409s (stale client), retry
        // with the next free suffix a few times before giving up.
        try {
            let res = null;
            for (let attempt = 0; attempt < 5; attempt++) {
                res = await ApiClient.createNode({
                    type: nodeData.type,
                    name: copyName,
                    id: newId,
                    properties: JSON.parse(JSON.stringify(nodeData.properties || {}))
                });
                if (!res.error) break;
                if (!/already exists/i.test(res.error || '')) break;
                copySuffix++;
                copyName = `${trimmedName}_${copySuffix}`;
                newId = idFromName(copyName);
            }
            if (res.error) {
                events.log(`Duplicate failed: ${res.error}`, 'error-msg');
                return;
            }
            await this._copyEdgesWithModals(nodeId, newId, nodeData.type);
            events.log(`Duplicated "${nodeData.name}" as "${copyName}" with edges.`, 'system-msg');
            worldState.fetch();
        } catch (err) {
            console.error('Node duplicate error:', err);
            events.log(`Duplicate failed: ${err.message}`, 'error-msg');
        }
    },

    /** Copy edges from source node to new node, with modals for each category.
     *  Creates actual copies of related nodes instead of linking to originals.
     *  @param {string} sourceId - Original node ID
     *  @param {string} newId - New duplicate node ID
     *  @param {string} sourceType - Type of the source node
     *  @param {boolean} [skipModals=false] - Skip modals for recursive calls */
    async _copyEdgesWithModals(sourceId, newId, sourceType, skipModals = false) {
        const edgesArr = await ApiClient.getGraphEdges();

        // Gather all outgoing edges (source -> target) and incoming edges (target <- source)
        const outgoingEdges = [];
        const incomingEdges = [];
        for (const edge of edgesArr) {
            if (edge.source === sourceId) {
                outgoingEdges.push(edge);
            }
            if (edge.target === sourceId) {
                incomingEdges.push(edge);
            }
        }

        // Track which nodes we've duplicated (id map: originalId -> newCopyId)
        const dupMap = new Map();
        dupMap.set(sourceId, newId);

        // Group ALL edges (outgoing + incoming) by target type.
        // Outgoing: area → item/way/character/area (e.g. area unlocks a way)
        // Incoming: item → area / character → area / way → area (e.g. item in room)
        const itemsOut = [];       // edges where target/source is an item
        const waysOut = [];        // edges where target/source is a way
        const charsOut = [];       // edges where target/source is a character
        const areasOut = [];       // edges where target/source is an area
        const triggersOut = [];    // edges where target/source is a trigger node
        // 'unlocks' edges are obsolete — ignored during duplication

        // Process outgoing edges (source === sourceId)
        for (const edge of outgoingEdges) {
            if (edge.type === 'unlocks') continue;
            const targetNode = graphManager.nodes.get(edge.target);
            if (!targetNode) continue;
            if (edge.type === 'triggers') {
                triggersOut.push(edge);
            } else if (edge.type === 'equipped' || edge.type === 'carrying') {
                itemsOut.push(edge);
            } else {
                switch (targetNode.type) {
                    case 'item': itemsOut.push(edge); break;
                    case 'way': waysOut.push(edge); break;
                    case 'character': charsOut.push(edge); break;
                    case 'area': areasOut.push(edge); break;
                    default: break;
                }
            }
        }

        // Process incoming edges (target === sourceId)
        // These represent things INSIDE or CONNECTED TO the area from outside
        // e.g. item → area (item in room), character → area (person in room), way → area (door into room)
        for (const edge of incomingEdges) {
            if (edge.type === 'unlocks') continue;
            const sourceNode = graphManager.nodes.get(edge.source);
            if (!sourceNode) continue;
            if (edge.type === 'triggers') {
                triggersOut.push({ source: edge.target, target: edge.source, type: 'triggers', properties: edge.properties });
            } else if (edge.type === 'equipped' || edge.type === 'carrying') {
                itemsOut.push(edge);
            } else {
                switch (sourceNode.type) {
                    case 'item': itemsOut.push(edge); break;
                    case 'way': waysOut.push(edge); break;
                    case 'character': charsOut.push(edge); break;
                    case 'area': areasOut.push(edge); break;
                    default: break;
                }
            }
        }

        // Ask about duplicating each category that has relevant edges
        const _nodeName = (e) => {
            const nodeId = e.type === 'triggers' ? (e.source === sourceId ? e.target : e.source) : (e.source === sourceId ? e.target : e.source);
            return graphManager.nodes.get(nodeId)?.name || nodeId;
        };
        if (itemsOut.length > 0 && !skipModals) {
            const dupItems = await this._showDuplicateChoiceModal(
                `This ${sourceType} has <strong>${itemsOut.length}</strong> item(s) attached (${itemsOut.map(_nodeName).join(', ')}).<br><br>Duplicate these items?`,
                'Duplicate Items?'
            );
            if (dupItems) {
                await this._duplicateNodesByType(itemsOut, 'item', sourceId, newId, dupMap, true);
            }
        } else if (itemsOut.length > 0 && skipModals) {
            await this._duplicateNodesByType(itemsOut, 'item', sourceId, newId, dupMap, true);
        }

        if (waysOut.length > 0 && !skipModals) {
            const dupWays = await this._showDuplicateChoiceModal(
                `This ${sourceType} has <strong>${waysOut.length}</strong> way(s) connected (${waysOut.map(_nodeName).join(', ')}).<br><br>Duplicate these ways?`,
                'Duplicate Ways?'
            );
            if (dupWays) {
                await this._duplicateNodesByType(waysOut, 'way', sourceId, newId, dupMap, true);
            }
        } else if (waysOut.length > 0 && skipModals) {
            await this._duplicateNodesByType(waysOut, 'way', sourceId, newId, dupMap, true);
        }

        if (charsOut.length > 0 && !skipModals) {
            const dupChars = await this._showDuplicateChoiceModal(
                `This ${sourceType} has <strong>${charsOut.length}</strong> character(s) in it (${charsOut.map(_nodeName).join(', ')}).<br><br>Duplicate these characters?`,
                'Duplicate Characters?'
            );
            if (dupChars) {
                await this._duplicateNodesByType(charsOut, 'character', sourceId, newId, dupMap, true);
            }
        } else if (charsOut.length > 0 && skipModals) {
            await this._duplicateNodesByType(charsOut, 'character', sourceId, newId, dupMap, true);
        }

        if (areasOut.length > 0 && !skipModals) {
            const dupAreas = await this._showDuplicateChoiceModal(
                `This ${sourceType} is connected to <strong>${areasOut.length}</strong> area(s) (${areasOut.map(_nodeName).join(', ')}).<br><br>Duplicate these areas?`,
                'Duplicate Areas?'
            );
            if (dupAreas) {
                await this._duplicateNodesByType(areasOut, 'area', sourceId, newId, dupMap, true);
            }
        } else if (areasOut.length > 0 && skipModals) {
            await this._duplicateNodesByType(areasOut, 'area', sourceId, newId, dupMap, true);
        }

        // Ask about duplicating triggers
        if (triggersOut.length > 0 && !skipModals) {
            const dupTriggers = await this._showDuplicateChoiceModal(
                `This ${sourceType} has <strong>${triggersOut.length}</strong> trigger(s) attached (${triggersOut.map(_nodeName).join(', ')}).<br><br>Duplicate these triggers?`,
                'Duplicate Triggers?'
            );
            if (dupTriggers) {
                await this._duplicateNodesByType(triggersOut, 'trigger', sourceId, newId, dupMap, false);
            }
        } else if (triggersOut.length > 0 && skipModals) {
            await this._duplicateNodesByType(triggersOut, 'trigger', sourceId, newId, dupMap, false);
        }

        // All categories with edges have been handled by modals above.
        // If user said NO to a category, those edges are simply not copied.
        // Obsolete 'unlocks' edges and unknown edge types are always ignored.

        // Handle incoming edges (edges pointing TO the source from outside)
        // Do NOT create edges from external nodes to the new copy.
        // A hallway connecting to room A should NOT auto-connect to room A_copy.
    },

    /** Duplicate a batch of edges targeting nodes of a specific type.
     *  Creates copies of the target nodes and links them to the given parent.
     *  @param {Array} edges - Edges to process
     *  @param {string} targetType - Type of nodes to duplicate
     *  @param {string} sourceId - Original node ID being duplicated
     *  @param {string} parentId - New copy node ID to link duplicates to
     *  @param {Map} dupMap - Map of original IDs to copy IDs
     *  @param {boolean} recurse - Whether to recursively duplicate children's edges */
    async _duplicateNodesByType(edges, targetType, sourceId, parentId, dupMap, recurse = false) {
        for (const edge of edges) {
            // Resolve the related node: outgoing edges have it at target, incoming at source
            const relatedNodeId = edge.source === sourceId ? edge.target : edge.source;
            const targetNode = graphManager.nodes.get(relatedNodeId);
            if (!targetNode) continue;
            // Skip if already duplicated
            if (dupMap.has(relatedNodeId)) continue;

            const copyName = targetNode.name + '_copy';
            // Use the actual node type from the target, not the edge type
            const actualType = targetNode.type || targetType;
            const copyId = `${actualType}_${copyName.replace(/\s+/g, '_')}`.toLowerCase();

            // For characters, special handling needed
            if (targetType === 'character') {
                const charShortName = copyName.replace(/\s+/g, '_');
                const res = await ApiClient.createCharacter(charShortName);
                if (res.error) continue;
                const charNewId = `player_${charShortName}`;
                const origPlayer = worldState.players?.[targetNode.name];
                if (origPlayer) {
                    const copy = {};
                    ['description', 'base_description', 'personality', 'traits', 'tags',
                     'stats', 'skills', 'equipped', 'npc_behavior',
                     'npc_action_interval', 'simple_npc'].forEach(key => {
                        if (origPlayer[key] !== undefined && origPlayer[key] !== null) copy[key] = origPlayer[key];
                    });
                    if (Object.keys(copy).length > 0) {
                        await ApiClient.updateCharacter(charShortName, copy);
                    }
                }
                dupMap.set(relatedNodeId, charNewId);
                // Determine correct edge direction based on original
                const isOutgoing = edge.source === sourceId;
                if (isOutgoing) {
                    await ApiClient.createEdge(parentId, charNewId, edge.type, JSON.parse(JSON.stringify(edge.properties || {})));
                } else {
                    await ApiClient.createEdge(charNewId, parentId, edge.type, JSON.parse(JSON.stringify(edge.properties || {})));
                }
                // Recursively duplicate the character's own edges (no modals)
                if (recurse) {
                    await this._copyEdgesWithModals(charNewId, charNewId, 'character', true);
                }
            } else {
                const res = await ApiClient.createNode({
                    type: actualType,
                    name: copyName,
                    id: copyId,
                    properties: JSON.parse(JSON.stringify(targetNode.properties || {}))
                });
                if (res.error) continue;
                dupMap.set(relatedNodeId, copyId);
                // Determine correct edge direction based on original
                const isOutgoing = edge.source === sourceId;
                if (isOutgoing) {
                    await ApiClient.createEdge(parentId, copyId, edge.type, JSON.parse(JSON.stringify(edge.properties || {})));
                } else {
                    await ApiClient.createEdge(copyId, parentId, edge.type, JSON.parse(JSON.stringify(edge.properties || {})));
                }
                // Recursively duplicate the copied node's own edges (no modals)
                if (recurse) {
                    await this._copyEdgesWithModals(copyId, copyId, actualType, true);
                }
            }
        }
    },

    /** Copy all edges from the original node onto the new one.
     *  For edges pointing to items (not rooms/areas), new copies of
     *  those items are created so the duplicate gets its own attached
     *  items rather than sharing the originals.
     *  @deprecated Use _copyEdgesWithModals instead. Kept for fallback. */
    async _copyEdges(sourceId, newId) {
        const edgesArr = await ApiClient.getGraphEdges();
        for (const edgeObj of edgesArr) {
            if (edgeObj.source === sourceId) {
                const targetNode = graphManager.nodes.get(edgeObj.target);
                if (targetNode && targetNode.type === 'item') {
                    const copyName = targetNode.name + '_copy';
                    const copyId = `item_${copyName.replace(/\s+/g, '_')}`.toLowerCase();
                    const res = await ApiClient.createNode({
                        type: 'item',
                        name: copyName,
                        id: copyId,
                        properties: JSON.parse(JSON.stringify(targetNode.properties || {}))
                    });
                    if (!res.error) {
                        await this._copyEdges(edgeObj.target, copyId);
                        await ApiClient.createEdge(newId, copyId, edgeObj.type, JSON.parse(JSON.stringify(edgeObj.properties || {})));
                    }
                } else {
                    await ApiClient.createEdge(newId, edgeObj.target, edgeObj.type, JSON.parse(JSON.stringify(edgeObj.properties || {})));
                }
            }
            if (edgeObj.target === sourceId) {
                await ApiClient.createEdge(edgeObj.source, newId, edgeObj.type, JSON.parse(JSON.stringify(edgeObj.properties || {})));
            }
        }
    },

    /**
     * Creates a special edge (triggers, unlocks) between two nodes.
     * Prompts the user to select a target node from a list of candidates
     * appropriate for the edge type, and optionally enter a description.
     *
     * @param {string} fromNodeId - The source node identifier
     * @param {string} edgeType - The edge type (e.g. 'triggers', 'unlocks')
     * @param {string} emoji - Visual indicator emoji for log messages
     */
    async createSpecialEdge(fromNodeId, edgeType, emoji) {
        const fromNode = graphManager.nodes.get(fromNodeId);
        if (!fromNode) return;

        // Build a list of possible target nodes to connect to
        const allNodes = Array.from(graphManager.nodes.entries());
        const roomNodes = allNodes.filter(([id, nodeData]) => nodeData.type === 'area');
        const doorNodes = allNodes.filter(([id, nodeData]) => nodeData.type === 'way');
        const itemNodes = allNodes.filter(([id, nodeData]) => nodeData.type === 'item');

        // Suggest appropriate targets based on edge type
        let candidates = [];
        let promptMsg = '';
        if (edgeType === 'unlocks') {
            candidates = doorNodes;
            promptMsg = `🔓 Which way should "${fromNode.name}" unlock?\n`;
        } else if (edgeType === 'triggers') {
            candidates = [...roomNodes, ...doorNodes, ...itemNodes];
            promptMsg = `⚡ What should "${fromNode.name}" trigger?\n`;
        }

        if (candidates.length === 0) {
            events.log(`No suitable target nodes found for ${edgeType} edge.`, 'error-msg');
            return;
        }

        // Show prompt with numbered list
        const candidateList = candidates.map(([id, nodeData], index) =>
            `${index + 1}. ${nodeData.name || id} (${nodeData.type})`
        ).join('\n');

        const desc = prompt(promptMsg + candidateList + '\n\nEnter number, or node ID:', '1');
        if (!desc) return;

        // Parse: either a number or node ID
        let targetId = null;
        const num = parseInt(desc);
        if (num > 0 && num <= candidates.length) {
            targetId = candidates[num - 1][0];
        } else {
            // Try as direct node ID
            if (graphManager.nodes.has(desc.trim())) {
                targetId = desc.trim();
            }
        }

        if (!targetId || targetId === fromNodeId) {
            events.log('Invalid target selected.', 'error-msg');
            return;
        }

        // Ask for optional description
        const description = prompt(`Enter a description for this ${edgeType} edge (optional):`, '');

        const properties = {};
        if (description) properties.description = description;

        const result = await ApiClient.createEdge(fromNodeId, targetId, edgeType, properties);
        if (result.status === 'success') {
            events.log(`${emoji} Created ${edgeType} edge: ${fromNode.name} → ${graphManager.nodes.get(targetId)?.name || targetId}`, 'system-msg');
            worldState.fetch();
        } else {
            events.log(`Failed to create edge: ${result.error || 'unknown error'}`, 'error-msg');
        }
    }
};
