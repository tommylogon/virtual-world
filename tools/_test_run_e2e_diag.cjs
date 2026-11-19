
    const { chromium } = require('playwright');
    (async () => {
        const browser = await chromium.launch({ headless: true });
        const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
        await page.goto('http://127.0.0.1:59326', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(2000);

        // Check 1: Open Library Browser (bug-520)
        // Click the build dropdown then click Library
        const libResult = await page.evaluate(async () => {
            await window.openLibraryBrowser();
            await new Promise(r => setTimeout(r, 400));
            const el = document.getElementById('library-modal');
            const rect = el ? el.getBoundingClientRect() : null;
            const res = {
                display: el ? window.getComputedStyle(el).display : null,
                visible: rect ? (rect.width > 0 && rect.height > 0) : false
            };
            window.closeLibraryBrowser();
            return res;
        });
        console.log('CHECK 1 (Library modal):', JSON.stringify(libResult));

        // Check 3: Person menu exposes task-610 actions & Check 5: no orphaned .tsv-scrim (task-612)
        const htcCheck = await page.evaluate(async () => {
            // Request turn for Explorer
            window.HumanTurnComposer.request('Explorer');
            await new Promise(r => setTimeout(r, 600));

            // In htc_fixture, Explorer is in Courtyard where Doc Holliday also is!
            const personChips = [...document.querySelectorAll('#htc-scene-people .tsv-person-chip')];
            let actionsFound = [];
            let chipClicked = false;
            if (personChips.length > 0) {
                chipClicked = true;
                personChips[0].click();
                await new Promise(r => setTimeout(r, 300));
                const menuItems = [...document.querySelectorAll('.tsv-person-menu button, .tsv-person-menu .dropdown-item')];
                actionsFound = menuItems.map(b => b.innerText.trim());
            }

            // Close the turn modal while menu is open
            const closeBtn = document.querySelector('#htc-modal .modal-close') || document.querySelector('#htc-modal button.modal-close');
            if (closeBtn) closeBtn.click();
            else window.HumanTurnComposer.hidePanel?.();

            await new Promise(r => setTimeout(r, 300));
            const scrims = [...document.querySelectorAll('.tsv-scrim')];
            const visibleScrims = scrims.filter(s => {
                const r = s.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && window.getComputedStyle(s).display !== 'none';
            });

            return {
                chipClicked,
                personChipsCount: personChips.length,
                actionsCount: actionsFound.length,
                sampleActions: actionsFound.slice(0, 8),
                visibleScrimsCount: visibleScrims.length
            };
        });
        console.log('CHECK 3 & 5 (HTC person menu & scrim):', JSON.stringify(htcCheck));

        // Check 4: Hidden way stays out of WAYS OUT (bug-23)
        // Check scene for Explorer in Library
        const wayCheck = await page.evaluate(async () => {
            const scene = await fetch('/api/scene/Explorer').then(r => r.json());
            const wayNames = (scene.ways || []).map(w => w.name);
            return {
                area: scene.area ? scene.area.name : null,
                ways: wayNames,
                hiddenWayLeaked: wayNames.some(w => w.includes('false bookcase'))
            };
        });
        console.log('CHECK 4 (Hidden ways gate):', JSON.stringify(wayCheck));

        await browser.close();
    })();
    