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
        const config = (window as *FIX*).config;
        await config?._initPromise;
        (window as *FIX*).llmClient?.configure(config?.toLLMConfig?.());
        (window as *FIX*).CommonsUI.init();
        await (window as *FIX*).CommonsState.sync();
        (window as *FIX*).CommonsState.startLiveUpdates();
        (window as *FIX*).CommonsAgent.start();

        // Auto-pause when tab is hidden, resume when visible
        document.addEventListener('visibilitychange', () => {
            (window as *FIX*).CommonsState.setPaused(document.hidden, 'visibility');
        });
        if (document.hidden) (window as *FIX*).CommonsState.setPaused(true, 'visibility');
    });
})();
