/**
 * narration-ui.js — Narration Mode Toggle UI
 * 
 * Provides a 3-way toggle for narration mode:
 *   - "none": Static descriptions only (default)
 *   - "player": Player is prompted to narrate actions/descriptions
 *   - "ai": AI generates narrative flavor text
 * 
 * The narration text feeds into:
 *   - The area event log for the current turn
 *   - Character perception context (recent_hearing / recent events)
 *   - Replaces the default area description/items the agent sees
 */
const narrationUiTag = (strings, ...values) => window.Lit.html(strings, ...values);

class NarrationUI {
    constructor() {
        this.mode = 'none'; // 'none' | 'player' | 'ai'
        this.pendingNarration = null; // {type: 'area'|'action', context: {...}, resolve: fn}
        this._initPromise = this._loadSetting();
    }

    async _loadSetting() {
        try {
            const res = await fetch('/api/settings/narration');
            const data = await res.json();
            this.mode = data.mode || 'none';
        } catch (e) {
            this.mode = 'none';
        }
    }

    async setMode(mode) {
        if (!['none', 'player', 'ai'].includes(mode)) return;
        this.mode = mode;
        try {
            await fetch('/api/settings/narration', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode })
            });
        } catch (e) {
            console.error('Failed to save narration mode:', e);
        }
        // Update UI
        this._updateUI();
    }

    getMode() { return this.mode; }

    /**
     * Get narrated area context - replaces the default area description
     * with player or AI narration when applicable.
     * Returns the narrated text, or null if no narration is needed.
     */
    async getNarratedRoomContext(roomContext, charName) {
        if (this.mode === 'none') return null;
        
        if (this.mode === 'player') {
            // Show a pre-filled popup with the current area context
            return await this.promptPlayerNarration({
                type: 'area',
                areaName: roomContext.areaName || 'unknown',
                characters: roomContext.characters || [],
                items: roomContext.items || [],
                description: roomContext.description || '',
                exits: roomContext.exits || ''
            });
        }
        
        if (this.mode === 'ai') {
            // AI generates a narrative description
            return await this._generateAINarration(roomContext, charName);
        }
        
        return null;
    }

    /**
     * Get narrated action result - replaces the default action output
     * with player or AI narration when applicable.
     */
    async getNarratedActionResult(actionOutput, charName, action) {
        if (this.mode === 'none') return null;
        
        if (this.mode === 'player') {
            return await this.promptPlayerNarration({
                type: 'action',
                actor: charName,
                description: action,
                result: actionOutput,
                areaName: worldState.players?.[charName]?.current_area || 'unknown'
            });
        }
        
        if (this.mode === 'ai') {
            return await this._generateAINarrationResult(actionOutput, charName, action);
        }
        
        return null;
    }

    /**
     * Prompt the player for narration text (player mode).
     * Shows a modal with the current context pre-filled that the player can edit.
     */
    async promptPlayerNarration(context) {
        if (this.mode !== 'player') return null;
        
        return new Promise((resolve) => {
            // Build pre-filled text based on context
            let prefillText = '';
            if (context.type === 'area') {
                prefillText = `You are in ${context.areaName}.\n`;
                if (context.description) prefillText += `${context.description}\n`;
                if (context.items && context.items.length > 0) prefillText += `You can see: ${context.items.join(', ')}\n`;
                if (context.characters && context.characters.length > 0) prefillText += `Also here: ${context.characters.join(', ')}\n`;
                if (context.exits) prefillText += `Exits: ${context.exits}`;
            } else if (context.type === 'action') {
                prefillText = `${context.actor} ${context.description}\n`;
                if (context.result) prefillText += `Result: ${context.result}`;
            }

            const overlay = document.createElement('div');
            overlay.className = 'narration-overlay';
            window.Lit.render(narrationUiTag`
                <div class="narration-modal">
                    <div class="narration-header">🎭 Player Narration</div>
                    <div class="narration-context">Edit the description the agent will see:</div>
                    <textarea class="narration-input" rows="5">${prefillText}</textarea>
                    <div class="narration-actions">
                        <button class="btn btn-sm btn-ghost narration-skip" title="Use default description">⏭ Use Default</button>
                        <button class="btn btn-sm btn-green narration-submit">📝 Narrate</button>
                    </div>
                </div>
            `, overlay);
            document.body.appendChild(overlay);

            const textarea = overlay.querySelector('.narration-input');
            const submitBtn = overlay.querySelector('.narration-submit');
            const skipBtn = overlay.querySelector('.narration-skip');

            const cleanup = (result) => {
                overlay.remove();
                resolve(result);
            };

            submitBtn.onclick = () => {
                const text = textarea.value.trim();
                cleanup(text || null);
            };
            skipBtn.onclick = () => cleanup(null);
            
            // Enter to submit, Shift+Enter for newline
            textarea.onkeydown = (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    submitBtn.click();
                }
                if (e.key === 'Escape') {
                    cleanup(null);
                }
            };

            textarea.focus();
            textarea.select();
        });
    }

    /**
     * Generate AI narration for a area context
     */
    async _generateAINarration(roomContext, charName) {
        if (!config.apiKey || !config.model) return null;
        
        try {
            const systemMsg = `You are a narrative game master — a DM describing a scene to a player. Write in second person ("You see...", "You notice...", "You smell..."). Be atmospheric and vivid. Use sensory details: sight, sound, smell, touch. Keep it 2-4 sentences. Do NOT list items mechanically. Integrate notable items into the description naturally. Do NOT use markdown or quotes.`;
            const items = roomContext.items || [];
            const itemText = items.length > 0 ? `Notable objects here: ${items.join(', ')}. Work them into the description naturally.` : '';
            const prompt = `Describe this scene for ${charName}, who is standing in the ${roomContext.areaName || 'unknown'}:\n\nThe area: ${roomContext.description || 'A area.'}\n${itemText}\n${roomContext.characters?.length ? `Also present: ${roomContext.characters.join(', ')}` : ''}\nExits: ${roomContext.exits || 'unknown'}\n\nWrite a short atmospheric description in second person.`;
            
            const response = await llmClient.chat([
                { role: 'system', content: systemMsg },
                { role: 'user', content: prompt }
            ], { temperature: 0.8, label: 'narrate-area' });
            
            if (response) {
                let cleaned = response.trim();
                const jm = cleaned.match(/```(?:text)?\s*([\s\S]*?)\s*```/);
                if (jm) cleaned = jm[1].trim();
                events.log(`[AI Narration] ${cleaned}`, 'system-msg');
                return cleaned;
            }
        } catch (e) {
            console.warn('AI narration failed:', e);
        }
        return null;
    }

    /**
     * Generate AI narration for an action result
     */
    async _generateAINarrationResult(actionOutput, charName, action) {
        if (!config.apiKey || !config.model) return null;
        
        try {
            const systemMsg = `You are a narrative game master for a game. Describe the outcome of actions atmospherically. Keep it 1-3 sentences. Make it feel immersive.`;
            const prompt = `Narrate the result of this action:\nCharacter: ${charName}\nAction: ${action}\nResult: ${actionOutput || 'Nothing notable happens.'}`;
            
            const response = await llmClient.chat([
                { role: 'system', content: systemMsg },
                { role: 'user', content: prompt }
            ], { temperature: 0.8, label: 'narrate-result' });
            
            if (response) {
                let cleaned = response.trim();
                const jm = cleaned.match(/```(?:text)?\s*([\s\S]*?)\s*```/);
                if (jm) cleaned = jm[1].trim();
                events.log(`[AI Narration] ${cleaned}`, 'system-msg');
                return cleaned;
            }
        } catch (e) {
            console.warn('AI narration failed:', e);
        }
        return null;
    }

    _updateUI() {
        const indicator = document.getElementById('narration-indicator');
        if (!indicator) return;
        
        const labels = {
            'none': '🔇 No Narration',
            'player': '🎭 Player Narration',
            'ai': '🤖 AI Narration'
        };
        indicator.textContent = labels[this.mode] || labels['none'];
        indicator.className = `narration-badge narration-${this.mode}`;
    }
}

// Singleton
window.narrationUI = new NarrationUI();