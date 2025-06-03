import requests
from bs4 import BeautifulSoup
import os
import yaml
import pandas as pd

USER_AGENT = os.getenv("USER_AGENT")
header = {
    'User-Agent': USER_AGENT
}

def load_base_url():
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config.get('urls', [None])[0]


def get_url(base_url):
    try:
        response = requests.get(base_url, headers=header)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except requests.RequestException as e:
        print(f"Error fetching {base_url}: {e}")
        return None

def get_links(soup, base_url):
    if not soup:
        print("No soup object provided.")
        return None

    raw_titles = []
    for card_div in soup.find_all('div', attrs={'class': 'glue-card__inner'}):
        title_span = card_div.find('span', attrs={'class': 'headline-5'})
        if title_span:
            raw_title = title_span.text.strip()
            raw_titles.append(raw_title)

    if not raw_titles:
        print("No titles found in the provided URL.")
        return None

    post_urls = [
        f'{base_url}{raw_title.replace("multimodel", "multi-model").replace(":", "").replace("/", "").replace(" ", "-").lower()}/'
        for raw_title in raw_titles
    ]

    title_url_pairs = list(zip(raw_titles, post_urls))
    return title_url_pairs

csv_file = './data/raw/google_ai_links.csv'
base_url = load_base_url()
soup = get_url(base_url)
if soup:
    links = get_links(soup, base_url)
    if links:
        # Load existing data if file exists
        if os.path.exists(csv_file):
            existing_df = pd.read_csv(csv_file)
        else:
            existing_df = pd.DataFrame(columns=['title', 'url'])

        # Create new DataFrame from scraped data
        new_df = pd.DataFrame(links, columns=['title', 'url'])

        # Concatenate and drop duplicates
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=['title', 'url'], inplace=True)

        # Save back to CSV (overwrite)
        combined_df.to_csv(csv_file, index=False)
    else:
        print("No links found.")