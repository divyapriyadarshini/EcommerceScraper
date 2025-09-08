import json
import csv
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

def save_to_json(data: Dict[str, Any], filename: str, directory: str = "data/raw"):
    """Save data to JSON file"""
    try:
        filepath = f"{directory}/{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"💾 Data saved to: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"❌ Error saving JSON: {e}")
        return None

def save_reviews_to_csv(reviews: List[Dict[str, Any]], filename: str, directory: str = "data/processed"):
    """Save reviews to CSV file"""
    try:
        if not reviews:
            logger.warning("⚠️ No reviews to save")
            return None
        
        filepath = f"{directory}/{filename}"
        df = pd.DataFrame(reviews)
        df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"📊 Reviews saved to CSV: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"❌ Error saving CSV: {e}")
        return None

def generate_filename(product_name: str, asin: str, file_type: str = "json") -> str:
    """Generate safe filename from product data"""
    # Clean product name for filename
    safe_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
    safe_name = safe_name.replace(' ', '_')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return f"amazon_{safe_name}_{asin}_{timestamp}.{file_type}"

def print_scraping_summary(data: Dict[str, Any]):
    """Print a nice summary of scraped data"""
    product = data.get("product_details", {})
    reviews = data.get("reviews", [])
    
    print("\n" + "="*60)
    print("🎯 SCRAPING SUMMARY")
    print("="*60)
    print(f"📦 Product: {product.get('name', 'N/A')}")
    print(f"💰 Price: {product.get('currency', '')} {product.get('price', 'N/A')}")
    print(f"⭐ Rating: {product.get('rating', 0)}/5")
    print(f"📊 Original Review Count: {product.get('review_count', 0)}")
    print(f"📝 Reviews Scraped: {len(reviews)}")
    print(f"✅ Verified Purchases: {sum(1 for r in reviews if r.get('verified_purchase', False))}")
    print(f"🏪 Seller: {product.get('seller_info', {}).get('name', 'N/A')}")
    print(f"📋 Features Found: {len(product.get('features', []))}")
    
    if reviews:
        ratings = [r.get('rating', 0) for r in reviews if r.get('rating', 0) > 0]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            print(f"📈 Average Scraped Rating: {avg_rating:.2f}")
            
            # Rating distribution
            print("\n📊 Rating Distribution:")
            for rating in range(1, 6):
                count = ratings.count(rating)
                percentage = (count / len(ratings)) * 100 if ratings else 0
                bar = "█" * int(percentage / 5)
                print(f"  {rating} ⭐: {count:3d} ({percentage:5.1f}%) {bar}")
    
    print("="*60)
