import streamlit as st
import json
import os
from PIL import Image
from datetime import datetime
import os
from src.utils.config import get_config

config = get_config()

def load_articles():
    """Load all article JSON files."""
    articles_dir = config['data_dir']
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

def get_local_image_path(article_index, section_id):
    """Get all image paths for a section."""
    if not article_index:
        return []
    
    base_path = os.path.join(config.get('images_dir', 'images'), f'article_{article_index.strip()}')
    found_images = []
    
    # Expanded patterns to catch more image variations
    base_patterns = [
        # Standard patterns
        f'image_{section_id}.jpg',
        f'image_{section_id}.png',
        f'image_{section_id}.jpeg',
        # Number after section
        f'image_{section_id}_1.jpg',
        f'image_{section_id}_2.jpg',
        f'image_{section_id}_3.jpg',
        f'image_{section_id}_4.jpg',
        # Number with dot separator
        f'image_{section_id}.1.jpg',
        f'image_{section_id}.2.jpg',
        f'image_{section_id}.3.jpg',
        f'image_{section_id}.4.jpg'
    ]
    
    # Add PNG and JPEG variations
    all_patterns = []
    for pattern in base_patterns:
        all_patterns.append(pattern)
        all_patterns.append(pattern.replace('.jpg', '.png'))
        all_patterns.append(pattern.replace('.jpg', '.jpeg'))
    
    # Check all patterns
    for pattern in all_patterns:
        path = os.path.join(base_path, pattern)
        if os.path.exists(path):
            found_images.append(path)
            print(f"Found image: {path}")
        
    # Sort found images to ensure consistent order
    found_images.sort()
    
    if not found_images:
        print(f"No images found for article {article_index} section {section_id}")
    else:
        print(f"Found {len(found_images)} images for article {article_index} section {section_id}")
    
    return found_images
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
    """Display an article with its summaries and images."""
    st.title(article.get('title', ''))
    
    if article.get('published_date'):
        st.caption(f"{article['published_date']} - {article['author']}")
    
    if article.get('url'):
        st.markdown(f"[Original Article]({article['url']})")
    
    st.markdown("---")
    
    # Get article index from file path
    file_path = article.get('_file_path', '')
    article_index = os.path.basename(file_path).split('_')[0]
    
    for section_idx, section in enumerate(article.get('sections', [])):
        if section.get('section_title'):
            st.subheader(section['section_title'])
        
        # Get and display all images for this section
        image_paths = get_local_image_path(article_index, section_idx + 1)
        if image_paths:
            num_images = len(image_paths)
            if num_images > 1:
                cols = st.columns(min(num_images, 2))
            
            for idx, img_path in enumerate(image_paths):
                try:
                    image = Image.open(img_path)
                    width, height = image.size
                    max_width = 800
                    if width > max_width:
                        ratio = max_width / width
                        new_size = (int(width * ratio), int(height * ratio))
                        image = image.resize(new_size, Image.Resampling.LANCZOS)
                    
                    if num_images > 1:
                        col_idx = idx % 2
                        cols[col_idx].image( # type: ignore
                            image, 
                            use_container_width=True,
                            output_format="PNG"
                        )
                    else:
                        col1, col2, col3 = st.columns([1, 3, 1])
                        with col2:
                            st.image(
                                image, 
                                use_container_width=True,
                                output_format="PNG"
                            )
                            
                except Exception as e:
                    st.error(f"Error loading image {img_path}: {e}")
        
        # Display paragraphs
        for paragraph in section.get('paragraphs', []):
            if isinstance(paragraph, dict) and 'summary' in paragraph:
                st.write(paragraph['summary'])
            else:
                st.write(paragraph)

def load_read_status():
    """Load the read status of articles from a JSON file."""
    try:
        status_path = os.path.join(os.path.dirname(config['data_dir']), 'read_status.json')
        with open(status_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_read_status(read_status):
    """Save the read status of articles to a JSON file."""
    status_dir = os.path.dirname(config['data_dir'])
    os.makedirs(status_dir, exist_ok=True)
    status_path = os.path.join(status_dir, 'read_status.json')
    with open(status_path, 'w') as f:
        json.dump(read_status, f)

def run_streamlit_app():
    # Load articles and read status
    articles = load_articles()
    
    # Sort articles by date (newest first)
    filtered_articles = sorted(
        articles,
        key=lambda x: parse_date(x.get('published_date', '')),
        reverse=True  # Newest first
    )

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
            
        # Pagination setup with basic validation of YAML config
        articles_per_page = config.get('articles_per_page')
        if not isinstance(articles_per_page, int) or articles_per_page <= 0:
            st.warning("Invalid articles_per_page in config; using default of 10.")
            articles_per_page = 10

        total_pages = max((len(filtered_articles) - 1) // articles_per_page + 1, 1)
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        current_page = min(max(st.session_state.current_page, 1), total_pages)

        start_idx = (current_page - 1) * articles_per_page
        end_idx = start_idx + articles_per_page
        page_articles = filtered_articles[start_idx:end_idx]
        
        # Main page content
        st.markdown("""
            <div style='display: flex; align-items: center; justify-content: center; margin-bottom: 2rem;'>
                <h1 style='margin: 0;'>📚Articles</h1>
            </div>
        """, unsafe_allow_html=True)
        
        # Create columns for the table header
        header_cols = st.columns([0.5, 0.2, 0.15, 0.15])
        header_cols[0].markdown("<div style='text-align: center;'><strong>Title</strong></div>", unsafe_allow_html=True)
        header_cols[1].markdown("<div style='text-align: center;'><strong>Date</strong></div>", unsafe_allow_html=True)
        header_cols[2].markdown("<div style='text-align: center;'><strong>Source</strong></div>", unsafe_allow_html=True)
        header_cols[3].markdown("<div style='text-align: center;'><strong>Read</strong></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Display articles in table format
        for relative_idx, article in enumerate(page_articles):
            idx = start_idx + relative_idx
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
        # Navigation bar at the bottom
        nav_cols = st.columns([1, 1, 1])
        with nav_cols[0]:
            if st.button("⬅️ Previous", disabled=current_page <= 1, key="prev_page_bottom"):
                st.session_state.current_page -= 1
                st.rerun()
        nav_cols[1].markdown(
            f"<div style='text-align: center;'>Page {current_page} of {total_pages}</div>",
            unsafe_allow_html=True
        )
        with nav_cols[2]:
            if st.button("Next ➡️", disabled=current_page >= total_pages, key="next_page_bottom"):
                st.session_state.current_page += 1
                st.rerun()
    # Save read status at the end
    save_read_status(st.session_state.read_articles)

