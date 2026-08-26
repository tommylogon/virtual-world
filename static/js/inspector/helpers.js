/**
 * InspectorHelpers — Shared utility methods used across inspector views
 * Extracted from inspector.js for modularity.
 * All functions access globals (worldState, api, events, VW.inspector) directly.
 *
 * task-216: HTML-producing functions return lit-html TemplateResults
 * (via window.Lit.html) instead of strings, so consumers can nest them
 * in their own templates without escaping issues.
 */

window.InspectorHelpers = (() => {
    const H = {};
    // Lazy tag: classic scripts run before the deferred module bootstrap,
    // so window.Lit only exists at call time (when views render).
    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

    /**
     * Build lit-html for per-node graph physics gravity control
     * @param {string} nodeId - Graph node ID
     * @param {object} props - Node properties
     * @returns {TemplateResult}
     */
    H.graphGravityControl = function(nodeId, props = {}) {
        const enabled = props.central_gravity_enabled !== false;
        return htmlTag`<div class="inspector-section">
            <h3>Graph Physics</h3>
            <div class="field">
                <label title="When off, this node is excluded from graph physics and stays in place.">
                    <input type="checkbox" ?checked=${enabled}
                        @change=${(ev) => H.setCentralGravity(nodeId, ev.target.checked)}>
                    Central pull enabled
                </label>
                <div class="section-hint" style="margin-top:4px;">Turn off to lock this node in place while the rest of the graph moves.</div>
            </div>
        </div>`;
    };

    /**
     * Toggle central gravity for a node
     * @param {string} nodeId - Graph node ID
     * @param {boolean} enabled - Whether central gravity is enabled
     */
    H.setCentralGravity = async function(nodeId, enabled) {
        const saved = await api.updateNode(nodeId, {
            properties: { central_gravity_enabled: enabled }
        });
        if (!saved) {
            console.warn(`Could not update graph gravity for node ${nodeId}`);
            return;
        }
        await worldState.fetch();
        if (graphManager) {
            graphManager.loadGraphData();
        }
    };

    /**
     * Add a parameter key-value pair to a node (reads from #param-key-{nodeId}, #param-val-{nodeId})
     * @param {string} nodeId - Graph node ID
     */
    H.addParam = async function(nodeId) {
        const keyInput = document.getElementById(`param-key-${nodeId}`);
        const valInput = document.getElementById(`param-val-${nodeId}`);
        if (!keyInput || !valInput) return;
        const key = keyInput.value.trim();
        const val = valInput.value.trim();
        if (!key) { events.log('Parameter key cannot be empty.', 'error-msg'); return; }
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const params = Object.assign({}, node.properties?.parameters || {});
        params[key] = val;
        await api.updateNode(nodeId, { properties: { parameters: params } });
        worldState.fetch();
    };

    /**
     * Remove a parameter by key from a node
     * @param {string} nodeId - Graph node ID
     * @param {string} key - Parameter key to remove
     */
    H.removeParam = async function(nodeId, key) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const params = Object.assign({}, node.properties?.parameters || {});
        delete params[key];
        await api.updateNode(nodeId, { properties: { parameters: params } });
        worldState.fetch();
    };

    /**
     * Update a parameter key name
     * @param {string} nodeId - Graph node ID
     * @param {string} oldKey - Current key name
     * @param {string} newKey - New key name
     */
    H.updateParamKey = async function(nodeId, oldKey, newKey) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const params = Object.assign({}, node.properties?.parameters || {});
        if (!(oldKey in params)) return;
        if (oldKey === newKey) return;
        if (!newKey.trim()) { events.log('Key cannot be empty.', 'error-msg'); return; }
        params[newKey.trim()] = params[oldKey];
        delete params[oldKey];
        await api.updateNode(nodeId, { properties: { parameters: params } });
        worldState.fetch();
    };

    /**
     * Update a parameter value
     * @param {string} nodeId - Graph node ID
     * @param {string} key - Parameter key
     * @param {string} value - New value
     */
    H.updateParamValue = async function(nodeId, key, value) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const params = Object.assign({}, node.properties?.parameters || {});
        params[key] = value;
        await api.updateNode(nodeId, { properties: { parameters: params } });
        worldState.fetch();
    };

    /**
     * Save personality text from the inspector textarea
     * @param {string} charName - Character name
     */
    H.savePersonality = async function(charName) {
        const ta = document.getElementById('inspector-personality');
        if (!ta) return;
        await ApiClient.updateCharacter(charName, { personality: ta.value });
        worldState.fetch();
        events.log('Personality saved.', 'system-msg');
    };

    /**
     * Save description and base description from inspector textareas
     * @param {string} charName - Character name
     */
    H.saveDescription = async function(charName) {
        const ta = document.getElementById('inspector-description');
        const baseTa = document.getElementById('inspector-base-description');
        const payload = {};
        if (ta) payload.description = ta.value;
        if (baseTa) payload.base_description = baseTa.value;
        await ApiClient.updateCharacter(charName, payload);
        worldState.fetch();
        events.log('Appearance saved.', 'system-msg');
    };

    /**
     * Rename a graph node
     * @param {string} oldId - Current node ID
     * @param {string} newId - Desired new node ID
     */
    H.renameNode = async function(oldId, newId) {
        const cleaned = newId.toLowerCase().replace(/\s+/g, '_');
        if (cleaned === oldId) return;
        if (!cleaned) { events.log('ID cannot be empty.', 'error-msg'); return; }
        const res = await ApiClient.renameNode(oldId, cleaned);
        if (res.error) { events.log(`Rename failed: ${res.error}`, 'error-msg'); return; }
        events.log(`Renamed "${oldId}" → "${cleaned}"`, 'system-msg');
        worldState.fetch();
        if (window.VW?.inspector) window.VW.inspector.showNode(cleaned);
    };

    /**
     * Sync node ID from its display name: derives {type}_{sanitized_name}
     * and renames if different. Handles duplicate protection (backend returns 409).
     * @param {string} nodeId - Current node ID
     * @param {string} displayName - Current display name
     */
    H.syncIdFromName = async function(nodeId, displayName) {
        const prefix = nodeId.includes('_') ? nodeId.split('_')[0] + '_' : '';
        const sanitized = displayName.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
        const newId = prefix + sanitized;
        if (newId === nodeId) {
            events.log('ID already matches name.', 'system-msg');
            return;
        }
        await H.renameNode(nodeId, newId);
    };

    /**
     * Save skill check configuration for a node
     * @param {string} nodeId - Graph node ID
     */
    H.saveSkillCheck = async function(nodeId) {
        const escId = nodeId.replace(/'/g, "\\'");
        const skill = document.getElementById(`skill-name-${escId}`)?.value || '';
        const dc = parseInt(document.getElementById(`skill-dc-${escId}`)?.value) || 10;
        await api.updateNode(nodeId, { properties: { skill_check: { skill, dc } } });
        worldState.fetch();
    };

    // ──────────────────────────────────────────────
    // Shared HTML/escaping helpers (previously duplicated in every view)
    // ──────────────────────────────────────────────

    /**
     * HTML-escape double quotes for attribute safety.
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    H.esc = function(text) {
        return (text || '').replace(/"/g, '&quot;');
    };

    /**
     * Escape a node ID for safe inline-handler embedding (single quotes → \').
     * @param {string} nodeId - Graph node ID
     * @returns {string} Escaped ID
     */
    H.escId = function(nodeId) {
        return String(nodeId || '').replace(/'/g, "\\'");
    };

    /**
     * Build an HTML section for binding an image to a graph node (task-249).
     * Supports uploading a bundled file, pasting an explicit URL/path, or
     * removing the current image. Images render as graph thumbnails when the
     * 🖼 Images graph toggle is on.
     * @param {string} nodeId - Graph node ID
     * @param {object} props - Node properties (reads `image`)
     * @returns {string} HTML string
     */
    H.renderImageSection = function(nodeId, props = {}) {
        const escId = H.escId(nodeId);
        const image = props.image || '';
        const preview = image
            ? `<img src="${H.esc(image)}" alt="Node image" style="max-width:100px;max-height:100px;border-radius:6px;border:1px solid var(--border);display:block;margin-bottom:6px;">`
            : `<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No image set.</div>`;
        const removeBtn = image
            ? `<button class="btn btn-sm btn-danger" onclick="InspectorHelpers.clearNodeImage('${escId}')">🗑 Remove</button>`
            : '';
        return `<div class="inspector-section">
            <h3>🖼 Image</h3>
            <div id="img-preview-${escId}">${preview}</div>
            <div style="display:flex;gap:4px;align-items:center;margin-top:2px;">
                <input type="file" accept="image/*" onchange="InspectorHelpers.setNodeImage('${escId}', this)" title="Upload an image (bundled under static/images) — works offline" style="flex:1;font-size:10px;">
            </div>
            <div class="field" style="display:flex;gap:4px;align-items:center;margin-top:4px;">
                <input type="text" id="img-url-${escId}" placeholder="...or paste a URL / path" value="${H.esc(image)}" style="flex:1;font-size:11px;">
                <button class="btn btn-sm" onclick="InspectorHelpers.setNodeImageUrl('${escId}')">Set</button>
            </div>
            <div id="img-actions-${escId}" style="display:flex;gap:4px;margin-top:4px;">${removeBtn}</div>
            <div class="section-hint" style="margin-top:4px;">Shown as a thumbnail on the graph when the 🖼 Images toggle is on.</div>
        </div>`;
    };

    /**
     * Refresh the inline image preview + URL field in place after a change.
     * @param {string} nodeId - Graph node ID
     * @param {string} image - New image URL/path ('' to clear)
     */
    H._refreshImagePreview = function(nodeId, image) {
        const previewEl = document.getElementById(`img-preview-${nodeId}`);
        if (previewEl) {
            const previewLit = image
                ? htmlTag`<img src=${image} alt="Node image" style="max-width:100px;max-height:100px;border-radius:6px;border:1px solid var(--border);display:block;margin-bottom:6px;">`
                : htmlTag`<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No image set.</div>`;
            window.Lit.render(previewLit, previewEl);
        }
        const urlEl = document.getElementById(`img-url-${nodeId}`);
        if (urlEl) urlEl.value = image || '';
        const removeBtn = image ? htmlTag`<button class="btn btn-sm btn-danger" @click=${() => H.clearNodeImage(nodeId)}>🗑 Remove</button>` : window.Lit.nothing;
        const wrap = document.getElementById(`img-actions-${nodeId}`);
        if (wrap) window.Lit.render(removeBtn, wrap);
    };

    /**
     * Upload a file as a node's image via the endpoint, then refresh the world.
     * @param {string} nodeId - Graph node ID
     * @param {HTMLInputElement} inputEl - The file input
     */
    H.setNodeImage = async function(nodeId, inputEl) {
        const file = inputEl && inputEl.files && inputEl.files[0];
        if (!file) return;
        const res = await api.uploadNodeImage(nodeId, file);
        if (res.error) {
            events.log('Image upload failed: ' + res.error, 'error-msg');
            return;
        }
        events.log('Image set.', 'system-msg');
        H._refreshImagePreview(nodeId, res.image || '');
        if (graphManager) graphManager._lastSig = '';
        worldState.fetch();
        if (graphManager) graphManager.loadGraphData();
    };

    /**
     * Bind an explicit image URL/path to a node (from the URL text input).
     * @param {string} nodeId - Graph node ID
     */
    H.setNodeImageUrl = async function(nodeId) {
        const inputEl = document.getElementById(`img-url-${nodeId}`);
        const url = (inputEl && inputEl.value.trim()) || '';
        if (!url) { events.log('Image URL is empty.', 'error-msg'); return; }
        await api.updateNode(nodeId, { properties: { image: url } });
        events.log('Image URL set.', 'system-msg');
        H._refreshImagePreview(nodeId, url);
        if (graphManager) graphManager._lastSig = '';
        worldState.fetch();
        if (graphManager) graphManager.loadGraphData();
    };

    /**
     * Clear a node's image binding.
     * @param {string} nodeId - Graph node ID
     */
    H.clearNodeImage = async function(nodeId) {
        await api.removeNodeImage(nodeId);
        events.log('Image removed.', 'system-msg');
        H._refreshImagePreview(nodeId, '');
        if (graphManager) graphManager._lastSig = '';
        worldState.fetch();
        if (graphManager) graphManager.loadGraphData();
    };

    /**
     * Render a field-lock toggle for AI Improve. Locked fields are preserved
     * during AI Improve/Refresh.
     * @param {string} field - Property field name
     * @param {string[]} lockedFields - Currently locked fields
     * @param {string} nodeId - Graph node ID
     * @returns {TemplateResult}
     */
    H.renderLockToggle = function(field, lockedFields, nodeId) {
        const isLocked = (lockedFields || []).includes(field);
        const icon = isLocked ? '🔒' : '🔓';
        const color = isLocked ? 'var(--orange)' : 'var(--text-muted)';
        return htmlTag`<span style="cursor:pointer;font-size:12px;color:${color};"
            @click=${(ev) => { ev.preventDefault(); H.toggleFieldLock(nodeId, field); }}
            title="${isLocked ? 'Unlock' : 'Lock'} ${field} — locked fields are preserved during Improve">${icon}</span>`;
    };

    /**
     * Toggle a field's locked state on a node.
     * @param {string} nodeId - Graph node ID
     * @param {string} field - Property field name
     */
    H.toggleFieldLock = function(nodeId, field) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const locked = [...(node.properties?.locked_fields || [])];
        const idx = locked.indexOf(field);
        if (idx >= 0) locked.splice(idx, 1);
        else locked.push(field);
        api.updateNode(nodeId, { properties: { locked_fields: locked } }).then(() => worldState.fetch());
    };

    /**
     * Get the locked-field list from a node's properties.
     * @param {object} props - Node properties
     * @returns {string[]} Locked fields
     */
    H.getLockedFields = function(props) {
        return props?.locked_fields || [];
    };

    /**
     * Shared "AI Improve" flow used by way/item/area inspectors.
     *
     * Handles the parts that are identical across all three: existence +
     * description + API-key checks, button busy state, LLM call with JSON
     * extraction, node update + refresh + re-render, and error handling.
     *
     * @param {string} nodeId - Graph node ID
     * @param {object} spec - { btnId, system, buildPrompt, apply }
     *   - btnId: id of the Improve button to disable while running
     *   - system: system prompt string for the LLM
     *   - buildPrompt(node, lockedFields): returns the user prompt string
     *   - apply(parsed, node, lockedFields, update): mutate `update` with
     *     the parsed name/properties to save
     */
    H.improveWithAI = async function(nodeId, spec) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const props = node.properties || {};
        const description = props.description || '';
        const lockedFields = props.locked_fields || [];

        if (!description) { toastInfo('Add a description first, then run Improve.'); return; }
        if (!config.apiKey || !config.model) { toastInfo('Configure API key and model in Settings first.'); return; }

        const improveBtn = document.getElementById(spec.btnId);
        if (improveBtn) { improveBtn.disabled = true; improveBtn.textContent = '⏳ Improving...'; }

        try {
            const resp = await llmClient.chat([
                { role: 'system', content: spec.system },
                { role: 'user', content: spec.buildPrompt(node, lockedFields) }
            ], { temperature: 0.7 });
            if (!resp) { toastError('No response from LLM.'); return; }

            let cleaned = resp.trim();
            const jsonMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
            if (jsonMatch) cleaned = jsonMatch[1].trim();
            else { const firstBrace = cleaned.indexOf('{'), lastBrace = cleaned.lastIndexOf('}'); if (firstBrace !== -1 && lastBrace > firstBrace) cleaned = cleaned.substring(firstBrace, lastBrace + 1); }
            const parsed = JSON.parse(cleaned);

            const update = {};
            spec.apply(parsed, node, lockedFields, update);

            await api.updateNode(nodeId, update);
            events.log(`AI improved ${node.name || nodeId}`, 'system-msg');
            worldState.fetch().then(() => {
                if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
            });
        } catch (error) {
            console.error(error);
            toastError('AI improvement failed: ' + error.message);
        } finally {
            if (improveBtn) { improveBtn.disabled = false; improveBtn.textContent = '✨ Improve'; }
        }
    };

    /**
     * Build a lit-html section for an editable Aliases area (subjective names
     * that resolve to this node in commands — works for items, ways, areas,
     * and characters). Comma-separated; saved on Enter or blur.
     * @param {string} nodeId - Graph node ID
     * @param {Array|string} aliases - Current aliases
     * @returns {TemplateResult}
     */
    H.renderAliasesSection = function(nodeId, aliases = []) {
        const list = Array.isArray(aliases) ? aliases : [];
        const value = list.join(', ');
        const save = (ev) => { if (ev.key && ev.key !== 'Enter') return; if (ev.key === 'Enter') ev.preventDefault(); H.saveAliases(nodeId, ev.target.value); };
        return htmlTag`<div class="inspector-section" id="aliases-section-${nodeId}">
            <h3>🔖 Aliases</h3>
            <div class="field">
                <input type="text" id="aliases-input-${nodeId}" .value=${value}
                    placeholder="Other names this resolves to (comma-separated)"
                    title="Subjective names characters use for this — e.g. 'the Butcher', 'trapdoor'. Saved on Enter or blur."
                    style="width:100%;font-size:11px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;"
                    @keydown=${save}
                    @blur=${save}>
                <div class="section-hint" style="margin-top:4px;">Other names that target this in commands (use, go, take, attack, examine...). Comma-separated.</div>
            </div>
        </div>`;
    };

    /**
     * Save a node's aliases from a comma-separated input value.
     * @param {string} nodeId - Graph node ID (unescaped)
     * @param {string} value - Comma-separated aliases
     */
    H.saveAliases = async function(nodeId, value) {
        const aliases = String(value || '')
            .split(/[,\|]/)
            .map(a => a.trim())
            .filter(Boolean);
        await api.updateNode(nodeId, { properties: { aliases } });
        worldState.fetch();
    };

    /**
     * Replace {param:key} placeholders in way text with values from the way parameters dict.
     * Unresolved keys are left as-is.
     * @param {string} text
     * @param {Object} parameters
     * @returns {string}
     */
    H.resolveWayParams = function(text, parameters = {}) {
        if (!text) return '';
        return String(text).replace(/\{param:([^}]+)\}/g, (match, key) => {
            const trimmed = String(key || '').trim();
            if (trimmed && Object.prototype.hasOwnProperty.call(parameters, trimmed)) {
                return String(parameters[trimmed]);
            }
            return match;
        });
    };

    /**
     * Keys referenced as {param:key} in text but missing from parameters.
     * @param {string} text
     * @param {Object} parameters
     * @returns {string[]}
     */
    H.unresolvedParamKeys = function(text, parameters = {}) {
        const missing = [];
        const seen = new Set();
        const re = /\{param:([^}]+)\}/g;
        let match;
        while ((match = re.exec(String(text || ''))) !== null) {
            const key = String(match[1] || '').trim();
            if (!key || seen.has(key)) continue;
            seen.add(key);
            if (!Object.prototype.hasOwnProperty.call(parameters, key)) missing.push(key);
        }
        return missing;
    };

    /**
     * HTML block showing resolved parameter preview + unresolved warnings.
     * @param {string} text - Raw text with {param:key} placeholders
     * @param {Object} parameters
     * @returns {string}
     */
    H.renderParamPreviewBlock = function(text, parameters = {}) {
        if (!text || !/\{param:/.test(text)) return '';
        const resolved = H.resolveWayParams(text, parameters);
        const unresolved = H.unresolvedParamKeys(text, parameters);
        let html = `<div class="way-param-preview" style="margin-top:4px;padding:6px 8px;background:var(--bg-inset);border-radius:4px;font-size:10px;">`;
        html += `<div style="color:var(--text-dim);margin-bottom:2px;">Resolved preview:</div>`;
        html += `<div style="color:var(--text);white-space:pre-wrap;">${H.esc(resolved)}</div>`;
        if (unresolved.length) {
            html += `<div style="color:var(--orange);margin-top:4px;">⚠ Missing parameters: ${unresolved.map(k => H.esc(k)).join(', ')}</div>`;
        }
        html += `</div>`;
        return html;
    };

    return H;
})();
