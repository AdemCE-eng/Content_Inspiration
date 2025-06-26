import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone
import os
import pandas as pd
from dotenv import load_dotenv
from src.utils.logger import setup_logger
from src.utils.rate_limiter import rate_limit
from src.utils.retry import retry_on_failure
from src.utils.config import get_config
import glob

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

logger = setup_logger('article_scraper')
config = get_config()

# Get User-Agent from environment variables with validation
USER_AGENT = os.getenv("USER_AGENT")
if not USER_AGENT:
    logger.error("USER_AGENT not found in .env file")
    raise ValueError("USER_AGENT environment variable is required")

HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

CSV_FILE = os.path.join('.', 'data', 'raw', 'google_ai_links.csv')
DATA_DIR = config['data_dir']
REQUESTS_PER_SECOND = config.get('requests_per_second', 1)
SECONDS_PER_REQUEST = 1 / REQUESTS_PER_SECOND if REQUESTS_PER_SECOND else 1

@rate_limit(seconds_per_request=SECONDS_PER_REQUEST)
@retry_on_failure(max_retries=config.get('max_retries', 3))
def get_url(url):
    """Fetch URL with rate limiting and retry logic."""
    try:
        timeout = config.get('timeout', 30)
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        raise

def scrape_data(soup, url):
    p_tags = soup.find_all("p", limit=10)
    date = p_tags[8].text.strip() if len(p_tags) > 8 else ""
    author = p_tags[9].text.strip() if len(p_tags) > 9 else ""

    article_data = {
        "title": soup.find("h1").text.strip() if soup and soup.find("h1") else "No Title",
        "url": url,
        "published_date": date,
        "author": author,
        "sections": [],
        "scraped_date": datetime.now(timezone.utc).isoformat()
    }

    sections = []
    section_counter = 0
    current_section = None
    pending_paragraphs: list[str] = []
    pending_images: list[str] = []
    
    article_body = soup.find("div", class_="blog-detail-wrapper") if soup else None
    if not article_body:
        logger.warning(f"No article body found for {url}.")
        return article_data

    # Debug print to check what we're finding
    logger.debug(f"Found {len(article_body.find_all('img'))} images in article {url}")

    # Find all h2, h3, p, and img tags
    for elem in article_body.find_all(["h2", "h3", "p", "img"], recursive=True):
        if elem.name in ["h2", "h3"]:
            # Finalize previous section with pending content
            if current_section:
                current_section["paragraphs"].extend(pending_paragraphs)
                current_section["images"].extend(pending_images)
                if current_section["paragraphs"] or current_section["images"]:
                    sections.append(current_section)
            pending_paragraphs = []
            pending_images = []

            section_counter += 1
            current_section = {
                "section_id": section_counter,
                "section_title": elem.text.strip(),
                "section_level": 2 if elem.name == "h2" else 3,
                "paragraphs": [],
                "images": []
            }
        elif elem.name == "p":
            pending_paragraphs.append(elem.text.strip())
            # Check for images inside paragraphs too
            for img in elem.find_all("img"):
                img_url = img.get("src")
                if img_url:
                    logger.debug(f"Found image in paragraph: {img_url}")
                    pending_images.append(img_url)
        elif elem.name == "img":
            img_url = elem.get("src")
            if img_url:
                logger.debug(f"Found standalone image: {img_url}")

    # Append the final section
    if current_section:
        current_section["paragraphs"].extend(pending_paragraphs)
        current_section["images"].extend(pending_images)
        if current_section["paragraphs"] or current_section["images"]:
            sections.append(current_section)
    elif pending_paragraphs or pending_images:
        # Handle case with no headings in article
        section_counter += 1
        sections.append({
            "section_id": section_counter,
            "section_title": "Introduction",
            "paragraphs": pending_paragraphs,
            "images": pending_images,
        })

    # Debug print for sections with images
    for section in sections:
        if section["images"]:
            logger.debug(f"Section {section['section_id']} has {len(section['images'])} images")

    article_data["sections"] = sections
    return article_data

def save_article(article_data, idx):
    """Save the scraped article data to a JSON file."""
    try:
        # Get highest existing index
        output_dir = DATA_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        existing_files = glob.glob(os.path.join(output_dir, "*.json"))
        max_index = -1
        for f in existing_files:
            try:
                file_index = int(os.path.basename(f).split('_')[0])
                max_index = max(max_index, file_index)
            except ValueError:
                continue
        
        # Create new index
        new_index = max_index + 1
        
        # Create safe filename
        safe_title = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_' 
            for c in article_data['title']
        )[:50]
        
        # Save with new index
        output_path = os.path.join(output_dir, f"{new_index}_{safe_title}.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved article: {safe_title} with index {new_index}")
        
        return new_index
        
    except Exception as e:
        logger.error(f"Error saving article {idx}: {e}", exc_info=True)
        return None

# --- Run for all URLs in the CSV and update 'checked' column ---
def scrape_articles_from_links(progress_callback=None):
    """Scrape articles with progress tracking."""
    try:
        df = pd.read_csv(CSV_FILE)
        to_process = df[~df.get('checked', False)]
        total_articles = len(to_process)
        processed = 0
        
        if total_articles == 0:
            logger.info("No new articles to process")
            return 0

        for idx, row in to_process.iterrows():
            try:
                if progress_callback:
                    progress = processed / total_articles
                    progress_callback(progress, f"Processing article {processed + 1}/{total_articles}")
                
                url = row['url']
                if soup := get_url(url):
                    article_data = scrape_data(soup, url)
                    save_article(article_data, idx)
                    df.at[idx, 'checked'] = True
                    processed += 1
                    
                    # Save progress after each article
                    df.to_csv(CSV_FILE, index=False)
                
            except Exception as e:
                logger.error(f"Error processing article {idx}: {e}")
                continue
        
        return processed
        
    except Exception as e:
        logger.error(f"Fatal error in article scraping: {e}")
        return 0