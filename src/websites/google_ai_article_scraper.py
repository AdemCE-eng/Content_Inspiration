import pandas as pd
import requests
from bs4 import BeautifulSoup
import os

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
        return f"Error: {e}"
