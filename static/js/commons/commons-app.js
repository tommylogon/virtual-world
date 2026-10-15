"use strict";
/**
 * @module commons-app — Bootstrap entrypoint for the The Commons page
 * @contributes Initializes UI, State, Agent, and visibility listeners
 * @powers Boots The Commons
 * @relates CommonsUI, CommonsState, CommonsAgent
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', async () => {
        const config = window.config;
        await config?._initPromise;
        window.llmClient?.configure(config?.toLLMConfig?.());
        window.CommonsUI.init();
        await window.CommonsState.sync();
        window.CommonsState.startPolling(2500);
        window.CommonsAgent.start();
        // Auto-pause when tab is hidden, resume when visible
        document.addEventListener('visibilitychange', () => {
            window.CommonsState.setPaused(document.hidden, 'visibility');
        });
        if (document.hidden)
            window.CommonsState.setPaused(true, 'visibility');
    });
})();
