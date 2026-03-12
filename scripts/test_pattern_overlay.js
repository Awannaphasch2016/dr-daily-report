#!/usr/bin/env node
/**
 * Test pattern overlay rendering with Puppeteer
 */

const puppeteer = require('puppeteer');

async function testPatternOverlay() {
    console.log('🚀 Testing pattern overlay rendering...\n');

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Collect console messages
    page.on('console', msg => {
        console.log('[Console ' + msg.type() + '] ' + msg.text());
    });

    page.on('pageerror', error => {
        console.log('❌ [Error] ' + error);
    });

    try {
        console.log('📄 Loading chart viewer...');
        await page.goto('http://localhost:8001/', {
            waitUntil: 'networkidle2',
            timeout: 15000
        });

        // Take initial screenshot
        await page.screenshot({ path: '/tmp/pattern_before.png' });
        console.log('📸 Screenshot (before): /tmp/pattern_before.png');

        // Clear and enter PFE ticker
        console.log('\n📝 Entering ticker: PFE');
        await page.evaluate(() => document.getElementById('ticker').value = '');
        await page.type('#ticker', 'PFE');

        // Select 6mo period (6 months) for pattern detection
        console.log('📝 Selecting period: 6mo');
        await page.select('#period', '6mo');

        // Click load button
        console.log('🖱️  Clicking "Load Chart" button...');
        await page.click('button');

        // Wait for chart and patterns to load
        console.log('⏳ Waiting for chart and patterns to render...');
        await new Promise(resolve => setTimeout(resolve, 10000));

        // Take screenshot after loading
        await page.screenshot({ path: '/tmp/pattern_after.png', fullPage: true });
        console.log('📸 Screenshot (after): /tmp/pattern_after.png');

        // Check chart rendering (canvas ID is 'chart', not inside #chartContainer)
        const chartInfo = await page.evaluate(() => {
            const canvas = document.querySelector('#chart') || document.querySelector('canvas');
            if (!canvas) return { found: false };

            const ctx = canvas.getContext('2d');
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const hasPixels = imageData.data.some(pixel => pixel !== 0);

            return {
                found: true,
                width: canvas.width,
                height: canvas.height,
                hasPixels: hasPixels
            };
        });

        console.log('\n📊 Chart info:', chartInfo);

        // Check pattern list content
        const patternInfo = await page.evaluate(() => {
            const patternList = document.getElementById('pattern-list');
            if (!patternList) return { found: false };

            const items = patternList.querySelectorAll('li, div, p');
            const text = patternList.innerText || patternList.textContent;

            return {
                found: true,
                itemCount: items.length,
                text: text.trim().substring(0, 500)
            };
        });

        console.log('\n📋 Pattern list:', patternInfo);

        // Check page content for pattern indicators
        const pageContent = await page.evaluate(() => {
            const bodyText = document.body.innerText;
            return {
                hasVCPText: bodyText.includes('VCP') || bodyText.includes('vcp') || bodyText.includes('VCPU'),
                hasBullishText: bodyText.includes('bullish') || bodyText.includes('Bullish'),
                hasPatternText: bodyText.includes('pattern') || bodyText.includes('Pattern'),
                hasNoPatterns: bodyText.includes('No patterns')
            };
        });

        console.log('\n🔍 Page content check:', pageContent);

        // Summary
        console.log('\n' + '='.repeat(60));
        console.log('RESULT');
        console.log('='.repeat(60));

        if (chartInfo.found && chartInfo.hasPixels) {
            console.log('✅ Chart rendered successfully');
            console.log('   Canvas: ' + chartInfo.width + 'x' + chartInfo.height);
        } else {
            console.log('❌ Chart not rendered');
        }

        if (pageContent.hasNoPatterns) {
            console.log('⚠️  "No patterns" displayed - pattern overlay NOT rendering');
        } else if (pageContent.hasVCPText || pageContent.hasBullishText) {
            console.log('✅ Pattern information displayed on page');
        } else {
            console.log('⚠️  Pattern display status unclear - check screenshots');
        }

        console.log('\n📸 Screenshots saved to:');
        console.log('   Before: /tmp/pattern_before.png');
        console.log('   After:  /tmp/pattern_after.png');

    } catch (error) {
        console.error('\n❌ Test failed:', error.message);
        await page.screenshot({ path: '/tmp/pattern_error.png' });
        console.log('📸 Error screenshot: /tmp/pattern_error.png');
    } finally {
        await browser.close();
    }
}

testPatternOverlay()
    .then(() => {
        console.log('\n✅ Test complete');
        process.exit(0);
    })
    .catch(err => {
        console.error('\n❌ Test failed:', err);
        process.exit(1);
    });
