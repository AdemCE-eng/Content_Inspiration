import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone
import os
import pandas as pd

CSV_FILE = os.path.join(os.path.dirname(__file__), '../../data/raw/google_ai_links.csv')
USER_AGENT = os.getenv("USER_AGENT")
HEADERS = {'User-Agent': USER_AGENT}

def get_url(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except Exception as e:
        print(f"Error fetching {url}: {e}")
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
    current_section = {
        "section_title": "Introduction",
        "paragraphs": [],
        "images": []
    }

    # Find article content
    article_body = soup.find("div", class_="blog-detail-wrapper") if soup else None
    if not article_body:
        print("No article body found.")
        article_data["sections"] = []
        return article_data

    # Iterate through direct children of article
    for elem in article_body.find_all(["h2", "p", "img"], recursive=True):
        if elem.name == "h2":
            if current_section["paragraphs"] or current_section["images"]:
                sections.append(current_section)
            current_section = {
                "section_title": elem.text.strip(),
                "paragraphs": [],
                "images": []
            }
        elif elem.name == "p":
            current_section["paragraphs"].append(elem.text.strip())
        elif elem.name == "img":
            img_url = elem.get("src")
            current_section["images"].append(img_url)

    if current_section["paragraphs"] or current_section["images"]:
        sections.append(current_section)

    article_data["sections"] = sections
    return article_data

# --- Run for all URLs in the CSV and update 'checked' column ---
df = pd.read_csv(CSV_FILE)
for idx, row in df.iterrows():
    if not row.get('checked', False):
        url = row['url']
        soup = get_url(url)
        if soup:
            article_json = scrape_data(soup, url)
            # Save each article as a separate JSON file
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in row['title'])[:50]
            output_path = f'./data/processed/{safe_title}.json'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(article_json, f, ensure_ascii=False, indent=2)
            # Mark as checked
            df.at[idx, 'checked'] = True
        else:
            print(f"Failed to fetch the article: {url}")

df.to_csv(CSV_FILE, index=False)