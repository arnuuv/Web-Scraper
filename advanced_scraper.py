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

# Example usage
if __name__ == "__main__":
    # Initialize the scraper with custom settings
    scraper = AdvancedWebScraper(
        rate_limit=2.0,  # 2 seconds between requests
        max_retries=3,
        proxy_list=[
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080"
        ],
        timeout=30
    )
    
    # Example selectors
    selectors = {
        "headings": "h1, h2, h3",
        "paragraphs": "p",
        "links": "a"
    }
    
    # Scrape a single website
    results = scraper.scrape_website(
        "https://example.com",
        selectors=selectors,
        export_format="json"
    )
    
    # Scrape multiple websites asynchronously
    urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net"
    ]
    
    async def main():
        results = await scraper.scrape_multiple_websites(urls, selectors)
        print(json.dumps(results, indent=2))
    
    asyncio.run(main()) 