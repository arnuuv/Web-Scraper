import requests
from bs4 import BeautifulSoup
import time
import random
import json
import csv
import pandas as pd
from typing import Dict, List, Optional, Union, Any
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
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
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

class InteractiveScraper(JavaScriptScraper):
    def __init__(
        self,
        rate_limit: float = 1.0,
        max_retries: int = 3,
        proxy_list: Optional[List[str]] = None,
        timeout: int = 30,
        headless: bool = True,
        wait_time: int = 10
    ):
        """Initialize the interactive web scraper."""
        super().__init__(rate_limit, max_retries, proxy_list, timeout, headless, wait_time)
        self.actions = ActionChains(self.driver)

    def wait_and_click(self, selector: str, timeout: Optional[int] = None) -> bool:
        """
        Wait for an element to be clickable and click it.
        
        Args:
            selector (str): CSS selector of the element
            timeout (int): Optional custom timeout
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            timeout = timeout or self.wait_time
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            return True
        except (TimeoutException, ElementClickInterceptedException) as e:
            logging.error(f"Error clicking element {selector}: {str(e)}")
            return False

    def fill_form(
        self,
        form_data: Dict[str, str],
        submit_selector: Optional[str] = None
    ) -> bool:
        """
        Fill out a form with the provided data.
        
        Args:
            form_data (Dict[str, str]): Dictionary of field selectors and values
            submit_selector (str): Optional selector for the submit button
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for selector, value in form_data.items():
                element = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                element.clear()
                element.send_keys(value)
                time.sleep(0.5)  # Small delay between fields
            
            if submit_selector:
                return self.wait_and_click(submit_selector)
            return True
            
        except (TimeoutException, WebDriverException) as e:
            logging.error(f"Error filling form: {str(e)}")
            return False

    def scroll_to_element(self, selector: str) -> bool:
        """
        Scroll to a specific element on the page.
        
        Args:
            selector (str): CSS selector of the element
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            element = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)  # Wait for scroll to complete
            return True
        except (TimeoutException, WebDriverException) as e:
            logging.error(f"Error scrolling to element {selector}: {str(e)}")
            return False

    def infinite_scroll(
        self,
        max_scrolls: int = 10,
        scroll_pause_time: float = 2.0,
        load_more_selector: Optional[str] = None
    ) -> bool:
        """
        Perform infinite scroll on a page.
        
        Args:
            max_scrolls (int): Maximum number of scrolls to perform
            scroll_pause_time (float): Time to wait between scrolls
            load_more_selector (str): Optional selector for "Load More" button
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            
            while scroll_count < max_scrolls:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                
                # Click "Load More" if selector provided
                if load_more_selector:
                    try:
                        load_more = self.driver.find_element(By.CSS_SELECTOR, load_more_selector)
                        if load_more.is_displayed():
                            load_more.click()
                            time.sleep(scroll_pause_time)
                    except WebDriverException:
                        pass
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # Break if no more content
                if new_height == last_height:
                    break
                    
                last_height = new_height
                scroll_count += 1
            
            return True
            
        except WebDriverException as e:
            logging.error(f"Error during infinite scroll: {str(e)}")
            return False

    def handle_popup(self, popup_selector: str, close_selector: str) -> bool:
        """
        Handle popup windows or modals.
        
        Args:
            popup_selector (str): Selector for the popup element
            close_selector (str): Selector for the close button
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Wait for popup
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, popup_selector))
            )
            
            # Click close button
            return self.wait_and_click(close_selector)
            
        except (TimeoutException, WebDriverException) as e:
            logging.error(f"Error handling popup: {str(e)}")
            return False

    def extract_dynamic_table(
        self,
        table_selector: str,
        wait_for_rows: bool = True
    ) -> Optional[List[Dict[str, str]]]:
        """
        Extract data from a dynamic table.
        
        Args:
            table_selector (str): CSS selector for the table
            wait_for_rows (bool): Whether to wait for rows to load
            
        Returns:
            List[Dict[str, str]]: List of dictionaries containing table data
        """
        try:
            if wait_for_rows:
                WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, f"{table_selector} tr"))
                )
            
            table = self.driver.find_element(By.CSS_SELECTOR, table_selector)
            headers = [th.text for th in table.find_elements(By.TAG_NAME, "th")]
            
            data = []
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                row_data = {}
                for header, cell in zip(headers, cells):
                    row_data[header] = cell.text
                data.append(row_data)
            
            return data
            
        except WebDriverException as e:
            logging.error(f"Error extracting table data: {str(e)}")
            return None

# Update example usage
if __name__ == "__main__":
    # Initialize the interactive scraper
    interactive_scraper = InteractiveScraper(
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
        # Example: Fill out a login form
        login_data = {
            "#username": "test_user",
            "#password": "test_pass"
        }
        
        # Navigate to login page
        interactive_scraper.driver.get("https://example.com/login")
        
        # Fill and submit form
        if interactive_scraper.fill_form(login_data, "#login-button"):
            # Wait for login to complete
            time.sleep(2)
            
            # Handle any popup
            interactive_scraper.handle_popup(".welcome-popup", ".close-button")
            
            # Scroll to content
            interactive_scraper.scroll_to_element(".main-content")
            
            # Perform infinite scroll
            interactive_scraper.infinite_scroll(
                max_scrolls=5,
                scroll_pause_time=2.0,
                load_more_selector=".load-more-button"
            )
            
            # Extract table data
            table_data = interactive_scraper.extract_dynamic_table("#data-table")
            if table_data:
                print(json.dumps(table_data, indent=2))
        
    finally:
        # Always close the scraper
        interactive_scraper.close() 