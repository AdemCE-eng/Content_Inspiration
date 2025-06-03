import requests
from bs4 import BeautifulSoup
import os
import yaml

USER_AGENT = os.getenv("USER_AGENT")
header = {
    'User-Agent': f'{USER_AGENT}'
    }

def get_url(url):
    try:
        response = requests.get(url, headers=header)
        response.raise_for_status() # Check for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
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
