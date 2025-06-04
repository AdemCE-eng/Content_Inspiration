from src.websites.google_ai_links_scraper import scrape_homepage
from src.websites.google_ai_article_scraper import scrape_articles_from_links
from src.image_downloader import batch_process_articles
from src.utils.logger import setup_logger

logger = setup_logger('main')

# This script orchestrates the scraping process for Google AI articles.
def main():
    try:
        # Step 1: scrape links from homepage and save them
        logger.info("Starting homepage scraping...")
        scrape_homepage()
        logger.info("Homepage scraping completed")

        # Step 2: scrape full articles from the links CSV
        logger.info("Starting article scraping...")
        scrape_articles_from_links()
        logger.info("Article scraping completed")

        # Step 3: download images from the scraped articles
        logger.info("Starting image downloads...")
        results = batch_process_articles()
        logger.info(f"Downloaded images from {len(results)} articles")

    except Exception as e:
        logger.error(f"Fatal error in main execution: {str(e)}", exc_info=True)
        raise
    else:
        logger.info("All processing completed successfully")

if __name__ == "__main__":
    main()
# This script orchestrates the scraping process for Google AI articles.