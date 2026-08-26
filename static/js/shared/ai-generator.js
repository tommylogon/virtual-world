/**
 * Shared AI Generator — handles the common LLM call + response parsing pattern.
 * 
 * Usage:
 *   const result = await AIGenerator.generate(
 *       userPrompt,
 *       systemMessage,
 *       { temperature: 0.8, onChunk: null }
 *   );
 *   if (result.success) {
 *       // result.data = parsed JSON
 *       // result.raw = raw response string
 *   } else {
 *       // result.error = error message
 *   }
 */

const AIGenerator = {
    /** Check if AI is configured (API key + model). Shows toast if missing. */
    isConfigured() {
        if (!config.apiKey || !config.model) {
            if (typeof toastInfo === 'function') toastInfo('Configure API key and model in Settings first.');
            return false;
        }
        return true;
    },

    /** Call LLM with system + user messages, parse JSON response.
     *  Returns { success, data, raw, error }.
     *  If LLM returns empty/no response, auto-generates a mock fallback. */
    async generate(userPrompt, systemMessage, options = {}) {
        const temp = options.temperature ?? 0.8;
        const fallback = options.fallback || null;

        if (!userPrompt) return { success: false, data: null, raw: '', error: 'No prompt provided' };
        if (!this.isConfigured()) return { success: false, data: null, raw: '', error: 'AI not configured' };

        const t0 = performance.now();
        let response = null;

        try {
            response = await llmClient.chat([
                { role: 'system', content: systemMessage },
                { role: 'user', content: userPrompt }
            ], { temperature: temp });

            if (!response && fallback) {
                const fallbackData = typeof fallback === 'function' ? fallback(userPrompt) : fallback;
                return { success: true, data: fallbackData, raw: JSON.stringify(fallbackData), error: null };
            }
            if (!response) {
                return { success: false, data: null, raw: '', error: 'No response from LLM' };
            }

            const parsed = parseJSONFromResponse(response);
            if (parsed.json) {
                return { success: true, data: parsed.json, raw: parsed.raw, error: null };
            }

            return { success: false, data: null, raw: response, error: 'Failed to parse JSON from response' };
        } catch (err) {
            return { success: false, data: null, raw: response || '', error: err.message || 'Unknown error' };
        }
    },

    /** Convenience: generate and populate form fields via a setter callback.
     *  Returns { success, data } or shows error toast. */
    async generateAndPopulate(userPrompt, systemMessage, setFormData, options = {}) {
        const result = await this.generate(userPrompt, systemMessage, options);
        if (result.success && result.data) {
            if (typeof setFormData === 'function') setFormData(result.data);
            return { success: true, data: result.data };
        }
        if (result.error && typeof toastError === 'function') {
            toastError('AI generation failed: ' + result.error);
        }
        return { success: false, data: null, error: result.error };
    },

    /** Build a system message that includes available trigger/effect/condition types. */
    buildItemSystem(extra = '') {
        let msg = 'You are a procedural item generator. Generate an item based on the description. Respond with ONLY raw JSON.\n\n'
            + 'Fields: name, description, actions (comma-separated), uses (number, -1=infinite), weight (number), '
            + 'equip_slots (array, e.g. ["head","torso"]), '
            + 'container (bool), current_state (string, e.g. normal/hidden/open/closed/locked/lit)\n'
            + 'tags: array of strings\n'
            + 'triggers: array of trigger objects\n\n'
            + 'Available trigger types: on_take, on_drop, on_examine, on_use, on_use_on, on_eat, on_drink, on_read, '
            + 'on_light, on_activate, on_equip, on_unequip, on_toggle_on, on_toggle_off, on_tick, on_open, on_close\n'
            + 'Available effect types: message, adjust_vital (stat, amount), set_state (node_id, state), '
            + 'set_environment (light, temperature, air, smell, noise), spawn_item (item_id, name), '
            + 'remove_item (item_id), damage (amount, target), heal (amount), teleport (area), '
            + 'unlock_way (way_id), destroy_self, drain (amount, stat), set_description (target, value), '
            + 'append_description (target, text), rename (new_name)\n'
            + 'Available conditions: has_item (value), state_equals (target, value), random_chance (value), '
            + 'uses_reached (value), skill_check (skill, dc), save_throw (stat/skill, dc, optional target)\n'
            + 'Triggers can use effects array for multi-step: {"effects":[{"type":"set_state","params":{}},...]}\n\n'
            + 'Generate appropriate triggers based on item type:\n'
            + '- Food/drink -> on_eat/on_drink + adjust_vital (Hunger/Thirst)\n'
            + '- Tools/keys -> on_use_on + unlock_way or adjust_vital\n'
            + '- Light sources -> on_light + set_state (lit) + set_environment (light)\n'
            + '- Books/notes -> on_read + message or set_description\n'
            + '- Containers -> on_use + spawn_item items\n'
            + '- Wearables -> on_equip + adjust_vital\n'
            + '- Interactive -> effects array for multi-step\n\n'
            + 'For wearable items: set equip_slots. For held items: equip_slots ["hand_left","hand_right"]. '
            + 'For two-handed: include "two_handed" in tags. equip_slots: ["hand_left","hand_right"]. '
            + 'For full-body suits (EVA suits, hardsuits): list every covered slot in equip_slots and include "equips_all_slots" in tags. '
            + 'For containers: container: true.';
        if (extra) msg += '\n\n' + extra;
        return msg;
    }
};
