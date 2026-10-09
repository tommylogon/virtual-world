/**
 * agent-loop.js — Multi-turn ReAct Agent Loop for Natural-Language Editor (task-387).
 *
 * Runs tool-calling conversation turns against LLMClient, constructs system prompts
 * with library-first guidance, and handles clarifications and staging.
 *
 * @module nl-editor/agent-loop — the NL editor's multi-turn ReAct loop
 * @contributes NLEditorAgent: tool-calling turns, library-first system prompts, clarification + staging
 * @powers NL editor — the natural-language editor conversation (task-387)
 * @relates drives tools.js; results are buffered by staging.js
 * @docs docs/virtualWorld/dev_tasks/done/graph/task-387-natural-language-editor-mode.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const NLEditorAgent = (() => {
    'use strict';

    class AgentLoop {
        staging: StagingBuffer;
        router: ToolRouter;
        messages: AgentMessage[];
        contextManager: ContextManagerLike;
        busy: boolean;
        maxIterations: number;
        budget: NlBudget;
        listeners: Array<(event: string, data: unknown) => void>;

        constructor(stagingBuffer: StagingBuffer, toolRouter: ToolRouter) {
            this.staging = stagingBuffer;
            this.router = toolRouter;
            this.messages = [];
            const CWM = _contextWindowManager();
            this.contextManager = CWM ? new CWM({ maxTokens: 60000, maxMessages: 30, recentTurnCount: 8 }) : { prune: (m: unknown) => m, addMessage: () => {}, reset: () => {} };
            this.busy = false;
            this.maxIterations = 100;
            this.budget = { maxIterations: 100, maxTokens: 60000, maxMessages: 30, recentTurnCount: 8, maxCriticalMessages: 10 };
            this.listeners = [];
        }

        /**
         * Read the persisted budget knobs (task-422) and clamp them for the
         * active model. Missing knobs take model-aware defaults; unknown models
         * get the conservative token cap rather than an assumed large window.
         */
        async _readBudget(): Promise<NlBudget> {
            const B = _nlBudget();
            const s = _storage();
            const model = _activeModel();
            const raw: Partial<NlBudget> = {};
            if (s) {
                raw.maxIterations = _toNum(await s.getConfig('nl_max_iterations'));
                raw.maxTokens = _toNum(await s.getConfig('nl_max_tokens'));
                raw.maxMessages = _toNum(await s.getConfig('nl_max_messages'));
                raw.recentTurnCount = _toNum(await s.getConfig('nl_recent_turns'));
                raw.maxCriticalMessages = _toNum(await s.getConfig('nl_max_critical'));
            }
            return B ? B.clampBudget(raw, model) : this.budget;
        }

        /**
         * Apply the budget to the live manager WITHOUT rebuilding it: a new
         * ContextWindowManager would lose the message metadata it keys by
         * object, disabling bounded critical retention mid-session.
         */
        _applyBudget(b: NlBudget): void {
            this.budget = b;
            this.maxIterations = b.maxIterations;
            const cm = this.contextManager as unknown as {
                maxTokens?: number; maxMessages?: number;
                recentTurnCount?: number; maxCriticalMessages?: number;
            };
            if (typeof cm.maxTokens === 'number') {
                cm.maxTokens = b.maxTokens;
                cm.maxMessages = b.maxMessages;
                cm.recentTurnCount = b.recentTurnCount;
                cm.maxCriticalMessages = b.maxCriticalMessages;
            } else {
                const CWM = _contextWindowManager();
                if (CWM) {
                    this.contextManager = new CWM({
                        maxTokens: b.maxTokens, maxMessages: b.maxMessages,
                        recentTurnCount: b.recentTurnCount
                    });
                }
            }
        }

        /** Live context-window stats for the status readout, or null. */
        getContextStats(): ContextStats | null {
            const cm = this.contextManager as unknown as { getStats?: () => ContextStats };
            return (cm && typeof cm.getStats === 'function') ? cm.getStats() : null;
        }

        /**
         * Measure the array that is actually about to be sent. `getStats()` only
         * refreshes inside `prune()` when the window is OVER limit, so under the
         * limit it reports 0 — the readout would sit at `context 0/60k` until
         * overflow. This measures the pruned window directly.
         */
        _measureStats(messages: unknown[]): ContextStats | null {
            const cm = this.contextManager as unknown as {
                maxTokens?: number; maxMessages?: number;
                estimateTokens?: (m: unknown) => number;
            } | null;
            if (!cm) return null;
            const list: unknown[] = Array.isArray(messages) ? messages : [];
            let tokens = 0;
            if (typeof cm.estimateTokens === 'function') {
                for (const m of list) {
                    const t = Number(cm.estimateTokens(m));
                    if (isFinite(t)) tokens += t;
                }
            }
            const maxTokens = typeof cm.maxTokens === 'number' ? cm.maxTokens : 0;
            const maxMessages = typeof cm.maxMessages === 'number' ? cm.maxMessages : 0;
            return {
                totalMessages: list.length,
                totalTokens: tokens,
                maxTokens,
                maxMessages,
                utilization: maxTokens ? ((tokens / maxTokens) * 100).toFixed(1) + '%' : '0%',
                isOverLimit: tokens > maxTokens || list.length > maxMessages
            };
        }

        onUpdate(callback: (event: string, data: unknown) => void) {
            this.listeners.push(callback);
        }

        /**
         * Parse XML-ish tool-call prose from a model reply into real tool_calls.
         * Handles nested `<param>value</param>` children:
         *   "<search_library_items>\n<query>lantern</query>\n</search_library_items>"
         * → { id, type:'function', function:{ name:'search_library_items', arguments:'{"query":"lantern"}' } }
         * Only known tool names (from TOOL_DEFINITIONS) are matched. Returns [] when nothing found.
         */
        _extractXmlToolCalls(text: string): AgentToolCall[] {
            if (!text) return [];
            const known = new Set<string>(
                (_nlEditorTools()?.TOOL_DEFINITIONS || [])
                    .map((t: NlEditorToolDefinition) => t?.function?.name)
                    .filter((name: string | undefined): name is string => !!name)
            );
            const calls: AgentToolCall[] = [];
            let n = 0;

            // Params come in two shapes: `<k>v</k>` (native-ish) and
            // `<parameter name="k">v</parameter>` (Anthropic/AntML tool format).
            const parseArgs = (name: string, inner: string): void => {
                const args: Record<string, unknown> = {};
                const assign = (key: string, raw: string): void => {
                    const v = raw.trim();
                    try { args[key] = JSON.parse(v); } catch (e) { args[key] = v; }
                };
                let pm: RegExpExecArray | null;
                const named = /<parameter\s+name="([^"]+)"[^>]*>\s*([\s\S]*?)\s*<\/parameter>/g;
                while ((pm = named.exec(inner)) !== null) assign(pm[1], pm[2]);
                const bare = /<([a-zA-Z_][a-zA-Z0-9_]*)>\s*([\s\S]*?)\s*<\/\1>/g;
                while ((pm = bare.exec(inner)) !== null) {
                    if (pm[1] === 'parameter') continue;
                    assign(pm[1], pm[2]);
                }
                n++;
                calls.push({
                    id: `xml_${name}_${n}`,
                    type: 'function',
                    function: { name, arguments: JSON.stringify(args) }
                });
            };

            // The tool name inside a <tool_call> body: a leading token or a
            // <name>…</name> child. Returns the name and the params-only remainder.
            const parseToolBody = (raw: string): { name: string; inner: string } | null => {
                const nameChild = raw.match(/^\s*<name>\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*<\/name>/);
                if (nameChild) return { name: nameChild[1], inner: raw.slice(nameChild[0].length) };
                const bare = raw.match(/^\s*([a-zA-Z_][a-zA-Z0-9_]*)/);
                if (bare) return { name: bare[1], inner: raw.slice(bare[0].length) };
                return null;
            };

            let m: RegExpExecArray | null;
            // Shape A: <tool_name><k>v</k>…</tool_name>
            const reA = /<([a-zA-Z_][a-zA-Z0-9_]*)>\s*([\s\S]*?)\s*<\/\1>/g;
            while ((m = reA.exec(text)) !== null) {
                if (known.has(m[1])) parseArgs(m[1], m[2]);
            }
            // Shape B: <tool_call>tool_name<parameter name="k">v</parameter>…</tool_call>
            // (also <function_call>). The tool name is the leading token OR a
            // <name>…</name> child. This is what several models actually emit, and
            // the old parser silently dropped it — the call never ran.
            const reB = /<(?:tool_call|function_call)\b[^>]*>([\s\S]*?)<\/(?:tool_call|function_call)>/g;
            while ((m = reB.exec(text)) !== null) {
                const body = parseToolBody(m[1]);
                if (body && known.has(body.name)) parseArgs(body.name, body.inner);
            }

            // Shape C: <invoke name="tool_name">…</invoke> / <function name="tool_name">…</function>
            const reC = /<(?:invoke|function)\b[^>]*\bname="([a-zA-Z_][a-zA-Z0-9_]*)"[^>]*>\s*([\s\S]*?)<\/(?:invoke|function)>/g;
            while ((m = reC.exec(text)) !== null) {
                if (known.has(m[1])) parseArgs(m[1], m[2]);
            }

            // Shape D: <function=tool_name>…</function>
            const reD = /<function=([a-zA-Z_][a-zA-Z0-9_]*)>([\s\S]*?)<\/function>/g;
            while ((m = reD.exec(text)) !== null) {
                if (known.has(m[1])) parseArgs(m[1], m[2]);
            }

            // Shape E: a JSON tool-call object anywhere in the prose
            // ({"name":"update_node","arguments":{…}} or {"name":…,"parameters":{…}}).
            // Scanned with a balanced-brace reader, not a regex: the arguments
            // value nests ({"patch":{"name":…}}), which a lazy regex mangles.
            const nameRe = /"name"\s*:\s*"([a-zA-Z_][a-zA-Z0-9_]*)"/g;
            while ((m = nameRe.exec(text)) !== null) {
                const name = m[1];
                if (!known.has(name)) continue;
                const after = text.slice(m.index + m[0].length);
                const key = after.match(/^\s*,\s*"(?:arguments|parameters)"\s*:\s*/);
                if (!key) continue;
                const rest = after.slice(key[0].length);
                let valueText = '';
                if (rest[0] === '"') {
                    const strMatch = rest.match(/^"(?:[^"\\]|\\.)*"/);
                    if (!strMatch) continue;
                    valueText = strMatch[0];
                } else if (rest[0] === '{') {
                    let depth = 0, i = 0, inStr = false, esc = false;
                    for (; i < rest.length; i++) {
                        const ch = rest[i];
                        if (inStr) {
                            if (esc) esc = false;
                            else if (ch === '\\') esc = true;
                            else if (ch === '"') inStr = false;
                        } else if (ch === '"') inStr = true;
                        else if (ch === '{') depth++;
                        else if (ch === '}') { depth--; if (depth === 0) { i++; break; } }
                    }
                    valueText = rest.slice(0, i);
                } else continue;
                try {
                    const parsed = JSON.parse(valueText);
                    n++;
                    calls.push({
                        id: `xml_${name}_${n}`,
                        type: 'function',
                        function: { name, arguments: JSON.stringify(parsed) }
                    });
                } catch (e) { /* not JSON after all */ }
            }
            return calls;
        }

        _notify(event: string, data?: unknown) {
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
   - Every mutation (\`create_node\`, \`update_node\`, \`update_matching_nodes\`, \`delete_node\`, \`attach\`, \`detach\`, \`connect_areas\`, \`spawn_library_item\`, \`populate_area\`, \`link_to_library\`) stages changes in a local buffer.
   - The user will inspect the staged changes before applying. Ghost previews show them on the map as dashed nodes.
   - Read tools (\`search_graph_nodes\`, \`list_nodes\`, \`get_node\`, \`list_world_summary\`, \`get_background_map\`) can see your newly staged entities immediately.
3. **SELECTION AWARENESS**: when the user says "this room", "this node", "the selected area" etc., use the Selected node reported in LIVE WORLD CONTEXT — do not ask for its name.
4. **VALID TAGS & SCHEMAS**:
   - Use only valid mechanic tags: \`light_source\`, \`heat_source\`, \`sound_source\`, \`toggleable\`, \`insulation\`, \`armor\`, \`clothing\`, \`weapon\`, \`resistance\`, \`container\`, \`electric\`, \`two_handed\`.
   - Only use standard item actions: \`examine\`, \`take\`, \`use\`, \`open\`, \`close\`, \`eat\`, \`drink\`, \`read\`, \`light\`, \`activate\`, \`equip\`, \`unequip\`, \`throw\`, \`break\`.
   - Only use standard item states: \`normal\`, \`hidden\`, \`open\`, \`closed\`, \`locked\`, \`lit\`, \`unlit\`, \`on\`, \`broken\`, \`charged\`, \`depleted\`.
5. **INTERACTIVE CLARIFICATION**:
   - When a request is ambiguous or multiple options exist, call \`request_clarification\` with clear multiple-choice options for the user.
6. **STYLE & TONE**: write descriptions, names, and dialogue consistent with the scenario theme and world lore below. Reuse lore vocabulary; never invent naming that contradicts it.
7. **CHARACTERS — THE NODE IS THE RECORD**: a character's defining data lives on its \`character\` graph node and is patched with \`update_node\` (the patch map is flat). Recognised fields: \`traits\`, \`tags\`, \`interest_tags\`, \`stats\`, \`skills\`, \`vitals\`, \`decay_rates\`, \`personality\`, \`description\`, \`base_description\`, \`simple_npc\`, \`npc_behavior\`, \`npc_action_interval\`, \`emotion\`. Trait/dict patches MERGE, so existing values are kept. Example — give one character darkvision: \`update_node {"node_id":"...","patch":{"traits":{"dark_vision":true}}}\`. To RENAME a character use \`rename_character {"character":"Jake Halloway","new_name":"Cullen Rutherford"}\` — it moves the players key, the Player name, the node display name AND every character's relationship key. Do NOT rename via \`update_node {name}\`; that only changes the node and leaves the roster/inspector/relationships on the old name.
   - For a GROUP ("all goblins", "every character in the camp"), do NOT loop \`update_node\`: call \`update_matching_nodes {"selector":{"kind":"character","tags":["goblin"]},"patch":{...}}\`. The affected entities are resolved and listed for review before Apply.
8. **TRAITS**: \`traits\` maps a registered trait id to \`true\` (or a parameter string). Call \`list_library_traits\` first — never invent trait ids. \`dark_vision\` and \`darkvision\` are both valid aliases.
9. **FINDING THE CAST & CONTENTS**: \`list_nodes\` is the roster read — filter by \`kind\`, \`tags\`/\`tag\`, \`area\` (nodes with an \`in\` edge to it, i.e. "who is here"), or \`name_contains\`; it counts and pages. Use it before a bulk selector so the affected set is explicit. \`search_graph_nodes\` stays for fuzzy name/description search. Node ids are the storage keys; display names resolve at read time.
10. **ARCHETYPES & LIBRARY**: use \`upsert_library_entry\` / \`delete_library_entry\` for archetype-level changes ("all goblins have darkvision" as a template). They stage like every other op and are validated before Apply (id slug, known fields, mature gate). Library changes do NOT touch already-spawned nodes — \`link_to_library\` and refresh push a template to the world. \`list_library_traits\` / \`search_library_*\` first to reuse real ids.
11. **VALIDATION GATE**: Apply validates every staged op (node/endpoint existence, known trait ids, id slugs, bulk selectors). Errors block the whole Apply and are shown with the offending op index — fix the op (don't re-issue blind) and re-Apply.
12. **WORLD ISSUES**: \`list_world_issues\` reads the Issues tab's validator (empty triggers, orphan/dangling trigger edges, missing way cardinals, library drift, orphaned nodes). When asked to "fix the issues" or "clean up", call it first, work highest severity first, and stage fixes with the normal tools (\`update_node\`, \`delete_node\`, \`attach\`, \`detach\`, \`connect_areas\`, \`create_node\`). Apply re-validates; re-run \`list_world_issues\` after to confirm a fix cleared. You cannot dismiss an issue from here — fix it or leave it for the tab.
13. **TRIGGER AUTHORING**: call \`get_trigger_schema\` FIRST and use only real values. To ADD a trigger, use \`create_trigger\` with \`owner_id\` (the item/area/character that fires it) and \`trigger\` = \`{trigger_type, effects: [{type, params}], conditions?}\` — it writes the node AND the \`triggers\` edge via the engine materialiser (a bare \`create_node\` of a \`logic_trigger\` makes a node the engine never fires). To EDIT an existing trigger, \`update_node\` its properties. \`conditions\` is either a tree \`{operator: "and"|"or"|"not", conditions: [...]}\` or a leaf \`{type, ...}\`. Unknown trigger types, effect types and malformed condition trees are rejected by the validation gate (task-739).
14. **PLAYER STATE vs EDGES**: items/locations and worn gear are graph edges (\`attach\`/\`detach\`). A character's memories, relationships and emotions are Player state — use \`update_player\` with a patch (\`memories\`, \`relationship\`, \`remove_relationship\`, \`emotion\`, \`behaviors\`); do not try to model them as edges (task-738/739).
15. **BEHAVIOURS**: a character's behaviours are a compiled array (\`{trigger, interval, conditions, actions, priority}\`). Read the current set with \`get_behaviours\`, VALIDATE a behaviour-mode graph with \`compile_behaviours\` (it returns \`behaviors\` + \`compile_error\`), then write the compiled array with \`update_player\` \`behaviors\`. Each entry needs a non-empty \`actions\` list of \`{type, ...}\` (task-739).
16. **ACT, DON'T NARRATE**: if answering needs a tool, call it in the SAME response. Never end a turn with only a description of what you are about to do (e.g. "let me check…", "I'll read their arrays"). Prose with no tool call is only for your FINAL answer, after the tools have returned. If you are unsure which character or node is meant, call the read tool or \`request_clarification\` — do not narrate a plan and stop.

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
                const bg = (typeof window !== 'undefined' && _graphBackground()?._state) || null;
                if (bg && bg.imagePath) {
                    const r = bg.rect
                        ? ` placed at ${Math.round(bg.rect.x)},${Math.round(bg.rect.y)} spanning ${Math.round(bg.rect.width)}×${Math.round(bg.rect.height)} graph units`
                        : '';
                    out += `- Background map image: ${bg.imagePath}${r}${bg.locked ? ' (layout locked)' : ''}. You know this image exists but cannot see its pixels — call get_background_map for its transform.\n`;
                } else {
                    out += '- Background map image: none set for this scenario.\n';
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

        /**
         * Reconcile history after Apply WITHOUT discarding it.
         *
         * Applying staged ops changes the WORLD, not the conversation: the model
         * still needs everything it was told about the request. Resetting the
         * session here used to wipe `messages` and the chat transcript on every
         * commit, so each Apply threw away the whole conversation. Instead the
         * live world context is refreshed and the commit is recorded as a note,
         * which is all the model actually needs to stay truthful about what is
         * now real.
         */
        afterApply(appliedCount: number, remaining = 0) {
            if (this.messages.length === 0) {
                this.resetSession();
                return;
            }
            this.messages[0] = { role: 'system', content: this.buildSystemPrompt() };
            const pending = remaining > 0
                ? ` ${remaining} op(s) are STILL staged and do NOT exist in the world yet.`
                : '';
            const note = {
                role: 'system',
                content: `[Applied: ${appliedCount} staged change(s) are now committed to the live world.${pending} Earlier "staged" tool results in this conversation have landed — read the world (search_graph_nodes / list_nodes) instead of re-issuing them.]`
            };
            this.messages.push(note);
            this.contextManager.addMessage(note, { importance: 2 });
            this._notify('session:applied', { appliedCount, remaining });
        }

        /** Execute a turn based on user input */
        async runUserTurn(userPrompt: string, options: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
            if (this.busy) {
                return { error: 'Agent is already busy running a turn.' };
            }
            this.busy = true;
            this._notify('turn:start', { prompt: userPrompt });
            // task-422: read the knobs at turn start so a changed value takes
            // effect on the next prompt without a reload.
            this._applyBudget(await this._readBudget());

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

            let currentIteration = 0;
            let finalAssistantResponse = '';
            let suspended = false;
            let cappedStop = false;
            let ranTool = false;
            let turnError: string | null = null;

            try {
                while (currentIteration < this.maxIterations) {
                    currentIteration++;
                    const pruned = this.contextManager.prune(this.messages);

                    this._notify('llm:calling', {
                        iteration: currentIteration,
                        maxIterations: this.maxIterations,
                        context: this._measureStats(pruned as unknown[])
                    });
                    const response = await llmClient.chatWithTools(pruned, {
                        tools: _nlEditorTools()?.TOOL_DEFINITIONS,
                        tool_choice: 'auto',
                        label: `nl-editor-${currentIteration}`
                    });

                    if (!response) {
                        throw new Error('No response from LLM.');
                    }

                    const { content, tool_calls } = response;
                    // An empty array is truthy: normalise so "no native calls"
                    // means absent, and the XML-in-content fallback below runs.
                    let effectiveToolCalls = (Array.isArray(tool_calls) && tool_calls.length) ? tool_calls : null;

                    // Fallback: some providers/models write tool calls as XML-ish prose
                    // (e.g. "<search_library_items>\n<query>lantern</query>\n</search_library_items>")
                    // instead of native function_call entries — typically after a poisoned
                    // history or a non-tool-calling model. Parse them so the loop keeps
                    // working, and record real function_calls back into history so the
                    // model self-corrects on the next round.
                    if (!effectiveToolCalls && content) {
                        const parsed = this._extractXmlToolCalls(content);
                        if (parsed.length) {
                            effectiveToolCalls = parsed;
                        }
                    }

                    const assistantMsg = {
                        role: 'assistant',
                        content: content || '',
                        tool_calls: effectiveToolCalls || undefined
                    };

                    this.messages.push(assistantMsg);
                    this.contextManager.addMessage(assistantMsg, { importance: effectiveToolCalls ? 2 : 1 });
                    this._notify('message:added', assistantMsg);

                    if (content) finalAssistantResponse = content;

                    if (!effectiveToolCalls || effectiveToolCalls.length === 0) {
                        // Model finished thinking and issued final text
                        break;
                    }

                    // Execute tool calls
                    ranTool = true;
                    for (const call of effectiveToolCalls) {
                        const fnName = call.function?.name;
                        let fnArgs: Record<string, unknown> = {};
                        try {
                            fnArgs = JSON.parse(call.function?.arguments || '{}');
                        } catch (e) {
                            fnArgs = {};
                        }

                        this._notify('tool:start', { name: fnName, args: fnArgs, callId: call.id });

                        const result = await this.router.execute(fnName, fnArgs, {
                            onClarify: (question: string, choices: string[]) => {
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
                if (!suspended && currentIteration >= this.maxIterations) {
                    // task-422: a cap-hit must be visible, never a silent stop
                    // with an empty reply.
                    cappedStop = true;
                    const capMsg = {
                        role: 'system',
                        content: `[Stopped at the ${this.maxIterations}-round limit; the edit may be incomplete.]`
                    };
                    this.messages.push(capMsg);
                    // Dedicated event: the UI styles it as a notice chip. Do not
                    // route it through `message:added`, which would dump the whole
                    // system prompt on every session reset.
                    this._notify('turn:capped', { maxIterations: this.maxIterations });
                }
            } catch (err) {
                console.error('NL Editor agent error:', err);
                turnError = err instanceof Error ? err.message : String(err);
                const errorMsg = { role: 'system', content: `[Error: ${turnError}]` };
                this.messages.push(errorMsg);
                this._notify('error', { error: turnError });
            } finally {
                this.busy = false;
                this._notify('turn:end', {
                    response: finalAssistantResponse,
                    stagedCount: this.staging.getOps().length,
                    error: turnError,
                    capped: cappedStop,
                    ranTool,
                    maxIterations: this.maxIterations
                });
            }

            return {
                messages: this.messages,
                response: finalAssistantResponse,
                stagedOps: this.staging.getOps(),
                error: turnError,
                capped: cappedStop,
                ranTool,
                maxIterations: this.maxIterations
            };
        }
    }

    return { AgentLoop };
})();
(window as unknown as { NLEditorAgent: typeof NLEditorAgent }).NLEditorAgent = NLEditorAgent;

/**
 * Type declarations live BELOW the first value statement on purpose: TypeScript
 * drops a file's leading JSDoc when the first statement is type-only, and
 * `tools/js_module_index.py` reads `@module` out of the emitted .js.
 *
 * The three accessor helpers above are the same shape: `ContextWindowManager`,
 * `NLEditorTools` and `window.GraphBackground` are real runtime globals but are
 * not declared in types/globals.d.ts, which is a shared hub under concurrent
 * edit, so they are read through local casts rather than added there.
 */

/** Resolve the optional ContextWindowManager global, if the page loaded it. */
function _contextWindowManager(): ContextWindowManagerCtor | null {
    const bare = (globalThis as unknown as { ContextWindowManager?: unknown }).ContextWindowManager;
    if (typeof bare !== 'undefined' && bare) return bare as ContextWindowManagerCtor;
    return (window as unknown as { ContextWindowManager?: ContextWindowManagerCtor }).ContextWindowManager || null;
}

/** Resolve the optional NLEditorTools global (nl-editor/tools.js). */
function _nlEditorTools(): NlEditorToolsApi | undefined {
    const bare = (globalThis as unknown as { NLEditorTools?: unknown }).NLEditorTools;
    if (typeof bare !== 'undefined' && bare) return bare as NlEditorToolsApi;
    return (window as unknown as { NLEditorTools?: NlEditorToolsApi }).NLEditorTools;
}

/** Read the graph-background module's private state for the system prompt. */
function _graphBackground(): { _state?: GraphBackgroundState } | undefined {
    return (window as unknown as { GraphBackground?: { _state?: GraphBackgroundState } }).GraphBackground;
}

/** Resolve the optional NlEditorBudget global (nl-editor/budget.js, task-422). */
function _nlBudget(): NlBudgetApi | null {
    return (window as unknown as { NlEditorBudget?: NlBudgetApi }).NlEditorBudget || null;
}

/** Resolve the optional storage provider global for persisting knobs. */
function _storage(): StorageLike | null {
    return (window as unknown as { storage?: StorageLike }).storage || null;
}

/** The active model name, for model-aware token defaults. */
function _activeModel(): string | null {
    const cfg = (window as unknown as { config?: { model?: string } }).config;
    return (cfg && cfg.model) || null;
}

/** Coerce a stored config string to a number (or undefined when absent). */
function _toNum(value: unknown): number | undefined {
    if (value === undefined || value === null || value === '') return undefined;
    const n = Number(value);
    return isFinite(n) ? n : undefined;
}

interface GraphBackgroundState {
    imagePath?: string;
    locked?: boolean;
    rect?: { x: number; y: number; width: number; height: number };
}

interface ContextWindowManagerCtor {
    new (opts: { maxTokens: number; maxMessages: number; recentTurnCount: number }): ContextManagerLike;
}

interface ContextManagerLike {
    prune(messages: unknown): unknown;
    addMessage(message: unknown, meta?: { importance?: number; keepAlways?: boolean }): void;
    reset(): void;
    // Set in place by _applyBudget; absent on the no-op stub.
    maxTokens?: number;
    maxMessages?: number;
    recentTurnCount?: number;
    maxCriticalMessages?: number;
    getStats?: () => ContextStats;
}

/** The five NL editor budget knobs (mirrors nl-editor/budget.js). */
interface NlBudget {
    maxIterations: number;
    maxTokens: number;
    maxMessages: number;
    recentTurnCount: number;
    maxCriticalMessages: number;
}

/** Shape returned by ContextWindowManager.getStats(). */
interface ContextStats {
    totalMessages: number;
    totalTokens: number;
    maxTokens: number;
    maxMessages: number;
    utilization: string;
    isOverLimit: boolean;
}

/** The pure budget helpers published by nl-editor/budget.js (task-422). */
interface NlBudgetApi {
    CONSERVATIVE_MAX_TOKENS: number;
    BUDGET_KEYS: string[];
    contextLengthFor(model?: string | null): number | null;
    defaultBudget(model?: string | null): NlBudget;
    clampBudget(raw?: Partial<NlBudget> | null, model?: string | null): NlBudget;
}

/** The storage provider's async config accessors (config.js). */
interface StorageLike {
    getConfig(key: string): Promise<string | null | undefined> | string | null | undefined;
    setConfig?(key: string, value: unknown): Promise<void> | void;
}

/** One entry of NLEditorTools.TOOL_DEFINITIONS. */
interface NlEditorToolDefinition {
    function?: { name?: string };
}

interface NlEditorToolsApi {
    TOOL_DEFINITIONS?: NlEditorToolDefinition[];
}

/** A tool call as it appears in conversation history. */
interface AgentToolCall {
    id: string;
    type: string;
    function: { name: string; arguments: string };
}

interface AgentMessage {
    role: string;
    content: string;
    tool_calls?: AgentToolCall[];
    tool_call_id?: string;
    name?: string;
}

/** The staging buffer (nl-editor/staging.js) surface this loop uses. */
interface StagingBuffer {
    getOps(): unknown[];
}

interface ToolRouter {
    overlay: { listWorldSummary(): string };
    execute(name: string | undefined, args: Record<string, unknown>,
             hooks?: { onClarify?: (question: string, choices: string[]) => void }): Promise<unknown>;
}
