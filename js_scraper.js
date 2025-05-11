const puppeteer = require('puppeteer');
const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');

class JSScraper {
    constructor(options = {}) {
        this.options = {
            headless: options.headless ?? true,
            slowMo: options.slowMo ?? 50,
            timeout: options.timeout ?? 30000,
            viewport: options.viewport ?? { width: 1920, height: 1080 },
            userAgent: options.userAgent ?? 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        };
        this.browser = null;
        this.page = null;
    }

    async initialize() {
        this.browser = await puppeteer.launch({
            headless: this.options.headless,
            slowMo: this.options.slowMo,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu'
            ]
        });
        this.page = await this.browser.newPage();
        await this.page.setViewport(this.options.viewport);
        await this.page.setUserAgent(this.options.userAgent);
        
        // Enable request interception
        await this.page.setRequestInterception(true);
        this.page.on('request', (request) => {
            if (['image', 'stylesheet', 'font'].includes(request.resourceType())) {
                request.abort();
            } else {
                request.continue();
            }
        });
    }

    async navigate(url) {
        try {
            await this.page.goto(url, { waitUntil: 'networkidle0', timeout: this.options.timeout });
            return true;
        } catch (error) {
            console.error(`Navigation error: ${error.message}`);
            return false;
        }
    }

    async waitForSelector(selector, timeout = this.options.timeout) {
        try {
            await this.page.waitForSelector(selector, { timeout });
            return true;
        } catch (error) {
            console.error(`Selector not found: ${selector}`);
            return false;
        }
    }

    async extractData(selectors) {
        const data = {};
        for (const [key, selector] of Object.entries(selectors)) {
            try {
                const elements = await this.page.$$(selector);
                data[key] = await Promise.all(
                    elements.map(el => el.evaluate(node => node.textContent.trim()))
                );
            } catch (error) {
                console.error(`Error extracting ${key}: ${error.message}`);
                data[key] = [];
            }
        }
        return data;
    }

    async executeCustomJS(script) {
        try {
            return await this.page.evaluate(script);
        } catch (error) {
            console.error(`JS execution error: ${error.message}`);
            return null;
        }
    }

    async handleInfiniteScroll(options = {}) {
        const {
            maxScrolls = 10,
            delay = 1000,
            loadMoreSelector = null
        } = options;

        let previousHeight = 0;
        let scrollCount = 0;

        while (scrollCount < maxScrolls) {
            previousHeight = await this.page.evaluate('document.body.scrollHeight');
            await this.page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
            await this.page.waitForTimeout(delay);

            if (loadMoreSelector) {
                try {
                    const loadMoreButton = await this.page.$(loadMoreSelector);
                    if (loadMoreButton) {
                        await loadMoreButton.click();
                        await this.page.waitForTimeout(delay);
                    }
                } catch (error) {
                    console.log('No load more button found');
                }
            }

            const newHeight = await this.page.evaluate('document.body.scrollHeight');
            if (newHeight === previousHeight) break;
            scrollCount++;
        }
    }

    async captureScreenshot(options = {}) {
        const {
            fullPage = true,
            path = `screenshot_${Date.now()}.png`
        } = options;

        try {
            await this.page.screenshot({ path, fullPage });
            return path;
        } catch (error) {
            console.error(`Screenshot error: ${error.message}`);
            return null;
        }
    }

    async monitorNetworkRequests() {
        const requests = [];
        this.page.on('request', request => {
            requests.push({
                url: request.url(),
                method: request.method(),
                resourceType: request.resourceType()
            });
        });
        return requests;
    }

    async exportToPython(data, format = 'json') {
        const pythonScript = `
import json
import sys

data = ${JSON.stringify(data)}
print(json.dumps(data))
        `;

        const pythonProcess = spawn('python', ['-c', pythonScript]);
        let output = '';

        return new Promise((resolve, reject) => {
            pythonProcess.stdout.on('data', (data) => {
                output += data.toString();
            });

            pythonProcess.stderr.on('data', (data) => {
                console.error(`Python Error: ${data}`);
            });

            pythonProcess.on('close', (code) => {
                if (code === 0) {
                    resolve(JSON.parse(output));
                } else {
                    reject(new Error(`Python process exited with code ${code}`));
                }
            });
        });
    }

    async close() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    // Download a file from a link selector
    async downloadFile(linkSelector, downloadPath = './downloads') {
        const fs = require('fs');
        const path = require('path');
        await fs.promises.mkdir(downloadPath, { recursive: true });
        const client = await this.page.target().createCDPSession();
        await client.send('Page.setDownloadBehavior', {
            behavior: 'allow',
            downloadPath: path.resolve(downloadPath)
        });
        await this.page.click(linkSelector);
        // Wait for download to finish (simple version)
        await this.page.waitForTimeout(5000);
    }

    // Cookie management
    async getCookies() {
        return await this.page.cookies();
    }
    async setCookie(cookie) {
        await this.page.setCookie(cookie);
    }
    async deleteCookie(cookieName) {
        await this.page.deleteCookie({ name: cookieName });
    }

    // Screenshot of a specific element
    async captureElementScreenshot(selector, options = {}) {
        try {
            const element = await this.page.$(selector);
            if (!element) throw new Error('Element not found');
            const filePath = options.path || `element_${Date.now()}.png`;
            await element.screenshot({ path: filePath });
            return filePath;
        } catch (error) {
            console.error(`Element screenshot error: ${error.message}`);
            return null;
        }
    }

    // Emulate a device (mobile/tablet)
    async emulateDevice(deviceName = 'iPhone X') {
        const puppeteer = require('puppeteer');
        const devices = puppeteer.KnownDevices || puppeteer.devices;
        const device = devices[deviceName];
        if (!device) throw new Error('Device not found');
        await this.page.emulate(device);
    }

    // Set geolocation
    async setGeolocation(latitude, longitude) {
        await this.page.setGeolocation({ latitude, longitude });
    }

    // Save page as PDF
    async saveAsPDF(options = {}) {
        const filePath = options.path || `page_${Date.now()}.pdf`;
        await this.page.pdf({ path: filePath, format: 'A4', ...options });
        return filePath;
    }

    /**
     * Advanced auto-scroll with error correction, DOM change detection, and custom end conditions.
     * @param {Object} options
     * @param {number} options.maxScrolls - Maximum number of scrolls.
     * @param {number} options.delay - Delay between scrolls (ms).
     * @param {number} options.maxRetries - Max retries on error or no new content.
     * @param {string} [options.untilSelector] - Stop if this selector appears.
     * @param {function} [options.untilCallback] - Stop if this callback returns true (runs in browser context).
     * @returns {Promise<{scrolls: number, retries: number, stoppedBy: string}>}
     */
    async advancedAutoScroll(options = {}) {
        const {
            maxScrolls = 20,
            delay = 1000,
            maxRetries = 5,
            untilSelector = null,
            untilCallback = null
        } = options;

        let scrollCount = 0;
        let retries = 0;
        let lastHeight = await this.page.evaluate('document.body.scrollHeight');
        let lastNodeCount = await this.page.evaluate('document.body.getElementsByTagName(\"*\").length');
        let stoppedBy = 'maxScrolls';

        while (scrollCount < maxScrolls) {
            try {
                // Check for end conditions
                if (untilSelector) {
                    const found = await this.page.$(untilSelector);
                    if (found) {
                        stoppedBy = 'untilSelector';
                        break;
                    }
                }
                if (untilCallback) {
                    const shouldStop = await this.page.evaluate(untilCallback);
                    if (shouldStop) {
                        stoppedBy = 'untilCallback';
                        break;
                    }
                }

                await this.page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
                await this.page.waitForTimeout(delay);

                const newHeight = await this.page.evaluate('document.body.scrollHeight');
                const newNodeCount = await this.page.evaluate('document.body.getElementsByTagName(\"*\").length');

                if (newHeight === lastHeight && newNodeCount === lastNodeCount) {
                    retries++;
                    if (retries >= maxRetries) {
                        stoppedBy = 'maxRetries';
                        break;
                    }
                    await this.page.waitForTimeout(delay * 2);
                } else {
                    lastHeight = newHeight;
                    lastNodeCount = newNodeCount;
                    scrollCount++;
                    retries = 0; // Reset retries on success
                }
            } catch (error) {
                console.error(`Advanced auto-scroll error (attempt ${retries + 1}):`, error);
                retries++;
                if (retries >= maxRetries) {
                    stoppedBy = 'error';
                    break;
                }
                await this.page.waitForTimeout(delay * 2);
            }
        }
        return { scrolls: scrollCount, retries, stoppedBy };
    }
}

// Example usage
async function main() {
    const scraper = new JSScraper({
        headless: true,
        slowMo: 50
    });

    try {
        await scraper.initialize();
        
        // Navigate to a website
        await scraper.navigate('https://example.com');
        
        // Wait for content to load
        await scraper.waitForSelector('.main-content');
        
        // Extract data
        const data = await scraper.extractData({
            headings: 'h1, h2, h3',
            paragraphs: 'p',
            links: 'a'
        });
        
        // Handle infinite scroll
        await scraper.handleInfiniteScroll({
            maxScrolls: 5,
            delay: 1000,
            loadMoreSelector: '.load-more'
        });
        
        // Take a screenshot
        await scraper.captureScreenshot({
            fullPage: true,
            path: 'full_page.png'
        });
        
        // Execute custom JavaScript
        const customData = await scraper.executeCustomJS(`
            return {
                title: document.title,
                url: window.location.href,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            };
        `);
        
        // Export data to Python
        const pythonData = await scraper.exportToPython({
            ...data,
            customData
        });
        
        console.log('Scraping completed successfully');
        console.log(pythonData);
        
        // Advanced auto-scroll
        const result = await scraper.advancedAutoScroll({
            maxScrolls: 30,
            delay: 1200,
            maxRetries: 7,
            untilSelector: '.end-of-content',
            untilCallback: null
        });
        console.log('Auto-scroll result:', result);
        
    } catch (error) {
        console.error('Scraping failed:', error);
    } finally {
        await scraper.close();
    }
}

// Run the example
if (require.main === module) {
    main().catch(console.error);
}

module.exports = JSScraper; 

async function autoScrollWithRetry(page, maxScrolls = 10, delay = 1000, maxRetries = 3) {
    let scrollCount = 0;
    let retries = 0;
    let lastHeight = await page.evaluate('document.body.scrollHeight');

    while (scrollCount < maxScrolls) {
        try {
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
            await page.waitForTimeout(delay);

            const newHeight = await page.evaluate('document.body.scrollHeight');
            if (newHeight === lastHeight) {
                break;
            }
            lastHeight = newHeight;
            scrollCount++;
            retries = 0; // Reset retries on success
        } catch (error) {
            console.error(`Auto-scroll error (attempt ${retries + 1}):`, error);
            retries++;
            if (retries >= maxRetries) {
                console.error('Max auto-scroll retries reached. Stopping.');
                break;
            }
            await page.waitForTimeout(delay * 2); // Wait longer before retrying
        }
    }
} 