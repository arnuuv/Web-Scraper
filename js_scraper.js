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

    /**
     * Download and save all images on the current page to a local directory.
     * @param {string} dir - Directory to save images (default: './images')
     */
    async saveAllImages(dir = './images') {
        await fs.promises.mkdir(dir, { recursive: true });
        const imageUrls = await this.page.evaluate(() =>
            Array.from(document.images).map(img => img.src)
        );
        for (const url of imageUrls) {
            try {
                const view = await this.page.goto(url);
                const fileName = path.join(dir, path.basename(new URL(url).pathname));
                await fs.promises.writeFile(fileName, await view.buffer());
                console.log(`Saved: ${fileName}`);
            } catch (err) {
                console.error(`Failed to save image ${url}:`, err.message);
            }
        }
    }

    /**
     * Wait for a network request matching a URL substring or regex and return its response body.
     * @param {string|RegExp} urlMatch - Substring or regex to match request URL.
     * @param {number} timeout - Timeout in ms (default 10000).
     * @returns {Promise<string|undefined>} - The response body as text, or undefined if not found.
     */
    async waitForNetworkResponse(urlMatch, timeout = 10000) {
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.page.removeListener('response', onResponse);
                resolve(undefined);
            }, timeout);

            const onResponse = async (response) => {
                const url = response.url();
                const match = typeof urlMatch === 'string'
                    ? url.includes(urlMatch)
                    : urlMatch.test(url);
                if (match) {
                    clearTimeout(timer);
                    this.page.removeListener('response', onResponse);
                    try {
                        resolve(await response.text());
                    } catch (err) {
                        resolve(undefined);
                    }
                }
            };

            this.page.on('response', onResponse);
        });
    }

    async scrape_dynamic_content(url, selectors, wait_for, timeout, headless, export_format) {
        // Implementation of scrape_dynamic_content method
    }

    async execute_js(url, js_code, wait_for) {
        // Implementation of execute_js method
    }

    /**
     * Fill and submit a form with validation and error handling
     * @param {Object} options
     * @param {string} options.formSelector - CSS selector for the form
     * @param {Object} options.fields - Object mapping field selectors to values
     * @param {boolean} options.submit - Whether to submit the form after filling
     * @param {number} options.timeout - Timeout for form operations
     * @param {Function} options.validate - Custom validation function
     * @returns {Promise<{success: boolean, errors: Array}>}
     */
    async handleForm(options = {}) {
        const {
            formSelector,
            fields = {},
            submit = true,
            timeout = 5000,
            validate = null
        } = options;

        const errors = [];
        try {
            // Wait for form to be present
            await this.page.waitForSelector(formSelector, { timeout });

            // Fill each field
            for (const [selector, value] of Object.entries(fields)) {
                try {
                    const element = await this.page.$(selector);
                    if (!element) {
                        errors.push(`Field not found: ${selector}`);
                        continue;
                    }

                    // Handle different input types
                    const type = await element.evaluate(el => el.type);
                    const tagName = await element.evaluate(el => el.tagName.toLowerCase());

                    if (tagName === 'select') {
                        await this.page.select(selector, value);
                    } else if (type === 'checkbox' || type === 'radio') {
                        if (value) {
                            await element.click();
                        }
                    } else if (type === 'file') {
                        await element.uploadFile(value);
                    } else {
                        await element.type(value, { delay: 100 });
                    }
                } catch (error) {
                    errors.push(`Error filling ${selector}: ${error.message}`);
                }
            }

            // Run custom validation if provided
            if (validate) {
                const validationResult = await this.page.evaluate(validate);
                if (!validationResult.valid) {
                    errors.push(...validationResult.errors);
                }
            }

            // Submit form if requested and no errors
            if (submit && errors.length === 0) {
                const form = await this.page.$(formSelector);
                await form.evaluate(form => form.submit());
                await this.page.waitForNavigation({ timeout });
            }

            return {
                success: errors.length === 0,
                errors
            };
        } catch (error) {
            errors.push(`Form handling error: ${error.message}`);
            return { success: false, errors };
        }
    }

    /**
     * Handle dynamic form fields that appear based on user input
     * @param {Object} options
     * @param {string} options.triggerSelector - Selector for element that triggers dynamic fields
     * @param {string} options.fieldSelector - Selector for dynamic fields
     * @param {number} options.timeout - Timeout for waiting for fields
     * @returns {Promise<Array>} - Array of dynamic field elements
     */
    async handleDynamicFormFields(options = {}) {
        const {
            triggerSelector,
            fieldSelector,
            timeout = 5000
        } = options;

        try {
            // Click trigger element
            await this.page.click(triggerSelector);

            // Wait for dynamic fields to appear
            await this.page.waitForSelector(fieldSelector, { timeout });

            // Get all dynamic fields
            const fields = await this.page.$$(fieldSelector);
            return fields;
        } catch (error) {
            console.error('Error handling dynamic form fields:', error);
            return [];
        }
    }

    /**
     * Handle form validation and error messages
     * @param {Object} options
     * @param {string} options.formSelector - Form selector
     * @param {string} options.errorSelector - Selector for error messages
     * @returns {Promise<{valid: boolean, errors: Array}>}
     */
    async validateForm(options = {}) {
        const {
            formSelector,
            errorSelector = '.error-message, .invalid-feedback'
        } = options;

        try {
            // Trigger form validation
            await this.page.evaluate(selector => {
                const form = document.querySelector(selector);
                if (form) form.reportValidity();
            }, formSelector);

            // Wait for potential error messages
            await this.page.waitForTimeout(500);

            // Get all error messages
            const errors = await this.page.evaluate(selector => {
                const errorElements = document.querySelectorAll(selector);
                return Array.from(errorElements).map(el => el.textContent.trim());
            }, errorSelector);

            return {
                valid: errors.length === 0,
                errors
            };
        } catch (error) {
            console.error('Form validation error:', error);
            return { valid: false, errors: [error.message] };
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
        
        // Advanced auto-scroll
        const result = await scraper.advancedAutoScroll({
            maxScrolls: 30,
            delay: 1200,
            maxRetries: 7,
            untilSelector: '.end-of-content',
            untilCallback: null
        });
        console.log('Auto-scroll result:', result);
        
        // Example form handling
        const formResult = await scraper.handleForm({
            formSelector: '#login-form',
            fields: {
                '#username': 'testuser',
                '#password': 'testpass',
                '#remember-me': true
            },
            submit: true,
            validate: () => {
                const username = document.querySelector('#username').value;
                const password = document.querySelector('#password').value;
                const errors = [];
                
                if (username.length < 3) {
                    errors.push('Username must be at least 3 characters');
                }
                if (password.length < 6) {
                    errors.push('Password must be at least 6 characters');
                }
                
                return {
                    valid: errors.length === 0,
                    errors
                };
            }
        });

        console.log('Form submission result:', formResult);

        // Handle dynamic form fields
        const dynamicFields = await scraper.handleDynamicFormFields({
            triggerSelector: '#add-field',
            fieldSelector: '.dynamic-input'
        });

        // Validate form
        const validationResult = await scraper.validateForm({
            formSelector: '#login-form',
            errorSelector: '.error-message'
        });

        console.log('Form validation result:', validationResult);

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