import requests
from bs4 import BeautifulSoup
import os
import yaml
import pandas as pd

USER_AGENT = os.getenv("USER_AGENT")
HEADERS = {
    'User-Agent': USER_AGENT
}

def load_base_url():
    # Load the base URL from the YAML config file
    config_path = os.path.join("config", "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config.get('urls', [None])[0]

def get_url(base_url):
    # Fetch the HTML content of the base URL
    try:
        response = requests.get(base_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except requests.RequestException as e:
        print(f"Error fetching {base_url}: {e}")
        return None

def get_links(soup, base_url):
    # Extract titles and URLs from the soup object
    if not soup:
        print("No soup object provided.")
        return None

    raw_titles = []
    post_urls = []
    for card_div in soup.find_all('li', class_='glue-grid__col'):
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
            print("Missing title or link in a card.")
            
    if not raw_titles:
        print("No titles found in the provided URL.")
        return None    

    title_url_pairs = list(zip(raw_titles, post_urls))
    return title_url_pairs

csv_file = './data/raw/google_ai_links.csv'
base_url = load_base_url()
soup = get_url(base_url)
if soup:
    links = get_links(soup, base_url)
    if links:
        # Load existing data if file exists, otherwise create an empty DataFrame
        if os.path.exists(csv_file):
            existing_df = pd.read_csv(csv_file)
        else:
            existing_df = pd.DataFrame(columns=['title', 'url'])

        # Create new DataFrame from scraped data and add 'checked' column
        new_df = pd.DataFrame(links, columns=['title', 'url'])
        new_df['checked'] = False

        # Concatenate and drop duplicates
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=['title', 'url'], inplace=True)

        # Ensure 'checked' column exists and fill NaN with False
        if 'checked' not in combined_df.columns:
            combined_df['checked'] = False
        else:
            combined_df['checked'] = combined_df['checked'].fillna(False)

        # Save the updated DataFrame back to CSV
        combined_df.to_csv(csv_file, index=False)
    else:
        print("No links found.")