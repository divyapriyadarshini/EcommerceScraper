import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from loguru import logger
import time

from .base_scraper import BaseScraper
from config.settings import settings

class AmazonScraper(BaseScraper):
    """
    Amazon scraper implementing presentation specifications:
    🎯 Extracts product details: Product name, price, features, ratings, review count, seller information
    📝 Collects customer reviews: Review text and ratings, reviewer metadata, verified purchase status
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = ""
    
    def detect_amazon_domain(self, url: str) -> str:
        """Detect Amazon domain from URL"""
        if 'amazon.com' in url:
            return 'https://www.amazon.com'
        elif 'amazon.co.uk' in url:
            return 'https://www.amazon.co.uk'
        elif 'amazon.in' in url:
            return 'https://www.amazon.in'
        elif 'amazon.de' in url:
            return 'https://www.amazon.de'
        else:
            return 'https://www.amazon.com'
    
    def extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from URL or page source"""
        # First try URL patterns
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'asin=([A-Z0-9]{10})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If not found in URL, extract from page source
        return self.extract_asin_from_page()

    def extract_asin_from_page(self) -> Optional[str]:
        """Extract ASIN from loaded page HTML"""
        try:
            from bs4 import BeautifulSoup
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Try multiple methods to find ASIN
            # Method 1: Meta tag
            asin_meta = soup.find('meta', {'name': 'pageId'})
            if asin_meta:
                return asin_meta.get('content')
            
            # Method 2: Data attributes
            asin_element = soup.find(attrs={'data-asin': True})
            if asin_element:
                return asin_element.get('data-asin')
            
            # Method 3: JavaScript variables (look for ASIN in script tags)
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    asin_match = re.search(r'"ASIN"\s*:\s*"([A-Z0-9]{10})"', script.string)
                    if asin_match:
                        return asin_match.group(1)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting ASIN from page: {e}")
            return None

    def resolve_short_url(self, url: str) -> str:
        """Resolve shortened Amazon URLs to full URLs"""
        try:
            import requests
            response = requests.head(url, allow_redirects=True, timeout=10)
            final_url = response.url
            logger.info(f"🔗 Resolved URL: {final_url}")
            return final_url
        except Exception as e:
            logger.warning(f"⚠️ Could not resolve short URL: {e}, using original")
            return url



    def extract_product_details(self, url: str) -> Dict[str, Any]:
        """
        Extract product details as specified in presentation:
        • Product name, price, features
        • Ratings and review count
        • Seller information
        • ASIN extraction from page source (handles short URLs)
        """
    
        # Resolve short URL
        resolved_url = self.resolve_short_url(url)
        
        product_data = {
            "url": resolved_url,
            "name": "",
            "price": "",
            "currency": "",
            "rating": 0.0,
            "review_count": 0,
            "features": [],
            "seller_name": "",
            "asin": "",
            "images": [] 
        }
        
        try:
            base_url = self.detect_amazon_domain(resolved_url)
            
            logger.info(f"🌐 Navigating to: {resolved_url}")
            self.driver.get(resolved_url)
            self.ethical_delay()
            
            # Extract ASIN from page source (fixes short URL issue)
            product_data["asin"] = self.extract_asin_from_page() or ""
            logger.info(f"📦 ASIN: {product_data['asin']}")
            
            # Product name
            name_selectors = [
                "#productTitle",
                ".product-title h1",
                "h1.a-size-large"
            ]
            
            for selector in name_selectors:
                element = self.safe_find_element(By.CSS_SELECTOR, selector)
                if element:
                    product_data["name"] = self.safe_get_text(element)
                    logger.info(f"📝 Product: {product_data['name'][:50]}...")
                    break
            
            # Price extraction
            self._extract_price_info(product_data)
            
            # Rating and review count
            self._extract_rating_info(product_data)
            
            # Features
            self._extract_features(product_data)
            
            # Seller information
            self._extract_seller_info(product_data)
            
            # Availability
            self._extract_availability(product_data)
            
            # Product images
            self._extract_images(product_data)
            
            logging_summary = f"""
            ✅ Product Details Extracted:
            📦 Name: {product_data['name'][:50]}...
            💰 Price: {product_data['currency']} {product_data['price']}
            ⭐ Rating: {product_data['rating']}/5 ({product_data['review_count']} reviews)
            🏪 Seller: {product_data['seller_name']}
            📋 Features: {len(product_data['features'])} items
            🆔 ASIN: {product_data['asin']}
            """
            logger.info(logging_summary)
            
        except Exception as e:
            logger.error(f"❌ Error extracting product details: {e}")
        
        return product_data
    
    def _extract_asin_from_page(self) -> Optional[str]:
        """
        Extract ASIN from loaded page HTML - handles short URLs
        """
        try:
            from bs4 import BeautifulSoup
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Method 1: Try URL patterns first
            current_url = self.driver.current_url
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', current_url)
            if asin_match:
                return asin_match.group(1)
            
            # Method 2: Meta tag with pageId
            meta_tag = soup.find('meta', {'name': 'pageId'})
            if meta_tag:
                content = meta_tag.get('content', '')
                if len(content) == 10 and content.isalnum():
                    return content
            
            # Method 3: Data attributes
            asin_element = soup.find(attrs={'data-asin': True})
            if asin_element:
                asin = asin_element.get('data-asin')
                if asin and len(asin) == 10:
                    return asin
            
            # Method 4: JavaScript variables in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for ASIN in various JS patterns
                    patterns = [
                        r'"ASIN"\s*:\s*"([A-Z0-9]{10})"',
                        r'asin\s*:\s*"([A-Z0-9]{10})"',
                        r'"asin"\s*:\s*"([A-Z0-9]{10})"',
                        r'ASIN\s*=\s*"([A-Z0-9]{10})"'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, script.string)
                        if match:
                            return match.group(1)
            
            # Method 5: Form inputs with ASIN
            asin_input = soup.find('input', attrs={'name': 'ASIN'})
            if asin_input:
                asin = asin_input.get('value')
                if asin and len(asin) == 10:
                    return asin
            
            # Method 6: Look in image URLs
            images = soup.find_all('img')
            for img in images:
                src = img.get('src', '')
                if '/images/I/' in src:
                    # Amazon product images often contain ASIN-like patterns
                    match = re.search(r'/([A-Z0-9]{10})\.', src)
                    if match:
                        return match.group(1)
            
            logger.warning("⚠️ Could not extract ASIN from page")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting ASIN from page: {e}")
            return None
        
    
    
    def _extract_price_info(self, product_data: Dict[str, Any]):
        """Extract price and currency information"""
        price_selectors = [
            ".a-price-whole",
            ".a-offscreen",
            "#apex_desktop .a-price .a-offscreen",
            "#price_inside_buybox",
            ".a-price .a-offscreen"
        ]
        
        for selector in price_selectors:
            element = self.safe_find_element(By.CSS_SELECTOR, selector)
            if element:
                price_text = self.safe_get_text(element)
                if price_text:
                    # Extract currency and price
                    if '$' in price_text:
                        product_data["currency"] = "USD"
                        product_data["price"] = re.sub(r'[^\d.]', '', price_text)
                    elif '₹' in price_text:
                        product_data["currency"] = "INR"
                        product_data["price"] = re.sub(r'[^\d.]', '', price_text)
                    elif '£' in price_text:
                        product_data["currency"] = "GBP" 
                        product_data["price"] = re.sub(r'[^\d.]', '', price_text)
                    elif '€' in price_text:
                        product_data["currency"] = "EUR"
                        product_data["price"] = re.sub(r'[^\d.]', '', price_text)
                    else:
                        product_data["price"] = re.sub(r'[^\d.]', '', price_text)
                    
                    logger.info(f"💰 Price: {product_data['currency']} {product_data['price']}")
                    break
    
    def _extract_rating_info(self, product_data: Dict[str, Any]):
        """Extract rating and review count"""
        # Rating
        rating_selectors = [
            ".a-icon-alt",
            "[data-hook='average-star-rating'] .a-icon-alt",
            ".reviewCountTextLinkedHistogram .a-icon-alt"
        ]
        
        for selector in rating_selectors:
            element = self.safe_find_element(By.CSS_SELECTOR, selector)
            if element:
                rating_text = self.safe_get_attribute(element, "textContent") or self.safe_get_text(element)
                if rating_text:
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        product_data["rating"] = float(rating_match.group(1))
                        break
        
        # Review count
        review_count_selectors = [
            "#acrCustomerReviewText",
            "[data-hook='total-review-count']",
            ".reviewCountTextLinkedHistogram .a-link-normal"
        ]
        
        for selector in review_count_selectors:
            element = self.safe_find_element(By.CSS_SELECTOR, selector)
            if element:
                count_text = self.safe_get_text(element)
                if count_text:
                    count_match = re.search(r'([\d,]+)', count_text)
                    if count_match:
                        try:
                            product_data["review_count"] = int(count_match.group(1).replace(',', ''))
                            break
                        except ValueError:
                            pass
        
        logger.info(f"⭐ Rating: {product_data['rating']}/5 ({product_data['review_count']} reviews)")

    def _extract_reviews_from_page(self) -> List[Dict[str, Any]]:
        """Extract reviews from current page"""
        
        reviews = []
        
        try:
            # Find all review elements
            review_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-hook='review']")
            
            if not review_elements:
                logger.warning("⚠️ No review elements found on current page")
                return reviews
            
            for element in review_elements:
                try:
                    review_data = {}
                    
                    # Reviewer name
                    try:
                        reviewer_element = element.find_element(By.CSS_SELECTOR, ".a-profile-name")
                        review_data["reviewer_name"] = self.safe_get_text(reviewer_element)
                    except:
                        review_data["reviewer_name"] = "Anonymous"
                    
                    # Rating
                    try:
                        rating_element = element.find_element(By.CSS_SELECTOR, "i.a-icon span.a-icon-alt")
                        rating_text = self.safe_get_text(rating_element)
                        rating_match = re.search(r'(\d+)', rating_text)
                        review_data["rating"] = int(rating_match.group(1)) if rating_match else 0
                    except:
                        review_data["rating"] = 0
                    
                    # Review title
                    try:
                        title_element = element.find_element(By.CSS_SELECTOR, "[data-hook='review-title'] span")
                        review_data["title"] = self.safe_get_text(title_element)
                    except:
                        review_data["title"] = ""
                    
                    # Review content
                    try:
                        content_element = element.find_element(By.CSS_SELECTOR, "[data-hook='review-body'] span")
                        review_data["content"] = self.safe_get_text(content_element)
                    except:
                        review_data["content"] = ""
                    
                    # Review date
                    try:
                        date_element = element.find_element(By.CSS_SELECTOR, "[data-hook='review-date']")
                        review_data["date"] = self.safe_get_text(date_element)
                    except:
                        review_data["date"] = ""
                    
                    # Verified purchase status
                    try:
                        verified_elements = element.find_elements(By.CSS_SELECTOR, "[data-hook='avp-badge']")
                        review_data["verified_purchase"] = len(verified_elements) > 0
                    except:
                        review_data["verified_purchase"] = False
                    
                    # Helpful votes
                    try:
                        helpful_element = element.find_elements(By.CSS_SELECTOR, "[data-hook='helpful-vote-statement']")
                        if helpful_element:
                            helpful_text = self.safe_get_text(helpful_element[0])
                            helpful_match = re.search(r'(\d+)', helpful_text)
                            review_data["helpful_votes"] = int(helpful_match.group(1)) if helpful_match else 0
                        else:
                            review_data["helpful_votes"] = 0
                    except:
                        review_data["helpful_votes"] = 0
                    
                    # Vine customer
                    try:
                        vine_elements = element.find_elements(By.CSS_SELECTOR, "[data-hook='vine-customer-review']")
                        review_data["vine_customer"] = len(vine_elements) > 0
                    except:
                        review_data["vine_customer"] = False
                    
                    # Only add review if it has meaningful content
                    if review_data["content"] and len(review_data["content"].strip()) >= 10:
                        reviews.append(review_data)
                    
                except Exception as e:
                    logger.debug(f"❌ Error parsing individual review: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ Error extracting reviews from page: {e}")
        
        return reviews

    def wait_for_reviews_to_load(self):
        """Wait for review elements to load"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Wait up to 20 seconds for review elements to appear
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-hook='review']"))
            )
            logger.info("✅ Reviews loaded successfully")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Timeout waiting for reviews: {e}")
            return False

    
    def _extract_features(self, product_data: Dict[str, Any]):
        """Extract product features"""
        feature_selectors = [
            "#feature-bullets ul li",
            "#productDetails_feature_div li",
            ".a-unordered-list .a-list-item"
        ]
        
        for selector in feature_selectors:
            elements = self.safe_find_elements(By.CSS_SELECTOR, selector)
            if elements:
                for element in elements[:10]:  # Limit to 10 features
                    feature_text = self.safe_get_text(element)
                    if feature_text and len(feature_text) > 10 and not feature_text.startswith("Make sure"):
                        # Clean the feature text
                        feature_text = re.sub(r'^[•\-\*]\s*', '', feature_text)
                        product_data["features"].append(feature_text.strip())
                break
        
        logger.info(f"📋 Features extracted: {len(product_data['features'])}")
    
    def _extract_seller_info(self, product_data: Dict[str, Any]):
        """Extract seller information"""
        seller_selectors = [
            "#sellerProfileTriggerId",
            "#bylineInfo",
            ".po-brand .po-break-word"
        ]
        
        seller_info = {}
        
        for selector in seller_selectors:
            element = self.safe_find_element(By.CSS_SELECTOR, selector)
            if element:
                seller_text = self.safe_get_text(element)
                if seller_text and not seller_text.startswith("Visit"):
                    seller_info["name"] = seller_text.replace("Brand:", "").strip()
                    break
        
        if not seller_info.get("name"):
            seller_info["name"] = "Amazon"
        
        product_data["seller_info"] = seller_info
        logger.info(f"🏪 Seller: {seller_info['name']}")
    
    def _extract_availability(self, product_data: Dict[str, Any]):
        """Extract availability information"""
        availability_selectors = [
            "#availability span",
            ".a-color-success",
            ".a-color-price"
        ]
        
        for selector in availability_selectors:
            element = self.safe_find_element(By.CSS_SELECTOR, selector)
            if element:
                availability_text = self.safe_get_text(element)
                if "stock" in availability_text.lower() or "available" in availability_text.lower():
                    product_data["availability"] = availability_text
                    break
    
    def _extract_images(self, product_data: Dict[str, Any]):
        """Extract product images"""
        image_selectors = [
            "#altImages img",
            "#landingImage",
            ".a-dynamic-image"
        ]
        
        for selector in image_selectors:
            elements = self.safe_find_elements(By.CSS_SELECTOR, selector)
            if elements:
                for element in elements[:5]:  # Limit to 5 images
                    img_src = self.safe_get_attribute(element, "src")
                    if img_src and "http" in img_src:
                        product_data["images"].append(img_src)
                break
    

    def collect_customer_reviews(self, url: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """Collect customer reviews"""
        
        reviews = []
        
        try:
            asin = self.extract_asin(url)
            if not asin:
                logger.error("❌ Could not extract ASIN")
                return reviews
            
            base_url = self.detect_amazon_domain(url)
            
            # FIX: Build complete URL with domain
            reviews_url = f"{base_url}/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?reviewerType=all_reviews&sortBy=recent"
            
            logger.info(f"🌐 Navigating to reviews: {reviews_url}")
            
            if not self.navigate_with_retry(reviews_url):
                logger.error("❌ Failed to navigate to reviews page")
                return reviews
            
            for page in range(1, max_pages + 1):
                logger.info(f"📄 Scraping page {page}")
                
                page_reviews = self._extract_reviews_from_page()
                reviews.extend(page_reviews)
                
                logger.info(f"📝 Found {len(page_reviews)} reviews on page {page}")
                
                # Navigate to next page
                try:
                    next_button = self.safe_find_element(By.CSS_SELECTOR, "li.a-last a")
                    if next_button and "a-disabled" not in next_button.get_attribute("class"):
                        next_button.click()
                        self.ethical_delay()
                    else:
                        break
                except:
                    break
            
        except Exception as e:
            logger.error(f"❌ Error collecting reviews: {e}")
        
        logger.info(f"✅ Total reviews collected: {len(reviews)}")
        return reviews

    def _extract_reviews_from_page(self) -> List[Dict[str, Any]]:
        """Extract reviews from current page"""
        
        reviews = []
        
        try:
            # Wait for reviews to load
            if not self.wait_for_reviews_to_load():
                logger.warning("⚠️ Reviews did not load within timeout")
                return reviews
            
            # Find all review elements
            review_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-hook='review']")
                
            if not review_elements:
                logger.warning("⚠️ No review elements found on current page")
                return reviews
            
            for element in review_elements:
                try:
                    review_data = {}
                    
                    # Review ID
                    review_data["review_id"] = self.safe_get_attribute(element, "id")
                    
                    # Reviewer metadata (per presentation spec)
                    reviewer_element = self.safe_find_element(By.CSS_SELECTOR, ".a-profile-name")
                    if reviewer_element:
                        review_data["reviewer_name"] = self.safe_get_text(reviewer_element)
                    else:
                        review_data["reviewer_name"] = "Anonymous"
                    
                    # Rating
                    rating_element = element.find_element(By.CSS_SELECTOR, "i.a-icon span.a-icon-alt")
                    rating_text = self.safe_get_text(rating_element)
                    if rating_text:
                        rating_match = re.search(r'(\d+)', rating_text)
                        if rating_match:
                            review_data["rating"] = int(rating_match.group(1))
                        else:
                            review_data["rating"] = 0
                    else:
                        review_data["rating"] = 0
                    
                    # Review title
                    title_element = element.find_element(By.CSS_SELECTOR, "[data-hook='review-title'] span")
                    review_data["title"] = self.safe_get_text(title_element)
                    
                    # Review text (main content)
                    content_element = element.find_element(By.CSS_SELECTOR, "[data-hook='review-body'] span")
                    review_data["review_text"] = self.safe_get_text(content_element)
                    
                    # Review date
                    date_element = element.find_element(By.CSS_SELECTOR, "[data-hook='review-date']")
                    review_data["date"] = self.safe_get_text(date_element)
                    
                    # Verified purchase status (per presentation spec)
                    verified_element = element.find_elements(By.CSS_SELECTOR, "[data-hook='avp-badge']")
                    review_data["verified_purchase"] = len(verified_element) > 0
                    
                    # Helpful votes
                    helpful_element = element.find_elements(By.CSS_SELECTOR, "[data-hook='helpful-vote-statement']")
                    if helpful_element:
                        helpful_text = self.safe_get_text(helpful_element[0])
                        helpful_match = re.search(r'(\d+)', helpful_text)
                        review_data["helpful_votes"] = int(helpful_match.group(1)) if helpful_match else 0
                    else:
                        review_data["helpful_votes"] = 0
                    
                    # Vine customer
                    vine_element = element.find_elements(By.CSS_SELECTOR, "[data-hook='vine-customer-review']")
                    review_data["vine_customer"] = len(vine_element) > 0
                    
                    # Only add review if it has meaningful content
                    if review_data["review_text"] and len(review_data["review_text"].strip()) >= 10:
                        reviews.append(review_data)
                    
                except Exception as e:
                    logger.debug(f"❌ Error parsing individual review: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"❌ Error extracting reviews from page: {e}")
        
        return reviews
    
    def _navigate_to_next_page(self) -> bool:
        """Navigate to next page of reviews"""
        try:
            # Find next page button
            next_button = self.safe_find_element(By.CSS_SELECTOR, "li.a-last a")
            
            if not next_button:
                return False
            
            # Check if button is disabled
            if "a-disabled" in next_button.get_attribute("class"):
                return False
            
            # Click next page
            next_button.click()
            
            # Wait for page to load
            self.ethical_delay(2, 4)
            self.handle_dynamic_content_loading()
            
            return True
            
        except Exception as e:
            logger.debug(f"❌ Failed to navigate to next page: {e}")
            return False

    def scrape_product(self, url: str) -> Dict[str, Any]:
        """Complete product scraping (details + reviews)"""
        logger.info(f"🎯 Starting complete product scraping for: {url}")
        
        # Extract product details
        product_details = self.extract_product_details(url)
        
        # Collect customer reviews
        reviews = self.collect_customer_reviews(url)
        
        return {
            "product_details": product_details,
            "reviews": reviews,
            "total_reviews_scraped": len(reviews),
            "scraping_timestamp": time.time()
        }
