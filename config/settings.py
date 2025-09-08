from pydantic_settings import BaseSettings
from typing import List
import os

class ScrapingSettings(BaseSettings):
    # Scraping Layer Specifications from Presentation
    
    # Product Details to Extract
    EXTRACT_PRODUCT_NAME: bool = True
    EXTRACT_PRICE: bool = True
    EXTRACT_FEATURES: bool = True
    EXTRACT_RATINGS: bool = True
    EXTRACT_REVIEW_COUNT: bool = True
    EXTRACT_SELLER_INFO: bool = True
    
    # Review Collection Settings
    MAX_REVIEWS_PER_PRODUCT: int = 1000
    MAX_PAGES_TO_SCRAPE: int = 20
    COLLECT_REVIEWER_METADATA: bool = True
    COLLECT_VERIFIED_STATUS: bool = True
    
    # Anti-Bot Measures (as per presentation challenges)
    USE_UNDETECTED_CHROME: bool = True
    ROTATE_USER_AGENTS: bool = True
    RANDOM_DELAYS: bool = True
    HANDLE_CAPTCHAS: bool = True
    
    # Rate Limiting and IP Protection
    MIN_DELAY: float = 1.0
    MAX_DELAY: float = 3.0
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    
    # Browser Settings
    HEADLESS: bool = True
    WINDOW_SIZE: str = "1920,1080"
    
    # File Paths
    DATA_DIR: str = "data"
    RAW_DATA_DIR: str = "data/raw"
    PROCESSED_DATA_DIR: str = "data/processed"
    LOG_DIR: str = "logs"
    
    class Config:
        env_file = ".env"

# Create directories
settings = ScrapingSettings()
for directory in [settings.DATA_DIR, settings.RAW_DATA_DIR, settings.PROCESSED_DATA_DIR, settings.LOG_DIR]:
    os.makedirs(directory, exist_ok=True)
