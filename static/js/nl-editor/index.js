/**
 * index.js — Natural-Language Editor Main Controller (task-387).
 *
 * Integrates StagingBuffer, ToolRouter, AgentLoop, and UI.
 * Exposes window.NLEditor singleton.
 */

window.NLEditor = (() => {
    'use strict';

    class NaturalLanguageEditor {
        constructor() {
            this.staging = new NLEditorStaging.StagingBuffer();
            this.router = new NLEditorTools.ToolRouter(this.staging);
            this.agent = new NLEditorAgent.AgentLoop(this.staging, this.router);
            this.ui = new NLEditorUI.UI(this);
            this.initialized = false;
        }

        init() {
            if (this.initialized) return;
            this.initialized = true;
            this.ui.init();

            // Wire staging changes to UI
            this.staging.onChange((ops) => {
                this.ui.updateStagedOps(ops);
            });

            // Wire agent events to UI
            this.agent.onUpdate((event, data) => {
                switch (event) {
                    case 'turn:start':
                        this.ui.hideClarification();
                        this.ui.setStatus('Thinking...', true);
                        break;
                    case 'llm:calling':
                        this.ui.setStatus(`Thinking (round ${data.iteration}/10)…`, true);
                        break;
                    case 'message:added':
                        if (data.role === 'user') {
                            this.ui.appendUserMessage(data.content);
                        } else if (data.role === 'assistant') {
                            this.ui.appendAssistantMessage(data.content, data.tool_calls);
                        }
                        break;
                    case 'tool:start':
                        this.ui.appendToolRunning(data.name);
                        this.ui.setStatus(`running ${data.name}…`, true);
                        break;
                    case 'tool:finished':
                        this.ui.appendToolEvent(data.name, data.result);
                        this.ui.setStatus('Thinking...', true);
                        break;
                    case 'clarification:requested':
                        this.ui.showClarification(data.question, data.choices);
                        this.ui.setStatus('Waiting for choice', false);
                        break;
                    case 'turn:end':
                        this.ui.setStatus('Ready', false);
                        // Refresh ghost previews; auto-pan when this turn staged
                        // something new ("here's what I just drafted").
                        if (typeof NLEditorGhosts !== 'undefined' && NLEditorGhosts?.refresh) {
                            NLEditorGhosts.refresh({ freshOps: true });
                        }
                        break;
                    case 'error':
                        this.ui.setStatus('Error', false);
                        break;
                    case 'session:reset':
                        if (this.ui.chatList) this.ui.chatList.innerHTML = '';
                        this.ui.hideClarification();
                        this.ui.setStatus('Ready', false);
                        break;
                }
            });

            // Listen for scenario change / restart from worldState
            if (typeof worldState !== 'undefined' && worldState?.on) {
                let lastScenario = null;
                worldState.on('update', (state) => {
                    const currentScenario = state?._scenario_source || state?.scenario || null;
                    if (lastScenario !== null && currentScenario !== lastScenario) {
                        this.reset();
                    }
                    lastScenario = currentScenario;
                });
            }
        }

        /** Submit user message to agent */
        async send(userText) {
            this.init();
            return this.agent.runUserTurn(userText);
        }

        /** Reset session */
        reset() {
            this.staging.clear();
            this.agent.resetSession();
            this.ui.hideClarification();
        }

        /** Apply staged mutations to live world */
        async apply() {
            const res = await this.staging.apply();
            if (res.success) {
                if (typeof toastSuccess === 'function') {
                    toastSuccess(`Applied ${res.appliedCount} changes to world.`);
                }
                this.agent.resetSession();
            } else if (res.errors && res.errors.length > 0) {
                if (typeof toastError === 'function') {
                    toastError(`Apply partially failed: ${res.errors.join(', ')}`);
                }
            }
            if (typeof NLEditorGhosts !== 'undefined') NLEditorGhosts?.refresh();
            return res;
        }

        /** Apply only the checked staged ops; unchecked stay staged. */
        async applySelected(ids) {
            const res = await this.staging.apply(ids);
            if (res.success) {
                if (typeof toastSuccess === 'function') {
                    toastSuccess(`Applied ${res.appliedCount} changes. ${this.staging.getOps().length} still staged.`);
                }
                this.agent.resetSession();
            } else if (res.errors && res.errors.length > 0) {
                if (typeof toastError === 'function') {
                    toastError(`Apply partially failed: ${res.errors.join(', ')}`);
                }
            }
            if (typeof NLEditorGhosts !== 'undefined') NLEditorGhosts?.refresh();
            return res;
        }

        /** Open NL Editor side panel */
        openPanel() {
            this.init();
            if (typeof ui !== 'undefined' && ui?.switchLeftTab) {
                ui.switchLeftTab('nl-editor');
            } else if (window.ui?.switchLeftTab) {
                window.ui.switchLeftTab('nl-editor');
            } else {
                const tabBtn = document.querySelector('[data-tab="nl-editor"]');
                tabBtn?.click();
            }
            setTimeout(() => {
                document.getElementById('nl-input')?.focus();
            }, 100);
        }
    }

    const instance = new NaturalLanguageEditor();

    // Auto-init when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => instance.init());
    } else {
        setTimeout(() => instance.init(), 100);
    }

    return instance;
})();
