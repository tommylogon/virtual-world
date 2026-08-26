/**
 * ItemLibraryAI — AI item generation and improvement
 * Extracted from item-library.js
 *
 * These methods operate via .call(this) where this is an ItemLibrary instance.
 * They access instance properties (this.data, this._targetArea, this.selectedId)
 * and delegate methods (this._refreshEditorWithTriggers(), this._renderContentsSection(), etc.)
 */

window.ItemLibraryAI = {
    // Lazy tag: classic scripts parse before the deferred lit-bootstrap module
    // runs, so window.Lit only exists when a view actually renders.
    htmlTag: (strings, ...values) => window.Lit.html(strings, ...values),

    // --- AI: Improve Existing Item ---

    /**
     * Improve an existing item's properties using AI.
     * Reads current fields from the editor form, sends them to the LLM,
     * and populates the editor with the improved result.
     * @returns {Promise<void>}
     */
    async improveWithAI() {
        const name = document.getElementById('lib-item-name')?.value || '';
        const description = document.getElementById('lib-item-desc')?.value || '';
        const currentActions = document.getElementById('lib-item-actions')?.value || 'examine,take,use';
        const currentTags = document.getElementById('lib-item-tags')?.value || '';
        const currentUses = document.getElementById('lib-item-uses')?.value || '-1';
        const currentWeight = document.getElementById('lib-item-weight')?.value || '0.1';

        if (!description) {
            toastInfo('Add a description first, then run Improve.');
            return;
        }
        if (!config.apiKey || !config.model) { toastInfo('Configure API key and model in Settings first.'); return; }

        const improveBtn = document.getElementById('lib-improve-btn');
        if (improveBtn) { improveBtn.disabled = true; improveBtn.textContent = '⏳ Improving...'; }

        const system = `You are a procedural item enhancer for a text adventure game. The item data schema supports:

FIELDS: name, description, actions, uses (number, -1=infinite), weight (number), current_state (string, e.g. normal/hidden/open/closed/locked/lit), equip_slots (array of strings, e.g. ["head","torso"]), tags (array of strings - include "two_handed", "equips_all_slots", and "container" as tags instead of separate fields), contents (array of {id, name}), triggers (array of objects)

ACTIONS: examine, take, use, drop, inspect, read, eat, drink, wear, activate, combine, unlock, repair, break

EFFECT TYPES FOR TRIGGERS:
- message: Show a flavor message
- destroy_self: Destroy the item after effect
- damage: Deal HP damage (amount, target: self/other)
- heal: Restore HP (amount)
- spawn_item: Spawn an item in area (item_id, name)
- remove_item: Remove item from area (item_id)
- set_state: Change a node's state (node_id, state)
- set_environment: Change area environment (light 0-100, temperature, air: fresh/stale/humid/toxic/smoky/fragrant, smell, noise: quiet/dripping/humming/windy/loud/chaotic/silent)
- teleport: Teleport to area (area)
- rename: Change item's displayed name (new_name)
- unlock_way: Unlock a way (way_id)

CONDITIONS (optional — only fire trigger when met):
- uses_reached: Condition value is the number of uses remaining when trigger fires (e.g. "0" = fires when uses left == 0)
- has_item: Check if character has item in inventory
- state_equals: Check if a node's state equals a value (e.g. "door_south=open")
- random_chance: Random percentage chance (1-100)
- save_throw: Target rolls a stat or skill vs DC to resist (stat, dc, optional target)

CONTAINER ITEMS: If the description mentions "contains", "inside", "with", "including" followed by item names, you MUST:
1. Extract each item mentioned as a separate child in "contents" array
2. Each content item has: { "id": "item_key", "name": "Display Name" }
3. Remove the enumeration from the description (so the container's description doesn't spoil contents)
4. Add a trigger: on_use → spawn_item for each child item (so opening it spawns them)
5. Add a trigger: on_use → rename to "Empty [Original Name]" when uses runs out
6. Also add a trigger: on_examine → message for the empty state (conditional on uses_reached=0)
7. Set uses to 1 (one open = contents spill out)
8. Add all child items as separate entries in "contents" array

For wearable items (clothing, armor, accessories): set equip_slots to the body part(s) it covers (e.g. ["head"] for helmet, ["torso"] for shirt/armor, ["feet"] for boots, ["hand_left","hand_right"] for weapons). For two-handed items: include "two_handed" in tags. For full-body suits that cover the whole body at once (EVA suits, jumpsuits, hardsuits): list every slot they cover in equip_slots and include "equips_all_slots" in tags.

IMPORTANT: If you extract children into contents, also add them as triggers with spawn_item so the game engine spawns them when the container is used.

Example container output:
{
  "name": "Medicine Cabinet",
  "description": "A rusted metal cabinet mounted on the wall.",
  "actions": "examine,take,use",
  "uses": 1,
  "weight": 5,
  "tags": ["container", "metal", "medical"],
  "contents": [
    {"id": "expired_aspirin", "name": "Expired Aspirin"},
    {"id": "bandages", "name": "Bandages"},
    {"id": "antiseptic_bottle", "name": "Bottle of Antiseptic"}
  ],
  "triggers": [
    {"trigger_type": "on_examine", "effect_type": "message", "effect_params": {"message": "A rusted medicine cabinet mounted on the wall."}},
    {"trigger_type": "on_use", "effect_type": "spawn_item", "effect_params": {"item_id": "expired_aspirin", "name": "Expired Aspirin", "message": "Expired aspirin spills out!"}, "condition": {"type": "uses_reached", "value": "1"}},
    {"trigger_type": "on_use", "effect_type": "spawn_item", "effect_params": {"item_id": "bandages", "name": "Bandages", "message": "Bandages fall out!"}, "condition": {"type": "uses_reached", "value": "1"}},
    {"trigger_type": "on_use", "effect_type": "spawn_item", "effect_params": {"item_id": "antiseptic_bottle", "name": "Bottle of Antiseptic", "message": "A bottle of antiseptic tumbles out!"}, "condition": {"type": "uses_reached", "value": "1"}},
    {"trigger_type": "on_use", "effect_type": "rename", "effect_params": {"new_name": "Empty Medicine Cabinet", "message": "The cabinet is now empty."}, "condition": {"type": "uses_reached", "value": "1"}},
    {"trigger_type": "on_examine", "effect_type": "message", "effect_params": {"message": "An empty medicine cabinet. Nothing left inside."}, "condition": {"type": "uses_reached", "value": "0"}}
  ]
}

OUTPUT FORMAT: Respond with ONLY raw JSON. No markdown, no code fences, just JSON.`;

        const prompt = `Item Name: ${name}\nDescription: ${description}\n\nCurrent fields:\n- actions: ${currentActions}\n- tags: ${currentTags}\n- uses: ${currentUses}\n- weight: ${currentWeight}\n\nImprove this item. If the description mentions contents (contains/inside/with/including), extract them into the contents array and spawn triggers.`;

        try {
            const result = await AIGenerator.generate(prompt, system, { temperature: 0.7 });
            if (!result.success) { toastError(result.error || 'AI generation failed.'); return; }
            const parsed = result.data;

            const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ''; };
            set('lib-item-name', parsed.name || name);
            set('lib-item-desc', parsed.description || description);
            set('lib-item-actions', parsed.actions || currentActions);
            set('lib-item-uses', parsed.uses ?? currentUses);
            set('lib-item-weight', parsed.weight ?? currentWeight);
            const stateEl = document.getElementById('lib-item-state');
            if (stateEl && parsed.current_state) stateEl.value = parsed.current_state;
            const slotsEl = document.getElementById('lib-item-equip-slots');
            if (slotsEl && Array.isArray(parsed.equip_slots)) {
                Array.from(slotsEl.options).forEach(opt => opt.selected = parsed.equip_slots.includes(opt.value));
            }
            if (parsed.tags) set('lib-item-tags', Array.isArray(parsed.tags) ? parsed.tags.join(', ') : parsed.tags);

            // Triggers
            if (parsed.triggers) {
                document.getElementById('lib-item-triggers').value = JSON.stringify(parsed.triggers);
                this._refreshEditorWithTriggers();
            }

            // Contents
            if (parsed.contents) {
                document.getElementById('lib-item-contents').value = JSON.stringify(parsed.contents);
                const listEl = document.getElementById('lib-contents-list');
                if (listEl) window.Lit.render(this._renderContentsSection(parsed.contents), listEl);
            }

            // Update action checkboxes
            if (parsed.actions) {
                const actionList = typeof parsed.actions === 'string' ? parsed.actions.split(',') : parsed.actions;
                document.querySelectorAll('.act-chk-lib').forEach(cb => {
                    cb.checked = actionList.includes(cb.value);
                });
                this._updateActionsPreview();
            }

            events.log(`AI improved: ${parsed.name || name}`, 'system-msg');
        } catch (err) {
            console.error(err);
            toastError('AI improvement failed: ' + err.message);
        } finally {
            if (improveBtn) { improveBtn.disabled = false; improveBtn.textContent = '✨ Improve'; }
        }
    },

    // --- AI Generation ---

    /**
     * Generate a new item from an AI prompt.
     * Reads the prompt from the editor, calls the LLM,
     * and populates the editor form fields with the result.
     * @returns {Promise<void>}
     */
    async generateWithAI() {
        const input = document.getElementById('lib-ai-prompt');
        const prompt = (input?.value || '').trim();
        if (!prompt) { input?.focus(); return; }
        if (!config.apiKey || !config.model) { toastInfo('Configure API key and model in Settings first.'); return; }

        input.disabled = true;
        input.value = 'Generating...';

        let system = 'You are a procedural item generator. Generate an item based on the description. Respond with ONLY raw JSON.\n\nFields:\n- name, description, actions (comma-separated), uses (number, -1=infinite), weight (number), current_state (string, e.g. normal/hidden/open/closed/locked/lit), equip_slots (array of strings, e.g. ["head","torso"])\n- tags: array of strings (include "two_handed", "equips_all_slots", and "container" as tags instead of separate fields)\n- triggers: array of trigger objects (see below)\n\nTrigger types: on_take, on_drop, on_examine, on_use, on_use_on, on_eat, on_drink, on_read, on_light, on_activate, on_equip, on_unequip, on_toggle_on, on_toggle_off, on_tick, on_open, on_close\nEffect types: message, adjust_vital (stat, amount), set_state (node_id, state), set_environment (light, temperature, air, smell, noise), spawn_item (item_id, name), remove_item (item_id), damage (amount, target), heal (amount, teleport (area), unlock_way (way_id), destroy_self, drain (amount, stat), set_description (target, value), append_description (target, text), rename (new_name)\nConditions: has_item (value), state_equals (target, value), random_chance (value), uses_reached (value), skill_check (skill, dc)\nTriggers can use effects array for multi-step: {"effects":[{"type":"set_state","params":{}},{"type":"message","params":{}}]}\n\nGenerate appropriate triggers. Common: eat/drink->on_eat/on_drink+adjust_vital; tools/keys->on_use_on+unlock_way; light->on_light+set_state; books->on_read+message; containers->on_use+spawn_item items; wearables->on_equip+adjust_vital; interactive->effects array multi-step.\n\nFor wearable items: set equip_slots (e.g. ["head"] for helmet, ["torso"] for shirt/armor, ["feet"] for boots). For held items: equip_slots ["hand_left", "hand_right"]. For two-handed weapons: include "two_handed" in tags, equip_slots: ["hand_left", "hand_right"]. For full-body suits (EVA suits, hardsuits): list every covered slot in equip_slots and include "equips_all_slots" in tags. For containers (backpacks, pouches): include "container" in tags.';
        if (window.VW?.PromptDocs?.ITEM_GENERATION_SYSTEM) {
            system += '\n\n' + VW.PromptDocs.ITEM_GENERATION_SYSTEM;
        }
        const useContext = document.getElementById('lib-gen-use-context')?.checked !== false;
        if (useContext && this._targetArea) {
            const roomDesc = worldState.areas?.[this._targetArea]?.description;
            if (roomDesc) {
                system += `\nThis item will be placed in "${this._targetArea}": ${roomDesc}`;
            }
        }

        try {
            const result = await AIGenerator.generate(prompt, system, { temperature: 0.8 });
            if (!result.success) { toastError(result.error || 'AI generation failed.'); return; }
            const parsed = result.data;

            const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ''; };
            if (this.selectedId === '__new__') {
                set('lib-item-id', parsed.name?.toLowerCase().replace(/[^a-z0-9_]+/g, '_') || 'gen_item');
            }
            set('lib-item-name', parsed.name);
            set('lib-item-desc', parsed.description);
            set('lib-item-actions', parsed.actions);
            set('lib-item-uses', parsed.uses ?? -1);
            set('lib-item-weight', parsed.weight ?? 0.1);
            const slotsEl = document.getElementById('lib-item-equip-slots');
            if (slotsEl && Array.isArray(parsed.equip_slots)) {
                Array.from(slotsEl.options).forEach(opt => opt.selected = parsed.equip_slots.includes(opt.value));
            }
            if (parsed.tags) set('lib-item-tags', parsed.tags.join(', '));
            if (parsed.triggers) {
                document.getElementById('lib-item-triggers').value = JSON.stringify(parsed.triggers);
                this._refreshEditorWithTriggers();
            }
            if (parsed.contents) {
                document.getElementById('lib-item-contents').value = JSON.stringify(parsed.contents);
                const listEl = document.getElementById('lib-contents-list');
                if (listEl) window.Lit.render(this._renderContentsSection(parsed.contents), listEl);
            }
            if (parsed.actions) {
                const actionList = typeof parsed.actions === 'string' ? parsed.actions.split(',') : parsed.actions;
                document.querySelectorAll('.act-chk-lib').forEach(cb => {
                    cb.checked = actionList.includes(cb.value);
                });
                this._updateActionsPreview();
            }
            events.log(`AI generated: ${parsed.name || 'unnamed'}`, 'system-msg');
        } catch (err) {
            console.error(err);
            toastError('AI generation failed: ' + err.message);
        } finally {
            input.disabled = false;
            input.value = '';
            input.placeholder = 'Describe an item...';
        }
    },

    /**
     * Show a prompt preview modal where the user can review and edit
     * the system + user prompt before sending.
     */
    async previewPrompt() {
        const input = document.getElementById('lib-ai-prompt');
        const prompt = (input?.value || '').trim();
        if (!prompt) { input?.focus(); return; }
        if (!config.apiKey || !config.model) { toastInfo('Configure API key and model in Settings first.'); return; }

        let system = 'You are a procedural item generator. Generate an item based on the description. Respond with ONLY raw JSON.\n\nFields: name, description, actions (comma-separated), uses (number), weight (number), current_state (string, e.g. normal/hidden/open/closed/locked/lit), equip_slots (array), tags (array - include "two_handed", "equips_all_slots", and "container" as tags), triggers (array).\nAvailable trigger types: on_take, on_drop, on_examine, on_use, on_use_on, on_eat, on_drink, on_read, on_light, on_activate, on_equip, on_unequip, on_toggle_on, on_toggle_off, on_tick, on_open, on_close\nAvailable effect types: message, adjust_vital, set_state, set_environment, spawn_item, remove_item, damage, heal, teleport, unlock_way, destroy_self, drain, set_description, append_description, rename\nAvailable conditions: has_item, state_equals, random_chance, uses_reached, skill_check, save_throw\nGenerate appropriate triggers based on item type (eat->on_eat, tools->on_use_on, light->on_light, books->on_read, containers->on_use+spawn_item). For wearables: include equip_slots. For two-handed items: include "two_handed" in tags. For full-body suits: include "equips_all_slots" in tags. For containers: include "container" in tags.';
        if (window.VW?.PromptDocs?.ITEM_GENERATION_SYSTEM) {
            system += '\n\n' + VW.PromptDocs.ITEM_GENERATION_SYSTEM;
        }
        const useContext = document.getElementById('lib-gen-use-context')?.checked !== false;
        if (useContext && this._targetArea) {
            const roomDesc = worldState.areas?.[this._targetArea]?.description;
            if (roomDesc) {
                system += `\nThis item will be placed in "${this._targetArea}": ${roomDesc}`;
            }
        }

        const fullPrompt = `[System]\n${system}\n\n[User prompt]\n${prompt}`;

        const existingModal = document.getElementById('prompt-preview-modal');
        if (existingModal) {
            document.getElementById('prompt-preview-textarea').value = fullPrompt;
            existingModal.style.display = 'flex';
            existingModal._type = 'lib';
            existingModal._systemMsg = system;
            return;
        }

        const overlay = document.createElement('div');
        overlay.id = 'prompt-preview-modal';
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:10000;';
        const htmlTemplate = window.ItemLibraryAI.htmlTag`<div style="background:var(--bg-panel);border:1px solid var(--border);border-radius:8px;padding:12px;width:90%;max-width:700px;max-height:80vh;display:flex;flex-direction:column;">
            <h3 style="margin:0 0 8px;">👁️ Prompt Preview</h3>
            <textarea id="prompt-preview-textarea" style="flex:1;min-height:300px;width:100%;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:8px;font-size:11px;font-family:monospace;resize:vertical;" spellcheck="false" .value=${fullPrompt}></textarea>
            <div style="display:flex;gap:6px;margin-top:8px;justify-content:flex-end;">
                <button class="btn btn-sm" @click=${() => document.getElementById('prompt-preview-modal').style.display='none'} style="background:var(--bg-inset);border-color:var(--border);">Cancel</button>
                <button class="btn btn-sm" @click=${() => VW.itemLib._sendPreviewPrompt()} style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">Send</button>
            </div>
        </div>`;
        window.Lit.render(htmlTemplate, overlay);
        document.body.appendChild(overlay);
        overlay._type = 'lib';
        overlay._systemMsg = system;
    },

    /**
     * Send the edited prompt from the preview modal.
     * Parses the user portion from the edited text and triggers generateWithAI.
     */
    sendPreviewPrompt() {
        const modal = document.getElementById('prompt-preview-modal');
        if (!modal) return;
        const edited = document.getElementById('prompt-preview-textarea').value;
        modal.style.display = 'none';

        const userMarker = '[User prompt]\n';
        const userIdx = edited.lastIndexOf(userMarker);
        let editedUserPrompt = '';
        if (userIdx !== -1) {
            editedUserPrompt = edited.substring(userIdx + userMarker.length).trim();
        } else {
            editedUserPrompt = edited;
        }
        if (!editedUserPrompt) return;

        const input = document.getElementById('lib-ai-prompt');
        if (input) {
            input.value = editedUserPrompt;
        }
        this.generateWithAI();
    }
};
