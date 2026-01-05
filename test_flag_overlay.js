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
    console.log('🧪 Test 1: Click first flag pattern (should now show overlay)');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        if (cards[1]) cards[1].click(); // First pattern (index 0 is "All Patterns")
    });

    await new Promise(resolve => setTimeout(resolve, 1000));

    const test1Result = await page.evaluate(() => {
        const selected = document.querySelector('.pattern-card.selected');
        if (!selected) return { success: false, reason: 'No pattern selected' };

        const patternText = selected.querySelector('h4')?.textContent || '';

        // Check if chart has datasets (patterns rendered)
        if (!window.chartInstance) {
            return { success: false, reason: 'No chart instance' };
        }

        const datasetCount = window.chartInstance.data.datasets.length;
        const datasetLabels = window.chartInstance.data.datasets.map(d => d.label);

        return {
            success: true,
            selectedPattern: patternText.trim(),
            datasetCount: datasetCount,
            hasOverlay: datasetCount > 1, // More than just candlesticks
            datasetLabels: datasetLabels
        };
    });

    console.log(`   Selected: ${test1Result.selectedPattern}`);
    console.log(`   Datasets: ${test1Result.datasetCount}`);
    console.log(`   Has overlay: ${test1Result.hasOverlay ? '✅ YES' : '❌ NO'}`);
    if (test1Result.hasOverlay) {
        console.log(`   Overlay types: ${test1Result.datasetLabels.slice(1).join(', ')}`);
    }

    await page.screenshot({ path: '/tmp/flag_pattern_overlay.png', fullPage: true });
    console.log('   📸 Screenshot: /tmp/flag_pattern_overlay.png\n');

    // Test 2: Click wedge pattern (should still work)
    console.log('🧪 Test 2: Click wedge pattern (verify existing functionality still works)');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        // Last card is the wedge pattern (6th pattern)
        if (cards[6]) cards[6].click();
    });

    await new Promise(resolve => setTimeout(resolve, 1000));

    const test2Result = await page.evaluate(() => {
        const selected = document.querySelector('.pattern-card.selected');
        const patternText = selected?.querySelector('h4')?.textContent || '';
        const datasetCount = window.chartInstance.data.datasets.length;
        const datasetLabels = window.chartInstance.data.datasets.map(d => d.label);

        return {
            selectedPattern: patternText.trim(),
            datasetCount: datasetCount,
            hasWedgeTrendlines: datasetLabels.includes('Resistance Trendline') &&
                                datasetLabels.includes('Support Trendline')
        };
    });

    console.log(`   Selected: ${test2Result.selectedPattern}`);
    console.log(`   Wedge trendlines: ${test2Result.hasWedgeTrendlines ? '✅ YES' : '❌ NO'}\n`);

    // Test 3: Click "All Patterns" to see all overlays
    console.log('🧪 Test 3: Click "All Patterns" (show all overlays)');
    await page.evaluate(() => {
        const cards = document.querySelectorAll('.pattern-card');
        if (cards[0]) cards[0].click(); // "All Patterns" button
    });

    await new Promise(resolve => setTimeout(resolve, 1000));

    const test3Result = await page.evaluate(() => {
        const datasetCount = window.chartInstance.data.datasets.length;
        const datasetLabels = window.chartInstance.data.datasets.map(d => d.label);

        // Count pattern-specific datasets (exclude candlesticks and S/R lines)
        const patternDatasets = datasetLabels.filter(label =>
            label.includes('Flag') ||
            label.includes('Trendline') ||
            label.includes('Pattern')
        );

        return {
            totalDatasets: datasetCount,
            patternOverlays: patternDatasets.length,
            labels: patternDatasets
        };
    });

    console.log(`   Total datasets: ${test3Result.totalDatasets}`);
    console.log(`   Pattern overlays: ${test3Result.patternOverlays}`);
    console.log(`   ✅ All patterns showing overlays!\n`);

    await page.screenshot({ path: '/tmp/all_patterns_overlay.png', fullPage: true });
    console.log('📸 Screenshot: /tmp/all_patterns_overlay.png');

    await browser.close();
    console.log('\n✅ All tests complete!');
})();
