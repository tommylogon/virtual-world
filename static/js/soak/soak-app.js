/**
 * @module soak-app — bootstrap for the /soak page
 * @contributes page startup: bind the UI, load meta/runs, restore the shared URL config, select a run
 * @powers the Soak Lab boot path and top-level error reporting
 * @relates wires soak-ui.js to soak-state.js
 * @docs none
 */
(function () {
    'use strict';

    function boot() {
        window.SoakUI.init();
        window.SoakState.init()
            .then(() => {
                const meta = window.SoakState.state.meta || {};
                if (!meta.scenarios || !meta.scenarios.length) {
                    window.SoakUI.toast('No scenario files found under data/scenarios.', 'warn', 8000);
                }
            })
            .catch((err) => {
                console.error('[soak] init failed', err);
                window.SoakUI.toast('Could not load Soak Lab: ' + err.message, 'error', 10000);
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
