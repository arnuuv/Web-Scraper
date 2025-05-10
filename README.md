# Advanced Web Scraper

A powerful web scraping solution that combines JavaScript (Puppeteer) and Python capabilities for handling both static and dynamic web content.

## Features

### JavaScript Scraper (Puppeteer)

- Full browser automation
- Dynamic content handling
- Resource optimization
- Network request monitoring
- Screenshot capture
- Infinite scroll support
- Custom JavaScript execution
- Python integration

### Python Scraper

- Rate limiting
- Proxy support
- Advanced error handling
- Multiple export formats (JSON, CSV, Excel)
- Async scraping capabilities
- Interactive element handling
- Form submission support

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

### JavaScript Scraper

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
    });

    // Handle infinite scroll
    await scraper.handleInfiniteScroll({
      maxScrolls: 5,
      delay: 1000,
    });

    // Take a screenshot
    await scraper.captureScreenshot({
      fullPage: true,
    });
  } finally {
    await scraper.close();
  }
}
```

### Python Scraper

```python
from advanced_scraper import AdvancedWebScraper, InteractiveScraper

# Basic scraping
scraper = AdvancedWebScraper(
    rate_limit=2.0,
    max_retries=3
)

# Interactive scraping
interactive_scraper = InteractiveScraper(
    headless=True,
    wait_time=10
)

# Scrape with form handling
form_data = {
    "#username": "user123",
    "#password": "pass123"
}
interactive_scraper.fill_form(form_data, "#submit-button")
```

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

## Integration

The scrapers can be used together:

```python
# Python code
import subprocess
import json

def run_js_scraper():
    result = subprocess.run(['node', 'js_scraper.js'],
                          capture_output=True,
                          text=True)
    return json.loads(result.stdout)
```

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
