"""
E-Commerce Web Scraper
Focus: Scraping Layer Implementation

Based on presentation specifications:
🎯 Extracts product details: Product name, price, features, ratings, review count, seller information
📝 Collects customer reviews: Review text and ratings, reviewer metadata, verified purchase status
🛡️ Handles challenges: Dynamic content loading, Anti-bot measures (CAPTCHAs), Rate limiting and IP blocking, Multiple page pagination
"""

import sys
import argparse
from loguru import logger

from scraper.amazon_scraper import AmazonScraper
from scraper.utils import save_to_json, save_reviews_to_csv, generate_filename, print_scraping_summary
from config.settings import settings

def setup_logging():
    """Setup logging configuration"""
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>"
    )
    logger.add(
        f"{settings.LOG_DIR}/scraper.log",
        rotation="10 MB",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

def scrape_amazon_product(url: str, save_files: bool = True) -> dict:
    """Scrape Amazon product with all details and reviews"""
    
    logger.info("🛍️ E-Commerce Web Scraper Starting...")
    logger.info(f"🔗 Target URL: {url}")
    logger.info(f"⚙️ Max Reviews: {settings.MAX_REVIEWS_PER_PRODUCT}")
    logger.info(f"📄 Max Pages: {settings.MAX_PAGES_TO_SCRAPE}")
    
    try:
        with AmazonScraper() as scraper:
            # Complete product scraping
            result = scraper.scrape_product(url)
            
            if save_files:
                # Save complete data
                product_name = result["product_details"].get("name", "unknown_product")
                asin = result["product_details"].get("asin", "unknown_asin")
                
                # Save complete data as JSON
                json_filename = generate_filename(product_name, asin, "json")
                save_to_json(result, json_filename)
                
                # Save reviews as CSV
                if result["reviews"]:
                    csv_filename = generate_filename(product_name, asin, "csv")
                    save_reviews_to_csv(result["reviews"], csv_filename)
            
            # Print summary
            print_scraping_summary(result)
            
            return result
            
    except KeyboardInterrupt:
        logger.info("⚠️ Scraping interrupted by user")
        return {}
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        return {}

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description="E-Commerce Web Scraper - Extract product details and reviews"
    )
    parser.add_argument("url", help="Amazon product URL to scrape")
    parser.add_argument("--no-save", action="store_true", help="Don't save files")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    # Override settings if needed
    if args.headless:
        settings.HEADLESS = True
    
    setup_logging()
    
    def is_amazon_url(url: str) -> bool:
        """Check if URL is from Amazon (including short links)"""
        amazon_domains = [
            'amazon.com', 'amazon.in', 'amazon.co.uk', 'amazon.de',
            'amzn.in', 'amzn.to', 'a.co'  # Amazon short URLs
        ]
        return any(domain in url.lower() for domain in amazon_domains)

    # Use the function
    if not is_amazon_url(args.url):
        logger.error("❌ Please provide a valid Amazon product URL")
        sys.exit(1)

    
    # Start scraping
    result = scrape_amazon_product(args.url, save_files=not args.no_save)
    
    if result and result.get("reviews"):
        logger.info("✅ Scraping completed successfully!")
        return True
    else:
        logger.error("❌ Scraping failed or no data collected")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
