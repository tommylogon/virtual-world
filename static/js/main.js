/**
 * main.js — Bootstrap file that wires all modules together
 * This is the only entry point loaded from the HTML.
 * All modules are loaded in order via <script> tags in the HTML.
 * 
 * Architecture:
 *   VW namespace  →  global singleton registry
 *   Legacy globals →  kept as aliases for HTML onclick compatibility
 *   Modules       →  classes with singletons, initialized here
 */

// ============================================
// GLOBAL NAMESPACE
// ============================================
window.VW = {};

const mainJsTag = (strings, ...values) => window.Lit.html(strings, ...values);

// All singletons are registered here after module files are loaded
// Order of module loading (in HTML): 
//   0. event-bus.js    → class AppEventBus, const appEvents
//   1. storage.js       → class StorageProvider, const storage
//   2. context-window.js → class ContextWindowManager
//   3. llm-client.js    → class LLMClient, const llmClient
//   4. event-stream.js  → class EventBus, const events
//      (loaded after its collaborators in static/js/stream/: turn-cards,
//       filters, raw-llm, persistence, scrubber, control-mode — task-340)
//   5. world-state.js   → class WorldState, const worldState
//   6. config.js        → class ConfigManager, const config
//   7. api.js           → ApiClient (static), const api
//   8. agent-engine.js  → class AgentEngine, const agent
//   9. ui-controller.js → class UIController, const ui
//   10. graph-manager.js → class GraphManager, const graphManager
//   11. item-library.js → class ItemLibrary, const itemLib
//   12. inspector.js    → class Inspector, const inspector
//   13. main.js         → this file - wires singletons and bootstraps

// Register singletons in VW namespace
(() => {
    VW.appEvents = appEvents;
    VW.storage = storage;
    VW.llm = llmClient;
    VW.events = events;
    VW.state = worldState;
    VW.config = config;
    VW.api = api;
    VW.agent = agent;
    VW.ui = ui;
    VW.graph = graphManager;
    VW.itemLib = itemLib;
    VW.inspector = inspector;
    VW.libraryBrowser = libraryBrowser;
VW.worldSync = worldSync;
    VW.agentLens = agentLens;
    VW.humanTurnComposer = HumanTurnComposer;
})();

// ============================================
// LEGACY GLOBAL FUNCTIONS (for onclick in HTML)
// ============================================

// Simulation controls (left panel buttons)
function startAgent() { agent.start(); }
function stopAgent() { agent.stop(); }
function agentStepOnce() { agent.stepOnce(); }
function cancelStep() { agent.cancel(); }

// File save dialog (native "Save As") with fallback
async function saveFileWithDialog(blob, suggestedName) { WorldExport.saveFileWithDialog(blob, suggestedName); }

// World save/load
function downloadWorld() { SaveLoadView.downloadWorld(); }
function uploadWorld(event) { SaveLoadView.uploadWorld(event); }

// Save/Load Game & Scenario
async function saveScenarioToFile() { SaveLoadView.saveScenarioToFile(); }

async function saveGame() { SaveLoadView.saveGame(); }

async function loadGameList() { SaveLoadView.loadGameList(); }

async function doLoadGame(filename) { SaveLoadView.doLoadGame(filename); }

async function doDeleteSave(filename) { SaveLoadView.doDeleteSave(filename); }

async function confirmDeleteAllSaves() { SaveLoadView.confirmDeleteAllSaves(); }

// Settings modal functions
function switchSettingsTab(tabId) { SettingsView.switchTab(tabId); }

async function testAgentConnection() { SettingsView.testConnection(); }

// Character management
function createCharacter() {
    const input = document.getElementById('char-name');
    const name = (input?.value || '').trim();
    if (!name) { toastInfo('Enter a character name.'); return; }
    api.createCharacter(name).then(res => {
        events.log('Created character: ' + res.player, 'system-msg');
        if (input) input.value = '';
        worldState.fetch();
    });
}
function setActiveCharacter(name) {
    api.setActivePlayer(name).then(res => {
        if (res.error) { toastError('Error: ' + res.error); return; }
        events.log('Active character: ' + res.active, 'system-msg');
        worldState.fetch();
    });
}
function deleteCharacter(name) {
    if (!confirm("Delete character '" + name + "'?")) return;
    api.deleteCharacter(name).then(res => {
        if (res.error) toastError('Error: ' + res.error);
        else { events.log('Deleted: ' + name, 'system-msg'); worldState.fetch(); }
    });
}

// Graph toolbar buttons
function addRoomViaGraph() {
    openCreateModal('area', async (data) => {
        if (!data.name) { toastInfo('Area name required'); return; }
        const res = await api.createRoom(data);
        if (res.error) toastError('Error: ' + res.error);
        else { events.log('Created area: ' + data.name, 'system-msg'); worldState.fetch(); }
    });
}
function addItemViaGraph() {
    openCreateModal('item', async (data) => {
        if (!data.name) { toastInfo('Item name required'); return; }
        const res = await api.createItem(data);
        if (res.error) toastError('Error: ' + res.error);
        else {
            events.log('Added ' + data.name, 'system-msg');
            const libId = data.name.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_|_$/g, '');
            if (libId) {
                api.saveLibraryItem({ id: libId, name: data.name, description: data.description || '', actions: data.actions || 'examine,take,use', uses: data.uses ?? -1, weight: data.weight ?? 0.5, current_state: data.current_state || 'normal', equip_slots: data.equip_slots || [], tags: data.tags || [] }).catch(() => {});
            }
            worldState.fetch();
        }
    });
}
function connectRoomsViaGraph() {
    openCreateModal('connection', async (data) => {
        if (!data.room1 || !data.room2) { toastInfo('Select both rooms'); return; }
        const payload = {
            room1: data.room1, room2: data.room2,
            dir1: data.dir1.trim(), dir2: data.dir2.trim(),
            state: data.state || 'open',
            description: data.description || '',
            pass_message: data.pass_message || '',
            auto_close: data.auto_close || false,
            see_through: data.see_through || false,
            needs_open: data.needs_open || { enabled: false, skill: 'Athletics', dc: 15 },
            tags: data.tags || [],
            triggers: data.triggers || [],
            view_from_a: data.view_from_a || '',
            view_from_b: data.view_from_b || '',
        };
        if (data.way_id) payload.way_id = data.way_id;
        const res = await api.connectRooms(payload);
        if (res.error) toastError('Error: ' + res.error);
        else { events.log('Connected rooms', 'system-msg'); worldState.fetch(); }
    });
}
// Legacy HTML onclick wrappers — used by templates/index.html
function openItemLibrary() { itemLib.open(); }
function closeItemLibrary() { itemLib.close(); }
function filterItemLibrary() { itemLib.filter(); }
function addAllWorldItemsToLibrary() { itemLib.syncAllWorldItems(); }

function openLibraryBrowser() { libraryBrowser.open(); }
function closeLibraryBrowser() { libraryBrowser.close(); }

function openWorldSync() { VW.worldSync.open(); }
function closeWorldSync() { VW.worldSync.close(); }

// Settings/profile buttons — used by templates/index.html
function switchProfile(name) { config.switchProfile(name); }
function saveProfileFromCurrent() { config.saveProfileFromCurrent(); }
function saveProfileAsNew() { config.saveProfileAsNew(); }
function deleteProfile() { config.deleteProfile_(); }
function saveAgentSettings() { SettingsView.saveConfigToServer(); }

// Graph editor toolbar
const graphEditor = {
    undo() { graphManager.loadGraphData(); events.log('Undo (refreshed graph)', 'system-msg'); },
    redo() { graphManager.loadGraphData(); events.log('Redo (refreshed graph)', 'system-msg'); },
    showTemplates() { VW?.inspector?.showTemplates?.() || events.log('Templates panel', 'system-msg'); },
    fetchGraph() { graphManager.loadGraphData(); }
};



// Printer-friendly world summary
function printWorld() { WorldExport.printWorld(); }

// Legacy HTML onclick wrappers — used by templates/index.html
function newLibraryItem() { itemLib.newItem(); }

// Model select visibility
function updateModelDropdown() { SettingsView.updateModelDropdown(); }

function updateModelSelectVisibility() { SettingsView.updateModelSelectVisibility(); }

/**
 * Generate mock fallback data when LLM is unavailable.
 * @param {string} type - The type of content ('area', 'item', or 'connection')
 * @param {string} prompt - The user prompt text
 * @returns {Object} Mock data object matching the expected JSON structure
 */
function generateMockFallback(type, prompt) {
    const words = prompt.split(' ');
    const theme = words[Math.floor(Math.random() * words.length)] || 'mysterious';
    let data;
    if (type === 'area') {
        data = { name: theme.charAt(0).toUpperCase() + theme.slice(1) + ' Area', description: 'A ' + theme + ' area.', light: 50, temperature: 21, air: 'fresh', smell: 'musty', noise: 'quiet' };
    } else if (type === 'item') {
        data = { name: theme.charAt(0).toUpperCase() + theme.slice(1), description: 'A ' + theme + ' object.', actions: 'examine,take,use', uses: -1, weight: 0.5, hidden: false };
    } else {
        data = { room1: '', room2: '', dir1: 'north', dir2: 'south', locked: false };
    }
    events.log('AI generation used mock (no LLM)', 'system-msg');
    return data;
}

// AI generation (create modal)
function generateWithAI(type) {
    // Use the same generateWithAI from the create modal - inline due to complexity
    const promptInput = document.getElementById('ai-prompt');
    let prompt = (promptInput?.value || '').trim();
    if (!prompt) {
        // Auto-generate from context when prompt is empty
        if (type === 'connection') {
            const roomA = document.getElementById('conn-roomA')?.value;
            const roomB = document.getElementById('conn-roomB')?.value;
            if (roomA && roomB) {
                prompt = `The passage between ${roomA} and ${roomB}`;
            } else {
                promptInput?.focus(); return;
            }
        } else {
            promptInput?.focus(); return;
        }
    }
    promptInput.disabled = true;
    promptInput.value = 'Generating...';

    (async () => {
        try {
            const useContext = document.getElementById('gen-use-context')?.checked !== false;
            let systemMsg = `You are a procedural content generator for a game. Generate a ${type} based on the user's prompt. Respond ONLY with raw JSON matching the form fields. No markdown.

For connections, the 'description' is what the player sees when they look at the passage — be creative and contextually appropriate. The connection could be a way, gate, archway, stone portal, natural rock bridge, woven vine tunnel, frozen waterfall, narrow ravine, animal trail, fallen log, rope bridge, tunnel through roots, or any other passage that fits the two rooms. Use area descriptions to decide what makes sense. A forest path should NOT be described as a way with hinges and a handle — it should be a trail, a gap in the trees, a root arch, etc. The view_from_a and view_from_b describe what you see looking THROUGH the passage into the other area.

For items, generate appropriate triggers based on the item's purpose. Common patterns:
- Food/drink → on_eat/on_drink with adjust_vital (Hunger/Thirst)
- Light sources → on_light with set_state (lit) + set_environment (light)
- Tools/keys → on_use_on with unlock_way or adjust_vital
- Containers → on_use with spawn_item + uses=1 + on_take
- Interactive items → on_use with effects array for multi-step actions
- Books/notes → on_read with set_description or message
- Wearables → on_equip with adjust_vital (specific stats)

Use conditions (has_item, state_equals, random_chance) for gated interactions.
Use the effects array for multi-step effects.`;
            if (useContext) {
                if (type === 'area') {
                    const existing = Object.entries(worldState.areas || {}).map(([name, r]) =>
                        `- ${name}: ${(r.description || '(no description)').split('\n')[0]}`
                    ).join('\n');
                    if (existing) systemMsg += `\n\nExisting rooms in this world:\n${existing}\n\nGenerate a new area that fits thematically.`;
                } else if (useContext && type === 'item') {
                    const targetType = document.querySelector('input[name="item-target-type"]:checked')?.value || 'item';
                    const targetId = document.getElementById('item-target-id')?.value || '';
                    const relation = document.getElementById('item-target-relation')?.value || 'in';
                    let targetDesc = '';
                    if (targetId) {
                        const node = worldState.getNode(targetId);
                        if (node) {
                            const relationLabel = targetType === 'area' ? 'in' : targetType === 'character' ? 'carried by' : relation;
                            const desc = node.properties?.description || '(no description)';
                            targetDesc = `\nThis item will be placed ${relationLabel} "${node.name || targetId}": ${desc}`;
                        }
                    }
                    if (targetDesc) systemMsg += targetDesc;
                    if (window.VW?.PromptDocs?.ITEM_GENERATION_SYSTEM) {
                        systemMsg += '\n\n' + VW.PromptDocs.ITEM_GENERATION_SYSTEM;
                    }
                } else if (type === 'connection') {
                    const roomA = document.getElementById('conn-roomA')?.value;
                    const roomB = document.getElementById('conn-roomB')?.value;
                    const descA = roomA && worldState.areas?.[roomA]?.description;
                    const descB = roomB && worldState.areas?.[roomB]?.description;
                    const exitsA = roomA && worldState.areas?.[roomA]?.exits
                        ? Object.keys(worldState.areas[roomA].exits).join(', ') : 'none';
                    const exitsB = roomB && worldState.areas?.[roomB]?.exits
                        ? Object.keys(worldState.areas[roomB].exits).join(', ') : 'none';
                    if (descA) systemMsg += `\n\nRoom A ("${roomA}"): ${descA}\nExisting exits from ${roomA}: ${exitsA}`;
                    if (descB) systemMsg += `\n\nRoom B ("${roomB}"): ${descB}\nExisting exits from ${roomB}: ${exitsB}`;
                    systemMsg += '\n\nPick dir1 (from A to B) and dir2 (from B to A) that are NOT already in use by existing exits. Use directions that make geographic sense given the area descriptions. Include view descriptions from each side.';
                }
            }
            // Build format hint for the user message
            let formatHint = '';
            if (type === 'area') formatHint = '{"name":"Area Name","description":"...","light":80,"temperature":21,"air":"fresh","smell":"musty","noise":"quiet","tags":["indoor","cold"]}';
            else if (type === 'item') formatHint = '{"name":"...","description":"...","actions":"examine,take,use","uses":1,"weight":0.5,"current_state":"normal","tags":["food","apple"],"equip_slots":[],"triggers":[{"trigger_type":"on_eat","effect_type":"adjust_vital","effect_params":{"stat":"Hunger","amount":30,"message":"You feel nourished."}},{"trigger_type":"on_use","conditions":[{"type":"has_item","value":"matches"}],"effects":[{"type":"set_state","params":{"node_id":"fireplace","state":"lit"}},{"type":"set_environment","params":{"temperature":25,"light":"bright","noise":"crackling","smell":"woodsmoke"}},{"type":"message","params":{"message":"The fire roars to life."}}]}]}';
            else if (type === 'connection') formatHint = '{"room1":"Frozen Lake","room2":"Dense Forest","dir1":"north","dir2":"south","state":"open","description":"A narrow trail winds between the pines, the snow here packed hard by passing animals","pass_message":"The branches close behind you, muffling the sound of the wind","auto_close":false,"see_through":false,"needs_open":{"enabled":false,"skill":"Athletics","dc":15},"tags":["outdoor","trail"],"view_from_a":"the frozen lake shimmers through the gap in the trees","view_from_b":"a dense tangle of frozen branches casts pale blue shadows ahead","triggers":[]}';

            // Include the full JSON schema description in the system message for items and connections
            // so the LLM knows all available trigger types, not just the format example
            if ((type === 'item' || type === 'connection') && !systemMsg.includes('Available trigger types:')) {
                systemMsg += '\n\nAvailable trigger types: on_take, on_drop, on_examine, on_use, on_use_on, on_eat, on_drink, on_read, on_light, on_activate, on_equip, on_unequip, on_toggle_on, on_toggle_off, on_tick, on_open, on_close';
                systemMsg += '\nAvailable effect types: message, adjust_vital, set_state, set_environment, spawn_item, remove_item, damage, heal, teleport, unlock_way, destroy_self, drain, set_description, append_description, rename';
                systemMsg += '\nAvailable conditions: has_item, state_equals, random_chance, uses_reached, skill_check, save_throw (stat/skill, dc, optional target)';
                systemMsg += '\nTriggers can have a single effect (effect_type + effect_params) OR an effects array for multi-step sequences.';
                systemMsg += '\nConditions can be a single condition OR a conditions array (all must pass).';
            }

            const userContent = `${prompt}\n\nOutput JSON:\n${formatHint}`;
            const result = await AIGenerator.generate(userContent, systemMsg, { 
                temperature: 0.8,
                fallback: () => generateMockFallback(type, prompt)
            });
            if (!result.success) {
                events.log('AI generation failed: ' + result.error, 'error-msg');
                return;
            }
            const data = result.data;

            const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ''; };
            if (type === 'area') {
                set('area-name', data.name); set('area-desc', data.description);
                const lightEl = document.getElementById('area-light');
                if (lightEl) {
                    const levels = ['pitch_black','dim','normal','bright','blinding'];
                    let lv = data.light ?? 'normal';
                    if (typeof lv === 'number') {
                        if (lv <= 20) lv = 'pitch_black';
                        else if (lv <= 40) lv = 'dim';
                        else if (lv <= 70) lv = 'normal';
                        else if (lv <= 90) lv = 'bright';
                        else lv = 'blinding';
                    }
                    lightEl.value = levels.includes(lv) ? lv : 'normal';
                }
                set('area-temp', data.temperature); document.getElementById('area-air') && (document.getElementById('area-air').value = data.air || 'fresh');
                set('area-smell', data.smell); set('area-noise', data.noise);
                if (window.CreateModal?._tagMSArea && data.tags) {
                    window.CreateModal._tagMSArea.setValue(Array.isArray(data.tags) ? data.tags : typeof data.tags === 'string' ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : []);
                }
            } else if (type === 'item') {
                set('item-name', data.name); set('item-desc', data.description);
                set('item-uses', data.uses ?? -1); set('item-weight', data.weight ?? 0.1);
                const stateEl = document.getElementById('item-state'); if (stateEl) stateEl.value = data.current_state || 'normal';
                if (window.CreateModal?._tagMSItem && data.tags) {
                    window.CreateModal._tagMSItem.setValue(Array.isArray(data.tags) ? data.tags : typeof data.tags === 'string' ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : []);
                }
                const es = document.getElementById('item-equip-slots');
                if (es && Array.isArray(data.equip_slots)) {
                    Array.from(es.options).forEach(opt => opt.selected = data.equip_slots.includes(opt.value));
                }
                const tf = document.getElementById('item-triggers-json');
                if (tf && data.triggers) tf.value = JSON.stringify(data.triggers);
            } else if (type === 'connection') {
                set('conn-roomA', data.room1); set('conn-roomB', data.room2);
                VW._onConnRoomChange(); // refresh view-from hints when rooms change
                set('conn-dir1', data.dir1); set('conn-dir2', data.dir2);
                set('conn-desc', data.description || '');
                set('conn-id', data.way_id || '');
                const stateSelect = document.getElementById('conn-state');
                if (stateSelect) stateSelect.value = data.state || 'open';
                set('conn-pass-msg', data.pass_message || '');
                const autoCloseCheckbox = document.getElementById('conn-auto-close');
                if (autoCloseCheckbox) autoCloseCheckbox.checked = data.auto_close || false;
                const needsOpenConfig = data.needs_open;
                const noChk = document.getElementById('conn-needs-open');
                if (noChk && needsOpenConfig?.enabled) {
                    noChk.checked = true;
                    const cfg = document.getElementById('conn-needs-config');
                    if (cfg) cfg.style.display = 'flex';
                    set('conn-needs-skill', needsOpenConfig.skill || 'Athletics');
                    const dcEl = document.getElementById('conn-needs-dc');
                    if (dcEl) dcEl.value = needsOpenConfig.dc || 15;
                }
                if (window.CreateModal?._tagMSConn && data.tags) {
                    window.CreateModal._tagMSConn.setValue(Array.isArray(data.tags) ? data.tags : typeof data.tags === 'string' ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : []);
                }
                const seeThroughEl = document.getElementById('conn-see-through');
                if (seeThroughEl && data.see_through !== undefined) seeThroughEl.checked = data.see_through;
                set('conn-view-from-a', data.view_from_a || '');
                set('conn-view-from-b', data.view_from_b || '');
                const tf = document.getElementById('conn-triggers-json');
                if (tf && data.triggers) tf.value = JSON.stringify(data.triggers, null, 2);
            }
            events.log(`AI generated ${type}: ${data.name || 'unnamed'}`, 'system-msg');
        } catch (err) {
            events.log('AI generation failed: ' + err.message, 'error-msg');
        } finally {
            promptInput.disabled = false;
            promptInput.value = '';
            promptInput.placeholder = 'AI prompt...';
        }
    })();
}

VW._onConnRoomChange = function() {
    const roomA = document.getElementById('conn-roomA')?.value;
    const roomB = document.getElementById('conn-roomB')?.value;
    const hintA = document.getElementById('conn-view-from-a');
    const hintB = document.getElementById('conn-view-from-b');
    if (hintA && roomA) hintA.placeholder = `What you see from ${roomA} toward ${roomB || 'the other area'}... e.g. "A heavy oak way set into the stone wall"`;
    if (hintB && roomB) hintB.placeholder = `What you see from ${roomB} toward ${roomA || 'the other area'}... e.g. "A warm glow spills from the doorway"`;
};

VW._toggleItemTargetType = function() {
    const val = document.querySelector('input[name="item-target-type"]:checked')?.value || 'item';
    const search = document.getElementById('item-target-search');
    const relation = document.getElementById('item-target-relation');
    if (search) {
        const labels = { item: 'Search items...', character: 'Search characters...', area: 'Search areas...' };
        search.placeholder = labels[val] || 'Search...';
    }
    if (relation) {
        relation.style.display = val === 'item' ? 'block' : 'none';
    }
};

VW._previewPrompt = function(type) {
    const promptInput = document.getElementById('ai-prompt');
    const prompt = (promptInput?.value || '').trim();
    if (!prompt) { promptInput?.focus(); return; }

    const useContext = document.getElementById('gen-use-context')?.checked !== false;
    let systemMsg = `You are a procedural content generator for a game. Generate a ${type} based on the user's prompt. Respond ONLY with raw JSON matching the form fields. No markdown.`;
    if (useContext && type === 'area') {
        const existing = Object.entries(worldState.areas || {}).map(([n, r]) =>
            `- ${n}: ${(r.description || '(no description)').split('\n')[0]}`
        ).join('\n');
        if (existing) systemMsg += `\n\nExisting rooms in this world:\n${existing}\n\nGenerate a new area that fits thematically.`;
        } else if (useContext && type === 'item') {
            const targetType = document.querySelector('input[name="item-target-type"]:checked')?.value || 'item';
            const targetId = document.getElementById('item-target-id')?.value || '';
            const relation = document.getElementById('item-target-relation')?.value || 'in';
            let targetDesc = '';
            if (targetId) {
                const node = worldState.getNode(targetId);
                if (node) {
                    const relationLabel = targetType === 'area' ? 'in' : targetType === 'character' ? 'carried by' : relation;
                    const desc = node.properties?.description || '(no description)';
                    targetDesc = `\nThis item will be placed ${relationLabel} "${node.name || targetId}": ${desc}`;
                }
            }
        if (targetDesc) systemMsg += targetDesc;
        if (window.VW?.PromptDocs?.ITEM_GENERATION_SYSTEM) {
            systemMsg += '\n\n' + VW.PromptDocs.ITEM_GENERATION_SYSTEM;
        }
    } else if (useContext && type === 'connection') {
        const roomA = document.getElementById('conn-roomA')?.value;
        const roomB = document.getElementById('conn-roomB')?.value;
        const descA = roomA && worldState.areas?.[roomA]?.description;
        const descB = roomB && worldState.areas?.[roomB]?.description;
        const exitsA = roomA && worldState.areas?.[roomA]?.exits
            ? Object.keys(worldState.areas[roomA].exits).join(', ') : 'none';
        const exitsB = roomB && worldState.areas?.[roomB]?.exits
            ? Object.keys(worldState.areas[roomB].exits).join(', ') : 'none';
        if (descA) systemMsg += `\n\nRoom A ("${roomA}"): ${descA}\nExisting exits from ${roomA}: ${exitsA}`;
        if (descB) systemMsg += `\n\nRoom B ("${roomB}"): ${descB}\nExisting exits from ${roomB}: ${exitsB}`;
        systemMsg += '\n\nPick dir1 (from A to B) and dir2 (from B to A) that are NOT already in use by existing exits. Use directions that make geographic sense given the area descriptions. Include view descriptions from each side.';
    }

    let formatHint = '';
    if (type === 'area') formatHint = '{"name":"Area Name","description":"...","light":80,"temperature":21,"air":"fresh","smell":"musty","noise":"quiet","tags":["indoor","cold"]}';
    else if (type === 'item') formatHint = '{"name":"...","description":"...","actions":"examine,take,use","uses":1,"weight":0.5,"current_state":"normal","tags":["food","apple"],"equip_slots":[],"triggers":[{"trigger_type":"on_use","effect_type":"message","effect_params":{"message":"..."}}]}';
    else if (type === 'connection') formatHint = '{"room1":"Frozen Lake","room2":"Dense Forest","dir1":"north","dir2":"south","state":"open","description":"A narrow trail winds between the pines","pass_message":"The branches close behind you","auto_close":false,"see_through":false,"needs_open":{"enabled":false,"skill":"Athletics","dc":15},"tags":["outdoor","trail"],"view_from_a":"the frozen lake shimmers through the gap in the trees","view_from_b":"a dense tangle of frozen branches casts pale blue shadows","triggers":[]}';

    const fullPrompt = `[System]\n${systemMsg}\n\n[User prompt]\n${prompt}\n\nOutput JSON:\n${formatHint}`;

    const existingModal = document.getElementById('prompt-preview-modal');
    if (existingModal) {
        document.getElementById('prompt-preview-textarea').value = fullPrompt;
        existingModal.style.display = 'flex';
        existingModal._type = type;
        existingModal._formatHint = formatHint;
        existingModal._systemMsg = systemMsg;
        return;
    }

    const overlay = document.createElement('div');
    overlay.id = 'prompt-preview-modal';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:10000;';
    window.Lit.render(mainJsTag`<div style="background:var(--bg-panel);border:1px solid var(--border);border-radius:8px;padding:12px;width:90%;max-width:700px;max-height:80vh;display:flex;flex-direction:column;">
        <h3 style="margin:0 0 8px;">👁️ Prompt Preview</h3>
        <textarea id="prompt-preview-textarea" style="flex:1;min-height:300px;width:100%;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:8px;font-size:11px;font-family:monospace;resize:vertical;" spellcheck="false">${fullPrompt}</textarea>
        <div style="display:flex;gap:6px;margin-top:8px;justify-content:flex-end;">
            <button class="btn btn-sm" @click=${() => { overlay.style.display = 'none'; }} style="background:var(--bg-inset);border-color:var(--border);">Cancel</button>
            <button class="btn btn-sm" @click=${() => VW._sendPreviewPrompt()} style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">Send</button>
        </div>
    </div>`, overlay);
    document.body.appendChild(overlay);
    overlay._type = type;
    overlay._formatHint = formatHint;
    overlay._systemMsg = systemMsg;
}

VW._sendPreviewPrompt = function() {
    const modal = document.getElementById('prompt-preview-modal');
    if (!modal) return;
    const edited = document.getElementById('prompt-preview-textarea').value;
    const type = modal._type;
    modal.style.display = 'none';

    const userMarker = '[User prompt]\n';
    const userIdx = edited.lastIndexOf(userMarker);
    let editedUserPrompt = '';
    if (userIdx !== -1) {
        editedUserPrompt = edited.substring(userIdx + userMarker.length).trim();
    } else {
        editedUserPrompt = edited;
    }

    const formatHint = modal._formatHint;
    if (formatHint && editedUserPrompt.endsWith(formatHint)) {
        editedUserPrompt = editedUserPrompt.trim();
    }

    if (!editedUserPrompt) { return; }

    const promptInput = document.getElementById('ai-prompt');
    if (promptInput) {
        promptInput.value = editedUserPrompt;
    }
    generateWithAI(type);
}

// Create modal — delegates to CreateModal module
function openCreateModal(type, onSubmit) { CreateModal.open(type, onSubmit); }
function closeCreateModal() { CreateModal.close(); }

// Toggle way state (open/close) from area inspector — authoring path, so
// designers can set any state even on open-passage ways (task-223). Goes
// straight to the node PATCH like the way editor's State dropdown.
function toggleDoorState(exitName, action, wayId) {
    if (wayId) {
        const newState = action === 'open' ? 'open' : 'closed';
        api.updateNode(wayId, { properties: { current_state: newState } }).then(() => {
            events.log(`${action === 'open' ? 'Opened' : 'Closed'} ${wayId} (designer).`, 'system-msg');
            worldState.fetch();
        }).catch(err => events.log('Failed to toggle way: ' + (err?.message || err), 'error-msg'));
        return;
    }
    const cmd = action + ' ' + exitName;
    api.action(cmd).then(data => {
        const output = data?.output || data?.error || 'Toggled ' + (wayId || exitName);
        events.log(output, 'system-msg');
        if (data?.system_messages) {
            data.system_messages.forEach(sm => events.log(sm, 'system-msg'));
        }
        worldState.fetch();
    });
}

// Nudge
function nudgeCharacter(charName) {
    const input = document.getElementById('nudge-input');
    const text = (input?.value || '').trim();
    if (text) agent.nudge(charName, text);
    if (input) input.value = '';
}

// Explanation
function explainAction(charName, historyIndex) {
    const state = events.getCharacterState(charName);
    const entry = state.actionHistory[historyIndex];
    if (!entry) return;
    const panel = document.getElementById('why-panel');
    if (!panel) return;
    if (panel.style.display !== 'none' && panel.dataset.char === charName && panel.dataset.idx === String(historyIndex)) {
        panel.style.display = 'none';
        return;
    }
    panel.dataset.char = charName;
    panel.dataset.idx = String(historyIndex);
    const isErr = (entry.result || '').toLowerCase().includes('valueerror') || (entry.result || '').toLowerCase().includes("don't");
    window.Lit.render(mainJsTag`<div><b>🧠 ${events.tickToTime(entry.tick)}: ${charName}</b></div>
        ${entry.thought ? mainJsTag`<div style="padding:4px 8px;background:rgba(188,140,255,0.1);border-radius:4px;border-left:3px solid var(--purple);margin:4px 0;"><span style="color:var(--purple);font-weight:500;">Thought:</span> ${entry.thought}</div>` : ''}
        <div><span style="color:var(--accent);font-weight:500;">Action:</span> <code>${entry.action || '?'}</code></div>
        <div><span style="color:${isErr ? 'var(--orange)' : 'var(--green)'};font-weight:500;">Result:</span> ${entry.result || 'No result'}</div>`, panel);
    panel.style.display = 'block';
}

    // Guest speech (no character needed)
    function speakAsGuest() {
        const input = document.getElementById('speak-input');
        const text = (input?.value || '').trim();
        if (!text) { input?.focus(); return; }
        
        // Find the active area
        const activePlayer = worldState.activePlayer;
        const activeRoom = activePlayer ? worldState.players?.[activePlayer]?.current_area : worldState.currentArea;
        const areaName = activeRoom || Object.keys(worldState.areas || {})[0];
        
        if (!areaName) {
            events.log('No rooms exist to speak in.', 'error-msg');
            return;
        }
        
        // Third-person identity so NPCs don't read their own speech as "you"
        const speakerName = '👤 A Guest';
    api.playerSpeak(speakerName, text, areaName).then(res => {
        if (res.error) {
            events.log(`Speak failed: ${res.error}`, 'error-msg');
            return;
        }
        events.log(`[${speakerName}] says: "${text}"`, 'msg-speech');
        if (input) input.value = '';
        worldState.fetch();
    });
}

// Speak on Enter key
document.addEventListener('DOMContentLoaded', () => {
    const speakInput = document.getElementById('speak-input');
    if (speakInput) {
        speakInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') speakAsGuest();
        });
    }
});

// Export event stream as text file
function exportEventLog() { WorldExport.exportEventLog(); }

// Copy event stream to clipboard
async function copyEventLogToClipboard() { WorldExport.copyEventLogToClipboard(); }

// LLM prompt/response clipboard helpers
async function copyPromptToClipboard() { WorldExport.copyPromptToClipboard(); }

function copyManualPrompt() { WorldExport.copyManualPrompt(); }

function openPasteModal() {
    document.getElementById('paste-response-textarea').value = '';
    document.getElementById('paste-response-modal').style.display = 'flex';
    document.getElementById('paste-response-textarea').focus();
}

async function pasteFromClipboard() {
    try {
        const text = await navigator.clipboard.readText();
        document.getElementById('paste-response-textarea').value = text;
    } catch (e) {
        events.log('⚠️ Could not read clipboard. Paste manually (Ctrl+V).', 'system-msg');
    }
}

function submitManualResponse() {
    const text = document.getElementById('paste-response-textarea').value.trim();
    if (!text) {
        events.log('⚠️ Paste a response first.', 'system-msg');
        return;
    }
    if (!llmClient._manualMode) {
        events.log('⚠️ Enable ✋ Manual Response Mode in settings first.', 'system-msg');
        return;
    }
    llmClient._manualResponse = text;
    document.getElementById('paste-response-modal').style.display = 'none';
    events.log('📝 Manual response injected! (' + text.length + ' chars) The next agent step will use it.', 'system-msg');
}

// Update time per tick on backend
async function updateTimePerTick(minutes) { SaveLoadView.updateTimePerTick(minutes); }

// Update scenario clock start time on backend
async function updateClockStart(value) { SaveLoadView.updateClockStart(value); }

// New empty scenario
async function newScenario() {
    const voidWorld = {
        players: {}, graph: { nodes: {}, edges: [] },
        time_ticks: 0, turn_number: 0, time_per_tick_minutes: 5,
        clock_start_hour: 8, clock_start_minute: 0
    };
    try {
        const resp = await fetch('/api/load', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(voidWorld)
        });
        const data = await resp.json();
        if (data.error) { toastError('Error: ' + data.error); return; }
        toastInfo('New empty scenario created.');
        worldState.fetch();
    } catch(e) { toastError('Failed to create new scenario: ' + e.message); }
}

// Restart scenario
async function restartScenario() { SaveLoadView.restartScenario(); }

// Toggle spectator
function toggleSpectator() { SaveLoadView.toggleSpectator(); }

/** Populate the new settings form fields from current config values */
function populateSettingsForm() { SettingsView.populateForm(); }

// Auto-scroll toggle
document.addEventListener('DOMContentLoaded', () => {
    const scrollToggle = document.getElementById('stream-auto-scroll');
    if (scrollToggle) {
        scrollToggle.addEventListener('click', () => {
            events.autoScroll = !events.autoScroll;
            scrollToggle.textContent = events.autoScroll ? '📌' : '📍';
            scrollToggle.title = events.autoScroll ? 'Auto-scroll (on)' : 'Auto-scroll (off)';
        });
    }

    if (window.SaveLoadView && typeof window.SaveLoadView.initScenarioNameEditor === 'function') {
        window.SaveLoadView.initScenarioNameEditor();
    }
});

// ============================================
// INITIALIZATION
// ============================================
(async function init() {
    // Wait for config to load from IndexedDB
    await config._initPromise;

    // lit-bootstrap.js is a deferred module script, so window.Lit may not
    // be stamped yet even though main.js runs right after its tag. block
    // until it is ready before anything that renders via window.Lit.
    const litDeadline = Date.now() + 5000;
    while (!window.Lit && Date.now() < litDeadline) {
        await new Promise(resolve => setTimeout(resolve, 20));
    }

    // Show the inspector's lit empty-state on boot (index.html ships no
    // static placeholder — lit never removes children it doesn't own, so a
    // static one would linger above every subsequent render). Skip if the
    // user already selected something before Lit finished loading.
    const bootPanel = document.getElementById('inspector-panel');
    if (bootPanel && !bootPanel.firstElementChild) inspector.hide();

    // Restore event log from IndexedDB (survives refresh)
    await events.restoreLog();
    
    // Configure LLM client from persisted config
    llmClient.configure(config.toLLMConfig());
    llmClient._manualMode = !!config.manualMode;
    
    // Sync filter checkboxes from persisted config
    const syncFilter = (id, val) => { const el = document.getElementById(id); if (el) el.checked = val; };
    syncFilter('filter-thoughts', config.filterThoughts);
    syncFilter('filter-speech', config.filterSpeech);
    syncFilter('filter-actions', config.filterActions);
    syncFilter('filter-system', config.filterSystem);
    syncFilter('filter-rawllm', config.filterRawLLM);
    
    // Initialize agent UI controls
    ui.initAgentUI();
    
    // Initialize profiles and settings
    await ui.initProfiles();
    
    // Initialize graph network
    await graphManager.init();
    
    // Initial state fetch
    await worldState.fetch();
    agentLens.init();
    
    // Fetch equipment slot configuration
    await worldState.fetchEquipSlots();
    
    // Persist event log every 5 seconds
    setInterval(() => events._persistLog(), 5000);
    
    // Wire state change handler for UI rendering
    worldState.on('update', (state) => {
        // Re-initialize or clear turn queue after scenario load/reset
        if (state?.players) {
            if (Object.keys(state.players).length === 0) {
                agent.turnQueue.length = 0;
            } else if (agent.turnQueue.length === 0) {
                agent.initializeTurnQueue();
            }
        }
        ui.renderAll(state);
        
        // Update play/pause buttons
        ui.showPlayPause(!config.running, config.running);
        
        // Reload graph data to reflect any changes (nodes deleted, edges added/removed, etc.)
        graphManager.loadGraphData();
    });
    
    // Command input handler & Tab autocomplete (task-6)
    const inputField = document.getElementById('command-input');
    if (inputField) {
        let autocompleteState = {
            active: false,
            verb: '',
            prefix: '',
            options: [],
            index: -1
        };

        const resetAutocomplete = () => {
            autocompleteState = { active: false, verb: '', prefix: '', options: [], index: -1 };
        };

        inputField.addEventListener('keydown', async function(e) {
            if (e.key === 'Tab') {
                const val = this.value;
                const match = val.match(/^(\S+)\s+(.*)$/);
                if (!match) return; // Only trigger if verb + space typed

                e.preventDefault();
                const verb = match[1].toLowerCase();
                const typedPrefix = match[2];

                if (autocompleteState.active && autocompleteState.verb === verb && autocompleteState.prefix === typedPrefix) {
                    if (autocompleteState.options.length === 0) return;
                    if (e.shiftKey) {
                        autocompleteState.index = (autocompleteState.index - 1 + autocompleteState.options.length) % autocompleteState.options.length;
                    } else {
                        autocompleteState.index = (autocompleteState.index + 1) % autocompleteState.options.length;
                    }
                    const selected = autocompleteState.options[autocompleteState.index];
                    this.value = `${verb} ${selected}`;
                    autocompleteState.prefix = selected;
                    return;
                }

                const activeChar = (typeof ui !== 'undefined' && ui.selectedAgent) ? ui.selectedAgent : null;
                const res = await ApiClient.getAutocomplete(verb, typedPrefix, activeChar);
                const opts = res?.options || [];
                if (opts.length === 0) {
                    resetAutocomplete();
                    return;
                }

                const firstOpt = opts[0];
                autocompleteState = {
                    active: true,
                    verb: verb,
                    prefix: firstOpt,
                    options: opts,
                    index: 0
                };
                this.value = `${verb} ${firstOpt}`;
                return;
            }

            if (e.key !== 'Shift') {
                resetAutocomplete();
            }
        });

        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && this.value.trim()) {
                resetAutocomplete();
                const cmd = this.value.trim();
                events.log('> ' + cmd, 'user-msg');
                this.value = '';
                api.action(cmd).then(data => {
                    const msg = data?.output || data?.error || cmd;
                    events.log(msg, msg.includes('ValueError') ? 'error-msg' : 'system-msg');
                    if (data?.system_messages) {
                        data.system_messages.forEach(sm => events.log(sm, 'system-msg'));
                    }
                    worldState.fetch();
                });
            }
        });
    }
    
                // Initialize ghost mode toggle from backend
                (async () => {
                    try {
                        const res = await ApiClient.getGhostMode();
                        const cb = document.getElementById('agent-ghost-mode');
                        if (cb) {
                            cb.checked = res.ghost_mode;
                            config.ghostMode = res.ghost_mode;
                            cb.addEventListener('change', async () => {
                                config.ghostMode = cb.checked;
                                await ApiClient.setGhostMode(cb.checked);
                                // Rebuild turn queue to reflect new ghost mode state
                                if (config.turnBased) {
                                    agent.initializeTurnQueue();
                                }
                                events.log(`👻 Ghost mode ${cb.checked ? 'activated' : 'deactivated'}`, 'system-msg');
                            });
                        }
                    } catch (e) {
                        console.warn('Ghost mode init:', e);
                        // If backend doesn't support it, still check config persistence
                        const cb = document.getElementById('agent-ghost-mode');
                        if (cb) {
                            cb.checked = config.ghostMode;
                            cb.addEventListener('change', () => {
                                config.ghostMode = cb.checked;
                                if (config.turnBased) {
                                    agent.initializeTurnQueue();
                                }
                            });
                        }
                    }
                })();

                // Initialize narration mode select from backend
                (async () => {
                    try {
                        await window.narrationUI._initPromise;
                        const select = document.getElementById('narration-select');
                        if (select) {
                            select.value = window.narrationUI.getMode();
                        }
                    } catch (e) {
                        console.warn('Narration init:', e);
                    }
                })();

                // Initialize panel resizing
                _initResizable();

                events.log('VirtualWorld Engine initialized', 'system-msg');
            })();

/** Initialize drag-to-resize for panel dividers */
function _initResizable() {
    // Left panel resize
    const leftHandle = document.getElementById('left-resize-handle');
    const leftPanel = document.getElementById('left-panel');
    if (leftHandle && leftPanel) {
        leftHandle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const startX = e.clientX;
            const startW = leftPanel.offsetWidth;
            const minW = 180;
            const maxW = 600;
            const onMove = (ev) => {
                const w = Math.min(maxW, Math.max(minW, startW + ev.clientX - startX));
                leftPanel.style.width = w + 'px';
                leftPanel.style.flexGrow = '0';
            };
            const onUp = () => {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                document.body.style.cursor = '';
                leftHandle.style.pointerEvents = '';
            };
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
            document.body.style.cursor = 'col-resize';
            leftHandle.style.pointerEvents = 'none';
        });
    }

    // Event stream vertical resize
    const eventSection = document.getElementById('event-section');
    if (eventSection) {
        // Create a vertical handle at the top of the event section
        const vHandle = document.createElement('div');
        vHandle.className = 'resize-handle-horizontal';
        vHandle.style.position = 'relative';
        vHandle.style.top = '-2px';
        vHandle.style.marginBottom = '-4px';
        vHandle.style.zIndex = '10';
        vHandle.title = 'Drag to resize event stream';
        eventSection.parentNode.insertBefore(vHandle, eventSection);

        vHandle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const startY = e.clientY;
            const startH = eventSection.offsetHeight;
            const minH = 80;
            const maxH = window.innerHeight * 0.7;
            const onMove = (ev) => {
                const h = Math.min(maxH, Math.max(minH, startH - (ev.clientY - startY)));
                eventSection.style.height = h + 'px';
                eventSection.style.flexShrink = '0';
            };
            const onUp = () => {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                document.body.style.cursor = '';
                vHandle.style.pointerEvents = '';
            };
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
            document.body.style.cursor = 'row-resize';
            vHandle.style.pointerEvents = 'none';
        });
    }
}
