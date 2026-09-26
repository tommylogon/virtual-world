/**
 * ConfigManager — Settings and profile management with IndexedDB persistence
 *
 * @module config — user settings, saved API profiles, and `toLLMConfig()`
 * @contributes the `config` singleton: model/keys, thinking, graph physics, UI toggles
 * @powers the Settings modal, profile switching, model picker, and every feature flag
 * @relates persists via storage.js; read by llm-client, graph, agent, and the UI
 * @docs docs/virtualWorld/UI & Settings/Settings & Configuration.md
 */
class ConfigManager {
    constructor() {
        this._ready = false;
        this._initPromise = this._init();
    }

    async _init() {
        await this._loadFromStorage();
        this._ready = true;
    }

    async _loadFromStorage() {
        this.apiKey = await storage.getConfig('api_key') || '';
        this.apiBase = await storage.getConfig('api_base') || 'https://api.openai.com/v1';
        this.model = await storage.getConfig('model') || 'gpt-4.1-mini';
        this.provider = await storage.getConfig('provider') || 'openai';
        this.temperature = await storage.getConfig('temperature') || '0.7';
        this.maxTokens = parseInt(await storage.getConfig('max_tokens')) || 512;
        this.softMaxTokens = parseInt(await storage.getConfig('soft_max_tokens')) || 0;
        this.showLogs = (await storage.getConfig('show_logs')) === 'true';
        this.streaming = (await storage.getConfig('streaming')) === 'true';
        this.turnBased = (await storage.getConfig('turn_based')) === 'true';
        this.turnOrder = await storage.getConfig('turn_order') || 'sequential';
        this.tickInterval = parseInt(await storage.getConfig('tick_interval')) || 10;
        this.frontendTemplate = await storage.getConfig('frontend_template') || 'index';
        this.lastProfile = await storage.getConfig('last_profile') || null;
        // Reactive mode: true = thought→act→react, false = combined single-step
        this.reactiveMode = (await storage.getConfig('reactive_mode')) !== 'false';

        // Graph visualization settings
        this.graphSpringLength = parseInt(await storage.getConfig('graph_spring_length')) || 100;
        this.graphGravitationalConstant = parseInt(await storage.getConfig('graph_gravitational_constant')) || -40;
        this.graphDamping = parseFloat(await storage.getConfig('graph_damping')) || 0.4;
        this.graphSpringConstant = parseFloat(await storage.getConfig('graph_spring_constant')) || 0.02;
        this.graphItemEdgeLength = parseInt(await storage.getConfig('graph_item_edge_length')) || 60;
        this.graphSolver = await storage.getConfig('graph_solver') || 'forceAtlas2Based';
        this.graphEdgeWidth = parseInt(await storage.getConfig('graph_edge_width')) || 1;
        this.graphArrows = (await storage.getConfig('graph_arrows')) !== 'false';
        this.graphImprovedLayout = (await storage.getConfig('graph_improved_layout')) === 'true';
        // Graph layout mode (task-485): 'free' = force physics with contents held
        // on a parent-relative offset; 'levels' = vis hierarchical layout, where
        // the layout engine places every node by relation level (physics off).
        this.graphLayoutMode = await storage.getConfig('graph_layout_mode') || 'free';
        // Map-layout pitch (task-523 follow-up): px per painted cell, i.e. the
        // padding between areas in Map mode. 40px = an area every 40px with the
        // way at the midpoint; raise it to de-clutter a dense painted grid.
        this.graphMapSpacing = parseInt(await storage.getConfig('graphMapSpacing')) || 40;
        // Node separation (graph/separation.js): nearby item/character nodes
        // push apart unless an edge already joins them. `min` is the distance
        // under which they repel, `max` the distance beyond which a pair is
        // ignored (and the grid cell size, so it bounds the cost).
        this.graphRepelEnabled = (await storage.getConfig('graph_repel_enabled')) !== 'false';
        this.graphRepelMin = parseInt(await storage.getConfig('graph_repel_min')) || 55;
        this.graphRepelMax = parseInt(await storage.getConfig('graph_repel_max')) || 220;
        this.graphRepelStrength = parseFloat(await storage.getConfig('graph_repel_strength')) || 0.6;
        // Restoring pull toward the parent for nodes separation displaced, so a
        // crowded room's contents do not drift outward. 0 = no pull.
        this.graphRepelPull = parseFloat(await storage.getConfig('graph_repel_pull'));
        if (!Number.isFinite(this.graphRepelPull)) this.graphRepelPull = 0.12;

        // Ghost mode: when true, dead characters can still act as ghosts
        this.ghostMode = (await storage.getConfig('ghost_mode')) === 'true';
        // Mature content opt-in (task-206): gates the pleasure/arousal subsystem
        this.matureContent = (await storage.getConfig('mature_content')) === 'true';
        // Raw LLM exchange capture opt-in (task-405): feeds the LLM inspector
        this.showRawLLM = (await storage.getConfig('show_raw_llm')) === 'true';
        // End-of-turn memory opt-in: memories are normally written at the START
        // of a character's turn, so asking for one at the END is optional.
        this.endOfTurnMemory = (await storage.getConfig('end_of_turn_memory')) === 'true';
        this.manualMode = (await storage.getConfig('manual_mode')) === 'true';

        // Invalid-action auto-retry (task-361): when an agent action fails, give
        // it one same-turn retry with the error fed back (default off).
        this.autoRetryInvalid = (await storage.getConfig('auto_retry_invalid')) === 'true';

        // task-101: the turn mode dial owns the simultaneous variants; the
        // legacy boolean setting is folded in so an old save keeps working.
        // "simultaneous_room" resolves rooms independently with characters
        // inside a room acting in order.
        this.turnOrder = window.VWSimultaneous.normalizeMode(
            await storage.getConfig('simultaneous_mode'),
            this.turnOrder
        );

        // Structured output: send response_format (json_schema / json_object)
        // with every LLM call that expects JSON. Auto-degrades per session when
        // the provider rejects the parameter (default on).
        this.structuredOutput = (await storage.getConfig('structured_output')) !== 'false';

        // Auto-generate equipment descriptions on equip/unequip (default on)
        this.autoGenerateDescriptions = (await storage.getConfig('auto_generate_descriptions')) !== 'false';

        // Embedding settings (task-91: OpenAI-compatible endpoint, browser-side
        // calls; vectors stored server-side. Dims 0 = auto-detect from first call)
        this.embedEnabled = (await storage.getConfig('embed_enabled')) === 'true';
        this.embedUrl = await storage.getConfig('embed_url') || 'http://localhost:1234/v1';
        this.embedModel = await storage.getConfig('embed_model') || 'text-embedding-nomic-embed-text-v1.5';
        this.embedDims = parseInt(await storage.getConfig('embed_dims')) || 0;
        this.embedApiKey = await storage.getConfig('embed_api_key') || '';

        // Thinking mode: sends reasoning_effort + thinking extra_body for reasoning models
        this.thinking = (await storage.getConfig('thinking')) === 'true';
        this.thinkingEffort = await storage.getConfig('thinking_effort') || 'high';

        // Suppress local thinking: injects empty assistant message to bypass
        // Qwen 3.5 reasoning block in LM Studio (workaround for API ignore)
        this.suppressLocalThinking = (await storage.getConfig('suppress_local_thinking')) !== 'false';

        // API format: auto | chat-completions | responses (auto resolves to chat-completions)
        this.apiFormat = await storage.getConfig('api_format') || 'auto';

        // Rate limiter (requests per minute — 0 = disabled)
        this.rpmLimit = parseInt(await storage.getConfig('rpm_limit')) || 0;
        // Token rate limiter (tokens per minute — 0 = disabled)
        this.tpmLimit = parseInt(await storage.getConfig('tpm_limit')) || 0;

        // Message filters: which types to show in event stream
        this.filterThoughts = (await storage.getConfig('filter_thoughts')) !== 'false';
        this.filterSpeech = (await storage.getConfig('filter_speech')) !== 'false';
        this.filterActions = (await storage.getConfig('filter_actions')) !== 'false';
        this.filterSystem = (await storage.getConfig('filter_system')) !== 'false';
        this.filterRawLLM = (await storage.getConfig('filter_rawllm')) !== 'false';
        this.filterRecalls = (await storage.getConfig('filter_recalls')) !== 'false';
        this.filterNpc = (await storage.getConfig('filter_npc')) !== 'false';

        this.running = false;
        this.busy = false;
        this.maxSteps = 10;
        this.stepsRun = 0;

        // Runtime maps
        this.lastActionResult = {};
        this.lastRoom = {};
        this._lastRoomMap = {};
        this._lastActionResultMap = {};
    }

    /** The simultaneous variant in effect, or false (derived from turnOrder). */
    get simultaneousMode() {
        return window.VWSimultaneous.isSimultaneous(this.turnOrder) ? this.turnOrder : false;
    }

    /**
     * Select a turn mode from the dial. The simultaneous variants conflict with
     * the turn queue, so choosing one turns Turn-Based Mode off.
     */
    async setTurnMode(mode) {
        this.turnOrder = window.VWSimultaneous.normalizeMode(mode, this.turnOrder);
        if (window.VWSimultaneous.isSimultaneous(this.turnOrder)) {
            this.turnBased = false;
            const turnBased = document.getElementById('agent-turn-based');
            if (turnBased) turnBased.checked = false;
            events.log(
                this.turnOrder === 'simultaneous_room'
                    ? '🏘️ Simultaneous per room enabled (rooms resolve independently)'
                    : '🌊 Simultaneous mode enabled (experimental — chaos by design)',
                'system-msg'
            );
        } else if (window.TurnQueue && this.turnBased) {
            TurnQueue.initialize();
        }
        await this.save();
        if (window.appEvents) appEvents.emit('state:updated', worldState?.data);
    }

    async save() {
        await storage.setConfig('api_key', this.apiKey);
        await storage.setConfig('api_base', this.apiBase);
        await storage.setConfig('model', this.model);
        await storage.setConfig('temperature', this.temperature);
        await storage.setConfig('max_tokens', String(this.maxTokens));
        await storage.setConfig('soft_max_tokens', String(this.softMaxTokens));
        await storage.setConfig('show_logs', this.showLogs ? 'true' : 'false');
        await storage.setConfig('streaming', this.streaming ? 'true' : 'false');
        await storage.setConfig('turn_based', this.turnBased ? 'true' : 'false');
        await storage.setConfig('turn_order', this.turnOrder);
        await storage.setConfig('tick_interval', String(this.tickInterval));
        await storage.setConfig('frontend_template', this.frontendTemplate);
        await storage.setConfig('last_profile', this.lastProfile || '');
        await storage.setConfig('reactive_mode', this.reactiveMode ? 'true' : 'false');
        await storage.setConfig('ghost_mode', this.ghostMode ? 'true' : 'false');
        await storage.setConfig('mature_content', this.matureContent ? 'true' : 'false');
        await storage.setConfig('show_raw_llm', this.showRawLLM ? 'true' : 'false');
        await storage.setConfig('end_of_turn_memory', this.endOfTurnMemory ? 'true' : 'false');
        await storage.setConfig('rpm_limit', String(this.rpmLimit));
        await storage.setConfig('tpm_limit', String(this.tpmLimit));
        await storage.setConfig('filter_thoughts', this.filterThoughts ? 'true' : 'false');
        await storage.setConfig('filter_speech', this.filterSpeech ? 'true' : 'false');
        await storage.setConfig('filter_actions', this.filterActions ? 'true' : 'false');
        await storage.setConfig('filter_system', this.filterSystem ? 'true' : 'false');
        await storage.setConfig('filter_rawllm', this.filterRawLLM ? 'true' : 'false');
        await storage.setConfig('filter_recalls', this.filterRecalls ? 'true' : 'false');
        await storage.setConfig('filter_npc', this.filterNpc ? 'true' : 'false');
        await storage.setConfig('manual_mode', this.manualMode ? 'true' : 'false');
        await storage.setConfig('auto_retry_invalid', this.autoRetryInvalid ? 'true' : 'false');
        await storage.setConfig('simultaneous_mode', this.simultaneousMode || 'false');
        await storage.setConfig('structured_output', this.structuredOutput ? 'true' : 'false');
        await storage.setConfig('auto_generate_descriptions', this.autoGenerateDescriptions ? 'true' : 'false');
        await storage.setConfig('embed_enabled', this.embedEnabled ? 'true' : 'false');
        await storage.setConfig('embed_url', this.embedUrl);
        await storage.setConfig('embed_model', this.embedModel);
        await storage.setConfig('embed_dims', String(this.embedDims));
        await storage.setConfig('embed_api_key', this.embedApiKey);
        await storage.setConfig('thinking', this.thinking ? 'true' : 'false');
        await storage.setConfig('thinking_effort', this.thinkingEffort);
        await storage.setConfig('suppress_local_thinking', this.suppressLocalThinking ? 'true' : 'false');
        await storage.setConfig('api_format', this.apiFormat);
        await storage.setConfig('graph_spring_length', String(this.graphSpringLength));
        await storage.setConfig('graph_gravitational_constant', String(this.graphGravitationalConstant));
        await storage.setConfig('graph_damping', String(this.graphDamping));
        await storage.setConfig('graph_spring_constant', String(this.graphSpringConstant));
        await storage.setConfig('graph_item_edge_length', String(this.graphItemEdgeLength));
        await storage.setConfig('graph_solver', this.graphSolver);
        await storage.setConfig('graph_edge_width', String(this.graphEdgeWidth));
        await storage.setConfig('graph_arrows', this.graphArrows ? 'true' : 'false');
        await storage.setConfig('graph_improved_layout', this.graphImprovedLayout ? 'true' : 'false');
        await storage.setConfig('graph_layout_mode', this.graphLayoutMode || 'free');
        await storage.setConfig('graph_repel_enabled', this.graphRepelEnabled ? 'true' : 'false');
        await storage.setConfig('graph_repel_min', String(this.graphRepelMin));
        await storage.setConfig('graph_repel_max', String(this.graphRepelMax));
        await storage.setConfig('graph_repel_strength', String(this.graphRepelStrength));
        await storage.setConfig('graph_repel_pull', String(this.graphRepelPull));

        this._saveToCurrentProfile();
    }

    async _saveToCurrentProfile() {
        try {
            const profileSelect = document.getElementById('profile-select');
            if (!profileSelect?.value) return;
            const currentProfile = profileSelect.value;
            const profileData = await storage.getProfile(currentProfile);
            if (profileData) {
                profileData.apiKey = this.apiKey;
                profileData.apiBase = this.apiBase;
                profileData.model = this.model;
                profileData.streaming = this.streaming;
                profileData.showLogs = this.showLogs;
                profileData.turnBased = this.turnBased;
                profileData.turnOrder = this.turnOrder;
                profileData.apiFormat = this.apiFormat;
                await storage.setProfile(currentProfile, profileData);
            }
        } catch (e) {
            console.warn('Failed to save to current profile:', e);
        }
    }

    async saveFromForm() {
        this.apiKey = document.getElementById('api-key-input')?.value.trim() || '';
        this.apiBase = (document.getElementById('api-base-input')?.value.trim() || document.getElementById('agent-api-base')?.value.trim() || 'https://api.openai.com/v1');
        this.model = document.getElementById('agent-model')?.value.trim() || 'gpt-4.1-mini';
        this.temperature = document.getElementById('agent-temperature')?.value || this.temperature;
        this.maxTokens = parseInt(document.getElementById('max-tokens-input')?.value) || this.maxTokens;
        this.softMaxTokens = parseInt(document.getElementById('soft-max-tokens-input')?.value) || this.softMaxTokens;
        this.turnBased = document.getElementById('agent-turn-based')?.checked || false;
        const turnOrderEl = document.getElementById('agent-turn-order');
        if (turnOrderEl) {
            this.turnOrder = window.VWSimultaneous.normalizeMode(turnOrderEl.value, this.turnOrder);
            // Simultaneous variants ignore the turn queue, so they imply turn-based off.
            if (window.VWSimultaneous.isSimultaneous(this.turnOrder)) this.turnBased = false;
        }
        this.showLogs = document.getElementById('agent-show-logs')?.checked || false;
        this.streaming = document.getElementById('agent-streaming')?.checked || false;
        this.reactiveMode = document.getElementById('agent-reactive-mode')?.checked ?? this.reactiveMode;
        this.ghostMode = document.getElementById('agent-ghost-mode')?.checked ?? this.ghostMode;
        this.matureContent = document.getElementById('agent-mature-content')?.checked ?? this.matureContent;
        this.showRawLLM = document.getElementById('agent-show-raw-llm')?.checked ?? this.showRawLLM;
        this.endOfTurnMemory = document.getElementById('agent-end-of-turn-memory')?.checked ?? this.endOfTurnMemory;
        this.manualMode = document.getElementById('agent-manual-mode')?.checked ?? this.manualMode;
        this.autoRetryInvalid = document.getElementById('agent-auto-retry-invalid')?.checked ?? this.autoRetryInvalid;
        this.structuredOutput = document.getElementById('agent-structured-output')?.checked ?? this.structuredOutput;
        this.autoGenerateDescriptions = document.getElementById('agent-auto-generate-descriptions')?.checked ?? this.autoGenerateDescriptions;
        this.embedEnabled = document.getElementById('embed-enabled')?.checked ?? this.embedEnabled;
        this.embedUrl = document.getElementById('embed-url')?.value.trim() || this.embedUrl;
        this.embedModel = document.getElementById('embed-model')?.value.trim() || this.embedModel;
        this.embedDims = parseInt(document.getElementById('embed-dims')?.value) || 0;
        this.embedApiKey = document.getElementById('embed-api-key')?.value.trim() ?? this.embedApiKey;
        this.thinking = document.getElementById('agent-thinking')?.checked ?? this.thinking;
        this.thinkingEffort = document.getElementById('agent-thinking-effort')?.value || this.thinkingEffort;
        this.suppressLocalThinking = document.getElementById('agent-suppress-local-thinking')?.checked ?? this.suppressLocalThinking;
        this.apiFormat = document.getElementById('agent-api-format')?.value || this.apiFormat;
        const rpmInput = document.getElementById('agent-rpm-limit');
        if (rpmInput) this.rpmLimit = parseInt(rpmInput.value) || 0;
        const tpmInput = document.getElementById('agent-tpm-limit');
        if (tpmInput) this.tpmLimit = parseInt(tpmInput.value) || 0;
        await this.save();
        
        VW.llm._manualMode = !!this.manualMode;
        if (!VW.llm._manualMode) VW.llm._manualResponse = null;
        
        const profileSelect = document.getElementById('profile-select');
        const currentProfile = profileSelect?.value;
        if (currentProfile) {
            const profileData = await storage.getProfile(currentProfile);
            if (profileData) {
                profileData.apiKey = this.apiKey;
                profileData.apiBase = this.apiBase;
                profileData.model = this.model;
                profileData.streaming = this.streaming;
                profileData.showLogs = this.showLogs;
                profileData.turnBased = this.turnBased;
                profileData.turnOrder = this.turnOrder;
                profileData.apiFormat = this.apiFormat;
                await storage.setProfile(currentProfile, profileData);
            }
        }
        
        VW?.llm?.configure(this.toLLMConfig());
        events.log('Settings saved.', 'system-msg');
    }

    toLLMConfig() {
        return {
            apiKey: this.apiKey,
            apiBase: this.apiBase,
            model: this.model,
            provider: this.provider,
            streaming: this.streaming,
            showLogs: this.showLogs,
            thinking: this.thinking,
            thinkingEffort: this.thinkingEffort,
            suppressLocalThinking: this.suppressLocalThinking,
            apiFormat: this.apiFormat
        };
    }

    // --- Profile Management ---

    async getProfiles() {
        const profiles = await storage.getAllProfiles();
        if (Object.keys(profiles).length === 0) {
            const defaults = this._getDefaultProfiles();
            for (const [name, data] of Object.entries(defaults)) {
                await storage.setProfile(name, data);
            }
            return defaults;
        }
        return profiles;
    }

    async getProfile(name) {
        return storage.getProfile(name);
    }

    async saveProfile(name, data) {
        await storage.setProfile(name, data);
    }

    async deleteProfile(name) {
        await storage.deleteProfile(name);
    }

    async applyProfile(name) {
        const profile = await storage.getProfile(name);
        if (!profile) return;
        
        this.apiKey = profile.apiKey || '';
        this.apiBase = profile.apiBase || 'https://api.openai.com/v1';
        this.model = profile.model || 'gpt-4.1-mini';
        this.streaming = !!profile.streaming;
        this.showLogs = !!profile.showLogs;
        this.turnBased = !!profile.turnBased;
        this.turnOrder = window.VWSimultaneous.normalizeMode(
            profile.simultaneousMode || profile.turnOrder,
            profile.turnOrder
        );
        if (window.VWSimultaneous.isSimultaneous(this.turnOrder)) this.turnBased = false;
        this.apiFormat = profile.apiFormat || 'auto';
        this.lastProfile = name;

        await this.save();
        
        VW?.llm?.configure(this.toLLMConfig());
        if (VW?.llm) {
            VW.llm._manualMode = !!this.manualMode;
            if (!VW.llm._manualMode) VW.llm._manualResponse = null;
        }
        
        (async () => {
            const modelSelect = document.getElementById('agent-model-select');
            if (modelSelect) {
                await VW?.ui?.populateModelSelect(profile.apiBase);
            }
        })();
        
        const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ''; };
        setVal('agent-api-key', profile.apiKey);
        setVal('api-key-input', profile.apiKey);
        setVal('agent-api-base', profile.apiBase);
        setVal('api-base-input', profile.apiBase);
        setVal('agent-model', profile.model);
        setVal('agent-turn-order', this.turnOrder);
        setVal('agent-api-format', profile.apiFormat || 'auto');
        
        document.getElementById('agent-turn-based') && (document.getElementById('agent-turn-based').checked = !!profile.turnBased);
        document.getElementById('agent-show-logs') && (document.getElementById('agent-show-logs').checked = !!profile.showLogs);
        document.getElementById('agent-streaming') && (document.getElementById('agent-streaming').checked = !!profile.streaming);
        
        const turnSettings = document.getElementById('turn-settings');
        if (turnSettings) turnSettings.style.display = profile.turnBased ? 'block' : 'none';

        events.log(`Switched to profile: ${name}`, 'system-msg');
    }

    getCurrentSettingsObject() {
        return {
            apiKey: document.getElementById('agent-api-key')?.value.trim() || this.apiKey,
            apiBase: document.getElementById('agent-api-base')?.value.trim() || this.apiBase,
            model: document.getElementById('agent-model')?.value.trim() || this.model,
            streaming: document.getElementById('agent-streaming')?.checked || false,
            showLogs: document.getElementById('agent-show-logs')?.checked || false,
            turnBased: document.getElementById('agent-turn-based')?.checked || false,
            turnOrder: (() => {
                const el = document.getElementById('agent-turn-order');
                return el ? window.VWSimultaneous.normalizeMode(el.value, this.turnOrder) : this.turnOrder;
            })(),
            apiFormat: document.getElementById('agent-api-format')?.value || this.apiFormat
        };
    }

    async saveProfileFromCurrent() {
        const sel = document.getElementById('profile-select');
        const name = sel?.value;
        if (!name) {
            this.saveProfileAsNew();
            return;
        }
        await storage.setProfile(name, this.getCurrentSettingsObject());
        events.log(`Profile "${name}" updated.`, 'system-msg');
    }

    async saveProfileAsNew() {
        const name = prompt('Enter a name for this profile:', '');
        if (!name || !name.trim()) return;
        await storage.setProfile(name.trim(), this.getCurrentSettingsObject());
        await VW?.ui?.populateProfileSelect();
        const sel = document.getElementById('profile-select');
        if (sel) sel.value = name.trim();
        events.log(`New profile "${name.trim()}" saved.`, 'system-msg');
    }

    async deleteProfile_() {
        const sel = document.getElementById('profile-select');
        const name = sel?.value;
        if (!name) return;
        if (!confirm(`Delete profile "${name}"?`)) return;
        await storage.deleteProfile(name);
        await VW?.ui?.populateProfileSelect();
        events.log(`Profile "${name}" deleted.`, 'system-msg');
    }

    _getDefaultProfiles() {
        const liveKey = this.apiKey || '';
        return {
            'OpenAI (GPT-4.1-mini)': {
                apiKey: liveKey, apiBase: 'https://api.openai.com/v1', model: 'gpt-4.1-mini',
                streaming: false, showLogs: false, turnBased: false, turnOrder: 'sequential'
            },
            'OpenAI (GPT-4o)': {
                apiKey: liveKey, apiBase: 'https://api.openai.com/v1', model: 'gpt-4o',
                streaming: false, showLogs: false, turnBased: false, turnOrder: 'sequential'
            },
            'LM Studio (Local)': {
                apiKey: 'not-needed', apiBase: 'http://localhost:1234/v1', model: '',
                streaming: true, showLogs: false, turnBased: false, turnOrder: 'sequential'
            },
            // DeepSeek is OpenAI-format compatible; base_url https://api.deepseek.com
            // also works (the /v1 suffix is what the OpenAI SDK-style calls here
            // expect). Current model names are `deepseek-flash` and
            // `deepseek-v4-pro`; deepseek-v4-flash / deepseek-chat /
            // deepseek-reasoner are retired legacy aliases.
            'DeepSeek': {
                apiKey: liveKey, apiBase: 'https://api.deepseek.com/v1', model: 'deepseek-flash',
                streaming: true, showLogs: false, turnBased: false, turnOrder: 'sequential'
            },
            'DeepSeek (V4 Pro)': {
                apiKey: liveKey, apiBase: 'https://api.deepseek.com/v1', model: 'deepseek-v4-pro',
                streaming: true, showLogs: false, turnBased: false, turnOrder: 'sequential'
            },
            'Groq': {
                apiKey: liveKey, apiBase: 'https://api.groq.com/openai/v1', model: 'llama3-70b-8192',
                streaming: false, showLogs: false, turnBased: false, turnOrder: 'sequential'
            }
        };
    }

    async switchProfile(profileName) {
        if (!profileName) return;
        await this.applyProfile(profileName);
    }
}

const config = new ConfigManager();