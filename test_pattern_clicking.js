const puppeteer = require('puppeteer');

(async () => {
    console.log('🚀 Launching browser...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1400, height: 900 });

    console.log('📄 Loading page: http://localhost:8080');
    await page.goto('http://localhost:8080', {
        waitUntil: 'networkidle0',
        timeout: 30000
    });

    console.log('✅ Page loaded\n');

    // Wait for patterns to load
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Get chart title before clicking
    const initialTitle = await page.evaluate(() => {
        const canvas = document.getElementById('chart');
        return canvas ? 'Chart loaded' : 'No chart';
    });
    console.log(`📊 Initial state: ${initialTitle}`);

    // Count pattern cards
    const patternCount = await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        return cards.length;
    });
    console.log(`📋 Found ${patternCount} pattern cards (including "All Patterns" button)\n`);

    // Click on the second pattern card (first actual pattern, index 1)
    console.log('🖱️  Clicking on first pattern card...');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        if (cards[1]) {
            cards[1].click();
        }
    });

    await new Promise(resolve => setTimeout(resolve, 1000));

    // Check if pattern is now selected
    const afterClick = await page.evaluate(() => {
        const selected = document.querySelector('.pattern-card.selected');
        if (!selected) return 'No selection';

        const h4 = selected.querySelector('h4');
        const text = h4 ? h4.textContent.trim() : 'Unknown';

        // Check if chart title changed
        const chartInstance = window.chartInstance;

        return {
            selectedPattern: text,
            hasThumbsUp: text.includes('👉'),
            cardHasSelectedClass: selected.classList.contains('selected')
        };
    });

    console.log('✅ After clicking:');
    console.log(`   Selected pattern: ${afterClick.selectedPattern}`);
    console.log(`   Has 👉 indicator: ${afterClick.hasThumbsUp}`);
    console.log(`   Card has .selected class: ${afterClick.cardHasSelectedClass}`);

    // Take screenshot of selected state
    await page.screenshot({ path: '/tmp/chart_pattern_selected.png', fullPage: true });
    console.log('\n📸 Screenshot saved: /tmp/chart_pattern_selected.png');

    // Click "All Patterns" button
    console.log('\n🖱️  Clicking "All Patterns" button...');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        if (cards[0]) {
            cards[0].click();
        }
    });

    await new Promise(resolve => setTimeout(resolve, 1000));

    // Check if back to all patterns
    const backToAll = await page.evaluate(() => {
        const selected = document.querySelector('.pattern-card.selected');
        const h4 = selected ? selected.querySelector('h4') : null;
        return h4 ? h4.textContent.trim() : 'None';
    });

    console.log('✅ After clicking "All Patterns":');
    console.log(`   Selected: ${backToAll}`);

    await browser.close();
    console.log('\n✅ Test complete!');
})();
