import time
import random
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from fake_useragent import UserAgent
from loguru import logger

from config.settings import settings

class BaseScraper(ABC):
    """
    Base scraper implementing presentation specifications:
    🛡️ Handles challenges:
    • Dynamic content loading
    • Anti-bot measures (CAPTCHAs)
    • Rate limiting and IP blocking
    • Multiple page pagination
    """
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.user_agent = UserAgent()
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with anti-detection measures"""
        try:
            if settings.USE_UNDETECTED_CHROME:
                options = uc.ChromeOptions()
                logger.info("Using undetected Chrome driver for anti-bot protection")
            else:
                options = Options()
            
            # Basic options
            if settings.HEADLESS:
                options.add_argument('--headless')
            
            # Anti-detection options (per presentation: Anti-bot measures)
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Faster loading
            options.add_argument(f'--window-size={settings.WINDOW_SIZE}')
            options.add_argument('--disable-web-security')
            options.add_argument('--ignore-certificate-errors')
            
            # User agent rotation (per presentation: rotating proxies, browser automation)
            if settings.ROTATE_USER_AGENTS:
                try:
                    user_agent = self.user_agent.random
                    options.add_argument(f'--user-agent={user_agent}')
                    logger.info(f"Using user agent: {user_agent[:50]}...")
                except:
                    logger.warning("Failed to set random user agent, using default")
            
            # Create driver
            if settings.USE_UNDETECTED_CHROME:
                self.driver = uc.Chrome(options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            # Set timeouts
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(settings.REQUEST_TIMEOUT)
            
            # WebDriverWait for explicit waits
            self.wait = WebDriverWait(self.driver, settings.REQUEST_TIMEOUT)
            
            logger.info("✅ Chrome driver setup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Chrome driver: {e}")
            raise
    
    def handle_dynamic_content_loading(self, timeout: int = 10):
        """Handle dynamic content loading challenge"""
        try:
            # Wait for basic page structure
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Scroll to trigger lazy loading
            self.scroll_page()
            
            # Wait for any AJAX requests to complete
            self.wait_for_page_ready()
            
        except TimeoutException:
            logger.warning("⚠️ Dynamic content loading timeout")
    
    def handle_anti_bot_measures(self):
        """Handle CAPTCHAs and anti-bot detection"""
        if not settings.HANDLE_CAPTCHAS:
            return
        
        try:
            # Check for common CAPTCHA elements
            captcha_selectors = [
                "iframe[src*='captcha']",
                "iframe[src*='recaptcha']", 
                ".captcha-container",
                "#captcha",
                "[data-testid='captcha']",
                ".g-recaptcha"
            ]
            
            for selector in captcha_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.warning("🤖 CAPTCHA detected! Waiting for manual resolution...")
                    logger.info("Please solve the CAPTCHA manually in the browser window")
                    
                    # Wait longer for manual CAPTCHA resolution
                    time.sleep(30)
                    break
            
            # Check for access denied or blocked pages
            page_text = self.driver.page_source.lower()
            blocked_indicators = [
                "access denied",
                "blocked",
                "captcha",
                "unusual traffic",
                "automated requests"
            ]
            
            if any(indicator in page_text for indicator in blocked_indicators):
                logger.warning("🚫 Potential blocking detected")
                self.ethical_delay(5, 10)  # Longer delay
                
        except Exception as e:
            logger.debug(f"Anti-bot check error: {e}")
    
    def ethical_delay(self, min_delay: float = None, max_delay: float = None):
        """Add ethical delays to prevent rate limiting"""
        if not settings.RANDOM_DELAYS:
            return
        
        min_delay = min_delay or settings.MIN_DELAY
        max_delay = max_delay or settings.MAX_DELAY
        
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"⏱️ Ethical delay: {delay:.2f} seconds")
        time.sleep(delay)
    
    def scroll_page(self, pause_time: float = 1.0, max_scrolls: int = 3):
        """Scroll page to load dynamic content"""
        try:
            current_height = self.driver.execute_script("return document.body.scrollHeight")
            
            for i in range(max_scrolls):
                # Scroll to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause_time)
                
                # Check if new content loaded
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == current_height:
                    break
                current_height = new_height
                
                logger.debug(f"📜 Scroll {i+1}: Page height = {new_height}")
                
        except Exception as e:
            logger.debug(f"Scrolling error: {e}")
    
    def wait_for_page_ready(self):
        """Wait for page to be fully loaded"""
        try:
            # Wait for document ready state
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Wait for jQuery if present
            try:
                self.wait.until(
                    lambda driver: driver.execute_script("return jQuery.active == 0")
                )
            except:
                pass  # jQuery not present
                
        except Exception as e:
            logger.debug(f"Page ready check error: {e}")
    
    def safe_find_element(self, by: By, value: str, timeout: int = 10) -> Optional[Any]:
        """Safely find element with timeout"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
    
    def safe_find_elements(self, by: By, value: str, timeout: int = 10) -> List[Any]:
        """Safely find multiple elements"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            return []
    
    def safe_get_text(self, element: Any) -> str:
        """Safely extract text from element"""
        if not element:
            return ""
        try:
            return element.text.strip()
        except:
            try:
                return element.get_attribute("textContent").strip()
            except:
                return ""
    
    def safe_get_attribute(self, element: Any, attribute: str) -> str:
        """Safely get attribute from element"""
        if not element:
            return ""
        try:
            return element.get_attribute(attribute) or ""
        except:
            return ""
    
    def navigate_with_retry(self, url: str) -> bool:
        """Navigate to URL with retry logic"""
        for attempt in range(settings.MAX_RETRIES):
            try:
                logger.info(f"🌐 Navigating to URL (attempt {attempt + 1}): {url}")
                
                self.driver.get(url)
                
                # Handle challenges from presentation
                self.handle_dynamic_content_loading()
                self.handle_anti_bot_measures()
                self.ethical_delay()
                
                logger.info("✅ Successfully navigated to URL")
                return True
                
            except Exception as e:
                logger.warning(f"❌ Navigation attempt {attempt + 1} failed: {e}")
                if attempt < settings.MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 2
                    logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error("❌ All navigation attempts failed")
                    return False
        
        return False
    
    @abstractmethod
    def extract_product_details(self, url: str) -> Dict[str, Any]:
        """
        Extract product details as per presentation:
        • Product name, price, features
        • Ratings and review count
        • Seller information
        """
        pass
    
    @abstractmethod
    def collect_customer_reviews(self, url: str) -> List[Dict[str, Any]]:
        """
        Collect customer reviews as per presentation:
        • Review text and ratings
        • Reviewer metadata
        • Verified purchase status
        """
        pass
    
    def close(self):
        """Close the driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔒 Driver closed successfully")
            except Exception as e:
                logger.error(f"❌ Error closing driver: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
