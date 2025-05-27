# Advanced Web Scraper

A powerful and feature-rich web scraper built with Python and Selenium, designed to handle complex web scraping tasks with robust error handling, form interactions, and data processing capabilities.

## Features

### Core Scraping Capabilities

- Dynamic content scraping using Selenium
- Support for JavaScript-rendered pages
- Rate limiting and retry mechanisms
- Multiple export formats (JSON, CSV, Excel)
- Pagination handling (infinite scroll, load more, page numbers)

### Form Handling

- Complex form submissions
- Dynamic form fields
- Field validation
- AJAX form handling
- File uploads
- CAPTCHA solving
- Form field dependencies
- Sensitive data handling
- Autofill and suggestions

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/web-scraper.git
cd web-scraper
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```
ANTHROPIC_API_KEY=your_api_key_here
CAPTCHA_API_KEY=your_captcha_service_key
ENCRYPTION_KEY=your_encryption_key
AUTOFILL_DATA_FILE=path/to/autofill_data.json
```

## Usage

### Basic Scraping

```python
from web_scraper import WebScraper

scraper = WebScraper()

# Simple website scraping
results = scraper.scrape_website(
    url="https://example.com",
    selectors={
        "headings": "h1, h2, h3",
        "paragraphs": "p",
        "links": "a"
    }
)
```

### Dynamic Content Scraping

```python
results = scraper.scrape_dynamic_content(
    url="https://example.com",
    selectors={
        "products": ".product-item",
        "prices": ".price",
        "descriptions": ".description"
    },
    wait_for=".product-list",
    timeout=10
)
```

### Form Submission

```python
result = scraper.handle_form_submission(
    url="https://example.com/login",
    form_selector="#login-form",
    form_data={
        "username": "testuser",
        "password": "securepass123"
    },
    submit_button_selector="#submit-button",
    wait_for=".dashboard"
)
```

### Advanced Form Features

#### File Upload

```python
form_data = {
    "profile_picture": {
        "path": "/path/to/image.jpg",
        "selector": "#profile-upload"
    }
}
```

#### CAPTCHA Handling

```python
captcha_config = {
    "type": "recaptcha",  # or "image" or "hcaptcha"
    "selector": ".g-recaptcha"
}
```

#### Form Validation

```python
validation_config = {
    "email": {
        "type": "email",
        "required": True
    },
    "password": {
        "type": "custom",
        "min_length": 8,
        "pattern": r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$"
    }
}
```

#### Field Dependencies

```python
field_dependencies = {
    "billing_address": {
        "conditions": [
            {
                "field": "payment_method",
                "operator": "equals",
                "value": "credit_card"
            }
        ],
        "action": {
            "type": "show"
        },
        "logic": "and"
    }
}
```

#### Sensitive Data Handling

```python
sensitive_fields = {
    "password": {
        "type": "password",
        "mask": True,
        "encrypt": True,
        "mask_type": "full"
    },
    "credit_card": {
        "type": "credit_card",
        "mask": True,
        "mask_type": "custom"
    }
}
```

#### Autofill and Suggestions

```python
autofill_config = {
    "email": {
        "type": "email",
        "use_saved": True,
        "save_new": True,
        "suggestions": ["user@example.com", "admin@example.com"]
    }
}
```

## Features in Detail

### 1. File Upload Support

- Handles multiple file types
- Validates file existence and permissions
- Supports custom file input selectors
- Integrates with form submission

### 2. CAPTCHA Handling

- Supports multiple CAPTCHA types:
  - Image-based CAPTCHAs
  - reCAPTCHA
  - hCaptcha
- Integrates with CAPTCHA solving services
- Handles both synchronous and asynchronous CAPTCHAs
- Provides detailed error reporting

### 3. Dynamic Form Fields

- Handles fields that appear based on user input
- Supports complex field dependencies
- Manages field visibility and state
- Handles dynamic validation rules

### 4. Form Validation

- Built-in validation rules:
  - Email
  - Phone
  - URL
  - Date
  - Number
  - Required fields
  - Custom patterns
- Field-level and form-level validation
- Detailed error reporting

### 5. AJAX Form Handling

- Supports AJAX form submissions
- Waits for AJAX responses
- Handles dynamic content updates
- Monitors jQuery and fetch requests

### 6. Field Dependencies

- Complex field relationships
- Multiple condition types:
  - Equals
  - Not equals
  - Contains
  - Greater than
  - Less than
  - Empty/not empty
  - Checked/not checked
- AND/OR logic for conditions

### 7. Sensitive Data Handling

- Data masking:
  - Full masking
  - Partial masking
  - Custom patterns
- Encryption using Fernet
- Secure storage
- Custom masking patterns for:
  - Credit cards
  - Social security numbers
  - Email addresses

### 8. Form Field Autofill

- Saves and loads form data
- Interactive suggestion dropdowns
- Custom autofill handlers
- Persistent storage
- Field type detection
- Smart value suggestions

## Error Handling

The scraper includes comprehensive error handling:

- Network errors
- Timeout handling
- Element not found errors
- Validation errors
- CAPTCHA errors
- Form submission errors
- File upload errors

## Best Practices

1. **Rate Limiting**

   - Always use appropriate rate limits
   - Respect website robots.txt
   - Implement exponential backoff

2. **Error Handling**

   - Always check return values
   - Implement proper logging
   - Handle edge cases

3. **Security**

   - Use environment variables for sensitive data
   - Encrypt sensitive information
   - Validate all inputs

4. **Performance**
   - Use headless mode when possible
   - Implement proper timeouts
   - Clean up resources

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
