// Error-boundary suite (task-444 Phase 4).
//
// Mocks server failures with page.route() and asserts the player sees a
// readable message, never a raw traceback. Also checks that malformed data
// produces a short error rather than a stack trace.

const TRACEBACK = 'Traceback (most recent call last):\n  File "app.py", line 1, in <module>\nValueError: boom';
const RAW_ERROR = /\bTraceback\b|File "\S/;

async function submitCommand(page, command) {
    await page.fill('#command-input', command);
    await page.press('#command-input', 'Enter');
    await page.waitForTimeout(900);
}

async function visibleText(page) {
    return page.evaluate(() => document.body.innerText || '');
}

module.exports = {
    name: 'error-boundaries',
    tests: [
        {
            name: 'a mocked JSON 500 shows a readable message, not a traceback',
            smoke: true,
            run: async (page) => {
                await page.route('**/api/action', route => route.fulfill({
                    status: 500,
                    contentType: 'application/json',
                    body: JSON.stringify({ error: TRACEBACK }),
                }));
                try {
                    await submitCommand(page, 'look');
                    const text = await visibleText(page);
                    if (RAW_ERROR.test(text)) {
                        throw new Error('raw traceback visible in the UI');
                    }
                    if (!/Request failed \(500/.test(text)) {
                        throw new Error('no readable "Request failed (500" message was shown');
                    }
                } finally {
                    await page.unroute('**/api/action');
                }
            },
        },
        {
            name: 'a non-JSON 500 still shows a readable message',
            run: async (page) => {
                await page.route('**/api/action', route => route.fulfill({
                    status: 500,
                    contentType: 'text/html',
                    body: `<html><body>${TRACEBACK}</body></html>`,
                }));
                try {
                    await submitCommand(page, 'look');
                    const text = await visibleText(page);
                    if (RAW_ERROR.test(text)) throw new Error('raw traceback visible in the UI');
                    if (!/Request failed \(500/.test(text)) {
                        throw new Error('no readable "Request failed (500" message was shown');
                    }
                } finally {
                    await page.unroute('**/api/action');
                }
            },
        },
        {
            name: 'malformed data produces a short error, not a traceback',
            run: async (page) => {
                // `ApiClient` is a top-level class binding, not a window
                // property, so reference it bare.
                const out = await page.evaluate(async () => ApiClient.post('/api/graph/node', {}));
                if (!out || !out.error) throw new Error('malformed request surfaced no error');
                if (RAW_ERROR.test(String(out.error))) {
                    throw new Error(`raw traceback surfaced: ${out.error}`);
                }
                if (String(out.error).length > 300) {
                    throw new Error(`error message is not readable: ${String(out.error).slice(0, 80)}...`);
                }
            },
        },
    ],
};
