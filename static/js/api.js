/**
 * ApiClient — Backend HTTP calls for the VirtualWorld engine
 */
class ApiClient {
    /** Generic POST helper */
    static async post(url, payload) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return resp.json();
    }

    /** Generic GET helper */
    static async get(url) {
        const resp = await fetch(url);
        return resp.json();
    }

    /** Status-condition catalog (for the inspector's condition editor) */
    static async conditionsCatalog() {
        return this.get('/api/conditions');
    }

    /** POST with callback (for legacy compatibility) */
    static postCallback(url, payload, callback) {
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(res => {
            if (res.error) { toastError("Error: " + res.error); }
            else if (callback) callback(res);
            else worldState.fetch();
        })
        .catch(err => console.error('[apiPost] fetch error:', err));
    }

    /** Game actions */
    static async action(command, charName) {
        const body = { command };
        if (charName) body.character = charName;
        return this.post('/api/action', body);
    }

    /** Autocomplete candidate options for verb & prefix (task-6) */
    static async getAutocomplete(verb, prefix = '', charName = null) {
        const body = { verb, prefix };
        if (charName) body.character = charName;
        return this.post('/api/autocomplete', body);
    }

    /** Scene snapshot for the human turn panel (task-333 Phase 1) */
    static async getScene(playerName) {
        return this.get('/api/scene/' + encodeURIComponent(playerName));
    }

    /** Reset world to initial state */
    static async resetWorld() {
        const resp = await fetch('/api/reset', { method: 'POST' });
        return resp.json();
    }

    /** Undo the last snapshot (e.g. restore state deleted by reset) */
    static async undo() {
        return this.post('/api/undo', {});
    }

    /** Redo a previously undone state */
    static async redo() {
        return this.post('/api/redo', {});
    }

    /** Narrative emote */
    static async emote(actor, emoteText) {
        return this.post('/api/emote', { actor, emote: emoteText });
    }

    /** Set active player */
    static async setActivePlayer(name) {
        return this.post('/api/players/active', { name });
    }

    /** Create character */
    static async createCharacter(name) {
        return this.post('/api/players', { name });
    }

    /** Delete character */
    static async deleteCharacter(name) {
        const resp = await fetch('/api/players/' + encodeURIComponent(name), { method: 'DELETE' });
        return resp.json();
    }

    /** Kill character (set HP=0, state=dead, spawn body) */
    static async killCharacter(name) {
        const resp = await fetch('/api/players/' + encodeURIComponent(name) + '/kill', { method: 'POST' });
        return resp.json();
    }

    /** Update character personality/rename */
    static async updateCharacter(name, data) {
        const resp = await fetch('/api/players/' + encodeURIComponent(name), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return resp.json();
    }

    static async importPlayer(charData) {
        const resp = await fetch('/api/players/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(charData)
        });
        return resp.json();
    }

    // --- Player Movement & Speech ---

    static async movePlayerToRoom(name, area) {
        return this.post(`/api/players/${encodeURIComponent(name)}/move`, { area });
    }

    static async playerSpeak(name, text, area) {
        return this.post(`/api/players/${encodeURIComponent(name)}/speak`, { text, area });
    }

    // --- Build API ---

    static async createRoom(data) {
        return this.post('/api/build/area', data);
    }

    static async createItem(data) {
        return this.post('/api/build/item', data);
    }

    static async connectRooms(data) {
        return this.post('/api/build/connect', data);
    }

    static async placeItemFromLibrary(target, itemId) {
        const payload = {};
        if (target.type === 'container') payload.container = target.id;
        else if (target.type === 'character') payload.character = target.id;
        else payload.area = target.name;
        return this.post(`/api/library/items/${encodeURIComponent(itemId)}/place`, payload);
    }

    // --- Graph API ---

    static async getGraphNodes() {
        const resp = await fetch('/api/graph/nodes');
        return resp.json();
    }

    static async getGraphEdges() {
        const resp = await fetch('/api/graph/edges');
        return resp.json();
    }

    static async updateNode(nodeId, data) {
        const resp = await fetch(`/api/graph/node/${encodeURIComponent(nodeId)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return resp.ok;
    }

    static async uploadNodeImage(nodeId, file) {
        const form = new FormData();
        form.append('file', file);
        const resp = await fetch(`/api/graph/node/${encodeURIComponent(nodeId)}/image`, {
            method: 'POST',
            body: form
        });
        return resp.json();
    }

    static async removeNodeImage(nodeId) {
        return ApiClient.updateNode(nodeId, { properties: { image: null } });
    }

    static async renameNode(nodeId, newId) {
        return ApiClient.post(`/api/graph/node/${encodeURIComponent(nodeId)}/rename`, { new_id: newId });
    }

    static async moveItemToRoom(nodeId, area, container, character, targetType, targetId, relation) {
        const payload = {};
        if (targetType && targetId) {
            payload.target_type = targetType;
            payload.target_id = targetId;
            if (relation) payload.relation = relation;
        } else {
            if (area) payload.area = area;
            if (container) payload.container = container;
            if (character) payload.character = character;
        }
        return ApiClient.post(`/api/graph/item/${encodeURIComponent(nodeId)}/move`, payload);
    }

    static async deleteNode(nodeId) {
        const resp = await fetch(`/api/graph/node/${encodeURIComponent(nodeId)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async updateEdge(source, target, data) {
        return this.post('/api/graph/edge/update', { source, target, ...data });
    }

    static async deleteEdge(source, target, type) {
        const resp = await fetch('/api/graph/edge', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, target, type })
        });
        return resp.json();
    }

    static async flipEdge(source, target, type) {
        return this.post('/api/graph/edge/flip', { source, target, type });
    }

    static async createNode(data) {
        return this.post('/api/graph/node', data);
    }

    static async createEdge(source, target, type, properties = {}) {
        return this.post('/api/graph/edge', { source, target, type, properties });
    }

    // --- Item Registry (Library) API ---

    static async getLibraryItems() {
        const resp = await fetch('/api/library/items');
        return resp.json();
    }

    static async saveLibraryItem(payload) {
        const resp = await fetch('/api/library/items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return resp.json();
    }

    static async deleteLibraryItem(id) {
        const resp = await fetch(`/api/library/items/${encodeURIComponent(id)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async refreshFromLibrary(nodeId, sections, templateId, entries) {
        const body = { node_id: nodeId };
        if (sections) body.sections = sections;
        if (templateId) body.template_id = templateId;
        if (entries && Object.keys(entries).length) body.entries = entries;
        return this.post('/api/library/refresh-to-world', body);
    }

    static async refreshWayFromLibrary(nodeId, sections) {
        const body = { node_id: nodeId };
        if (sections) body.sections = sections;
        return this.post('/api/library/refresh-to-world', body);
    }

    // --- Character Registry API ---

    static async saveCharacterToRegistry(charId, data) {
        const resp = await fetch('/api/library/characters', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: charId, data })
        });
        return resp.json();
    }

    static async getCharactersFromLibrary() {
        const resp = await fetch('/api/library/characters');
        return resp.json();
    }

    // --- Unified Library API ---

    static async getLibraryEntities() {
        const resp = await fetch('/api/library/entities');
        return resp.json();
    }

    static async getLibraryType(type) {
        const resp = await fetch(`/api/library/${encodeURIComponent(type)}`);
        return resp.json();
    }

    /** Fetch multiple registries in one round-trip. @param {string[]} types */
    static async getLibraryTypes(types) {
        const q = types && types.length ? `?types=${encodeURIComponent(types.join(','))}` : '';
        const resp = await fetch(`/api/library/all${q}`);
        return resp.json();
    }

    static async saveLibraryType(type, payload) {
        const resp = await fetch(`/api/library/${encodeURIComponent(type)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return resp.json();
    }

    static async deleteLibraryType(type, id) {
        const resp = await fetch(`/api/library/${encodeURIComponent(type)}/${encodeURIComponent(id)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async importCharacterFromLibrary(charId, options = {}) {
        return this.post(`/api/library/import/character/${encodeURIComponent(charId)}`, options);
    }

    static async importRoomFromLibrary(roomId, options = {}) {
        return this.post(`/api/library/import/area/${encodeURIComponent(roomId)}`, options);
    }

    static async importWayFromLibrary(wayId, options = {}) {
        return this.post(`/api/library/import/way/${encodeURIComponent(wayId)}`, options);
    }

    static async reconnectDoor(wayId, roomA, roomB, dirA = '', dirB = '') {
        return this.post('/api/graph/way/reconnect', { way_id: wayId, area_a: roomA, area_b: roomB, dir_a: dirA, dir_b: dirB });
    }

    // --- World Save/Load ---

    static async saveWorld() {
        const resp = await fetch('/api/save');
        return resp.json();
    }

    static async loadWorld(data) {
        return this.post('/api/load', data);
    }

    // --- Turn System ---

    static async applyTurn() {
        await fetch('/api/turn/apply', { method: 'POST' });
    }

    static async clearTurnEvents() {
        await fetch('/api/turn/clear', { method: 'POST' });
    }

    // --- Ghost Mode ---

    static async getGhostMode() {
        const resp = await fetch('/api/settings/ghost_mode');
        return resp.json();
    }

    static async setGhostMode(enabled) {
        return this.post('/api/settings/ghost_mode', { ghost_mode: enabled });
    }

    // --- Auto-Generate Descriptions ---

    static async setAutoGenerateDescriptions(enabled) {
        return this.post('/api/settings/auto_generate_descriptions', { auto_generate_descriptions: enabled });
    }

    // --- World Lore API ---

    static async getWorldLore() {
        const resp = await fetch('/api/world/lore');
        return resp.json();
    }

    static async setWorldLore(lore) {
        return this.post('/api/world/lore', { lore });
    }

    static async addWorldLoreEntry(entry) {
        return this.post('/api/world/lore/entry', entry);
    }

    static async updateWorldLoreEntry(entryId, data) {
        return this.post(`/api/world/lore/entry/${encodeURIComponent(entryId)}`, data);
    }

    static async deleteWorldLoreEntry(entryId) {
        const resp = await fetch(`/api/world/lore/entry/${encodeURIComponent(entryId)}`, { method: 'DELETE' });
        return resp.json();
    }

    // --- Per-Character Memory API ---

    static async getPlayerMemories(name) {
        const resp = await fetch(`/api/players/${encodeURIComponent(name)}/memories`);
        return resp.json();
    }

    static async setPlayerMemories(name, memories) {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories`, { memories });
    }

    static async addPlayerMemory(name, entry) {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/entry`, entry);
    }

    static async deletePlayerMemory(name, entryId) {
        const resp = await fetch(`/api/players/${encodeURIComponent(name)}/memories/entry/${encodeURIComponent(entryId)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async updatePlayerMemory(name, entryId, data) {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/entry/${encodeURIComponent(entryId)}`, data);
    }

    static async clearPlayerMemories(name) {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/clear`, {});
    }

    static async suppressPlayerMemory(name, data) {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/suppress`, data);
    }

    static async unblockPlayerMemory(name, data) {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/unblock`, data);
    }

    static async clearExpiredSuppressions(name, currentTick) {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/clear-expired`, { current_tick: currentTick });
    }

    static async getAreaDescription() {
        const resp = await fetch('/api/area/description');
        return resp.json();
    }

    // --- Save/Load Game & Scenario ---

    static async saveGame(name) {
        return this.post('/api/save-game', { name });
    }

    static async listSaveGames() {
        const resp = await fetch('/api/save-games');
        return resp.json();
    }

    static async loadGame(filename) {
        return this.post(`/api/load-game/${encodeURIComponent(filename)}`);
    }

    static async deleteSaveGame(filename) {
        const resp = await fetch(`/api/save-game/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async saveScenario(name) {
        return this.post('/api/save-scenario', { name });
    }
}

// Singleton
const api = ApiClient;

/** Run a game action and log the result to the event stream, then refresh state. */
window.runAction = async function(cmd, charName) {
    const body = { command: cmd };
    if (charName) body.character = charName;
    const resp = await fetch('/api/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });
    const data = await resp.json();
    if (data?.output) events.log(data.output, 'system-msg');
    await worldState.fetch();
    // Auto-generate equipment description after a SUCCESSFUL equip/unequip.
    // /api/action reports `success` so a failed wear/remove (e.g. "can't be
    // equipped") doesn't rewrite the appearance.
    const cmdLower = cmd.trim().toLowerCase();
    if (data.success === true && config.autoGenerateDescriptions && (cmdLower.startsWith('wear ') || cmdLower.startsWith('remove ') || cmdLower.startsWith('unequip '))) {
        const char = charName || worldState.activePlayer;
        if (char && window.InspectorAgentView?._generateDescription) {
            InspectorAgentView._generateDescription(char).catch(() => {});
        }
    }
};