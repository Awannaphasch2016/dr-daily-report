const puppeteer = require('puppeteer');

async function checkTilesPage() {
    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    // Set viewport
    await page.setViewport({ width: 1280, height: 720 });
    
    // Listen to console messages
    page.on('console', msg => {
        console.log('Browser console:', msg.text());
    });
    
    // Listen to network requests
    page.on('response', response => {
        if (response.url().includes('/api/tiles-data')) {
            console.log('API Response status:', response.status());
            response.json().then(data => {
                console.log('API Response data:', JSON.stringify(data, null, 2));
            }).catch(err => {
                console.log('Error parsing API response:', err);
            });
        }
    });
    
    try {
        console.log('Navigating to http://127.0.0.1:5000/tiles...');
        await page.goto('http://127.0.0.1:5000/tiles', {
            waitUntil: 'networkidle2',
            timeout: 10000
        });
        
        // Wait a bit for JavaScript to execute
        await page.waitForTimeout(3000);
        
        // Check what's in the tiles-container
        const tilesContainerContent = await page.evaluate(() => {
            const container = document.getElementById('tiles-container');
            return {
                innerHTML: container ? container.innerHTML : 'NOT FOUND',
                textContent: container ? container.textContent : 'NOT FOUND',
                children: container ? container.children.length : 0
            };
        });
        
        console.log('\n=== Tiles Container Content ===');
        console.log(JSON.stringify(tilesContainerContent, null, 2));
        
        // Check for errors
        const errors = await page.evaluate(() => {
            return window.errors || [];
        });
        
        if (errors.length > 0) {
            console.log('\n=== Errors ===');
            console.log(errors);
        }
        
        // Check API response
        const apiResponse = await page.evaluate(async () => {
            try {
                const response = await fetch('/api/tiles-data');
                const data = await response.json();
                return {
                    status: response.status,
                    dataLength: data.length,
                    sampleData: data.slice(0, 2)
                };
            } catch (err) {
                return { error: err.message };
            }
        });
        
        console.log('\n=== API Response Check ===');
        console.log(JSON.stringify(apiResponse, null, 2));
        
        // Take a screenshot
        await page.screenshot({ path: 'tiles-debug.png', fullPage: true });
        console.log('\nScreenshot saved to tiles-debug.png');
        
        // Wait before closing
        await page.waitForTimeout(2000);
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
}

checkTilesPage().catch(console.error);
