import requests
from bs4 import BeautifulSoup
import os
from src.utils.config import get_config
import pandas as pd
from src.utils.logger import setup_logger
from dotenv import load_dotenv

logger = setup_logger('links_scraper')

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

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

def load_base_url(url_index=0):
    """Load the base URL from the YAML config file."""
    try:
        config = get_config()
        sources = config.get('sources', [None])
        if isinstance(sources, dict):
            sources = list(sources.values())
        base_url = sources[url_index] if len(sources) > url_index else None
        if not base_url:
            logger.error("No URL found in config file")
            return None
        logger.info(f"Loaded base URL: {base_url}")
        return base_url
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}", exc_info=True)
        return None

def get_url(base_url):
    """Fetch the HTML content of the base URL."""
    try:
        config = get_config()
        timeout = config.get('timeout', 30)
        logger.info(f"Fetching URL: {base_url}")
        response = requests.get(base_url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except requests.RequestException as e:
        logger.error(f"Error fetching {base_url}: {str(e)}", exc_info=True)
        return None

def get_links(soup, base_url):
    """Extract titles and URLs from the soup object."""
    if not soup:
        logger.error("No soup object provided")
        return None

    raw_titles = []
    post_urls = []
    cards = soup.find_all('li', class_='glue-grid__col')
    logger.info(f"Found {len(cards)} article cards")

    for card_div in cards:
        title_span = card_div.find('span', class_='headline-5')
        link_tag = card_div.find('a')
        if title_span and link_tag and link_tag.has_attr('href'):
            raw_title = title_span.text.strip()
            post_url = link_tag['href']
            if not post_url.startswith('http'):
                post_url = base_url.replace("/blog/", "") + post_url
            raw_titles.append(raw_title)
            post_urls.append(post_url)
        else:
            logger.warning("Missing title or link in a card")
    
    if not raw_titles:
        logger.warning("No titles found in the provided URL")
        return None    

    return list(zip(raw_titles, post_urls))

def scrape_homepage():
    """Main function to scrape the homepage and update the CSV file."""
    csv_file = './data/raw/google_ai_links.csv'
    try:
        base_url = load_base_url()
        if not base_url:
            return

        soup = get_url(base_url)
        if not soup:
            return

        links = get_links(soup, base_url)
        if not links:
            logger.error("No links found")
            return

        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_file), exist_ok=True)

        # Load or create DataFrame
        if os.path.exists(csv_file):
            existing_df = pd.read_csv(csv_file)
            logger.info(f"Loaded existing CSV with {len(existing_df)} entries")
        else:
            existing_df = pd.DataFrame(columns=['title', 'url'])
            logger.info("Created new DataFrame")

        # Update DataFrame
        new_df = pd.DataFrame(links, columns=['title', 'url'])
        new_df['checked'] = False
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=['title', 'url'], inplace=True)
        
        # Handle checked column
        if 'checked' not in combined_df.columns:
            combined_df['checked'] = False
        else:
            combined_df['checked'] = combined_df['checked'].fillna(False)
            combined_df['checked'] = combined_df['checked'].astype(bool)

        # Save results
        combined_df.to_csv(csv_file, index=False)
        logger.info(f"Saved {len(combined_df)} entries to CSV")
        
    except Exception as e:
        logger.error(f"Unexpected error in scrape_homepage: {str(e)}", exc_info=True)