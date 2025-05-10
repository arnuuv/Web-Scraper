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
from typing import Dict, List, Optional

load_dotenv()

model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY"))

class WebScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape_website(self, url: str, selectors: Optional[Dict[str, str]] = None) -> Dict[str, List[str]]:
        """
        Scrape a website using provided CSS selectors.
        
        Args:
            url (str): The URL to scrape
            selectors (Dict[str, str]): Dictionary of name -> CSS selector pairs
            
        Returns:
            Dict[str, List[str]]: Dictionary of scraped data
        """
        try:
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
            
            return results
            
        except requests.RequestException as e:
            print(f"Error scraping {url}: {str(e)}")
            return {}

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
    
    