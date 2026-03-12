#!/usr/bin/env node
/**
 * Test chart viewer by simulating user interaction
 */

const puppeteer = require('puppeteer');

async function testChart() {
    console.log('🚀 Starting interactive chart test...\n');

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Collect console messages
    page.on('console', msg => {
        console.log(`[Console ${msg.type()}] ${msg.text()}`);
    });

    // Collect errors
    page.on('pageerror', error => {
        console.log(`❌ [Error] ${error}`);
    });

    try {
        console.log('📄 Loading page...');
        await page.goto('http://localhost:8001/', {
            waitUntil: 'networkidle2',
            timeout: 10000
        });

        console.log('✅ Page loaded');

        // Take initial screenshot
        await page.screenshot({ path: '/tmp/chart_before.png' });
        console.log('📸 Screenshot (before): /tmp/chart_before.png');

        // Clear and fill in ticker
        console.log('\n📝 Entering ticker: AAPL');
        await page.evaluate(() => document.getElementById('ticker').value = '');
        await page.type('#ticker', 'AAPL');

        // Select period
        console.log('📝 Selecting period: 30d');
        await page.select('#period', '30d');

        // Click load button
        console.log('🖱️  Clicking "Load Chart" button...');
        await page.click('button');

        // Wait for chart to load
        console.log('⏳ Waiting for chart to render...');
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Take final screenshot
        await page.screenshot({ path: '/tmp/chart_after.png', fullPage: true });
        console.log('📸 Screenshot (after): /tmp/chart_after.png');

        // Check if chart rendered
        const chartInfo = await page.evaluate(() => {
            const canvas = document.querySelector('#chartContainer canvas');
            if (!canvas) return { found: false };

            const ctx = canvas.getContext('2d');
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const hasPixels = imageData.data.some(pixel => pixel !== 0);

            return {
                found: true,
                width: canvas.width,
                height: canvas.height,
                hasPixels,
                parentId: canvas.parentElement?.id
            };
        });

        console.log('\n📊 Chart info:', chartInfo);

        // Check for error messages in UI
        const errorMessages = await page.evaluate(() => {
            const errorDivs = Array.from(document.querySelectorAll('.error, .error-message, [class*="error"]'));
            return errorDivs.map(div => div.textContent.trim()).filter(text => text);
        });

        if (errorMessages.length > 0) {
            console.log('\n⚠️  Error messages found:', errorMessages);
        }

        // Get pattern list status
        const patternListHTML = await page.evaluate(() => {
            const patternList = document.getElementById('pattern-list');
            return patternList ? patternList.innerHTML : null;
        });

        console.log('\n📋 Pattern list:', patternListHTML ? patternListHTML.substring(0, 200) + '...' : 'Not found');

        console.log('\n' + '='.repeat(60));
        console.log('RESULT');
        console.log('='.repeat(60));
        if (chartInfo.found && chartInfo.hasPixels) {
            console.log('✅ SUCCESS - Chart rendered with pixels!');
            console.log(`   Canvas: ${chartInfo.width}x${chartInfo.height}`);
        } else if (chartInfo.found) {
            console.log('⚠️  PARTIAL - Canvas found but no pixels rendered');
        } else {
            console.log('❌ FAILED - No chart canvas found');
        }

    } catch (error) {
        console.error('\n❌ Test failed:', error.message);
        await page.screenshot({ path: '/tmp/chart_error.png' });
        console.log('📸 Error screenshot: /tmp/chart_error.png');
        throw error;
    } finally {
        await browser.close();
    }
}

testChart()
    .then(() => {
        console.log('\n✅ Test complete');
        process.exit(0);
    })
    .catch(err => {
        console.error('\n❌ Test failed:', err);
        process.exit(1);
    });
