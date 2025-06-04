import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone
import os
import pandas as pd
from src.utils.logger import setup_logger

CSV_FILE = os.path.join(os.path.dirname(__file__), '../../data/raw/google_ai_links.csv')
USER_AGENT = os.getenv("USER_AGENT")
HEADERS = {'User-Agent': USER_AGENT}
logger = setup_logger('article_scraper')

def get_url(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

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
    section_counter = 1
    current_section = {
        "section_id": section_counter,
        "section_title": "Introduction",
        "paragraphs": [],
        "images": []
    }

    article_body = soup.find("div", class_="blog-detail-wrapper") if soup else None
    if not article_body:
        logger.warning(f"No article body found for {url}.")
        return article_data

    # Debug print to check what we're finding
    logger.debug(f"Found {len(article_body.find_all('img'))} images in article {url}")

    for elem in article_body.find_all(["h2", "p", "img"], recursive=True):
        if elem.name == "h2":
            if current_section["paragraphs"] or current_section["images"]:
                sections.append(current_section)
            section_counter += 1
            current_section = {
                "section_id": section_counter,
                "section_title": elem.text.strip(),
                "paragraphs": [],
                "images": []
            }
        elif elem.name == "p":
            current_section["paragraphs"].append(elem.text.strip())
            # Check for images inside paragraphs too
            for img in elem.find_all("img"):
                img_url = img.get("src")
                if img_url:
                    logger.debug(f"Found image in paragraph: {img_url}")
                    current_section["images"].append(img_url)
        elif elem.name == "img":
            img_url = elem.get("src")
            if img_url:
                logger.debug(f"Found standalone image: {img_url}")
                current_section["images"].append(img_url)

    # Don't forget the last section
    if current_section["paragraphs"] or current_section["images"]:
        sections.append(current_section)

    # Debug print for sections with images
    for section in sections:
        if section["images"]:
            logger.debug(f"Section {section['section_id']} has {len(section['images'])} images")

    article_data["sections"] = sections
    return article_data

# --- Run for all URLs in the CSV and update 'checked' column ---
def scrape_articles_from_links():
    try:
        df = pd.read_csv(CSV_FILE)
        output_dir = os.path.join('.', 'data', 'processed', 'google_articles')
        os.makedirs(output_dir, exist_ok=True)

        for count, (idx, row) in enumerate(df.iterrows(), start=1):
            if not row.get('checked', False):
                url = row['url']
                logger.info(f"Processing article {count}/{len(df)}: {url}")
                try:
                    soup = get_url(url)
                    if soup:
                        article_json = scrape_data(soup, url)
                        safe_title = "".join(
                            c if c.isalnum() or c in (' ', '-', '_') else '_' 
                            for c in row['title']
                        )[:50]
                        output_path = os.path.join(output_dir, f"{idx}_{safe_title}.json")
                        
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(article_json, f, ensure_ascii=False, indent=2)
                        df.at[idx, 'checked'] = True
                        logger.info(f"Successfully saved article: {safe_title}")
                    else:
                        logger.error(f"Failed to fetch article: {url}")
                except Exception as e:
                    logger.error(f"Error processing article {url}: {str(e)}", exc_info=True)

        df.to_csv(CSV_FILE, index=False)
        logger.info("Completed processing all articles")
    except Exception as e:
        logger.error(f"Fatal error in article scraping: {str(e)}", exc_info=True)
        raise