const puppeteer = require('puppeteer');

(async () => {
    console.log('🚀 Testing flag pattern overlay fix...\n');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1400, height: 900 });

    console.log('📄 Loading page...');
    await page.goto('http://localhost:8080', {
        waitUntil: 'networkidle0',
        timeout: 30000
    });

    await new Promise(resolve => setTimeout(resolve, 2000));
    console.log('✅ Page loaded\n');

    // Test 1: Click on first flag pattern
    console.log('🧪 Test 1: Clicking first Flag Pennant pattern...');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        console.log('Found', cards.length, 'pattern cards');
        if (cards[1]) {
            cards[1].click(); // First pattern
            console.log('Clicked first pattern');
        }
    });

    await new Promise(resolve => setTimeout(resolve, 1500));

    const selected1 = await page.evaluate(() => {
        const sel = document.querySelector('.pattern-card.selected');
        return sel ? sel.querySelector('h4')?.textContent.trim() : 'None';
    });

    console.log(`   ✅ Selected: ${selected1}`);
    await page.screenshot({ path: '/tmp/flag_pattern_1.png', fullPage: true });
    console.log('   📸 Screenshot saved: /tmp/flag_pattern_1.png\n');

    // Test 2: Click on third flag pattern
    console.log('🧪 Test 2: Clicking third Flag Pennant pattern...');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        if (cards[3]) cards[3].click(); // Third pattern
    });

    await new Promise(resolve => setTimeout(resolve, 1500));

    const selected2 = await page.evaluate(() => {
        const sel = document.querySelector('.pattern-card.selected');
        return sel ? sel.querySelector('h4')?.textContent.trim() : 'None';
    });

    console.log(`   ✅ Selected: ${selected2}`);
    await page.screenshot({ path: '/tmp/flag_pattern_3.png', fullPage: true });
    console.log('   📸 Screenshot saved: /tmp/flag_pattern_3.png\n');

    // Test 3: Click wedge pattern
    console.log('🧪 Test 3: Clicking Wedge Rising pattern...');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        if (cards[6]) cards[6].click(); // Wedge (last pattern)
    });

    await new Promise(resolve => setTimeout(resolve, 1500));

    const selected3 = await page.evaluate(() => {
        const sel = document.querySelector('.pattern-card.selected');
        return sel ? sel.querySelector('h4')?.textContent.trim() : 'None';
    });

    console.log(`   ✅ Selected: ${selected3}`);
    await page.screenshot({ path: '/tmp/wedge_pattern.png', fullPage: true });
    console.log('   📸 Screenshot saved: /tmp/wedge_pattern.png\n');

    // Test 4: All patterns
    console.log('🧪 Test 4: Clicking "All Patterns"...');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        if (cards[0]) cards[0].click(); // All Patterns button
    });

    await new Promise(resolve => setTimeout(resolve, 1500));

    console.log('   ✅ Showing all patterns');
    await page.screenshot({ path: '/tmp/all_patterns.png', fullPage: true });
    console.log('   📸 Screenshot saved: /tmp/all_patterns.png\n');

    await browser.close();
    console.log('✅ Testing complete! Check screenshots to verify overlays are visible.');
})();
