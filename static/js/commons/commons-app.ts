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
        const config = (window as any).config;
        await config?._initPromise;
        (window as any).llmClient?.configure(config?.toLLMConfig?.());
        (window as any).CommonsUI.init();
        await (window as any).CommonsState.sync();
        (window as any).CommonsState.startLiveUpdates();
        (window as any).CommonsAgent.start();

        // Auto-pause when tab is hidden, resume when visible
        document.addEventListener('visibilitychange', () => {
            (window as any).CommonsState.setPaused(document.hidden, 'visibility');
        });
        if (document.hidden) (window as any).CommonsState.setPaused(true, 'visibility');
    });
})();
