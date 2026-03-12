#!/usr/bin/env node
/**
 * Use Puppeteer to check chart page rendering
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function checkPage(url, outputDir) {
    console.log(`🔍 Checking page: ${url}`);

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Collect console messages
    const consoleMessages = [];
    page.on('console', msg => {
        const type = msg.type();
        const text = msg.text();
        consoleMessages.push({ type, text });
        console.log(`[Console ${type}] ${text}`);
    });

    // Collect errors
    const errors = [];
    page.on('pageerror', error => {
        errors.push(error.toString());
        console.log(`❌ [Page Error] ${error}`);
    });

    // Collect network failures
    page.on('requestfailed', request => {
        errors.push(`Network failure: ${request.url()}`);
        console.log(`❌ [Network] Failed to load: ${request.url()}`);
    });

    try {
        // Navigate to page
        console.log('\n📄 Loading page...');
        await page.goto(url, {
            waitUntil: 'networkidle2',
            timeout: 10000
        });

        // Wait a bit for charts to render
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Take screenshot
        const screenshotPath = path.join(outputDir, 'page_screenshot.png');
        await page.screenshot({
            path: screenshotPath,
            fullPage: true
        });
        console.log(`\n📸 Screenshot saved: ${screenshotPath}`);

        // Check for canvas elements
        const canvasCount = await page.evaluate(() => {
            return document.querySelectorAll('canvas').length;
        });
        console.log(`\n🎨 Found ${canvasCount} canvas element(s)`);

        // Check if chart is rendered
        const chartRendered = await page.evaluate(() => {
            const canvas = document.querySelector('#myChart');
            if (!canvas) return { exists: false };

            const ctx = canvas.getContext('2d');
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const hasPixels = imageData.data.some(pixel => pixel !== 0);

            return {
                exists: true,
                width: canvas.width,
                height: canvas.height,
                hasPixels
            };
        });
        console.log(`\n📊 Chart rendering:`, chartRendered);

        // Get page title
        const title = await page.title();
        console.log(`\n📋 Page title: ${title}`);

        // Check for specific elements
        const elements = await page.evaluate(() => {
            return {
                ticker_input: !!document.getElementById('ticker'),
                period_select: !!document.getElementById('period'),
                load_button: !!document.querySelector('button'),
                chart_canvas: !!document.getElementById('myChart'),
                pattern_list: !!document.getElementById('pattern-list')
            };
        });
        console.log(`\n🔍 Elements found:`, elements);

        // Generate report
        const report = {
            url,
            timestamp: new Date().toISOString(),
            title,
            canvasCount,
            chartRendered,
            elements,
            consoleMessages,
            errors,
            screenshotPath
        };

        const reportPath = path.join(outputDir, 'page_report.json');
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        console.log(`\n📄 Report saved: ${reportPath}`);

        // Summary
        console.log('\n' + '='.repeat(60));
        console.log('SUMMARY');
        console.log('='.repeat(60));
        console.log(`✅ Canvas elements: ${canvasCount}`);
        console.log(`${chartRendered.exists ? '✅' : '❌'} Chart canvas exists`);
        console.log(`${chartRendered.hasPixels ? '✅' : '⚠️'} Chart has pixels rendered`);
        console.log(`${errors.length === 0 ? '✅' : '❌'} Errors: ${errors.length}`);
        console.log(`📝 Console messages: ${consoleMessages.length}`);

        if (errors.length > 0) {
            console.log('\n❌ ERRORS FOUND:');
            errors.forEach((err, i) => console.log(`  ${i + 1}. ${err}`));
        }

        return report;

    } catch (error) {
        console.error(`\n❌ Fatal error: ${error.message}`);
        throw error;
    } finally {
        await browser.close();
    }
}

// Main
const url = process.argv[2] || 'http://localhost:8001/test_chart.html';
const outputDir = process.argv[3] || '/tmp';

checkPage(url, outputDir)
    .then(() => {
        console.log('\n✅ Check complete');
        process.exit(0);
    })
    .catch(err => {
        console.error('\n❌ Check failed:', err);
        process.exit(1);
    });
