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

def load_read_status():
    """Load the read status of articles from a JSON file."""
    try:
        status_path = os.path.join('data', 'processed', 'read_status.json')
        with open(status_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_read_status(read_status):
    """Save the read status of articles to a JSON file."""
    status_dir = os.path.join('data', 'processed')
    os.makedirs(status_dir, exist_ok=True)
    status_path = os.path.join(status_dir, 'read_status.json')
    with open(status_path, 'w') as f:
        json.dump(read_status, f)

def run_streamlit_app():
    # Load articles and read status
    articles = load_articles()
    filtered_articles = articles.copy()

    # Initialize read status
    if 'read_articles' not in st.session_state:
        st.session_state.read_articles = load_read_status()

    # Check if we're viewing an article
    selected_indices = st.session_state.get('selected_articles', set())
    if selected_indices:
        # Display single article view
        if st.button("← Back to Articles"):
            st.session_state.selected_articles = set()
            st.rerun()
        
        for idx in selected_indices:
            article = filtered_articles[idx]
            display_article(article)
    else:
        # Display main articles list
        with st.sidebar:
            # Filters section
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

            # Search section - keeping this intact
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

            # Apply filters for search - keeping this intact
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

            # Results count
            st.markdown("---")
            st.info(f"Found {len(filtered_articles)} matching articles")

        # Main page content
        st.title("📚 Articles")
        
        # Create columns for the table header
        header_cols = st.columns([0.5, 0.2, 0.15, 0.15])
        header_cols[0].markdown("<div style='text-align: center;'><strong>Title</strong></div>", unsafe_allow_html=True)
        header_cols[1].markdown("<div style='text-align: center;'><strong>Date</strong></div>", unsafe_allow_html=True)
        header_cols[2].markdown("<div style='text-align: center;'><strong>Source</strong></div>", unsafe_allow_html=True)
        header_cols[3].markdown("<div style='text-align: center;'><strong>Read</strong></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Display articles in table format
        for idx, article in enumerate(filtered_articles):
            title = article.get('title', 'Untitled')
            date = article.get('published_date', 'No date')
            url = article.get('url', '')
            article_id = article.get('_file_path', str(idx))
            
            # Create columns for each article row with matching widths
            cols = st.columns([0.5, 0.2, 0.15, 0.15])
            
            # Title with click to select - using only Streamlit button
            title_display = f"{title[:50]}..." if len(title) > 50 else title
            if cols[0].button(title_display, key=f"btn_{idx}", use_container_width=True):
                if idx not in st.session_state.get('selected_articles', set()):
                    st.session_state.selected_articles = {idx}
                else:
                    st.session_state.selected_articles.remove(idx)
            
            # Date - centered
            cols[1].markdown(
                f"<div style='text-align: center;'>{date.split(' ')[0] if date else ''}</div>",
                unsafe_allow_html=True
            )
            
            # URL Button
            if url:
                cols[2].link_button("🔗Open", url, help="Open article source", use_container_width=True)
            
            # Read checkbox
            cols[3].markdown(
                """
                <style>
                /* Center the checkbox container */
                div[data-testid="stHorizontalBlock"] > div:nth-child(4) {
                    display: flex;
                    justify-content: center;
                }
                /* Center the checkbox itself */
                div[data-testid="stHorizontalBlock"] > div:nth-child(4) div[data-testid="stCheckbox"] {
                    display: flex;
                    justify-content: center;
                    width: 100%;
                }
                </style>
                """, 
                unsafe_allow_html=True
            )
            read_state = st.session_state.read_articles.get(article_id, False)
            if cols[3].checkbox("", value=read_state, key=f"read_{idx}", help="Mark as read", label_visibility="collapsed"):
                st.session_state.read_articles[article_id] = True
            else:
                st.session_state.read_articles[article_id] = False

    # Save read status at the end
    save_read_status(st.session_state.read_articles)

