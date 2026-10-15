"use strict";
/**
 * @module stage-chat-app — Bootstrap entrypoint for the Stage Chat page
 * @contributes Initializes UI, State, Agent, and visibility listeners
 * @powers Boots Stage Chat
 * @relates StageChatUI, StageChatState, StageChatAgent
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', async () => {
        const config = window.config;
        await config?._initPromise;
        window.llmClient?.configure(config?.toLLMConfig?.());
        window.StageChatUI.init();
        await window.StageChatState.sync();
        window.StageChatState.startPolling(2500);
        window.StageChatAgent.start();
        // Auto-pause when tab is hidden, resume when visible
        document.addEventListener('visibilitychange', () => {
            window.StageChatState.setPaused(document.hidden, 'visibility');
        });
        if (document.hidden)
            window.StageChatState.setPaused(true, 'visibility');
    });
})();
