/**
 * Check /tiles endpoint using Puppeteer
 * Tests if the page shows "no data available"
 */
const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        console.log('🌐 Navigating to http://127.0.0.1:5000/tiles...');
        await page.goto('http://127.0.0.1:5000/tiles', {
            waitUntil: 'networkidle2',
            timeout: 10000
        });
        
        // Wait a bit for any dynamic content to load
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Get page content
        const content = await page.content();
        
        // Check for "no data available" text
        const bodyText = await page.evaluate(() => document.body.innerText);
        
        console.log('\n📄 Page Title:', await page.title());
        console.log('\n📝 Page Content (first 500 chars):');
        console.log(bodyText.substring(0, 500));
        
        // Check for specific error messages
        const hasNoData = bodyText.toLowerCase().includes('no data available') || 
                         bodyText.toLowerCase().includes('no data') ||
                         bodyText.toLowerCase().includes('empty-state');
        
        const hasError = bodyText.toLowerCase().includes('error') ||
                        bodyText.toLowerCase().includes('exception') ||
                        bodyText.toLowerCase().includes('traceback');
        
        console.log('\n🔍 Analysis:');
        console.log('  - Contains "no data available":', hasNoData);
        console.log('  - Contains error messages:', hasError);
        
        // Check for Bokeh content
        const bokehScripts = await page.evaluate(() => {
            const scripts = Array.from(document.querySelectorAll('script'));
            return scripts.some(s => s.innerHTML.includes('Bokeh') || s.src.includes('bokeh'));
        });
        
        console.log('  - Contains Bokeh scripts:', bokehScripts);
        
        // Take a screenshot
        await page.screenshot({ path: 'tiles_page_screenshot.png', fullPage: true });
        console.log('\n📸 Screenshot saved to tiles_page_screenshot.png');
        
        // Check console errors
        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });
        
        await page.reload({ waitUntil: 'networkidle2' });
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        if (errors.length > 0) {
            console.log('\n❌ Console Errors:');
            errors.forEach(err => console.log('   ', err));
        }
        
    } catch (error) {
        console.error('\n❌ Error:', error.message);
    } finally {
        await browser.close();
    }
})();
