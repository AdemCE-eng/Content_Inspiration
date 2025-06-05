import streamlit as st
import json
import os
from PIL import Image
from datetime import datetime
import os

def load_articles():
    """Load all article JSON files."""
    articles_dir = './data/processed/google_articles'
    articles = []
    try:
        for filename in os.listdir(articles_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(articles_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    article = json.load(f)
                    article['_file_path'] = file_path  # Add file path to article data
                    articles.append(article)
    except Exception as e:
        st.error(f"Error loading articles: {str(e)}")
    return articles

def get_local_image_path(article_index, section_id, image_index=1):
    """Get the path to the locally saved image."""
    # Ensure article_index is not empty
    if not article_index:
        return None
        
    return os.path.join(
        'images', 
        f'article_{article_index.strip()}',
        f'image_{section_id}{"."+str(image_index) if image_index > 1 else ""}.jpg'
    )
from datetime import datetime

def parse_date(date_str):
    """Parse date string to datetime object."""
    if not date_str:
        return datetime.min
    try:
        # Try different date formats
        for fmt in ['%B %d, %Y', '%Y-%m-%d', '%d/%m/%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return datetime.min
    except (ValueError, TypeError):
        return datetime.min
    
def display_article(article):
    """Display a single article with its content."""
    try:
        # Get article index from the article data
        article_path = article.get('_file_path', '')
        if article_path:
            article_index = os.path.basename(article_path).split('_')[0]
        else:
            # Fallback: try to get index from title
            article_index = ''.join(filter(str.isdigit, article.get('title', '')))[:2]  # Take first 2 digits only
        
        if not article_index:
            st.error("Could not determine article index")
            return
            
    except Exception as e:
        st.error(f"Error extracting article index: {str(e)}")
        return

    st.title(article.get('title', 'No Title'))
    
    # Display metadata if available
    col1, col2 = st.columns(2)
    with col1:
        if article.get('published_date'):
            st.text(f"Published: {article['published_date']}")
    with col2:
        if article.get('author'):
            st.text(f"Author: {article['author']}")
    
    # Display sections
    for section in article.get('sections', []):
        # Use different heading styles based on section_level
        if section.get('section_level', 2) == 2:
            st.header(section.get('section_title', 'Untitled Section'))
        else:
            st.subheader(section.get('section_title', 'Untitled Section'))
        
        # Display paragraphs
        for paragraph in section.get('paragraphs', []):
            st.write(paragraph)
        
        # Display images from local storage
        if section.get('images'):
            section_id = section.get('section_id')
            cols = st.columns(min(len(section['images']), 3))
            for idx, col in enumerate(cols, 1):
                img_path = get_local_image_path(article_index, section_id, idx)
                try:
                    if img_path and os.path.exists(img_path):
                        img = Image.open(img_path)
                        col.image(img, caption=f"Image {idx}", use_column_width=True)
                    else:
                        col.warning(f"Image not found locally: {img_path}")
                except Exception as e:
                    col.error(f"Error loading image: {str(e)}")

def run_streamlit_app():
    # Load articles
    articles = load_articles()
    filtered_articles = articles.copy()
    
    with st.sidebar:
        # 1. Filters section
        st.subheader("⚙️ Filters")
        
        # Sort options
        sort_method = st.selectbox(
            "Sort by",
            ["Date (Newest First)", "Date (Oldest First)", "Title (A-Z)", "Title (Z-A)"]
        )

        # Date range filter
        dates = [
            parse_date(article.get('published_date'))
            for article in articles 
            if article.get('published_date')
        ]
        dates = sorted([d for d in dates if d != datetime.min])
        
        if dates:
            # Convert datetime objects to strings for display
            date_strings = [d.strftime('%B %d, %Y') for d in dates]
            date_range = st.select_slider(
                "Date Range",
                options=date_strings,
                value=(date_strings[0], date_strings[-1])
            )
            
            # Convert selected strings back to datetime for filtering
            start_date = datetime.strptime(date_range[0], '%B %d, %Y')
            end_date = datetime.strptime(date_range[1], '%B %d, %Y')
            
            # Apply date filter
            filtered_articles = [
                article for article in filtered_articles 
                if start_date <= parse_date(article.get('published_date', '')) <= end_date
            ]

        # 2. Search section
        st.markdown("---")
        st.subheader("🔍 Search")
        search_title = st.text_input("Search in Title", key="search_title")
        search_content = st.text_input("Search in Content", key="search_content")

        # Add a small delay to prevent too frequent updates
        if st.session_state.get('search_title', '') != search_title:
            st.session_state.search_title = search_title
            st.rerun()
        
        if st.session_state.get('search_content', '') != search_content:
            st.session_state.search_content = search_content
            st.rerun()

        # Apply filters for search
        if search_title:
            filtered_articles = [
                article for article in filtered_articles 
                if any(
                    search_title.lower() in title.lower()
                    for title in [
                        article.get('title', ''),
                        *[section.get('section_title', '') for section in article.get('sections', [])]
                    ]
                )
            ]

        if search_content:
            filtered_articles = [
                article for article in filtered_articles 
                if any(
                    search_content.lower() in text.lower()
                    for section in article.get('sections', [])
                    for text in section.get('paragraphs', [])
                )
            ]

        # Apply sorting
        if filtered_articles:
            if sort_method == "Date (Newest First)":
                filtered_articles.sort(
                    key=lambda x: parse_date(x.get('published_date')),
                    reverse=True
                )
            elif sort_method == "Date (Oldest First)":
                filtered_articles.sort(
                    key=lambda x: parse_date(x.get('published_date'))
                )
            elif sort_method == "Title (A-Z)":
                filtered_articles.sort(key=lambda x: x.get('title', '').lower())
            elif sort_method == "Title (Z-A)":
                filtered_articles.sort(key=lambda x: x.get('title', '').lower(), reverse=True)

        # 3. Results count
        st.markdown("---")
        st.info(f"Found {len(filtered_articles)} matching articles")

        # 4. Clear filters button
        if st.button("Clear Filters"):
            st.rerun()

        # 5. Article selection (only the selection part stays in sidebar)
        st.markdown("---")
        selected_indices = []  # Initialize as empty list
        article_titles = []  # Initialize as empty list
        if filtered_articles:
            article_titles = [article.get('title', 'Untitled') for article in filtered_articles]
            selected_indices = st.multiselect(
                "Select articles to view:",
                range(len(article_titles)),
                format_func=lambda x: article_titles[x]
            )

    # Move article display outside sidebar (in main area)
    if not filtered_articles:
        st.warning("No articles match your current filters.")
    elif not selected_indices:
        st.info("Please select one or more articles from the sidebar.")
    else:
        # Display selected articles in main content area
        for idx in selected_indices:
            with st.expander(article_titles[idx], expanded=True):
                display_article(filtered_articles[idx])
            st.markdown("---")

