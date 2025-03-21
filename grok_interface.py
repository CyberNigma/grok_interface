from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
import json
import os
import logging
import asyncio

logging.getLogger('WDM').setLevel(logging.NOTSET)
logging.getLogger('requests').setLevel(logging.NOTSET)
logging.getLogger('urllib3').setLevel(logging.NOTSET)

CHAT_URL = "https://www.grok.com"
COOKIE_FILE = "grok_cookies.json"
REQUIRED_COOKIES = {"cf_clearance", "sso", "sso-rw"}

class GrokInterface:
    def __init__(self):
        self.driver = None
        self.initial_count = 0

    def _load_cookies(self):
        if not os.path.exists(COOKIE_FILE):
            print(f"Warning: Cookie file '{COOKIE_FILE}' does not exist. Please provide initial cookies.")
            sys.exit(1)
        
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies = json.load(f)
            if not cookies or not isinstance(cookies, list):
                print(f"Warning: '{COOKIE_FILE}' is empty or invalid. Expected a list of cookies.")
                sys.exit(1)
            filtered_cookies = [c for c in cookies if c["name"] in REQUIRED_COOKIES]
            if not all(name in [c["name"] for c in filtered_cookies] for name in REQUIRED_COOKIES):
                print(f"Warning: '{COOKIE_FILE}' does not contain all required cookies: {REQUIRED_COOKIES}")
                sys.exit(1)
            return filtered_cookies
        except json.JSONDecodeError:
            print(f"Warning: Failed to parse '{COOKIE_FILE}'. Invalid JSON format.")
            sys.exit(1)
        except Exception as e:
            print(f"Warning: Error loading cookies from '{COOKIE_FILE}': {e}")
            sys.exit(1)

    def _save_cookies(self, cookies):
        filtered_cookies = [c for c in cookies if c["name"] in REQUIRED_COOKIES]
        if len(filtered_cookies) != len(REQUIRED_COOKIES):
            print(f"Warning: Not all required cookies were captured: {[c['name'] for c in filtered_cookies]}")
        with open(COOKIE_FILE, 'w') as f:
            json.dump(filtered_cookies, f, indent=4)

    def _setup_driver(self, headless=False, cookies=None):
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--log-level=3")
        if headless:
            chrome_options.add_argument("--headless")
        service = Service(
            executable_path=ChromeDriverManager().install(),
            log_output=os.devnull
        )
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        if cookies:
            driver.get(CHAT_URL)
            for cookie in cookies:
                driver.add_cookie(cookie)
        return driver

    def _is_captcha_present(self):
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "challenge-container"))
            )
            return True
        except:
            try:
                self.driver.find_element(By.XPATH, "//textarea[contains(@class, 'bg-transparent')]")
                return False
            except:
                return True

    def _manual_login_and_refresh_cookies(self, existing_cookies):
        self.driver.get(CHAT_URL)
        
        if self._is_captcha_present():
            print("CAPTCHA detected! Browser is already in headed mode for manual solving...")
            print("Please solve the CAPTCHA and ensure the chat page loads fully. Press Enter here when ready...")
            input("Press Enter when chat is loaded: ")
            
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//textarea[contains(@class, 'bg-transparent')]"))
                )
            except:
                raise Exception("Chat page didn't load properly after CAPTCHA. Check URL or cookies.")
            
            updated_cookies = self.driver.get_cookies()
            self._save_cookies(updated_cookies)
            return updated_cookies
        else:
            return existing_cookies

    def connect(self):
        """Blocking function to initialize and connect to the chat."""
        initial_cookies = self._load_cookies()
        self.driver = self._setup_driver(headless=False, cookies=initial_cookies)
        try:
            updated_cookies = self._manual_login_and_refresh_cookies(initial_cookies)
            self.initial_count = len(self.driver.find_elements(By.XPATH, "//div[contains(@class, 'message-bubble') and not(contains(@class, 'bg-foreground'))]"))
        except Exception as e:
            print(f"Connection failed: {e}")
            self.driver.quit()
            raise

    def send_message(self, message):
        """Blocking function to send a message and wait for response to start."""
        if not self.driver:
            raise Exception("Not connected. Call connect() first.")
        
        input_field = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[contains(@class, 'bg-transparent')]"))
        )
        input_field.clear()
        input_field.send_keys(message)
        
        submit_button = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Submit']"))
        )
        submit_button.click()
        
        def get_grok_response_count():
            return len(self.driver.find_elements(By.XPATH, "//div[contains(@class, 'message-bubble') and not(contains(@class, 'bg-foreground'))]"))
        
        WebDriverWait(self.driver, 20).until(
            lambda d: get_grok_response_count() > self.initial_count
        )
        self.initial_count = get_grok_response_count()

    async def receive_message(self):
        """
        Asynchronous generator to yield complete paragraphs or list items.
        
        Yields paragraphs/list items only when:
        1. There is another paragraph/list item after it, or
        2. The entire response is complete (5 icons at the bottom)
        """
        if not self.driver:
            raise Exception("Not connected. Call connect() first.")
        
        # Maximum wait time
        max_wait_time = 120  # seconds
        start_time = time.time()
        response_complete = False
        
        # Keep track of elements we've already processed
        processed_elements = set()
        
        # Wait for the response to complete or timeout
        while not response_complete and (time.time() - start_time) < max_wait_time:
            # Check if response is complete (5 icons/buttons at the bottom)
            try:
                check_complete_script = """
                const bubbles = document.querySelectorAll('.message-bubble:not(.bg-foreground)');
                if (bubbles.length === 0) return false;
                
                const lastBubbleContainer = bubbles[bubbles.length - 1].closest('.group');
                if (!lastBubbleContainer) return false;
                
                // Look for the button container that appears when response is complete
                const buttonContainer = lastBubbleContainer.querySelector('.flex.items-center.gap-\\\\[2px\\\\].w-max');
                return buttonContainer && buttonContainer.querySelectorAll('button').length >= 5;
                """
                response_complete = self.driver.execute_script(check_complete_script)
            except Exception as e:
                await asyncio.sleep(0.5)
                continue
            
            # Get all paragraphs and list items
            try:
                extract_elements_script = """
                const bubbles = document.querySelectorAll('.message-bubble:not(.bg-foreground)');
                if (bubbles.length === 0) return [];
                
                const latestBubble = bubbles[bubbles.length - 1];
                
                // Check if the response is complete (has 5 icons at the bottom)
                const lastBubbleContainer = latestBubble.closest('.group');
                let responseIsComplete = false;
                
                if (lastBubbleContainer) {
                    const buttonContainer = lastBubbleContainer.querySelector('.flex.items-center.gap-\\\\[2px\\\\].w-max');
                    responseIsComplete = buttonContainer && buttonContainer.querySelectorAll('button').length >= 5;
                }
                
                // Use tree walking to process nodes in their natural DOM order
                function processContentNodes(rootNode) {
                    const results = [];
                    let index = 0;
                    
                    // Function to recursively process a node and its children
                    function processNode(node) {
                        // Skip script and style tags
                        if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE') {
                            return;
                        }
                        
                        // Process content nodes we're interested in
                        if (node.tagName === 'P' || node.tagName === 'LI') {
                            let text = node.textContent.trim();
                            
                            // Handle ordered lists (add numbers)
                            if (node.tagName === 'LI') {
                                const parentList = node.closest('ol');
                                if (parentList) {
                                    // Get the actual list index by counting previous siblings
                                    let number = 1;
                                    let sibling = node.previousElementSibling;
                                    while (sibling) {
                                        number++;
                                        sibling = sibling.previousElementSibling;
                                    }
                                    
                                    // Apply starting index offset if specified
                                    const startAttr = parentList.getAttribute('start');
                                    if (startAttr) {
                                        const start = parseInt(startAttr);
                                        if (!isNaN(start)) {
                                            number = start + number - 1;
                                        }
                                    }
                                    
                                    // Prepend the number to the text
                                    text = number + ". " + text;
                                }
                            }
                            
                            // Determine if element is complete
                            // It's complete if: 
                            // 1. It has a next sibling of the same type (p or li), or
                            // 2. The entire response is complete
                            let isComplete = false;
                            if (responseIsComplete) {
                                isComplete = true;
                            } else if (node.nextElementSibling && 
                                      (node.nextElementSibling.tagName === 'P' || 
                                       node.nextElementSibling.tagName === 'LI')) {
                                isComplete = true;
                            }
                            
                            if (text) {
                                results.push({
                                    id: 'text_' + index++,
                                    text: text,
                                    isComplete: isComplete,
                                    type: 'text'
                                });
                            }
                        } 
                        // Handle code blocks
                        else if (node.classList && node.classList.contains('not-prose')) {
                            // Get language if available
                            const langElement = node.querySelector('.font-mono');
                            const language = langElement ? langElement.textContent.trim() : '';
                            
                            // Get the actual code content
                            const codeElement = node.querySelector('code');
                            let codeContent = '';
                            
                            if (codeElement) {
                                codeContent = codeElement.textContent;
                            } else {
                                codeContent = node.textContent;
                            }
                            
                            // Code blocks are considered complete when the response is complete
                            results.push({
                                id: 'code_' + index++,
                                text: codeContent,
                                language: language,
                                isComplete: responseIsComplete,
                                type: 'code'
                            });
                        }
                        
                        // Recursively process child nodes
                        for (const child of node.children) {
                            processNode(child);
                        }
                    }
                    
                    // Start processing from the root
                    processNode(rootNode);
                    return results;
                }
                
                // Process the content nodes in order
                return processContentNodes(latestBubble);
                """
                elements = self.driver.execute_script(extract_elements_script)
                
                # If response is complete, mark all elements as complete
                if response_complete:
                    for element in elements:
                        element['isComplete'] = True
                
                # Process elements that are complete and haven't been processed yet
                for element in elements:
                    element_id = element['id']
                    text = element['text']
                    is_complete = element['isComplete']
                    element_type = element.get('type', 'text')  # Default to 'text' if type not specified
                    
                    if is_complete and element_id not in processed_elements and text:
                        processed_elements.add(element_id)
                        
                        # Handle different element types
                        if element_type == 'code':
                            language = element.get('language', '')
                            # Format code blocks with special markers
                            code_block = f"```{language}\n{text}\n```\n"
                            yield code_block
                        else:
                            # Regular text content
                            yield text + "\n"  # Single newline - original behavior
            except Exception as e:
                # If there's an error, just continue
                pass
            
            # Short delay to avoid hammering the DOM
            await asyncio.sleep(0.5)
        
        # Final check for any remaining content if we timed out
        if time.time() - start_time >= max_wait_time:
            print("Warning: Reached maximum wait time while receiving message.")
            
            try:
                final_extract_script = """
                const bubbles = document.querySelectorAll('.message-bubble:not(.bg-foreground)');
                if (bubbles.length === 0) return [];
                
                const latestBubble = bubbles[bubbles.length - 1];
                
                // Check for response completion one more time
                const lastBubbleContainer = latestBubble.closest('.group');
                let responseIsComplete = false;
                
                if (lastBubbleContainer) {
                    const buttonContainer = lastBubbleContainer.querySelector('.flex.items-center.gap-\\\\[2px\\\\].w-max');
                    responseIsComplete = buttonContainer && buttonContainer.querySelectorAll('button').length >= 5;
                }
                
                // Use tree walking to process nodes in their natural DOM order
                function processContentNodes(rootNode) {
                    const results = [];
                    let index = 0;
                    
                    // Function to recursively process a node and its children
                    function processNode(node) {
                        // Skip script and style tags
                        if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE') {
                            return;
                        }
                        
                        // Process content nodes we're interested in
                        if (node.tagName === 'P' || node.tagName === 'LI') {
                            let text = node.textContent.trim();
                            
                            // Handle ordered lists (add numbers)
                            if (node.tagName === 'LI') {
                                const parentList = node.closest('ol');
                                if (parentList) {
                                    // Get the actual list index by counting previous siblings
                                    let number = 1;
                                    let sibling = node.previousElementSibling;
                                    while (sibling) {
                                        number++;
                                        sibling = sibling.previousElementSibling;
                                    }
                                    
                                    // Apply starting index offset if specified
                                    const startAttr = parentList.getAttribute('start');
                                    if (startAttr) {
                                        const start = parseInt(startAttr);
                                        if (!isNaN(start)) {
                                            number = start + number - 1;
                                        }
                                    }
                                    
                                    // Prepend the number to the text
                                    text = number + ". " + text;
                                }
                            }
                            
                            // In final extraction, consider all elements complete
                            if (text) {
                                results.push({
                                    id: 'text_' + index++,
                                    text: text,
                                    isComplete: true,
                                    type: 'text'
                                });
                            }
                        } 
                        // Handle code blocks
                        else if (node.classList && node.classList.contains('not-prose')) {
                            // Get language if available
                            const langElement = node.querySelector('.font-mono');
                            const language = langElement ? langElement.textContent.trim() : '';
                            
                            // Get the actual code content
                            const codeElement = node.querySelector('code');
                            let codeContent = '';
                            
                            if (codeElement) {
                                codeContent = codeElement.textContent;
                            } else {
                                codeContent = node.textContent;
                            }
                            
                            results.push({
                                id: 'code_' + index++,
                                text: codeContent,
                                language: language,
                                isComplete: true,
                                type: 'code'
                            });
                        }
                        
                        // Recursively process child nodes
                        for (const child of node.children) {
                            processNode(child);
                        }
                    }
                    
                    // Start processing from the root
                    processNode(rootNode);
                    return results;
                }
                
                // Process the content nodes in order
                return processContentNodes(latestBubble);
                """
                final_elements = self.driver.execute_script(final_extract_script)
                
                for element in final_elements:
                    element_id = element['id']
                    text = element['text']
                    element_type = element.get('type', 'text')  # Default to 'text' if type not specified
                    
                    if element_id not in processed_elements and text:
                        processed_elements.add(element_id)
                        
                        # Handle different element types
                        if element_type == 'code':
                            language = element.get('language', '')
                            # Format code blocks with special markers
                            code_block = f"```{language}\n{text}\n```\n"
                            yield code_block
                        else:
                            # Regular text content
                            yield text + "\n"  # Single newline - original behavior
            except Exception as e:
                print(f"Error during final elements extraction: {e}")

    def close(self):
        """Close the driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None