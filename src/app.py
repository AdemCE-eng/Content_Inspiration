import streamlit as st
import json
import os
from PIL import Image
from datetime import datetime
from urllib.parse import urlparse
from src.utils.config import get_config
from src.utils.pdf_exporter import MultiArticlePDFExporter
import tempfile

config = get_config()

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

h1, h2, h3 {
    font-family: 'Source Serif 4', Georgia, serif !important;
    letter-spacing: -0.01em;
}

/* Masthead */
.masthead {
    text-align: center;
    padding: 0.5rem 0 1.25rem 0;
    border-bottom: 3px double #171717;
    margin-bottom: 1.5rem;
}
.masthead h1 {
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 2.4rem;
    font-weight: 700;
    margin: 0;
    color: #171717;
}
.masthead p {
    margin: 0.35rem 0 0 0;
    color: #6b6b6b;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
}

/* Article title buttons (tertiary) read like editorial headlines */
button[kind="tertiary"] {
    font-family: 'Source Serif 4', Georgia, serif !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    color: #171717 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    white-space: normal !important;
    padding: 0 !important;
    min-height: 0 !important;
    transition: color 150ms ease;
}
button[kind="tertiary"]:hover {
    color: #A16207 !important;
}
button[kind="tertiary"] p {
    font-family: 'Source Serif 4', Georgia, serif !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    text-align: left;
    color: inherit;
}

/* Source link button: keep label on one line */
a[data-testid="stBaseLinkButton-secondary"] p {
    white-space: nowrap !important;
}

/* Read toggle: keep its label on one line */
div[data-testid="stCheckbox"] label p {
    white-space: nowrap !important;
    flex-shrink: 0 !important;
}

/* Article cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    transition: border-color 150ms ease, box-shadow 150ms ease;
    border-radius: 10px;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #D4AF37;
    box-shadow: 0 2px 12px rgba(23, 23, 23, 0.07);
}

/* Reader typography */
.article-meta {
    color: #6b6b6b;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.25rem;
}
[data-testid="stAppViewContainer"] .stMarkdown p {
    line-height: 1.7;
}

/* Unread marker */
.unread-dot {
    color: #A16207;
    font-weight: 600;
}
</style>
"""


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

    # Sort found images to ensure consistent order
    found_images.sort()
    return found_images


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


def get_source_name(url):
    """Derive a readable publisher name from an article URL."""
    if not url:
        return ''
    lowered = url.lower()
    if 'research.google' in lowered or 'googleblog' in lowered:
        return 'Google Research'
    if 'nvidia.com' in lowered:
        return 'NVIDIA'
    try:
        domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
        return domain.capitalize()
    except Exception:
        return ''


def display_article(article):
    """Display an article with its summaries and images."""
    meta_parts = [
        get_source_name(article.get('url', '')),
        article.get('published_date', ''),
        article.get('author', ''),
    ]
    meta_line = ' &nbsp;·&nbsp; '.join(part for part in meta_parts if part)
    if meta_line:
        st.markdown(f"<div class='article-meta'>{meta_line}</div>", unsafe_allow_html=True)

    st.title(article.get('title', ''))

    if article.get('url'):
        st.markdown(f"[Read the original article]({article['url']})")

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
                        cols[col_idx].image(  # type: ignore
                            image,
                            use_container_width=True,
                            output_format="PNG"
                        )
                    else:
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


def create_export_section(filtered_articles):
    """Create the export section in the sidebar."""
    with st.expander("Export to PDF", icon=":material/picture_as_pdf:"):
        st.caption("Select articles to export")

        # Initialize export selection
        if 'export_selection' not in st.session_state:
            st.session_state.export_selection = set()

        # Select all/none buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select all", use_container_width=True):
                st.session_state.export_selection = set(range(len(filtered_articles)))
                st.rerun()
        with col2:
            if st.button("Clear", use_container_width=True):
                st.session_state.export_selection = set()
                st.rerun()

        # Article selection checkboxes
        for idx, article in enumerate(filtered_articles):
            title = article.get('title', f'Article {idx}')
            display_title = title[:50] + ('...' if len(title) > 50 else '')

            if st.checkbox(
                display_title,
                key=f"export_{idx}",
                value=idx in st.session_state.export_selection
            ):
                st.session_state.export_selection.add(idx)
            else:
                st.session_state.export_selection.discard(idx)

        # Export button
        if st.session_state.export_selection:
            st.caption(f"{len(st.session_state.export_selection)} selected")

            if st.button("Export PDF", type="primary", icon=":material/download:", use_container_width=True):
                export_selected_articles(filtered_articles)


def export_selected_articles(filtered_articles):
    """Export selected articles to PDF."""
    try:
        selected_indices = st.session_state.export_selection
        selected_articles = [filtered_articles[idx] for idx in selected_indices]

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            temp_path = tmp_file.name

        # Export to PDF
        with st.spinner('Generating PDF...'):
            exporter = MultiArticlePDFExporter()
            success = exporter.export_articles_to_pdf(selected_articles, temp_path)

        if success:
            # Read the PDF file
            with open(temp_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Extract publishers from selected articles
            publishers = {
                get_source_name(article.get('url', '')).replace(' ', '_')
                for article in selected_articles
                if article.get('url')
            }
            publishers.discard('')

            # Create filename based on publishers
            if len(publishers) == 1:
                publisher_name = list(publishers)[0]
                filename = f"content_inspiration_{publisher_name}_{timestamp}.pdf"
            else:
                filename = f"content_inspiration_articles_{timestamp}.pdf"

            # Provide download button
            st.download_button(
                label="Download PDF",
                data=pdf_data,
                file_name=filename,
                mime="application/pdf",
                icon=":material/download:",
                use_container_width=True
            )

            st.success(f"Exported {len(selected_articles)} articles.")

            # Clean up temp file
            os.unlink(temp_path)
        else:
            st.error("Failed to export articles. Check logs for details.")

    except Exception as e:
        st.error(f"Export error: {str(e)}")


def render_sidebar(articles, filtered_articles):
    """Render filters and search in the sidebar; return the filtered list."""
    with st.sidebar:
        st.subheader("Filters")

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
                "Date range",
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

        search_title = st.text_input(
            "Search in title", key="search_title",
            placeholder="e.g. Gemini", icon=":material/search:"
        )
        search_content = st.text_input(
            "Search in content", key="search_content",
            placeholder="e.g. reinforcement learning", icon=":material/manage_search:"
        )

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

        st.caption(f"{len(filtered_articles)} matching articles")
        st.divider()
        create_export_section(filtered_articles)

    return filtered_articles


def render_article_card(article, idx):
    """Render one article as a card in the library list."""
    title = article.get('title', 'Untitled')
    date = article.get('published_date', '')
    url = article.get('url', '')
    article_id = article.get('_file_path', str(idx))
    is_read = st.session_state.read_articles.get(article_id, False)

    with st.container(border=True):
        cols = st.columns([0.56, 0.2, 0.24], vertical_alignment="center")

        with cols[0]:
            if st.button(title, key=f"btn_{idx}", type="tertiary"):
                st.session_state.selected_articles = {idx}
                st.rerun()
            source = get_source_name(url)
            meta_parts = [p for p in (source, date) if p]
            if not is_read:
                meta_parts.append(":orange[Unread]")
            st.caption("  ·  ".join(meta_parts))

        with cols[1]:
            if url:
                st.link_button(
                    "Source", url,
                    icon=":material/open_in_new:",
                    help="Open the original article",
                    use_container_width=True
                )

        with cols[2]:
            read_state = st.toggle("Read", value=is_read, key=f"read_{idx}", help="Mark as read")
            st.session_state.read_articles[article_id] = read_state


def run_streamlit_app():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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
        if st.button("Back to library", icon=":material/arrow_back:", type="tertiary"):
            st.session_state.selected_articles = set()
            st.rerun()

        for idx in selected_indices:
            article = filtered_articles[idx]
            display_article(article)
    else:
        filtered_articles = render_sidebar(articles, filtered_articles)

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

        # Masthead
        st.markdown(
            """
            <div class="masthead">
                <h1>Content Inspiration</h1>
                <p>Curated AI research, summarized</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if not page_articles:
            st.info("No articles match the current filters. Try widening the date range or clearing the search.")

        # Article cards
        for relative_idx, article in enumerate(page_articles):
            render_article_card(article, start_idx + relative_idx)

        # Pagination
        if total_pages > 1:
            nav_cols = st.columns([1, 2, 1], vertical_alignment="center")
            with nav_cols[0]:
                if st.button("Previous", icon=":material/chevron_left:",
                             disabled=current_page <= 1, key="prev_page_bottom"):
                    st.session_state.current_page = current_page - 1
                    st.rerun()
            nav_cols[1].markdown(
                f"<div style='text-align: center; color: #6b6b6b;'>Page {current_page} of {total_pages}</div>",
                unsafe_allow_html=True
            )
            with nav_cols[2]:
                if st.button("Next", icon=":material/chevron_right:",
                             disabled=current_page >= total_pages, key="next_page_bottom"):
                    st.session_state.current_page = current_page + 1
                    st.rerun()

    # Save read status at the end
    save_read_status(st.session_state.read_articles)
