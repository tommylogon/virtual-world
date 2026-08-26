const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // Grab page text to confirm loaded
    const bodyText = await page.evaluate(() => document.body.textContent);
    console.log('Page loaded. Body:', bodyText);

    // Screenshot initial state
    await page.screenshot({ path: 'C:\\Projects\\code\\virtual_world\\tools\\initial.png', fullPage: false });

    // Click the graph canvas center to select a room node
    const canvas = await page.$('#graph-container canvas');
    if (canvas) {
        const box = await canvas.boundingBox();
        console.log('Canvas bounds:', JSON.stringify(box));
        await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
        await page.waitForTimeout(1500);
    }

    // Check what the inspector shows
    let inspText = '';
    try {
        inspText = await page.evaluate(() => document.getElementById('inspector-panel').textContent);
        console.log('Inspector after graph click:', inspText);
    } catch (e) {
        console.log('Inspector not updated by graph click');
    }

    // Also try clicking first agent in agent list to get any room context
    const agentItems = await page.$$('#agent-list .agent-item');
    console.log('Agent items found:', agentItems.length);
    if (agentItems.length > 0) {
        const agentText = await agentItems[0].evaluate(el => el.textContent);
        console.log('Clicking agent:', agentText.trim());
        await agentItems[0].click();
        await page.waitForTimeout(1000);

        inspText = await page.evaluate(() => document.getElementById('inspector-panel')?.textContent || 'empty');
        console.log('Inspector after agent click:', inspText);
        await page.screenshot({ path: 'C:\\Projects\\code\\virtual_world\\tools\\agent-inspected.png' });
    }

    // Now look for exits / door buttons in the inspector
    const exitItems = await page.$$('.exit-item');
    console.log('Exit items found:', exitItems.length);

    if (exitItems.length > 0) {
        // Try clicking Inspect Door first
        const inspectBtns = await page.$$('.exit-item button');
        console.log('Total exit buttons:', inspectBtns.length);

        for (const btn of inspectBtns) {
            const txt = await btn.evaluate(el => el.textContent.trim());
            console.log('  Button:', txt);
        }

        // Try the Open button
        const openBtn = await page.evaluate(() => {
            const buttons = document.querySelectorAll('.exit-item button');
            for (const b of buttons) {
                if (b.textContent.includes('Open') || b.textContent.includes('🔓')) {
                    b.click();
                    return 'clicked Open';
                }
            }
            return 'no Open button found';
        });
        console.log('Open button result:', openBtn);
        await page.waitForTimeout(1000);
        await page.screenshot({ path: 'C:\\Projects\\code\\virtual_world\\tools\\after-open.png' });

        // Check event stream
        const stream = await page.evaluate(() => document.getElementById('event-stream')?.textContent || 'empty');
        console.log('Event stream after open:', stream);

        // Check console logs
        const logs = await page.evaluate(() => {
            const entries = document.querySelectorAll('#event-stream .msg-bubble');
            return Array.from(entries).slice(-5).map(e => e.textContent.trim());
        });
        console.log('Last event stream entries:', JSON.stringify(logs));

        // Try Close button
        const closeBtn = await page.evaluate(() => {
            const buttons = document.querySelectorAll('.exit-item button');
            for (const b of buttons) {
                if (b.textContent.includes('Close') || b.textContent.includes('🔒')) {
                    b.click();
                    return 'clicked Close';
                }
            }
            return 'no Close button found';
        });
        console.log('Close button result:', closeBtn);
        await page.waitForTimeout(1000);
        await page.screenshot({ path: 'C:\\Projects\\code\\virtual_world\\tools\\after-close.png' });

        const stream2 = await page.evaluate(() => document.getElementById('event-stream')?.textContent|| 'empty');
        console.log('Event stream after close:', stream2);

        // Try Inspect Door
        const inspectResult = await page.evaluate(() => {
            const buttons = document.querySelectorAll('.exit-item button');
            for (const b of buttons) {
                if (b.textContent.includes('Inspect') || b.textContent.includes('🔍')) {
                    b.click();
                    return 'clicked Inspect Door';
                }
            }
            return 'no Inspect button found';
        });
        console.log('Inspect Door result:', inspectResult);
        await page.waitForTimeout(1000);
        await page.screenshot({ path: 'C:\\Projects\\code\\virtual_world\\tools\\after-inspect.png' });

        const stream3 = await page.evaluate(() => document.getElementById('inspector-panel')?.textContent || 'empty');
        console.log('Inspector after inspect:', stream3);
    } else {
        console.log('No exit items found. Look at full inspector HTML:');
        const html = await page.evaluate(() => document.getElementById('inspector-panel')?.innerHTML || 'empty');
        console.log(html);
    }

    await browser.close();
    console.log('Done');
})();
