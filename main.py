from mcp import Server, ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.prebuilt import create_react_agent
from langchain.agents import AgentExecutor
from langchain.agents.agent_toolkits import create_react_agent_toolkit
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
import asyncio
import os
import requests
from bs4 import BeautifulSoup
import json
import csv
import pandas as pd
import time
from typing import Dict, List, Optional, Union
from datetime import datetime

load_dotenv()

model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY"))

class WebScraper:
    def __init__(self, rate_limit: float = 1.0, max_retries: int = 3):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.rate_limit = rate_limit  # seconds between requests
        self.max_retries = max_retries
        self.last_request_time = 0

    def _respect_rate_limit(self):
        """Ensure we don't exceed the rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last_request)
        self.last_request_time = time.time()

    def _export_results(self, results: Dict[str, List[str]], format: str = "json", filename: Optional[str] = None) -> None:
        """
        Export scraped results to a file.
        
        Args:
            results (Dict[str, List[str]]): The scraped data
            format (str): Export format ('json', 'csv', or 'excel')
            filename (Optional[str]): Custom filename (without extension)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraped_data_{timestamp}"

        if format.lower() == "json":
            with open(f"{filename}.json", 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        elif format.lower() == "csv":
            # Convert to DataFrame for easier CSV export
            df = pd.DataFrame.from_dict(results, orient='index').T
            df.to_csv(f"{filename}.csv", index=False, encoding='utf-8')
        elif format.lower() == "excel":
            df = pd.DataFrame.from_dict(results, orient='index').T
            df.to_excel(f"{filename}.xlsx", index=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def scrape_website(
        self, 
        url: str, 
        selectors: Optional[Dict[str, str]] = None,
        export_format: str = "json",
        export_filename: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Scrape a website using provided CSS selectors.
        
        Args:
            url (str): The URL to scrape
            selectors (Dict[str, str]): Dictionary of name -> CSS selector pairs
            export_format (str): Format to export data ('json', 'csv', or 'excel')
            export_filename (Optional[str]): Custom filename for export (without extension)
            
        Returns:
            Dict[str, List[str]]: Dictionary of scraped data
        """
        for attempt in range(self.max_retries):
            try:
                self._respect_rate_limit()
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = {}
                
                if selectors:
                    for name, selector in selectors.items():
                        elements = soup.select(selector)
                        results[name] = [elem.get_text(strip=True) for elem in elements]
                else:
                    # Default scraping: get all text content
                    results['content'] = [soup.get_text(strip=True)]
                
                # Export the results
                self._export_results(results, export_format, export_filename)
                
                return results
                
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:  # Last attempt
                    print(f"Error scraping {url} after {self.max_retries} attempts: {str(e)}")
                    return {}
                time.sleep(2 ** attempt)  # Exponential backoff
                continue

async def main():
    server_params = StdioServerParameters(
        command="npx",
        env={
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
        }
    )
    server = Server(server_params)
    await server.start()

    client = stdio_client()
    session = ClientSession(client, server.mcp_server)
    
    # Example usage of the scraper
    scraper = WebScraper()
    url = "https://example.com"
    selectors = {
        "headings": "h1, h2, h3",
        "paragraphs": "p",
        "links": "a"
    }
    
    results = scraper.scrape_website(url, selectors)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
    
    