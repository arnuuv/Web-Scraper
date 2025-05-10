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