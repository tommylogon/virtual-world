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
        const config = (window as any).config;
        await config?._initPromise;
        (window as any).llmClient?.configure(config?.toLLMConfig?.());
        (window as any).StageChatUI.init();
        await (window as any).StageChatState.sync();
        (window as any).StageChatState.startPolling(2500);
        (window as any).StageChatAgent.start();

        // Auto-pause when tab is hidden, resume when visible
        document.addEventListener('visibilitychange', () => {
            (window as any).StageChatState.setPaused(document.hidden, 'visibility');
        });
        if (document.hidden) (window as any).StageChatState.setPaused(true, 'visibility');
    });
})();
