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
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from pathlib import Path
import mimetypes
import base64

load_dotenv()

model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY"))

class WebScraper:
    def __init__(self, rate_limit: float = 1.0, max_retries: int = 3):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.last_request_time = 0
        self.driver = None

    def _setup_selenium(self, headless: bool = True):
        """Set up Selenium WebDriver with Chrome options."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
        self.driver = webdriver.Chrome(options=chrome_options)

    def _wait_for_element(self, selector: str, timeout: int = 10):
        """Wait for an element to be present on the page."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            print(f"Timeout waiting for element: {selector}")
            return None

    def scrape_dynamic_content(
        self,
        url: str,
        selectors: Dict[str, str],
        wait_for: Optional[str] = None,
        timeout: int = 10,
        headless: bool = True,
        export_format: str = "json",
        export_filename: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Scrape dynamic content from JavaScript-rendered pages using Selenium.
        
        Args:
            url (str): The URL to scrape
            selectors (Dict[str, str]): Dictionary of name -> CSS selector pairs
            wait_for (Optional[str]): CSS selector to wait for before scraping
            timeout (int): Maximum time to wait for elements (seconds)
            headless (bool): Whether to run browser in headless mode
            export_format (str): Format to export data
            export_filename (Optional[str]): Custom filename for export
            
        Returns:
            Dict[str, List[str]]: Dictionary of scraped data
        """
        try:
            if not self.driver:
                self._setup_selenium(headless)
            
            self.driver.get(url)
            
            # Wait for specified element if provided
            if wait_for:
                self._wait_for_element(wait_for, timeout)
            
            results = {}
            for name, selector in selectors.items():
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                results[name] = [elem.text.strip() for elem in elements]
            
            # Export the results
            self._export_results(results, export_format, export_filename)
            
            return results
            
        except Exception as e:
            print(f"Error scraping dynamic content from {url}: {str(e)}")
            return {}
        
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def execute_js(self, url: str, js_code: str, wait_for: Optional[str] = None, timeout: int = 10) -> Optional[str]:
        """
        Execute custom JavaScript code on a page.
        
        Args:
            url (str): The URL to execute JavaScript on
            js_code (str): JavaScript code to execute
            wait_for (Optional[str]): CSS selector to wait for before execution
            timeout (int): Maximum time to wait for elements (seconds)
            
        Returns:
            Optional[str]: Result of JavaScript execution
        """
        try:
            if not self.driver:
                self._setup_selenium()
            
            self.driver.get(url)
            
            if wait_for:
                self._wait_for_element(wait_for, timeout)
            
            result = self.driver.execute_script(js_code)
            return str(result)
            
        except Exception as e:
            print(f"Error executing JavaScript on {url}: {str(e)}")
            return None
            
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

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

    def scrape_paginated_content(
        self,
        url: str,
        selectors: Dict[str, str],
        pagination_type: str = "infinite_scroll",  # or "load_more" or "page_numbers"
        max_pages: Optional[int] = None,
        scroll_pause_time: float = 2.0,
        load_more_selector: Optional[str] = None,
        page_number_selector: Optional[str] = None,
        wait_for: Optional[str] = None,
        timeout: int = 10,
        headless: bool = True,
        export_format: str = "json",
        export_filename: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Scrape content from paginated pages or infinite scroll websites.
        
        Args:
            url (str): The URL to scrape
            selectors (Dict[str, str]): Dictionary of name -> CSS selector pairs
            pagination_type (str): Type of pagination ("infinite_scroll", "load_more", or "page_numbers")
            max_pages (Optional[int]): Maximum number of pages to scrape
            scroll_pause_time (float): Time to pause between scrolls
            load_more_selector (Optional[str]): CSS selector for "Load More" button
            page_number_selector (Optional[str]): CSS selector for page number links
            wait_for (Optional[str]): CSS selector to wait for before scraping
            timeout (int): Maximum time to wait for elements (seconds)
            headless (bool): Whether to run browser in headless mode
            export_format (str): Format to export data
            export_filename (Optional[str]): Custom filename for export
            
        Returns:
            Dict[str, List[str]]: Dictionary of scraped data from all pages
        """
        try:
            if not self.driver:
                self._setup_selenium(headless)
            
            self.driver.get(url)
            if wait_for:
                self._wait_for_element(wait_for, timeout)
            
            all_results = {name: [] for name in selectors.keys()}
            current_page = 1
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while True:
                # Scrape current page
                for name, selector in selectors.items():
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    all_results[name].extend([elem.text.strip() for elem in elements])
                
                # Check if we've reached the maximum number of pages
                if max_pages and current_page >= max_pages:
                    break
                
                # Handle different pagination types
                if pagination_type == "infinite_scroll":
                    # Scroll to bottom
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(scroll_pause_time)
                    
                    # Check if we've reached the end
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                    
                elif pagination_type == "load_more" and load_more_selector:
                    try:
                        load_more = self._wait_for_element(load_more_selector, timeout)
                        if not load_more or not load_more.is_displayed():
                            break
                        load_more.click()
                        time.sleep(scroll_pause_time)
                    except TimeoutException:
                        break
                        
                elif pagination_type == "page_numbers" and page_number_selector:
                    try:
                        next_page = self.driver.find_element(By.CSS_SELECTOR, f"{page_number_selector}[data-page='{current_page + 1}']")
                        if not next_page or not next_page.is_displayed():
                            break
                        next_page.click()
                        time.sleep(scroll_pause_time)
                    except:
                        break
                
                current_page += 1
                self._respect_rate_limit()
            
            # Export the results
            self._export_results(all_results, export_format, export_filename)
            
            return all_results
            
        except Exception as e:
            print(f"Error scraping paginated content from {url}: {str(e)}")
            return {}
            
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def handle_file_upload(
        self,
        file_input_selector: str,
        file_path: Union[str, Path],
        timeout: int = 10
    ) -> bool:
        """
        Handle file upload to a file input element.
        
        Args:
            file_input_selector (str): CSS selector for the file input element
            file_path (Union[str, Path]): Path to the file to upload
            timeout (int): Maximum time to wait for the file input element
            
        Returns:
            bool: True if upload was successful, False otherwise
        """
        try:
            file_input = self._wait_for_element(file_input_selector, timeout)
            if not file_input:
                raise Exception(f"File input not found with selector: {file_input_selector}")
            
            # Convert path to absolute path
            abs_path = str(Path(file_path).resolve())
            
            # Send the file path to the input element
            file_input.send_keys(abs_path)
            return True
            
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return False

    def handle_form_submission(
        self,
        url: str,
        form_selector: str,
        form_data: Dict[str, Union[str, bool, List[str], Dict[str, str]]],  # Updated type hint
        submit_button_selector: Optional[str] = None,
        wait_for: Optional[str] = None,
        timeout: int = 10,
        headless: bool = True,
        validate_form: bool = True
    ) -> Dict[str, Any]:
        """
        Handle form submission on a webpage, including filling fields and submitting.
        
        Args:
            url (str): The URL containing the form
            form_selector (str): CSS selector for the form element
            form_data (Dict[str, Union[str, bool, List[str], Dict[str, str]]]): Dictionary of form field names and values
                - For text inputs: {"field_name": "value"}
                - For checkboxes: {"checkbox_name": True/False}
                - For select/radio: {"select_name": "option_value"}
                - For multiple select: {"select_name": ["option1", "option2"]}
                - For file uploads: {"file_field": {"path": "/path/to/file", "selector": "#file-input"}}
            submit_button_selector (Optional[str]): CSS selector for the submit button
            wait_for (Optional[str]): CSS selector to wait for after form submission
            timeout (int): Maximum time to wait for elements (seconds)
            headless (bool): Whether to run browser in headless mode
            validate_form (bool): Whether to validate form fields before submission
            
        Returns:
            Dict[str, Any]: Dictionary containing submission status and response data
        """
        try:
            if not self.driver:
                self._setup_selenium(headless)
            
            self.driver.get(url)
            
            # Wait for form to be present
            form = self._wait_for_element(form_selector, timeout)
            if not form:
                raise Exception(f"Form not found with selector: {form_selector}")
            
            # Fill form fields
            for field_name, value in form_data.items():
                try:
                    # Handle file uploads
                    if isinstance(value, dict) and "path" in value and "selector" in value:
                        if not self.handle_file_upload(value["selector"], value["path"], timeout):
                            raise Exception(f"Failed to upload file for field {field_name}")
                        continue
                    
                    # Handle other input types
                    input_element = form.find_element(By.NAME, field_name)
                    input_type = input_element.get_attribute("type")
                    
                    if input_type == "checkbox":
                        if input_element.is_selected() != value:
                            input_element.click()
                    
                    elif input_type == "radio":
                        if value:
                            radio = form.find_element(By.CSS_SELECTOR, f"input[name='{field_name}'][value='{value}']")
                            radio.click()
                    
                    elif input_element.tag_name.lower() == "select":
                        select = Select(input_element)
                        if isinstance(value, list):
                            # Handle multiple select
                            for option in value:
                                select.select_by_value(option)
                        else:
                            select.select_by_value(str(value))
                    
                    else:
                        # Handle text inputs
                        input_element.clear()
                        input_element.send_keys(str(value))
                        
                except Exception as e:
                    print(f"Error filling field {field_name}: {str(e)}")
                    if validate_form:
                        raise
            
            # Submit form
            if submit_button_selector:
                submit_button = form.find_element(By.CSS_SELECTOR, submit_button_selector)
                submit_button.click()
            else:
                form.submit()
            
            # Wait for response if specified
            if wait_for:
                self._wait_for_element(wait_for, timeout)
            
            # Get response data
            response_data = {
                "status": "success",
                "current_url": self.driver.current_url,
                "page_title": self.driver.title,
                "form_submitted": True
            }
            
            return response_data
            
        except Exception as e:
            print(f"Error submitting form on {url}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "form_submitted": False
            }
            
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

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

    # Example form submission
    form_data = {
        "username": "testuser",
        "password": "testpass",
        "remember_me": True,
        "country": "US",
        "interests": ["coding", "reading"]  # For multiple select
    }

    result = scraper.handle_form_submission(
        url="https://example.com/login",
        form_selector="#login-form",
        form_data=form_data,
        submit_button_selector="#submit-button",
        wait_for=".dashboard",  # Wait for dashboard to appear after login
        timeout=10
    )

    print(result)

if __name__ == "__main__":
    asyncio.run(main())
    
    