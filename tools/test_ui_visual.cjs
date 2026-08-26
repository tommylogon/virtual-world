const { chromium } = require('playwright');
const BASE = 'http://127.0.0.1:4444';

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

    page.on('pageerror', err => console.error('[PAGE ERROR]', err.message));

    await page.goto(BASE, { waitUntil: 'networkidle' });
    console.log('Page loaded — watch the browser window');

    // Open inspector via agent list
    try {
        const agentBtn = page.locator('[class*="agent"]').first();
        await agentBtn.waitFor({ timeout: 3000 });
        await agentBtn.click();
        await page.waitForTimeout(500);
        console.log('Inspector opened');
    } catch {
        console.log('Clicking first vis-network node instead');
        const node = page.locator('.vis-network .vis-node').first();
        await node.click();
        await page.waitForTimeout(500);
    }

    // Test tabs
    const tabCount = await page.locator('.inspector-tab').count();
    for (let i = 0; i < tabCount; i++) {
        const tab = page.locator('.inspector-tab').nth(i);
        const name = await tab.textContent();
        await tab.click();
        console.log(`Clicked tab: "${name}"`);
        await page.waitForTimeout(400);
    }

    // Hover over something with tooltip
    const tooltipTargets = page.locator('[data-tippy-content]');
    const count = await tooltipTargets.count();
    if (count > 0) {
        const target = tooltipTargets.first();
        await target.hover();
        console.log(`Hovered over tooltip target`);
        await page.waitForTimeout(800);
    }

    // Test toast
    await page.evaluate(() => toastSuccess('✅ Test toast — this is a success!'));
    await page.waitForTimeout(1000);
    await page.evaluate(() => toastError('❌ Test toast — this is an error!'));
    await page.waitForTimeout(1000);
    await page.evaluate(() => toastInfo('ℹ️ Test toast — this is info!'));
    await page.waitForTimeout(1500);

    console.log('Tests complete — closing in 3 seconds...');
    await page.waitForTimeout(3000);
    await browser.close();
})();
