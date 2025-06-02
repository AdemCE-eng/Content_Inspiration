import requests
from bs4 import BeautifulSoup
import os

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
def get_links(soup):
    titles = []
    if soup:
        for div in soup.find_all('div', attrs={'class': 'glue-card__inner'}):
            title = div.find('span', attrs={'class': 'headline-5'})
            if title:
                clean_title = title.text.strip().replace(':', '').replace('/', '').replace(' ', '-').lower()
                titles.append(clean_title)
    links = []
    for link in titles:
        links.append(f'https://research.google/blog/{link}/')
    if not links:
        print("No titles found in the provided URL.")
        return None
    return links
url = get_url('https://research.google/blog/')
if url:
    titles = get_links(url)
    if titles:
        print("Titles found:")
        for title in titles:
            print(title)
    else:
        print("No titles found.")