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
from typing import Dict, List, Optional, Union, Any, Callable, Tuple
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from pathlib import Path
import mimetypes
import base64
from PIL import Image
import io
import re
from enum import Enum
import operator
import hashlib
from cryptography.fernet import Fernet

load_dotenv()

model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY"))

class ConditionOperator(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_EQUALS = "greater_than_equals"
    LESS_THAN_EQUALS = "less_than_equals"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    IS_CHECKED = "is_checked"
    IS_NOT_CHECKED = "is_not_checked"

class WebScraper:
    def __init__(self, rate_limit: float = 1.0, max_retries: int = 3):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.last_request_time = 0
        self.driver = None
        self.captcha_api_key = os.getenv("CAPTCHA_API_KEY")  # Add your CAPTCHA solving service API key
        self.validation_rules = {
            "email": lambda x: bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", str(x))),
            "phone": lambda x: bool(re.match(r"^\+?[\d\s-]{10,}$", str(x))),
            "url": lambda x: bool(re.match(r"^https?://(?:[\w-]+\.)+[\w-]+(?:/[\w-./?%&=]*)?$", str(x))),
            "date": lambda x: bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(x))),
            "number": lambda x: str(x).replace(".", "").isdigit(),
            "required": lambda x: bool(str(x).strip()),
            "min_length": lambda x, min_len: len(str(x)) >= min_len,
            "max_length": lambda x, max_len: len(str(x)) <= max_len,
            "pattern": lambda x, pattern: bool(re.match(pattern, str(x))),
            "custom": lambda x, func: func(x)
        }
        self.ajax_timeout = 30  # Default timeout for AJAX requests
        self.condition_operators = {
            ConditionOperator.EQUALS: operator.eq,
            ConditionOperator.NOT_EQUALS: operator.ne,
            ConditionOperator.CONTAINS: lambda x, y: y in str(x),
            ConditionOperator.NOT_CONTAINS: lambda x, y: y not in str(x),
            ConditionOperator.GREATER_THAN: operator.gt,
            ConditionOperator.LESS_THAN: operator.lt,
            ConditionOperator.GREATER_THAN_EQUALS: operator.ge,
            ConditionOperator.LESS_THAN_EQUALS: operator.le,
            ConditionOperator.IS_EMPTY: lambda x: not str(x).strip(),
            ConditionOperator.IS_NOT_EMPTY: lambda x: bool(str(x).strip()),
            ConditionOperator.IS_CHECKED: lambda x: x.is_selected(),
            ConditionOperator.IS_NOT_CHECKED: lambda x: not x.is_selected()
        }
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        if self.encryption_key:
            self.fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(self.encryption_key.encode()).digest()))
        else:
            self.fernet = None
        self.autofill_data_file = os.getenv("AUTOFILL_DATA_FILE", "autofill_data.json")
        self.autofill_data = self._load_autofill_data()

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

    def solve_captcha(
        self,
        captcha_selector: str,
        captcha_type: str = "image",  # or "recaptcha" or "hcaptcha"
        timeout: int = 10
    ) -> Optional[str]:
        """
        Solve CAPTCHA using a CAPTCHA solving service.
        
        Args:
            captcha_selector (str): CSS selector for the CAPTCHA element
            captcha_type (str): Type of CAPTCHA ("image", "recaptcha", or "hcaptcha")
            timeout (int): Maximum time to wait for the CAPTCHA element
            
        Returns:
            Optional[str]: The solved CAPTCHA text or None if solving failed
        """
        try:
            if not self.captcha_api_key:
                raise Exception("CAPTCHA API key not found. Please set CAPTCHA_API_KEY environment variable.")

            if captcha_type == "image":
                # Handle image-based CAPTCHA
                captcha_element = self._wait_for_element(captcha_selector, timeout)
                if not captcha_element:
                    raise Exception(f"CAPTCHA element not found with selector: {captcha_selector}")

                # Get CAPTCHA image
                img_base64 = captcha_element.screenshot_as_base64
                img_data = base64.b64decode(img_base64)
                
                # Send to CAPTCHA solving service
                response = requests.post(
                    "https://api.captcha-service.com/solve",  # Replace with actual CAPTCHA service API
                    headers={"Authorization": f"Bearer {self.captcha_api_key}"},
                    json={
                        "image": img_base64,
                        "type": "image"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()["solution"]
                
            elif captcha_type in ["recaptcha", "hcaptcha"]:
                # Handle reCAPTCHA or hCaptcha
                site_key = self.driver.find_element(By.CSS_SELECTOR, captcha_selector).get_attribute("data-sitekey")
                
                response = requests.post(
                    "https://api.captcha-service.com/solve",  # Replace with actual CAPTCHA service API
                    headers={"Authorization": f"Bearer {self.captcha_api_key}"},
                    json={
                        "site_key": site_key,
                        "type": captcha_type,
                        "url": self.driver.current_url
                    }
                )
                
                if response.status_code == 200:
                    solution = response.json()["solution"]
                    # Execute JavaScript to set the CAPTCHA response
                    self.driver.execute_script(
                        f'document.querySelector("{captcha_selector}").innerHTML = "{solution}";'
                    )
                    return solution
            
            return None
            
        except Exception as e:
            print(f"Error solving CAPTCHA: {str(e)}")
            return None

    def handle_dynamic_form_fields(
        self,
        form: Any,
        field_dependencies: Dict[str, Dict[str, Any]],
        timeout: int = 10
    ) -> None:
        """
        Handle dynamic form fields that appear based on user input.
        
        Args:
            form: The form element
            field_dependencies: Dictionary defining field dependencies and their conditions
                {
                    "field_name": {
                        "trigger_field": "name of field that triggers this field",
                        "trigger_value": "value that triggers this field",
                        "selector": "CSS selector for the dynamic field",
                        "value": "value to set in the dynamic field"
                    }
                }
            timeout (int): Maximum time to wait for dynamic fields
        """
        for field_name, config in field_dependencies.items():
            try:
                # Wait for trigger field to be present
                trigger_field = form.find_element(By.NAME, config["trigger_field"])
                trigger_value = str(config["trigger_value"])
                
                # Set trigger field value
                if trigger_field.get_attribute("type") == "checkbox":
                    if trigger_field.is_selected() != (trigger_value.lower() == "true"):
                        trigger_field.click()
                else:
                    trigger_field.clear()
                    trigger_field.send_keys(trigger_value)
                
                # Wait for dynamic field to appear
                dynamic_field = WebDriverWait(form, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, config["selector"]))
                )
                
                # Set value in dynamic field
                if dynamic_field.tag_name.lower() == "select":
                    Select(dynamic_field).select_by_value(str(config["value"]))
                elif dynamic_field.get_attribute("type") == "checkbox":
                    if dynamic_field.is_selected() != (str(config["value"]).lower() == "true"):
                        dynamic_field.click()
                else:
                    dynamic_field.clear()
                    dynamic_field.send_keys(str(config["value"]))
                
            except Exception as e:
                print(f"Error handling dynamic field {field_name}: {str(e)}")
                continue

    def validate_form_field(
        self,
        field_element: Any,
        validation_rules: Dict[str, Any]
    ) -> List[str]:
        """
        Validate a form field against specified validation rules.
        
        Args:
            field_element: The form field element to validate
            validation_rules: Dictionary of validation rules to apply
                {
                    "type": "email|phone|url|date|number|required|custom",
                    "min_length": int,
                    "max_length": int,
                    "pattern": str,
                    "custom": Callable,
                    "error_message": str
                }
        
        Returns:
            List[str]: List of validation error messages
        """
        errors = []
        field_value = field_element.get_attribute("value")
        field_type = field_element.get_attribute("type")
        
        # Skip validation for empty optional fields
        if not validation_rules.get("required", False) and not field_value:
            return errors
        
        # Apply validation rules
        for rule, value in validation_rules.items():
            if rule == "type" and value in self.validation_rules:
                if not self.validation_rules[value](field_value):
                    errors.append(f"Invalid {value} format")
            
            elif rule == "min_length":
                if not self.validation_rules["min_length"](field_value, value):
                    errors.append(f"Minimum length is {value} characters")
            
            elif rule == "max_length":
                if not self.validation_rules["max_length"](field_value, value):
                    errors.append(f"Maximum length is {value} characters")
            
            elif rule == "pattern":
                if not self.validation_rules["pattern"](field_value, value):
                    errors.append("Invalid format")
            
            elif rule == "custom":
                if not self.validation_rules["custom"](field_value, value):
                    errors.append(validation_rules.get("error_message", "Invalid value"))
        
        return errors

    def validate_form(
        self,
        form: Any,
        validation_config: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Validate all form fields against specified validation rules.
        
        Args:
            form: The form element to validate
            validation_config: Dictionary of field validation rules
                {
                    "field_name": {
                        "type": "email|phone|url|date|number|required|custom",
                        "min_length": int,
                        "max_length": int,
                        "pattern": str,
                        "custom": Callable,
                        "error_message": str
                    }
                }
        
        Returns:
            Dict[str, List[str]]: Dictionary of field names and their validation errors
        """
        validation_errors = {}
        
        for field_name, rules in validation_config.items():
            try:
                field_element = form.find_element(By.NAME, field_name)
                errors = self.validate_form_field(field_element, rules)
                if errors:
                    validation_errors[field_name] = errors
            except Exception as e:
                print(f"Error validating field {field_name}: {str(e)}")
                validation_errors[field_name] = ["Field not found"]
        
        return validation_errors

    def wait_for_ajax(
        self,
        timeout: Optional[int] = None,
        check_interval: float = 0.5
    ) -> bool:
        """
        Wait for all AJAX requests to complete.
        
        Args:
            timeout (Optional[int]): Maximum time to wait for AJAX requests
            check_interval (float): Time between checks for AJAX completion
            
        Returns:
            bool: True if all AJAX requests completed, False if timed out
        """
        timeout = timeout or self.ajax_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if jQuery is present and no active AJAX requests
                jquery_ajax = self.driver.execute_script("""
                    return (typeof jQuery !== 'undefined' && jQuery.active === 0) ||
                           (typeof angular !== 'undefined' && angular.element(document).injector().get('$http').pendingRequests.length === 0);
                """)
                
                # Check if fetch requests are complete
                fetch_ajax = self.driver.execute_script("""
                    return window.fetch === undefined || 
                           !Array.from(document.querySelectorAll('script')).some(script => 
                               script.textContent.includes('fetch(') && 
                               script.textContent.includes('.then(')
                           );
                """)
                
                if jquery_ajax and fetch_ajax:
                    return True
                    
            except Exception:
                pass
                
            time.sleep(check_interval)
        
        return False
 def validate_form(
        self,
        form: Any,
        validation_config: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Validate all form fields against specified validation rules.
        
        Args:
            form: The form element to validate
            validation_config: Dictionary of field validation rules
                {
                    "field_name": {
                        "type": "email|phone|url|date|number|required|custom",
                        "min_length": int,
                        "max_length": int,
                        "pattern": str,
                        "custom": Callable,
                        "error_message": str
                    }
                }
        
        Returns:
            Dict[str, List[str]]: Dictionary of field names and their validation errors
        """
        validation_errors = {}
        
        for field_name, rules in validation_config.items():
            try:
                field_element = form.find_element(By.NAME, field_name)
                errors = self.validate_form_field(field_element, rules)
                if errors:
                    validation_errors[field_name] = errors
            except Exception as e:
                print(f"Error validating field {field_name}: {str(e)}")
                validation_errors[field_name] = ["Field not found"]
        
        return validation_errors

    def wait_for_ajax(
        self,
        timeout: Optional[int] = None,
        check_interval: float = 0.5
    ) -> bool:
        """
        Wait for all AJAX requests to complete.
        
        Args:
            timeout (Optional[int]): Maximum time to wait for AJAX requests
            check_interval (float): Time between checks for AJAX completion
            
        Returns:
            bool: True if all AJAX requests completed, False if timed out
        """
        timeout = timeout or self.ajax_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if jQuery is present and no active AJAX requests
                jquery_ajax = self.driver.execute_script("""
                    return (typeof jQuery !== 'undefined' && jQuery.active === 0) ||
                           (typeof angular !== 'undefined' && angular.element(document).injector().get('$http').pendingRequests.length === 0);
                """)
                
                # Check if fetch requests are complete
                fetch_ajax = self.driver.execute_script("""
                    return window.fetch === undefined || 
                           !Array.from(document.querySelectorAll('script')).some(script => 
                               script.textContent.includes('fetch(') && 
                               script.textContent.includes('.then(')
                           );
                """)
                
                if jquery_ajax and fetch_ajax:
                    return True
                    
            except Exception:
                pass
                
            time.sleep(check_interval)
        
        return 
    
    def handle_ajax_form_submission(
        self,
        form: Any,
        submit_button_selector: Optional[str] = None,
        wait_for_response: bool = True,
        response_selector: Optional[str] = None,
        timeout: Optional[int] = None,
        expected_status: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle form submission via AJAX and wait for response.
        
        Args:
            form: The form element
            submit_button_selector (Optional[str]): CSS selector for the submit button
            wait_for_response (bool): Whether to wait for AJAX response
            response_selector (Optional[str]): CSS selector for the response element
            timeout (Optional[int]): Maximum time to wait for response
            expected_status (Optional[int]): Expected HTTP status code
            
        Returns:
            Dict[str, Any]: Dictionary containing submission status and response data
        """
        try:
            # Store initial page state
            initial_url = self.driver.current_url
            initial_title = self.driver.title
            
            # Submit form
            if submit_button_selector:
                submit_button = form.find_element(By.CSS_SELECTOR, submit_button_selector)
                submit_button.click()
            else:
                form.submit()
            
            if not wait_for_response:
                return {"status": "submitted", "form_submitted": True}
            
            # Wait for AJAX requests to complete
            if not self.wait_for_ajax(timeout):
                return {
                    "status": "timeout",
                    "error": "AJAX request timed out",
                    "form_submitted": False
                }
            
            # Check for response element if specified
            if response_selector:
                try:
                    response_element = WebDriverWait(self.driver, timeout or self.ajax_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, response_selector))
                    )
                    response_text = response_element.text
                except TimeoutException:
                    return {
                        "status": "timeout",
                        "error": "Response element not found",
                        "form_submitted": False
                    }
            else:
                response_text = None
            
            # Check if page changed
            page_changed = (
                self.driver.current_url != initial_url or
                self.driver.title != initial_title
            )
            
            # Get response data
            response_data = {
                "status": "success",
                "form_submitted": True,
                "page_changed": page_changed,
                "current_url": self.driver.current_url,
                "page_title": self.driver.title
            }
            
            if response_text:
                response_data["response_text"] = response_text
            
            # Check for error messages
            try:
                error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error-message, .alert-danger, .validation-error")
                if error_elements:
                    response_data["errors"] = [elem.text for elem in error_elements]
                    response_data["status"] = "error"
            except:
                pass
            
            return response_data
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "form_submitted": False
            }

    def evaluate_condition(
        self,
        field_element: Any,
        condition: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a condition on a form field.
        
        Args:
            field_element: The form field element to evaluate
            condition: Dictionary defining the condition
                {
                    "operator": ConditionOperator,
                    "value": Any,
                    "type": "value|attribute|property"
                }
        
        Returns:
            bool: True if condition is met, False otherwise
        """
        try:
            operator_name = condition["operator"]
            expected_value = condition.get("value")
            value_type = condition.get("type", "value")
            
            # Get field value based on type
            if value_type == "value":
                field_value = field_element.get_attribute("value")
            elif value_type == "attribute":
                field_value = field_element.get_attribute(condition["attribute"])
            elif value_type == "property":
                field_value = field_element.get_property(condition["property"])
            else:
                field_value = field_element.text
            
            # Handle special operators
            if operator_name in [ConditionOperator.IS_EMPTY, ConditionOperator.IS_NOT_EMPTY,
                               ConditionOperator.IS_CHECKED, ConditionOperator.IS_NOT_CHECKED]:
                return self.condition_operators[operator_name](field_element)
            
            # Handle comparison operators
            if operator_name in self.condition_operators:
                return self.condition_operators[operator_name](field_value, expected_value)
            
            return False
            
        except Exception as e:
            print(f"Error evaluating condition: {str(e)}")
            return False

    def handle_field_dependencies(
        self,
        form: Any,
        dependencies: Dict[str, Dict[str, Any]],
        timeout: int = 10
    ) -> None:
        """
        Handle form field dependencies and conditional logic.
        
        Args:
            form: The form element
            dependencies: Dictionary defining field dependencies
                {
                    "target_field": {
                        "conditions": [
                            {
                                "field": "source_field_name",
                                "operator": ConditionOperator,
                                "value": Any,
                                "type": "value|attribute|property"
                            }
                        ],
                        "action": {
                            "type": "show|hide|enable|disable|set_value|clear",
                            "value": Any  # For set_value action
                        },
                        "logic": "and|or"  # How to combine multiple conditions
                    }
                }
            timeout (int): Maximum time to wait for field changes
        """
        for target_field, config in dependencies.items():
            try:
                # Get target field element
                target_element = form.find_element(By.NAME, target_field)
                
                # Evaluate conditions
                conditions = config["conditions"]
                logic = config.get("logic", "and")
                
                if logic == "and":
                    should_apply = all(
                        self.evaluate_condition(
                            form.find_element(By.NAME, condition["field"]),
                            condition
                        )
                        for condition in conditions
                    )
                else:  # or
                    should_apply = any(
                        self.evaluate_condition(
                            form.find_element(By.NAME, condition["field"]),
                            condition
                        )
                        for condition in conditions
                    )
                
                # Apply action if conditions are met
                if should_apply:
                    action = config["action"]
                    action_type = action["type"]
                    
                    if action_type == "show":
                        self.driver.execute_script(
                            "arguments[0].style.display = 'block';",
                            target_element
                        )
                    elif action_type == "hide":
                        self.driver.execute_script(
                            "arguments[0].style.display = 'none';",
                            target_element
                        )
                    elif action_type == "enable":
                        target_element.clear()
                        self.driver.execute_script(
                            "arguments[0].disabled = false;",
                            target_element
                        )
                    elif action_type == "disable":
                        self.driver.execute_script(
                            "arguments[0].disabled = true;",
                            target_element
                        )
                    elif action_type == "set_value":
                        if target_element.tag_name.lower() == "select":
                            Select(target_element).select_by_value(str(action["value"]))
                        elif target_element.get_attribute("type") == "checkbox":
                            if target_element.is_selected() != (str(action["value"]).lower() == "true"):
                                target_element.click()
                        else:
                            target_element.clear()
                            target_element.send_keys(str(action["value"]))
                    elif action_type == "clear":
                        target_element.clear()
                
            except Exception as e:
                print(f"Error handling dependency for field {target_field}: {str(e)}")
                continue

    def mask_sensitive_data(
        self,
        data: str,
        mask_type: str = "full",  # or "partial" or "custom"
        mask_char: str = "*",
        visible_chars: int = 4
    ) -> str:
        """
        Mask sensitive data like passwords, credit card numbers, etc.
        
        Args:
            data (str): The data to mask
            mask_type (str): Type of masking to apply
            mask_char (str): Character to use for masking
            visible_chars (int): Number of visible characters for partial masking
            
        Returns:
            str: Masked data
        """
        if not data:
            return data
            
        if mask_type == "full":
            return mask_char * len(data)
        elif mask_type == "partial":
            if len(data) <= visible_chars * 2:
                return mask_char * len(data)
            return data[:visible_chars] + mask_char * (len(data) - visible_chars * 2) + data[-visible_chars:]
        elif mask_type == "custom":
            # Custom masking patterns
            if re.match(r"^\d{16}$", data):  # Credit card
                return f"{data[:4]}{mask_char * 8}{data[-4:]}"
            elif re.match(r"^\d{3}-\d{2}-\d{4}$", data):  # SSN
                return f"***-**-{data[-4:]}"
            elif "@" in data:  # Email
                username, domain = data.split("@")
                return f"{username[0]}{mask_char * (len(username)-2)}{username[-1]}@{domain}"
            else:
                return mask_char * len(data)
        return data

    def encrypt_sensitive_data(self, data: str) -> Optional[str]:
        """
        Encrypt sensitive data using Fernet symmetric encryption.
        
        Args:
            data (str): The data to encrypt
            
        Returns:
            Optional[str]: Encrypted data or None if encryption failed
        """
        try:
            if not self.fernet:
                raise Exception("Encryption key not found")
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            print(f"Error encrypting data: {str(e)}")
            return None

    def decrypt_sensitive_data(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt sensitive data using Fernet symmetric encryption.
        
        Args:
            encrypted_data (str): The encrypted data to decrypt
            
        Returns:
            Optional[str]: Decrypted data or None if decryption failed
        """
        try:
            if not self.fernet:
                raise Exception("Encryption key not found")
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            print(f"Error decrypting data: {str(e)}")
            return None

    def handle_sensitive_form_data(
        self,
        form_data: Dict[str, Any],
        sensitive_fields: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Handle sensitive form data by masking and/or encrypting it.
        
        Args:
            form_data (Dict[str, Any]): The form data to process
            sensitive_fields (Dict[str, Dict[str, Any]]): Configuration for sensitive fields
                {
                    "field_name": {
                        "type": "password|credit_card|ssn|email|custom",
                        "mask": bool,
                        "encrypt": bool,
                        "mask_type": "full|partial|custom",
                        "mask_char": str,
                        "visible_chars": int
                    }
                }
        
        Returns:
            Dict[str, Any]: Processed form data with sensitive information handled
        """
        processed_data = form_data.copy()
        
        for field_name, config in sensitive_fields.items():
            if field_name not in processed_data:
                continue
                
            value = str(processed_data[field_name])
            
            # Apply masking if configured
            if config.get("mask", False):
                mask_type = config.get("mask_type", "full")
                mask_char = config.get("mask_char", "*")
                visible_chars = config.get("visible_chars", 4)
                
                processed_data[field_name] = self.mask_sensitive_data(
                    value,
                    mask_type,
                    mask_char,
                    visible_chars
                )
            
            # Apply encryption if configured
            if config.get("encrypt", False):
                encrypted_value = self.encrypt_sensitive_data(value)
                if encrypted_value:
                    processed_data[field_name] = encrypted_value
        
        return processed_data

    def _load_autofill_data(self) -> Dict[str, Any]:
        """Load autofill data from file."""
        try:
            if Path(self.autofill_data_file).exists():
                with open(self.autofill_data_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading autofill data: {str(e)}")
            return {}

    def _save_autofill_data(self) -> None:
        """Save autofill data to file."""
        try:
            with open(self.autofill_data_file, 'w') as f:
                json.dump(self.autofill_data, f, indent=2)
        except Exception as e:
            print(f"Error saving autofill data: {str(e)}")

    def handle_autofill(
        self,
        form: Any,
        autofill_config: Dict[str, Dict[str, Any]],
        save_new_data: bool = True
    ) -> None:
        """
        Handle form field autofill and suggestions.
        
        Args:
            form: The form element
            autofill_config: Dictionary defining autofill behavior
                {
                    "field_name": {
                        "type": "text|email|phone|address|credit_card|custom",
                        "use_saved": bool,
                        "save_new": bool,
                        "suggestions": List[str],
                        "custom_handler": Callable
                    }
                }
            save_new_data (bool): Whether to save new field values
        """
        for field_name, config in autofill_config.items():
            try:
                field_element = form.find_element(By.NAME, field_name)
                field_type = field_element.get_attribute("type")
                
                # Get current field value
                current_value = field_element.get_attribute("value")
                
                # Handle autofill based on configuration
                if config.get("use_saved", True) and field_name in self.autofill_data:
                    # Use saved value
                    saved_value = self.autofill_data[field_name]
                    if current_value != saved_value:
                        field_element.clear()
                        field_element.send_keys(saved_value)
                
                elif config.get("suggestions"):
                    # Handle suggestions
                    suggestions = config["suggestions"]
                    if suggestions and not current_value:
                        # Create and show suggestions dropdown
                        self.driver.execute_script("""
                            const field = arguments[0];
                            const suggestions = arguments[1];
                            
                            // Create suggestions container
                            const container = document.createElement('div');
                            container.style.position = 'absolute';
                            container.style.zIndex = '1000';
                            container.style.backgroundColor = 'white';
                            container.style.border = '1px solid #ccc';
                            container.style.maxHeight = '200px';
                            container.style.overflowY = 'auto';
                            
                            // Add suggestion items
                            suggestions.forEach(suggestion => {
                                const item = document.createElement('div');
                                item.textContent = suggestion;
                                item.style.padding = '5px 10px';
                                item.style.cursor = 'pointer';
                                item.onmouseover = () => item.style.backgroundColor = '#f0f0f0';
                                item.onmouseout = () => item.style.backgroundColor = 'white';
                                item.onclick = () => {
                                    field.value = suggestion;
                                    container.remove();
                                };
                                container.appendChild(item);
                            });
                            
                            // Position and show container
                            const rect = field.getBoundingClientRect();
                            container.style.top = (rect.bottom + window.scrollY) + 'px';
                            container.style.left = (rect.left + window.scrollX) + 'px';
                            container.style.width = rect.width + 'px';
                            document.body.appendChild(container);
                            
                            // Remove container when clicking outside
                            document.addEventListener('click', function removeContainer(e) {
                                if (!container.contains(e.target) && e.target !== field) {
                                    container.remove();
                                    document.removeEventListener('click', removeContainer);
                                }
                            });
                        """, field_element, suggestions)
                
                elif config.get("custom_handler"):
                    # Use custom handler
                    custom_value = config["custom_handler"](field_element, current_value)
                    if custom_value and custom_value != current_value:
                        field_element.clear()
                        field_element.send_keys(custom_value)
                
                # Save new value if configured
                if save_new_data and config.get("save_new", True):
                    new_value = field_element.get_attribute("value")
                    if new_value and new_value != current_value:
                        self.autofill_data[field_name] = new_value
                        self._save_autofill_data()
                
            except Exception as e:
                print(f"Error handling autofill for field {field_name}: {str(e)}")
                continue

    def handle_form_submission(
        self,
        url: str,
        form_selector: str,
        form_data: Dict[str, Union[str, bool, List[str], Dict[str, str]]],
        submit_button_selector: Optional[str] = None,
        wait_for: Optional[str] = None,
        timeout: int = 10,
        headless: bool = True,
        validate_form: bool = True,
        captcha_config: Optional[Dict[str, str]] = None,
        dynamic_fields: Optional[Dict[str, Dict[str, Any]]] = None,
        validation_config: Optional[Dict[str, Dict[str, Any]]] = None,
        is_ajax: bool = False,
        response_selector: Optional[str] = None,
        field_dependencies: Optional[Dict[str, Dict[str, Any]]] = None,
        sensitive_fields: Optional[Dict[str, Dict[str, Any]]] = None,
        autofill_config: Optional[Dict[str, Dict[str, Any]]] = None
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
            captcha_config (Optional[Dict[str, str]]): Configuration for CAPTCHA handling
                {
                    "type": "image|recaptcha|hcaptcha",
                    "selector": "CSS selector for CAPTCHA element"
                }
            dynamic_fields (Optional[Dict[str, Dict[str, Any]]]): Configuration for dynamic form fields
                {
                    "field_name": {
                        "trigger_field": "name of field that triggers this field",
                        "trigger_value": "value that triggers this field",
                        "selector": "CSS selector for the dynamic field",
                        "value": "value to set in the dynamic field"
                    }
                }
            validation_config (Optional[Dict[str, Dict[str, Any]]]): Configuration for form validation
                {
                    "field_name": {
                        "type": "email|phone|url|date|number|required|custom",
                        "min_length": int,
                        "max_length": int,
                        "pattern": str,
                        "custom": Callable,
                        "error_message": str
                    }
                }
            is_ajax (bool): Whether the form submission is handled via AJAX
            response_selector (Optional[str]): CSS selector for the AJAX response element
            field_dependencies (Optional[Dict[str, Dict[str, Any]]]): Configuration for field dependencies
                {
                    "target_field": {
                        "conditions": [
                            {
                                "field": "source_field_name",
                                "operator": ConditionOperator,
                                "value": Any,
                                "type": "value|attribute|property"
                            }
                        ],
                        "action": {
                            "type": "show|hide|enable|disable|set_value|clear",
                            "value": Any
                        },
                        "logic": "and|or"
                    }
                }
            sensitive_fields (Optional[Dict[str, Dict[str, Any]]]): Configuration for sensitive fields
                {
                    "field_name": {
                        "type": "password|credit_card|ssn|email|custom",
                        "mask": bool,
                        "encrypt": bool,
                        "mask_type": "full|partial|custom",
                        "mask_char": str,
                        "visible_chars": int
                    }
                }
            autofill_config (Optional[Dict[str, Dict[str, Any]]]): Configuration for form field autofill
                {
                    "field_name": {
                        "type": "text|email|phone|address|credit_card|custom",
                        "use_saved": bool,
                        "save_new": bool,
                        "suggestions": List[str],
                        "custom_handler": Callable
                    }
                }
            
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
            
            # Handle CAPTCHA if configured
            if captcha_config:
                captcha_solution = self.solve_captcha(
                    captcha_config["selector"],
                    captcha_config["type"],
                    timeout
                )
                if not captcha_solution:
                    raise Exception("Failed to solve CAPTCHA")
                
                # Add CAPTCHA solution to form data
                if captcha_config["type"] == "image":
                    form_data["captcha"] = captcha_solution
            
            # Handle dynamic fields if configured
            if dynamic_fields:
                self.handle_dynamic_form_fields(form, dynamic_fields, timeout)
            
            # Handle field dependencies if configured
            if field_dependencies:
                self.handle_field_dependencies(form, field_dependencies, timeout)
            
            # Handle sensitive data if configured
            if sensitive_fields:
                form_data = self.handle_sensitive_form_data(form_data, sensitive_fields)
            
            # Handle autofill if configured
            if autofill_config:
                self.handle_autofill(form, autofill_config)
            
            # Validate form if configured
            if validate_form and validation_config:
                validation_errors = self.validate_form(form, validation_config)
                if validation_errors:
                    return {
                        "status": "validation_error",
                        "errors": validation_errors,
                        "form_submitted": False
                    }
            
            # Submit form
            if is_ajax:
                return self.handle_ajax_form_submission(
                    form,
                    submit_button_selector,
                    True,
                    response_selector,
                    timeout
                )
            else:
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
    
    