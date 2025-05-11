# Advanced Web Scraper

A powerful web scraping solution that combines JavaScript (Puppeteer) and Python capabilities for handling both static and dynamic web content.

## Features

### JavaScript Scraper (Puppeteer)

- Full browser automation
- Dynamic content handling
- **Advanced auto-scroll with error correction**
- Resource optimization
- Network request monitoring
- Screenshot capture (full page and element)
- Infinite scroll support
- Custom JavaScript execution
- File download support
- Cookie management (get/set/delete)
- Device emulation and geolocation
- Save page as PDF
- **150+ DOM and scraping utility functions** (see `webscraper_features.js`)
- Python integration

### Python Scraper

- Rate limiting
- Proxy support
- Advanced error handling
- Multiple export formats (JSON, CSV, Excel)
- Async scraping capabilities
- Interactive element handling
- Form submission support
- **Example main.py for quick start**

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/web-scraper.git
cd web-scraper
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies:

```bash
npm install
```

## Usage

### Python Scraper Example (from main.py)

```python
from main import WebScraper

scraper = WebScraper()
url = "https://example.com"
selectors = {
    "headings": "h1, h2, h3",
    "paragraphs": "p",
    "links": "a"
}
results = scraper.scrape_website(url, selectors)
print(results)
```

### JavaScript Scraper Example

```javascript
const JSScraper = require("./js_scraper.js");

async function runScraper() {
  const scraper = new JSScraper({
    headless: true,
    slowMo: 50,
  });

  try {
    await scraper.initialize();
    await scraper.navigate("https://example.com");

    // Extract data
    const data = await scraper.extractData({
      headings: "h1, h2, h3",
      paragraphs: "p",
      links: "a",
    });

    // Advanced auto-scroll with error correction
    const scrollResult = await scraper.advancedAutoScroll({
      maxScrolls: 20,
      delay: 1000,
      maxRetries: 5,
      untilSelector: ".end-of-content",
    });
    console.log("Auto-scroll result:", scrollResult);

    // Download a file
    await scraper.downloadFile("a.download-link");

    // Cookie management
    const cookies = await scraper.getCookies();
    await scraper.setCookie({ name: "test", value: "123" });
    await scraper.deleteCookie("test");

    // Screenshot of a specific element
    await scraper.captureElementScreenshot(".main-content");

    // Device emulation
    await scraper.emulateDevice("iPhone X");

    // Set geolocation
    await scraper.setGeolocation(37.7749, -122.4194);

    // Save page as PDF
    await scraper.saveAsPDF({ path: "page.pdf" });

    // Use utility functions from webscraper_features.js in browser context
    // Example: await scraper.page.evaluate(getAllLinks);

    // Take a full page screenshot
    await scraper.captureScreenshot({ fullPage: true });

    console.log(data);
  } finally {
    await scraper.close();
  }
}
```

### Utility Functions

See `webscraper_features.js` for **150+ ready-to-use DOM and scraping helpers**, such as:

- `getAllLinks()`
- `getAllImages()`
- `getTextBySelector(selector)`
- `waitForElement(selector, timeout)`
- `scrollToBottom()`
- ...and many more!

You can use these in Puppeteer like:

```javascript
const links = await scraper.page.evaluate(getAllLinks);
```

### Integration

You can export data from JS to Python and vice versa. See the `exportToPython` method in `js_scraper.js`.

## Features in Detail

### JavaScript Scraper Features

1. **Browser Automation**
   - Headless mode support
   - Custom viewport settings
   - User agent rotation
   - Resource blocking
2. **Data Extraction**
   - CSS selector-based extraction
   - Custom JavaScript execution
   - Dynamic content handling
   - Structured data output
3. **Performance**
   - Resource optimization
   - Request interception
   - Network monitoring
   - Error handling
4. **Advanced Features**
   - Auto-scroll with error correction
   - File download
   - Cookie management
   - Device emulation
   - Geolocation
   - Save as PDF
   - Element screenshot
   - 150+ DOM helpers

### Python Scraper Features

1. **Advanced Scraping**
   - Rate limiting
   - Proxy support
   - Retry mechanism
   - Async capabilities
2. **Data Export**
   - JSON export
   - CSV export
   - Excel export
   - Custom formatting
3. **Interactive Features**
   - Form handling
   - Popup management
   - Dynamic table extraction
   - Infinite scroll support

## Configuration

### JavaScript Configuration

```javascript
const options = {
  headless: true,
  slowMo: 50,
  timeout: 30000,
  viewport: { width: 1920, height: 1080 },
};
```

### Python Configuration

```python
options = {
    rate_limit: 2.0,
    max_retries: 3,
    proxy_list: ["http://proxy1:8080"],
    timeout: 30
}
```

## Error Handling

Both scrapers include comprehensive error handling:

- Network errors
- Timeout handling
- Resource loading errors
- Element not found errors
- Browser automation errors

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Puppeteer for browser automation
- BeautifulSoup for HTML parsing
- Selenium for Python browser automation
