import pandas as pd
import requests
from bs4 import BeautifulSoup
import os

CSV_FILE = '/data/raw/google_ai_links.csv'  
USER_AGENT = os.getenv("USER_AGENT")
header = {
    'User-Agent': USER_AGENT
}

def scrape_article(url):
    try:
        response = requests.get(url, headers=header)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        # Example: get the first paragraph
        paragraph = soup.find('p')
        return paragraph.text.strip() if paragraph else "No paragraph found."
    except Exception as e:
        return f"Error: {e}"

def main():
    df = pd.read_csv(CSV_FILE)
    for idx, row in df.iterrows():
        url = row['url']
        print(f"Scraping: {url}")
        content = scrape_article(url)
        print(f"First paragraph: {content}\n")

if __name__ == "__main__":
    main()