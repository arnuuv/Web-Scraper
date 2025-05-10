import requests
from bs4 import BeautifulSoup
import time
import random
import json
import csv
import pandas as pd
from typing import Dict, List, Optional, Union
from datetime import datetime
import logging
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import aiohttp
import asyncio
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class AdvancedWebScraper:
    def __init__(
        self,
        rate_limit: float = 1.0,
        max_retries: int = 3,
        proxy_list: Optional[List[str]] = None,
        timeout: int = 30
    ):
        """
        Initialize the advanced web scraper with configurable options.
        
        Args:
            rate_limit (float): Minimum time between requests in seconds
            max_retries (int): Maximum number of retry attempts
            proxy_list (List[str]): List of proxy URLs
            timeout (int): Request timeout in seconds
        """
        self.rate_limit = rate_limit
        self.proxy_list = proxy_list or []
        self.timeout = timeout
        self.ua = UserAgent()
        self.last_request_time = 0
        
        # Configure retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get a random proxy from the proxy list."""
        if not self.proxy_list:
            return None
        proxy = random.choice(self.proxy_list)
        return {
            "http": proxy,
            "https": proxy
        }

    def _respect_rate_limit(self):
        """Ensure we respect the rate limit between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last_request)
        self.last_request_time = time.time()

    def scrape_website(
        self,
        url: str,
        selectors: Optional[Dict[str, str]] = None,
        export_format: str = "json"
    ) -> Union[Dict[str, List[str]], None]:
        """
        Scrape a website with advanced features.
        
        Args:
            url (str): The URL to scrape
            selectors (Dict[str, str]): Dictionary of name -> CSS selector pairs
            export_format (str): Format to export data (json, csv, excel)
            
        Returns:
            Dict[str, List[str]]: Dictionary of scraped data
        """
        try:
            self._respect_rate_limit()
            
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            proxies = self._get_random_proxy()
            
            response = self.session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = {}
            
            if selectors:
                for name, selector in selectors.items():
                    elements = soup.select(selector)
                    results[name] = [elem.get_text(strip=True) for elem in elements]
            else:
                results['content'] = [soup.get_text(strip=True)]
            
            # Export the results
            self._export_results(results, export_format)
            
            return results
            
        except requests.RequestException as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return None

    def _export_results(self, results: Dict[str, List[str]], format: str):
        """Export results to the specified format."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        
        if format == "json":
            filepath = export_dir / f"scrape_results_{timestamp}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        elif format == "csv":
            filepath = export_dir / f"scrape_results_{timestamp}.csv"
            df = pd.DataFrame.from_dict(results, orient='index').T
            df.to_csv(filepath, index=False)
        
        elif format == "excel":
            filepath = export_dir / f"scrape_results_{timestamp}.xlsx"
            df = pd.DataFrame.from_dict(results, orient='index').T
            df.to_excel(filepath, index=False)
        
        logging.info(f"Results exported to {filepath}")

    async def scrape_multiple_websites(
        self,
        urls: List[str],
        selectors: Optional[Dict[str, str]] = None
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Asynchronously scrape multiple websites.
        
        Args:
            urls (List[str]): List of URLs to scrape
            selectors (Dict[str, str]): Dictionary of name -> CSS selector pairs
            
        Returns:
            Dict[str, Dict[str, List[str]]]: Dictionary of results for each URL
        """
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                task = asyncio.create_task(self._async_scrape(session, url, selectors))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return dict(zip(urls, results))

    async def _async_scrape(
        self,
        session: aiohttp.ClientSession,
        url: str,
        selectors: Optional[Dict[str, str]] = None
    ) -> Dict[str, List[str]]:
        """Helper method for async scraping."""
        try:
            headers = {'User-Agent': self.ua.random}
            async with session.get(url, headers=headers) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                results = {}
                
                if selectors:
                    for name, selector in selectors.items():
                        elements = soup.select(selector)
                        results[name] = [elem.get_text(strip=True) for elem in elements]
                else:
                    results['content'] = [soup.get_text(strip=True)]
                
                return results
                
        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return {}

class JavaScriptScraper(AdvancedWebScraper):
    def __init__(
        self,
        rate_limit: float = 1.0,
        max_retries: int = 3,
        proxy_list: Optional[List[str]] = None,
        timeout: int = 30,
        headless: bool = True,
        wait_time: int = 10
    ):
        """
        Initialize the JavaScript-enabled web scraper.
        
        Args:
            rate_limit (float): Minimum time between requests in seconds
            max_retries (int): Maximum number of retry attempts
            proxy_list (List[str]): List of proxy URLs
            timeout (int): Request timeout in seconds
            headless (bool): Run browser in headless mode
            wait_time (int): Maximum time to wait for elements to load
        """
        super().__init__(rate_limit, max_retries, proxy_list, timeout)
        self.wait_time = wait_time
        self.driver = self._setup_driver(headless)

    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Set up and configure the Chrome WebDriver."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.ua.random}')
        
        if self.proxy_list:
            proxy = random.choice(self.proxy_list)
            chrome_options.add_argument(f'--proxy-server={proxy}')
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def scrape_dynamic_website(
        self,
        url: str,
        selectors: Optional[Dict[str, str]] = None,
        wait_for: Optional[str] = None,
        export_format: str = "json"
    ) -> Union[Dict[str, List[str]], None]:
        """
        Scrape a JavaScript-rendered website.
        
        Args:
            url (str): The URL to scrape
            selectors (Dict[str, str]): Dictionary of name -> CSS selector pairs
            wait_for (str): CSS selector to wait for before scraping
            export_format (str): Format to export data (json, csv, excel)
            
        Returns:
            Dict[str, List[str]]: Dictionary of scraped data
        """
        try:
            self._respect_rate_limit()
            self.driver.get(url)
            
            # Wait for specific element if provided
            if wait_for:
                try:
                    WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                    )
                except TimeoutException:
                    logging.warning(f"Timeout waiting for element: {wait_for}")
            
            # Additional wait for dynamic content
            time.sleep(2)
            
            # Get page source after JavaScript execution
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            results = {}
            
            if selectors:
                for name, selector in selectors.items():
                    elements = soup.select(selector)
                    results[name] = [elem.get_text(strip=True) for elem in elements]
            else:
                results['content'] = [soup.get_text(strip=True)]
            
            # Export the results
            self._export_results(results, export_format)
            
            return results
            
        except WebDriverException as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return None
        finally:
            # Don't close the driver here to allow for multiple requests
            pass

    def take_screenshot(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Take a screenshot of the webpage.
        
        Args:
            url (str): The URL to capture
            filename (str): Optional custom filename
            
        Returns:
            str: Path to the screenshot file
        """
        try:
            self.driver.get(url)
            time.sleep(2)  # Wait for page to load
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            screenshot_dir = Path("screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            
            filepath = screenshot_dir / filename
            self.driver.save_screenshot(str(filepath))
            logging.info(f"Screenshot saved to {filepath}")
            
            return str(filepath)
            
        except WebDriverException as e:
            logging.error(f"Error taking screenshot of {url}: {str(e)}")
            return None

    def close(self):
        """Close the WebDriver and clean up resources."""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def __del__(self):
        """Destructor to ensure WebDriver is closed."""
        self.close()

# Update example usage
if __name__ == "__main__":
    # Initialize the JavaScript scraper
    js_scraper = JavaScriptScraper(
        rate_limit=2.0,
        max_retries=3,
        proxy_list=[
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080"
        ],
        timeout=30,
        headless=True,
        wait_time=10
    )
    
    try:
        # Example selectors for a dynamic website
        selectors = {
            "headings": "h1, h2, h3",
            "paragraphs": "p",
            "links": "a"
        }
        
        # Scrape a JavaScript-rendered website
        results = js_scraper.scrape_dynamic_website(
            "https://example.com",
            selectors=selectors,
            wait_for=".main-content",  # Wait for this element to load
            export_format="json"
        )
        
        # Take a screenshot
        js_scraper.take_screenshot("https://example.com")
        
    finally:
        # Always close the scraper
        js_scraper.close() 