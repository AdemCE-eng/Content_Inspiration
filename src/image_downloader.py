import os
import json
import requests
from urllib.parse import urlparse
import glob
import re
from typing import Optional, Dict, List
from src.utils.logger import setup_logger

# Setup module logger
logger = setup_logger('image_downloader')

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
        response = requests.get(url, stream=True, timeout=10)
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
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {json_path}: {str(e)}")
        return None
    except IOError as e:
        logger.error(f"Cannot read file {json_path}: {str(e)}")
        return None

    # Create article directory
    article_dir = None
    try:
        article_index = os.path.basename(json_path).split('_')[0]
        article_dir = os.path.join(images_root, f"article_{article_index}")
        os.makedirs(article_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {article_dir}: {str(e)}")
        return None

    # Process sections with images
    download_results = []
    sections_with_images = [
        section for section in article_data.get('sections', [])
        if section.get('images')
    ]

    if not sections_with_images:
        logger.info(f"No images found in article {json_path}")
        return None

    total_images = sum(len(section.get('images', [])) for section in sections_with_images)
    logger.info(f"Found {total_images} images in {len(sections_with_images)} sections")

    for section in sorted(sections_with_images, key=lambda x: x.get('section_id', 0)):
        section_id = section.get('section_id')
        section_title = section.get('section_title', 'Unknown Section')
        logger.debug(f"Processing section {section_id}: {section_title}")

        for idx, img_url in enumerate(section.get('images', [])):
            img_name = f"image_{section_id}{'.'+str(idx+1) if idx > 0 else ''}.jpg"
            img_path = os.path.join(article_dir, img_name)
            success = fetch_and_save_image(img_url, img_path)
            download_results.append({
                'url': img_url,
                'path': img_path,
                'success': success,
                'section_id': section_id,
                'section_title': section_title
            })

    return {'article_index': article_index, 'downloads': download_results}

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