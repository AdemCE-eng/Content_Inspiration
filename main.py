from src.websites.google_ai_links_scraper import scrape_homepage
from src.websites.google_ai_article_scraper import scrape_articles_from_links
from src.image_downloader import batch_process_articles
from src.summarizer import batch_process_articles as summarize_articles
from src.utils.logger import setup_logger
import streamlit as st
import pandas as pd

logger = setup_logger('main')

def count_new_articles():
    """Count how many new articles were added."""
    csv_path = './data/raw/google_ai_links.csv'
    try:
        df = pd.read_csv(csv_path)
        if 'checked' not in df.columns:
            # If the column is missing, treat all rows as unchecked
            return len(df)
        
        # Ensure boolean dtype and count entries that are not checked
        unchecked = ~df['checked'].fillna(False).astype(bool)
        return int(unchecked.sum())
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
            status.write("### 📡 Step 1/4: Scraping Google AI homepage...")
            initial_links = scrape_homepage()
            progress_bar.progress(25)
            
            # Step 2: Scrape articles
            status.write("### 📑 Step 2/4: Downloading article content...")
            processed_count = scrape_articles_from_links(update_progress)
            progress_bar.progress(50)
            
            # Step 3: Download images
            status.write("### 🖼️ Step 3/4: Downloading images...")
            results = batch_process_articles()
            progress_bar.progress(75)
            
            # Step 4: Generate summaries with Ollama
            status.write("### 📝 Step 4/4: Generating summaries...")
            summary_results = summarize_articles()
            progress_bar.progress(100)
            
            # Final summary
            status.update(
                label=(f"✅ Done!"),
                state="complete"
            )
            progress_placeholder.empty()
            
            return {
                'new_articles': len(initial_links or []),
                'processed_articles': processed_count,
                'images_downloaded': sum(r.get('new_downloads', 0) for r in results if r),
                'summaries_generated': summary_results['processed']
            }
            
    except Exception as e:
        logger.error(f"Error in scraping process: {str(e)}", exc_info=True)
        st.error("❌ Error during scraping. Check logs for details.")
        return None

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
                    )
            except Exception as e:
                st.error(f"Failed to complete scraping: {str(e)}")

    # Run the article viewer
    from src.app import run_streamlit_app
    run_streamlit_app()

if __name__ == "__main__":
    main()