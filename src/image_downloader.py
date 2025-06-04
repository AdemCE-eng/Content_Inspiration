import os
import json
import requests
import pandas as pd
import glob
from typing import Optional, Dict, List
from src.utils.logger import setup_logger
from dotenv import load_dotenv

# Setup module logger
logger = setup_logger('image_downloader')

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
    """Check if article images were already downloaded."""
    try:
        df = pd.read_csv(CSV_FILE)
        if 'images_downloaded' not in df.columns:
            return False
        
        article_status = df.loc[df['url'] == article_url, 'images_downloaded'].iloc[0]
        return bool(article_status)
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
        response = requests.get(url, headers=HEADERS, stream=True, timeout=10)
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

def process_article_images(json_path: str, images_root: str = 'images') -> Optional[Dict]:
    """
    Process and download images from a single article JSON file.
    
    Args:
        json_path: Path to the article JSON file
        images_root: Root directory for saving images
    Returns:
        Optional[Dict]: Results of the download operation or None if failed
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            article_data = json.load(f)
            
        # Check if images were already downloaded
        article_url = article_data.get('url')
        if check_if_downloaded(article_url):
            logger.info(f"Images already downloaded for {article_url}")
            return None

        # Create article directory
        article_index = os.path.basename(json_path).split('_')[0]
        article_dir = os.path.join(images_root, f"article_{article_index}")
        os.makedirs(article_dir, exist_ok=True)

        # Process sections with images
        download_results = []
        sections_with_images = [
            section for section in article_data.get('sections', [])
            if section.get('images')
        ]

        if not sections_with_images:
            logger.info(f"No images found in article {json_path}")
            update_download_status(article_url, True)  # Mark as processed even if no images
            return None

        total_images = sum(len(section.get('images', [])) for section in sections_with_images)
        logger.info(f"Found {total_images} images in {len(sections_with_images)} sections")

        # Download images
        all_successful = True
        for section in sorted(sections_with_images, key=lambda x: x.get('section_id', 0)):
            section_id = section.get('section_id')
            for idx, img_url in enumerate(section.get('images', [])):
                img_name = f"image_{section_id}{'.'+str(idx+1) if idx > 0 else ''}.jpg"
                img_path = os.path.join(article_dir, img_name)
                success = fetch_and_save_image(img_url, img_path)
                all_successful &= success
                download_results.append({
                    'url': img_url,
                    'path': img_path,
                    'success': success,
                    'section_id': section_id
                })

        # Update CSV status only if all images were downloaded successfully
        update_download_status(article_url, all_successful)
        return {'article_index': article_index, 'downloads': download_results}

    except Exception as e:
        logger.error(f"Error processing article {json_path}: {str(e)}")
        return None

def batch_process_articles(json_folder: str = './data/processed/google_articles',
                         images_root: str = './images') -> List[Dict]:
    """
    Process all article JSON files in the specified folder.
    
    Args:
        json_folder: Directory containing article JSON files
        images_root: Root directory for saving images
    Returns:
        List[Dict]: Results of all download operations
    """
    try:
        os.makedirs(images_root, exist_ok=True)
        json_files = glob.glob(os.path.join(json_folder, '*.json'))
        
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
                logger.warning(f"Failed to process {json_file}")

        logger.info(f"Completed processing {len(results)}/{len(json_files)} articles")
        return results
        
    except Exception as e:
        logger.error(f"Fatal error in batch processing: {str(e)}", exc_info=True)
        return []