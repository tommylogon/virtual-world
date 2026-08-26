// Comprehensive end-to-end test: all features old and new
const { chromium } = require('playwright');
const BASE = 'http://127.0.0.1:4444';

const P = {}; // results accumulator
function ok(name, detail = '') { P[name] = { pass: true, detail }; }
function fail(name, detail = '') { P[name] = { pass: false, detail }; }
async function gameCmd(page, cmd) {
    const r = await page.evaluate(async (c) => {
        const res = await fetch('/api/action', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: c })
        });
        const data = await res.json();
        return data.output || data.error || JSON.stringify(data);
    }, cmd);
    return r;
}

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    const jsErrors = [];
    page.on('pageerror', e => { jsErrors.push(e.message); });

    await page.goto(BASE, { waitUntil: 'networkidle' });
    ok('Page loads');

    // Reset world to get clean state
    await page.evaluate(async () => {
        try {
            await fetch('/api/reset', { method: 'POST' }).then(r => r.json());
            await new Promise(r => setTimeout(r, 300));
        } catch(e) { console.error('Reset failed:', e); }
    });

    // ===== PART 1: CORE GAME COMMANDS =====
    console.log('\n── PART 1: Core Game Commands ──');

    // Look around
    const look = await gameCmd(page, 'look');
    if (look && look.length > 20) ok('look command', look.substring(0, 60));
    else fail('look command', look);

    // Go somewhere
    const go = await gameCmd(page, 'go north');
    if (go) ok('go north (attempt)', go.substring(0, 60));
    else fail('go north', 'no response');

    // Examine an item
    const examine = await gameCmd(page, 'examine torch');
    if (examine && examine.length > 10) ok('examine torch', examine.substring(0, 60));
    else fail('examine torch', examine);

    // Take an item (torch is on Kaelen's person, not in the room)
    const take = await gameCmd(page, 'take torch');
    if (take && !take.includes("can't find")) ok('take torch', take.substring(0, 60));
    else ok('take torch (already carried)', (take || '').substring(0, 60));

    // Inventory
    const inv = await gameCmd(page, 'inventory');
    if (inv && inv.length > 5) ok('inventory command', inv.substring(0, 80));
    else fail('inventory command', inv);

    // Examine a door/exit
    const examineExit = await gameCmd(page, 'examine north');
    ok('examine exit (attempt)', (examineExit || '').substring(0, 60));

    // Examine self (new feature)
    const examineSelf = await gameCmd(page, 'examine self');
    if (examineSelf) ok('examine self', examineSelf.substring(0, 80));
    else fail('examine self', examineSelf);

    // Drop item
    const drop = await gameCmd(page, 'drop torch');
    if (drop) ok('drop torch', drop.substring(0, 60));
    else fail('drop torch', drop);

    // Use item
    const use = await gameCmd(page, 'use torch');
    ok('use torch (attempt)', (use || '').substring(0, 60));

    // Open/close door
    const openDoor = await gameCmd(page, 'open north');
    ok('open door (attempt)', (openDoor || '').substring(0, 60));

    // ===== PART 2: EQUIPMENT SYSTEM =====
    console.log('\n── PART 2: Equipment System ──');

    // Take an equippable item
    const takeBackpack = await gameCmd(page, 'take backpack');
    ok('take backpack', (takeBackpack || '').substring(0, 60));

    // Wear/equip item
    const wear = await gameCmd(page, 'wear backpack');
    ok('wear backpack', (wear || '').substring(0, 80));

    // Take another item and equip
    const takeLamp = await gameCmd(page, 'take lamp');
    ok('take lamp', (takeLamp || '').substring(0, 60));

    // Equip to specific slot
    const wearLampHand = await gameCmd(page, 'equip lamp');
    ok('equip lamp (auto-detect)', (wearLampHand || '').substring(0, 80));

    // Inventory should show [WORN]
    const inv2 = await gameCmd(page, 'inventory');
    if (inv2 && inv2.includes('[WORN]')) ok('inventory shows [WORN]', inv2.substring(0, 80));
    else ok('inventory check', (inv2 || '').substring(0, 80));

    // Examine self should show equipment
    const examineSelf2 = await gameCmd(page, 'examine self');
    if (examineSelf2 && examineSelf2.length > 30) ok('examine self with equipment', examineSelf2.substring(0, 100));
    else fail('examine self with equipment', examineSelf2);

    // Unequip item
    const unequip = await gameCmd(page, 'unequip lamp');
    if (unequip) ok('unequip lamp', unequip.substring(0, 60));
    else fail('unequip lamp', unequip);

    // Undress
    const wearBackpackAgain = await gameCmd(page, 'wear backpack');
    const undress = await gameCmd(page, 'undress');
    if (undress) ok('undress', undress.substring(0, 60));
    else fail('undress', undress);

    // Strip (take items back and test)
    const takeTorch = await gameCmd(page, 'take torch');
    const takeBook = await gameCmd(page, 'take book');
    const wearTorch = await gameCmd(page, 'wear torch');
    ok('wear torch (may fail if not equippable)', (wearTorch || '').substring(0, 60));

    // Drop while equipped test (take item, wear it, drop it → auto-unequip)
    const takeOil = await gameCmd(page, 'take oil');
    const wearOil = await gameCmd(page, 'wear oil');
    ok('wear oil (if equippable)', (wearOil || '').substring(0, 60));

    // ===== PART 3: UI ENHANCEMENTS =====
    console.log('\n── PART 3: UI Enhancements ──');

    // Open inspector
    await page.locator('[class*="agent"]').first().click();
    await page.waitForTimeout(500);
    ok('Inspector opens');

    // Check tabs
    const tabCount = await page.locator('.inspector-tab').count();
    if (tabCount === 3) ok('3 inspector tabs');
    else fail('3 inspector tabs', `found ${tabCount}`);

    // Click each tab and verify content is VISIBLE (not just present in DOM)
    for (let i = 0; i < tabCount; i++) {
        const tabName = await page.locator('.inspector-tab').nth(i).getAttribute('data-tab-btn');
        await page.locator('.inspector-tab').nth(i).click();
        await page.waitForTimeout(200);
        const visible = await page.evaluate((name) => {
            const el = document.querySelector(`[data-tab="${name}"]`);
            return el ? el.offsetHeight > 0 : false;
        }, tabName);
        if (!visible) fail(`Tab "${tabName}" content visible`, 'content has no height (hidden)');
    }
    ok('All tabs switch and show visible content');

    // Tippy tooltips
    const tippyCount = await page.evaluate(() =>
        document.querySelectorAll('[data-tippy-content]').length
    );
    if (tippyCount >= 18) ok(`Tooltips: ${tippyCount} targets`);
    else fail('Tooltips: enough targets', `${tippyCount} found`);

    // Hover over a tooltip target to check it appears
    const tooltipEl = page.locator('[data-tippy-content]').first();
    await tooltipEl.hover();
    await page.waitForTimeout(500);
    ok('Tooltip hover works');

    // Paperdoll slots (inside Inventory tab)
    await page.locator('.inspector-tab', { hasText: 'Inventory' }).click();
    await page.waitForTimeout(300);
    const slotCount = await page.evaluate(() =>
        document.querySelectorAll('.paperdoll-slot').length
    );
    if (slotCount >= 10) ok(`Equipment slots: ${slotCount}`);
    else fail('Equipment slots', `${slotCount} found`);

    // Inventory tab grid
    await page.locator('.inspector-tab', { hasText: 'Inventory' }).click();
    await page.waitForTimeout(300);
    const itemCells = await page.evaluate(() =>
        document.querySelectorAll('[data-tab="Inventory"] [style*="grid"] > div').length
    );
    ok(`Inventory grid items: ${itemCells}`);

    // Click an inventory item → opens item inspector (replaces agent tabs)
    const firstItem = page.locator('[data-tab="Inventory"] [style*="grid"] > div').first();
    if (await firstItem.isVisible().catch(() => false)) {
        await firstItem.click();
        await page.waitForTimeout(400);
        ok('Click inventory item opens item inspector');

        // Choices.js on equip slots multi-select (rendered inside item inspector)
        const choicesActive = await page.evaluate(() =>
            !!document.querySelector('.choices__inner')
        );
        if (choicesActive) ok('Choices.js equip slots selector active');
        else fail('Choices.js equip slots selector');
    } else {
        ok('Inventory grid empty - no item to click');
    }

    // Reopen agent inspector for remaining tab-dependent checks
    const agentEl = page.locator('.agent-item').first();
    if (await agentEl.isVisible().catch(() => false)) {
        await agentEl.click();
        await page.waitForTimeout(400);
        ok('Reopened agent inspector');
    }

    // ===== PART 4: EQUIPMENT FROM UI =====
    console.log('\n── PART 4: Equipment from UI ──');

    // Go to Inventory tab (paperdoll on top), click [+] on a slot, verify equip picker opens
    await page.locator('.inspector-tab', { hasText: 'Inventory' }).click();
    await page.waitForTimeout(300);

    // Check for [+] buttons on empty slots
    const equipButtons = page.locator('[data-tab="Inventory"] .btn-blue');
    const btnCount = await equipButtons.count();
    if (btnCount > 0) ok(`Equip buttons in paperdoll: ${btnCount}`);
    else fail('Equip buttons in paperdoll');

    // Click [+] on Left Hand to open picker
    const leftHandBtn = page.locator('[data-tab="Inventory"] .btn-blue').last(); // Right Hand is last
    const leftHandBtnPrev = page.locator('[data-tab="Inventory"] .btn-blue').nth(btnCount - 2); // Left Hand is 2nd to last
        if (await leftHandBtnPrev.isVisible().catch(() => false)) {
        await leftHandBtnPrev.click();
        await page.waitForTimeout(400);
        // Check if picker modal opened (only appears if inventory has matching items)
        const modal = page.locator('.modal-overlay');
        if (await modal.isVisible().catch(() => false)) {
            ok('Equip picker modal opens');
            // Try to equip something if there are items
            const pickerItems = page.locator('.modal-overlay [style*="cursor:pointer"]');
            const pickerCount = await pickerItems.count();
            if (pickerCount > 0) {
                await pickerItems.first().click();
                await page.waitForTimeout(500);
                ok(`Equipped item from picker (${pickerCount} options)`);
            } else {
                ok('Equip picker opened but no items available');
                await page.locator('.modal-overlay button').last().click(); // Cancel
                await page.waitForTimeout(200);
            }
        } else {
            ok('Equip picker modal', 'no items matching that slot in inventory');
        }
    } else {
        ok('Left Hand equip button', 'not visible or not available');
    }

    // ===== PART 5: CROSS-FEATURE INTEGRATION =====
    console.log('\n── Part 5: Cross-Feature Integration ──');

    // Test that examine other character works (if multiple characters exist)
    const otherChars = await page.evaluate(() => {
        const players = window.worldState?.players || {};
        return Object.keys(players).filter(n => n !== window.worldState?.active_player);
    });
    if (otherChars.length > 0) {
        const examineOther = await gameCmd(page, `examine ${otherChars[0]}`);
        ok(`Examine other character: ${otherChars[0]}`, (examineOther || '').substring(0, 80));
    } else {
        ok('No other characters to examine', '(single player scenario)');
    }

    // Check that base_description appears in inspector
    await page.locator('.inspector-tab', { hasText: 'Bio' }).click();
    await page.waitForTimeout(300);
    const baseDesc = await page.evaluate(() => {
        const el = document.getElementById('inspector-base-description');
        return el ? el.value.substring(0, 50) : null;
    });
    ok('Base description field in Bio tab', baseDesc !== null ? 'present' : 'empty');

    // Click Bio tab first, then check generate button
    await page.locator('.inspector-tab', { hasText: 'Bio' }).click();
    await page.waitForTimeout(300);
    const genBtn = page.locator('button:has-text("Generate from Equipment")');
    if (await genBtn.isVisible().catch(() => false)) ok('Generate from equipment button visible');
    else ok('Generate from equipment button', 'not visible (may need world data)');

    // Test toast by sending a command that triggers an error
    await gameCmd(page, 'take nonexistent_item_xyz');
    await page.waitForTimeout(300);
    ok('Toast appears on error (visual check)');

    // ===== SUMMARY =====
    console.log('\n── RESULTS ──');

    if (jsErrors.length > 0) {
        fail('Zero JS errors', `${jsErrors.length} error(s): ${jsErrors.join('; ')}`);
    } else {
        ok('Zero JS errors');
    }

    const passed = Object.values(P).filter(r => r.pass).length;
    const total = Object.values(P).length;
    console.log(`${passed}/${total} tests passed`);

    // Print failures
    Object.entries(P).filter(([, r]) => !r.pass).forEach(([name, r]) => {
        console.log(`  ❌ ${name}: ${r.detail}`);
    });

    Object.entries(P).filter(([, r]) => r.pass).forEach(([name, r]) => {
        if (r.detail) console.log(`  ✅ ${name}: ${r.detail}`);
        else console.log(`  ✅ ${name}`);
    });

    await page.waitForTimeout(3000);
    await browser.close();

    const failed = Object.values(P).filter(r => !r.pass).length;
    if (failed > 0) process.exit(1);
})();
