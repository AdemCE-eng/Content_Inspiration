from src.websites.google_ai_links_scraper import scrape_homepage
from src.websites.google_ai_article_scraper import scrape_articles_from_links

# This script orchestrates the scraping process for Google AI articles.
def main():
    # Step 1: scrape links from homepage and save them
    scrape_homepage()

    # Step 2: scrape full articles from the links CSV
    scrape_articles_from_links()

    print("Done! All articles have been scraped and saved as JSON.")

if __name__ == "__main__":
    main()
# This script orchestrates the scraping process for Google AI articles.