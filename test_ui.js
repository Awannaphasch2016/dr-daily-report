const puppeteer = require('puppeteer');

(async () => {
    console.log('🚀 Launching browser...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Set viewport
    await page.setViewport({ width: 1400, height: 900 });

    console.log('📄 Loading page: http://localhost:8080');

    // Listen for console messages from the page
    page.on('console', msg => {
        console.log('BROWSER CONSOLE:', msg.text());
    });

    // Listen for failed requests
    page.on('requestfailed', request => {
        console.log('❌ FAILED REQUEST:', request.url());
        console.log('   Failure:', request.failure().errorText);
    });

    // Listen for network responses
    page.on('response', response => {
        const url = response.url();
        if (url.includes('chart-data')) {
            console.log(`📡 API Response: ${url}`);
            console.log(`   Status: ${response.status()}`);
        }
    });

    try {
        // Navigate to page
        await page.goto('http://localhost:8080', {
            waitUntil: 'networkidle0',
            timeout: 30000
        });

        console.log('✅ Page loaded');

        // Wait a bit for JavaScript to execute
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Take screenshot
        const screenshotPath = '/tmp/chart_viewer_ui.png';
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`📸 Screenshot saved: ${screenshotPath}`);

        // Check what's in the pattern-list div
        const patternListContent = await page.evaluate(() => {
            const elem = document.getElementById('pattern-list');
            return {
                innerHTML: elem ? elem.innerHTML : 'NOT FOUND',
                textContent: elem ? elem.textContent.trim() : 'NOT FOUND'
            };
        });

        console.log('\n📊 Pattern List Content:');
        console.log('---');
        console.log(patternListContent.textContent);
        console.log('---');

        // Check if error is displayed
        const hasError = await page.evaluate(() => {
            const elem = document.getElementById('pattern-list');
            if (!elem) return null;
            return {
                hasErrorText: elem.textContent.includes('Error Loading Data'),
                hasRetryButton: elem.innerHTML.includes('Retry'),
                hasLoadingText: elem.textContent.includes('Loading'),
                fullText: elem.textContent.trim()
            };
        });

        console.log('\n🔍 Error Check:');
        console.log(`   Has "Error Loading Data": ${hasError.hasErrorText}`);
        console.log(`   Has Retry Button: ${hasError.hasRetryButton}`);
        console.log(`   Has Loading Text: ${hasError.hasLoadingText}`);

        // Get chart title
        const chartTitle = await page.evaluate(() => {
            const elem = document.querySelector('.chart-container canvas');
            return elem ? 'Chart canvas present' : 'No chart canvas';
        });
        console.log(`\n🖼️  Chart: ${chartTitle}`);

        // Check network requests
        const requests = await page.evaluate(() => {
            return window.performance.getEntriesByType('resource')
                .filter(r => r.name.includes('chart-data'))
                .map(r => ({
                    url: r.name,
                    duration: r.duration,
                    transferSize: r.transferSize
                }));
        });

        console.log('\n🌐 Network Requests:');
        if (requests.length > 0) {
            requests.forEach(r => {
                console.log(`   ${r.url}`);
                console.log(`   Duration: ${r.duration.toFixed(2)}ms, Size: ${r.transferSize} bytes`);
            });
        } else {
            console.log('   No chart-data requests found');
        }

    } catch (error) {
        console.error('❌ Error:', error.message);

        // Take error screenshot
        await page.screenshot({ path: '/tmp/chart_viewer_error.png', fullPage: true });
        console.log('📸 Error screenshot saved: /tmp/chart_viewer_error.png');
    } finally {
        await browser.close();
        console.log('\n✅ Browser closed');
    }
})();
