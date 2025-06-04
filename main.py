from src.websites.google_ai_links_scraper import scrape_homepage
from src.websites.google_ai_article_scraper import scrape_articles_from_links
from src.image_downloader import batch_process_articles
from src.utils.logger import setup_logger
import streamlit as st
import pandas as pd

logger = setup_logger('main')

def count_new_articles():
    """Count how many new articles were added."""
    csv_path = './data/raw/google_ai_links.csv'
    try:
        df = pd.read_csv(csv_path)
        return len(df[~df.get('checked', False)])
    except Exception as e:
        logger.error(f"Error counting new articles: {e}")
        return 0

def scrape_and_process():
    """Run the scraping pipeline with detailed progress indicators."""
    try:
        with st.status("🔄 Starting scraping pipeline...") as status:
            progress_placeholder = st.empty()
            progress_bar = progress_placeholder.progress(0)
            
            def update_progress(progress, message):
                progress_bar.progress(int(progress * 100))
                status.write(message)
            
            # Step 1: Scrape homepage
            status.write("### 📡 Step 1/3: Scraping Google AI homepage...")
            initial_links = scrape_homepage()
            new_articles_count = count_new_articles()
            progress_bar.progress(33)
            
            # Step 2: Scrape articles with progress
            status.write("### 📑 Step 2/3: Downloading article content...")
            processed_count = scrape_articles_from_links(update_progress)
            
            progress_bar.progress(66)
            st.write("Step 2 completed: Articles downloaded")
            
            # Step 3: Download images (100% of total)
            status.write("### 🖼️ Step 3/3: Downloading images...")
            results = batch_process_articles()
            total_images = 0
            if results:
                total_images = sum(len(result.get('downloads', [])) for result in results if result)
                status.write(f"*Downloaded {total_images} images from {len(results)} articles*")
            progress_bar.progress(100)
            st.write("Step 3 completed: Images downloaded")
            
            # Final summary
            status.update(label="✅ Scraping completed!", state="complete")
            progress_placeholder.empty()  # Clear the progress bar when done
            
            return {
                'new_articles': new_articles_count,
                'processed_articles': processed_count,  # Use the actual count
                'images_downloaded': total_images
            }
            
    except Exception as e:
        logger.error(f"Error in scraping process: {str(e)}", exc_info=True)
        st.error("❌ Error during scraping. Check logs for details.")
        raise

def main():
    st.set_page_config(
        page_title="Google AI Article Viewer",
        page_icon="📚",
        layout="wide"
    )

    # Add scrape button in sidebar
    with st.sidebar:
        st.title("Actions")
        if st.button("🔄 Scrape New Articles"):
            try:
                results = scrape_and_process()
                if results:
                    st.success(
                        f"✨ Scraping completed successfully!\n\n"
                        f"Found {results['new_articles']} new articles\n"
                        f"Processed {results['processed_articles']} articles\n"
                        f"Downloaded {results['images_downloaded']} images"
                    )
            except Exception as e:
                st.error(f"Failed to complete scraping: {str(e)}")

    # Run the article viewer
    from src.app import run_streamlit_app
    run_streamlit_app()

if __name__ == "__main__":
    main()