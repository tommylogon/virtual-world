/**
 * @module stage-chat-app — Bootstrap entrypoint for the Stage Chat page
 * @contributes Initializes UI, State, Agent, and visibility listeners
 * @powers Boots Stage Chat
 * @relates StageChatUI, StageChatState, StageChatAgent
 * @docs docs/virtualWorld/dev_tasks/todo/gameplay/task-824-stage-chat-turn-based-character-perspective-chat-page.md
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', async () => {
        (window as any).StageChatUI.init();
        await (window as any).StageChatState.sync();
        (window as any).StageChatState.startPolling(2500);
        (window as any).StageChatAgent.start();

        // Auto-pause when tab is hidden, resume when visible
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                (window as any).StageChatAgent.stop();
            } else {
                (window as any).StageChatAgent.start();
            }
        });
    });
})();
