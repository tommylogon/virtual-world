/**
 * agent-loop.js — Multi-turn ReAct Agent Loop for Natural-Language Editor (task-387).
 *
 * Runs tool-calling conversation turns against LLMClient, constructs system prompts
 * with library-first guidance, and handles clarifications and staging.
 */

window.NLEditorAgent = (() => {
    'use strict';

    class AgentLoop {
        constructor(stagingBuffer, toolRouter) {
            this.staging = stagingBuffer;
            this.router = toolRouter;
            this.messages = [];
            const CWM = typeof ContextWindowManager !== 'undefined' ? ContextWindowManager : (typeof window !== 'undefined' ? window.ContextWindowManager : null);
            this.contextManager = CWM ? new CWM({ maxTokens: 6000, maxMessages: 30, recentTurnCount: 8 }) : { prune: m => m, addMessage: () => {}, reset: () => {} };
            this.busy = false;
            this.listeners = [];
        }

        onUpdate(callback) {
            this.listeners.push(callback);
        }

        _notify(event, data) {
            for (const cb of this.listeners) {
                try { cb(event, data); } catch (e) { console.error('Agent loop listener error:', e); }
            }
        }

        /** Rebuild system prompt containing rules, schemas, and live world context */
        buildSystemPrompt() {
            const worldSummary = this.router.overlay.listWorldSummary();
            return `You are an intelligent world-authoring assistant for a virtual world simulation editor.
You build, modify, and flesh out scenario areas, items, ways (doors/connections), and characters based on natural language requests.

### CRITICAL RULES:
1. **LIBRARY-FIRST MANDATE**:
   - Before creating any item from scratch via \`create_node\`, you MUST first search the library using \`search_library_items\`.
   - If a library item matches or can be reused/adapted, use \`spawn_library_item\` instead of inventing duplicate archetypes.
   - Only call \`create_node\` for items if no existing library archetype fits.
   - For whole-room requests ("furnish this room", "turn this into an apothecary"), prefer \`populate_area\` in a single call.
2. **STAGING FIREWALL**:
   - Every mutation (\`create_node\`, \`update_node\`, \`delete_node\`, \`attach\`, \`detach\`, \`connect_areas\`, \`spawn_library_item\`, \`populate_area\`, \`link_to_library\`) stages changes in a local buffer.
   - The user will inspect the staged changes before applying. Ghost previews show them on the map as dashed nodes.
   - Read tools (\`search_graph_nodes\`, \`get_node\`, \`list_world_summary\`) can see your newly staged entities immediately.
3. **SELECTION AWARENESS**: when the user says "this room", "this node", "the selected area" etc., use the Selected node reported in LIVE WORLD CONTEXT — do not ask for its name.
4. **VALID TAGS & SCHEMAS**:
   - Use only valid mechanic tags: \`light_source\`, \`heat_source\`, \`sound_source\`, \`toggleable\`, \`insulation\`, \`armor\`, \`clothing\`, \`weapon\`, \`resistance\`, \`container\`, \`electric\`, \`two_handed\`.
   - Only use standard item actions: \`examine\`, \`take\`, \`use\`, \`open\`, \`close\`, \`eat\`, \`drink\`, \`read\`, \`light\`, \`activate\`, \`equip\`, \`unequip\`, \`throw\`, \`break\`.
   - Only use standard item states: \`normal\`, \`hidden\`, \`open\`, \`closed\`, \`locked\`, \`lit\`, \`unlit\`, \`on\`, \`broken\`, \`charged\`, \`depleted\`.
5. **INTERACTIVE CLARIFICATION**:
   - When a request is ambiguous or multiple options exist, call \`request_clarification\` with clear multiple-choice options for the user.
6. **STYLE & TONE**: write descriptions, names, and dialogue consistent with the scenario theme and world lore below. Reuse lore vocabulary; never invent naming that contradicts it.

${this._buildWorldContext()}
${worldSummary}
`;
        }

        /** Live world context: scenario, theme, lore, and the user's selection. */
        _buildWorldContext() {
            let out = '\n### LIVE WORLD CONTEXT\n';
            try {
                const data = (typeof worldState !== 'undefined' && worldState.data) || {};
                const scenarioName = data._scenario_source || data.scenario || data._scenario_name || '';
                const theme = data.theme || data.scenario_theme || '';
                if (scenarioName) {
                    out += `- Scenario: ${scenarioName}${theme ? ` (theme: ${theme})` : ''}\n`;
                }
                const lore = data.world_lore || [];
                if (lore.length > 0) {
                    out += `- World lore (${lore.length} entries) — match style & vocabulary:\n`;
                    for (const entry of lore.slice(0, 6)) {
                        const title = entry.title ? `${entry.title}: ` : '';
                        out += `  · [${entry.category || 'general'}] ${title}${String(entry.content || '').slice(0, 220)}\n`;
                    }
                } else {
                    out += '- World lore: none yet — create flavor consistent with the theme.\n';
                }
                const view = (typeof VW !== 'undefined' && VW?.inspector) ? VW.inspector._currentView : null;
                if (view && view.type === 'node' && view.id && typeof worldState?.getNode === 'function') {
                    const n = worldState.getNode(view.id);
                    if (n) out += `- Selected node (user's current graph selection — their default "this room/node"): ${n.name} (id: ${n.id}) [${n.type}]\n`;
                    else out += '- Selected node: (stale — verify with search_graph_nodes)\n';
                } else {
                    out += '- Selected node: none — when a target is ambiguous, use search_graph_nodes or request_clarification.\n';
                }
            } catch (e) { /* context is best-effort */ }
            return out + '\n';
        }

        /** Reset or start a new session */
        resetSession() {
            this.messages = [];
            this.contextManager.reset();
            const sys = { role: 'system', content: this.buildSystemPrompt() };
            this.messages.push(sys);
            this.contextManager.addMessage(sys, { importance: 3, keepAlways: true });
            this._notify('session:reset', { messages: this.messages });
        }

        /** Execute a turn based on user input */
        async runUserTurn(userPrompt, options = {}) {
            if (this.busy) {
                return { error: 'Agent is already busy running a turn.' };
            }
            this.busy = true;
            this._notify('turn:start', { prompt: userPrompt });

            if (this.messages.length === 0) {
                this.resetSession();
            } else {
                // Update system prompt with fresh overlay summary
                this.messages[0] = { role: 'system', content: this.buildSystemPrompt() };
            }

            const userMsg = { role: 'user', content: userPrompt };
            this.messages.push(userMsg);
            this.contextManager.addMessage(userMsg, { importance: 1 });
            this._notify('message:added', userMsg);

            let maxIterations = 10;
            let currentIteration = 0;
            let finalAssistantResponse = '';
            let suspended = false;

            try {
                while (currentIteration < maxIterations) {
                    currentIteration++;
                    const pruned = this.contextManager.prune(this.messages);

                    this._notify('llm:calling', { iteration: currentIteration });
                    const response = await llmClient.chatWithTools(pruned, {
                        tools: NLEditorTools.TOOL_DEFINITIONS,
                        tool_choice: 'auto',
                        label: `nl-editor-${currentIteration}`
                    });

                    if (!response) {
                        throw new Error('No response from LLM.');
                    }

                    const { content, tool_calls } = response;
                    const assistantMsg = {
                        role: 'assistant',
                        content: content || '',
                        tool_calls: tool_calls || undefined
                    };

                    this.messages.push(assistantMsg);
                    this.contextManager.addMessage(assistantMsg, { importance: tool_calls ? 2 : 1 });
                    this._notify('message:added', assistantMsg);

                    if (content) finalAssistantResponse = content;

                    if (!tool_calls || tool_calls.length === 0) {
                        // Model finished thinking and issued final text
                        break;
                    }

                    // Execute tool calls
                    for (const call of tool_calls) {
                        const fnName = call.function?.name;
                        let fnArgs = {};
                        try {
                            fnArgs = JSON.parse(call.function?.arguments || '{}');
                        } catch (e) {
                            fnArgs = {};
                        }

                        this._notify('tool:start', { name: fnName, args: fnArgs, callId: call.id });

                        const result = await this.router.execute(fnName, fnArgs, {
                            onClarify: (question, choices) => {
                                suspended = true;
                                this._notify('clarification:requested', { question, choices, callId: call.id });
                            }
                        });

                        const toolMsg = {
                            role: 'tool',
                            tool_call_id: call.id,
                            name: fnName,
                            content: JSON.stringify(result)
                        };

                        this.messages.push(toolMsg);
                        this.contextManager.addMessage(toolMsg, { importance: 1 });
                        this._notify('tool:finished', { name: fnName, result, callId: call.id });
                    }

                    if (suspended) {
                        // Loop pauses waiting for user interaction on clarification
                        break;
                    }
                }
            } catch (err) {
                console.error('NL Editor agent error:', err);
                const errorMsg = { role: 'system', content: `[Error: ${err.message}]` };
                this.messages.push(errorMsg);
                this._notify('error', { error: err.message });
            } finally {
                this.busy = false;
                this._notify('turn:end', { response: finalAssistantResponse, stagedCount: this.staging.getOps().length });
            }

            return {
                messages: this.messages,
                response: finalAssistantResponse,
                stagedOps: this.staging.getOps()
            };
        }
    }

    return { AgentLoop };
})();
