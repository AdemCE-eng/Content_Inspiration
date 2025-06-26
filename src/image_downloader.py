import os
import json
import requests
import pandas as pd
import glob
from typing import Optional, Dict, List
from src.utils.logger import setup_logger
from dotenv import load_dotenv
from src.utils.config import get_config

# Setup module logger
logger = setup_logger('image_downloader')

config = get_config()
CSV_FILE = './data/raw/google_ai_links.csv'

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

# Get User-Agent from environment variables with validation
USER_AGENT = os.getenv("USER_AGENT")
if not USER_AGENT:
    logger.error("USER_AGENT not found in .env file")
    raise ValueError("USER_AGENT environment variable is required")

# Define headers for image requests
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'image/webp,image/*,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def update_download_status(article_url: str, status: bool):
    """Update the CSV file with image download status."""
    try:
        df = pd.read_csv(CSV_FILE)
        if 'images_downloaded' not in df.columns:
            df['images_downloaded'] = False
        
        # Update status for the article
        df.loc[df['url'] == article_url, 'images_downloaded'] = status
        df.to_csv(CSV_FILE, index=False)
        logger.info(f"Updated download status for {article_url}: {status}")
    except Exception as e:
        logger.error(f"Failed to update CSV status: {str(e)}")

def check_if_downloaded(article_url: str) -> bool:
    """Check if article images were already downloaded and verify they exist."""
    try:
        df = pd.read_csv(CSV_FILE)
        if 'images_downloaded' not in df.columns:
            df['images_downloaded'] = False
            df.to_csv(CSV_FILE, index=False)
            return False
        
        # Get the article's row
        article_row = df.loc[df['url'] == article_url]
        if article_row.empty:
            return False
            
        # Reset status to False if it's NaN
        if pd.isna(article_row['images_downloaded'].iloc[0]):
            df.loc[df['url'] == article_url, 'images_downloaded'] = False
            df.to_csv(CSV_FILE, index=False)
            return False
            
        return bool(article_row['images_downloaded'].iloc[0])
    except Exception as e:
        logger.error(f"Failed to check download status: {str(e)}")
        return False

def fetch_and_save_image(url: str, save_path: str) -> bool:
    """
    Fetch image from URL and save to specified path.
    
    Args:
        url: Image URL to download
        save_path: Local path to save the image
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        timeout = config.get('timeout', 30)
        response = requests.get(url, headers=HEADERS, stream=True, timeout=timeout)
        response.raise_for_status()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Successfully downloaded: {url} -> {save_path}")
        return True
    except requests.RequestException as e:
        logger.error(f"Network error downloading {url}: {str(e)}")
        return False
    except IOError as e:
        logger.error(f"File error saving to {save_path}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {str(e)}", exc_info=True)
        return False

def image_exists(img_path: str) -> bool:
    """Check if image already exists and is valid."""
    try:
        if os.path.exists(img_path):
            # Check if file is not empty
            return os.path.getsize(img_path) > 0
    except Exception as e:
        logger.error(f"Error checking image {img_path}: {e}")
    return False

def process_article_images(json_path: str, images_root: str | None = None) -> Optional[Dict]:
    """Process and download images from a single article JSON file."""
    try:
        if images_root is None:
            images_root = config.get('images_dir', 'images')
        with open(json_path, 'r', encoding='utf-8') as f:
            article_data = json.load(f)
            
        article_url = article_data.get('url')
        if not article_url:
            logger.error(f"No URL found in {json_path}")
            return None

        # Create article directory
        article_index = os.path.basename(json_path).split('_')[0]
        article_dir = os.path.join(images_root, f"article_{article_index}") # type: ignore
        
        # Force download if directory doesn't exist or is empty
        if not os.path.exists(article_dir) or not os.listdir(article_dir):
            update_download_status(article_url, False)
        
        # Only skip if both status is True and images exist
        if check_if_downloaded(article_url) and os.path.exists(article_dir) and os.listdir(article_dir):
            logger.info(f"Images already downloaded for {article_url}")
            return None

        # Process sections with images
        actual_downloads = 0
        download_results = []
        sections_with_images = [
            section for section in article_data.get('sections', [])
            if section.get('images')
        ]

        if not sections_with_images:
            logger.info(f"No images found in article {json_path}")
            update_download_status(article_url, True)
            return {
                'article_index': article_index,
                'downloads': [],
                'total_images': 0,
                'skipped_images': 0,
                'new_downloads': 0
            }

        total_images = sum(len(section.get('images', [])) for section in sections_with_images)
        logger.info(f"Found {total_images} images to process")

        # Download images
        all_successful = True
        skipped_count = 0
        for section in sorted(sections_with_images, key=lambda x: x.get('section_id', 0)):
            section_id = section.get('section_id')
            valid_images = [url for url in section.get('images', []) if url and url.strip()]
            
            for idx, img_url in enumerate(valid_images):
                img_name = f"image_{section_id}{'.'+str(idx+1) if idx > 0 else ''}.jpg"
                img_path = os.path.join(article_dir, img_name)
                
                if image_exists(img_path):
                    skipped_count += 1
                    logger.debug(f"Skipped existing image: {img_path}")
                    continue

                success = fetch_and_save_image(img_url, img_path)
                if success:
                    actual_downloads += 1
                    logger.debug(f"Successfully downloaded: {img_path}")
                all_successful &= success
                
                download_results.append({
                    'url': img_url,
                    'path': img_path,
                    'success': success,
                    'section_id': section_id
                })

        # Update CSV status and log results
        update_download_status(article_url, all_successful)
        logger.info(f"Article {article_index}: Successfully downloaded {actual_downloads} new images, Skipped {skipped_count} existing images")
        
        return {
            'article_index': article_index,
            'downloads': download_results,
            'total_images': total_images,
            'skipped_images': skipped_count,
            'new_downloads': actual_downloads
        }

    except Exception as e:
        logger.error(f"Error processing article {json_path}: {str(e)}")
        return None

def batch_process_articles(json_folder: str | None = None,
                         images_root: str | None = None) -> List[Dict]:
    """
    Process all article JSON files in the specified folder.
    
    Args:
        json_folder: Directory containing article JSON files
        images_root: Root directory for saving images
    Returns:
        List[Dict]: Results of all download operations
    """
    try:
        if json_folder is None:
            json_folder = config['data_dir']
        if images_root is None:
            images_root = config.get('images_dir', './images')
        os.makedirs(images_root, exist_ok=True) # type: ignore
        json_files = glob.glob(os.path.join(json_folder, '*.json')) # type: ignore
        
        if not json_files:
            logger.warning(f"No JSON files found in {json_folder}")
            return []

        logger.info(f"Found {len(json_files)} articles to process")
        results = []
        
        for json_file in json_files:
            logger.info(f"Processing article: {json_file}")
            result = process_article_images(json_file, images_root)
            if result:
                results.append(result)
                logger.info(f"Successfully processed {json_file}")
            else:
                logger.info(f"Skipped processing {json_file}")

        logger.info(f"Completed processing {len(results)}/{len(json_files)} articles")
        return results
        
    except Exception as e:
        logger.error(f"Fatal error in batch processing: {str(e)}", exc_info=True)
        return []