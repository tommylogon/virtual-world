// Smoke suite: the shell boots and its critical surfaces exist (task-444
// Phase 5). Runs in a few seconds; part of `--suite smoke`.

module.exports = {
    name: 'smoke',
    tests: [
        {
            name: 'shell boots with tabs and a command bar',
            smoke: true,
            run: async (page) => {
                const tabs = await page.$$eval('.left-tab',
                    els => els.filter(e => e.offsetParent).map(e => (e.textContent || '').trim()));
                if (tabs.length === 0) throw new Error('no visible .left-tab tabs');
                const cmd = await page.$('#command-input');
                if (!cmd) throw new Error('missing #command-input');
            },
        },
        {
            name: 'boot raises no page errors',
            smoke: true,
            run: async (page, H, ctx) => {
                const pageErrors = ctx.errors.filter(e => e.type === 'pageerror');
                if (pageErrors.length) {
                    throw new Error(pageErrors.map(e => e.message).join(' | '));
                }
            },
        },
    ],
};
