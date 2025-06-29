from fpdf import FPDF
import os
from datetime import datetime
from urllib.parse import urlparse
from src.utils.logger import setup_logger

logger = setup_logger('pdf_exporter')

class MultiArticlePDFExporter:
    def __init__(self):
        self.pdf = None
    
    def export_articles_to_pdf(self, articles, output_path):
        """Export multiple articles to a single PDF using fpdf2."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            self.pdf = FPDF()
            self.pdf.set_auto_page_break(auto=True, margin=15)
            
            # Add cover page
            self._create_cover_page(len(articles))
            
            # Add each article
            for idx, article in enumerate(articles):
                self.pdf.add_page()
                self._create_article_content(article)
            
            # Save PDF
            self.pdf.output(output_path)
            logger.info(f"Successfully exported {len(articles)} articles to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting articles to PDF: {str(e)}")
            return False
    
    def _create_cover_page(self, article_count):
        """Create a cover page for the PDF."""
        if self.pdf is None:
            return
            
        self.pdf.add_page()
        
        self.pdf.set_font('Arial', 'B', 24)
        self.pdf.cell(0, 20, 'Content Inspiration', 0, 1, 'C')
        
        self.pdf.set_font('Arial', '', 16)
        self.pdf.cell(0, 15, f'Collection of {article_count} Articles', 0, 1, 'C')
        
        self.pdf.set_font('Arial', '', 12)
        export_date = datetime.now().strftime('%B %d, %Y')
        self.pdf.cell(0, 10, f'Exported on: {export_date}', 0, 1, 'C')
    
    def _create_article_content(self, article):
        """Create content for a single article."""
        if self.pdf is None:
            return
            
        # Article title
        self.pdf.set_font('Arial', 'B', 16)
        title = self._clean_text(article.get('title', 'Untitled Article'))
        self.pdf.multi_cell(0, 10, title)
        self.pdf.ln(3)
        
        # Article metadata (date, author, publisher)
        metadata_parts = []
        
        if article.get('published_date'):
            metadata_parts.append(f"Date: {article['published_date']}")
        
        if article.get('author'):
            metadata_parts.append(f"Author: {article['author']}")
        
        # Extract publisher from URL
        publisher = self._extract_publisher(article.get('url', ''))
        if publisher:
            metadata_parts.append(f"Publisher: {publisher}")
        
        if metadata_parts:
            self.pdf.set_font('Arial', '', 10)
            metadata_text = ' | '.join(metadata_parts)
            self.pdf.multi_cell(0, 6, self._clean_text(metadata_text))
            self.pdf.ln(5)
        
        # Article sections
        for section in article.get('sections', []):
            if section.get('section_title'):
                self.pdf.set_font('Arial', 'B', 14)
                section_title = self._clean_text(section['section_title'])
                self.pdf.multi_cell(0, 8, section_title)
                self.pdf.ln(3)
            
            self.pdf.set_font('Arial', '', 11)
            for paragraph in section.get('paragraphs', []):
                if isinstance(paragraph, dict):
                    text = paragraph.get('summary', paragraph.get('original', ''))
                else:
                    text = str(paragraph)
                
                if text.strip():
                    text = self._clean_text(text)
                    self.pdf.multi_cell(0, 6, text)
                    self.pdf.ln(3)
    
    def _extract_publisher(self, url):
        """Extract publisher name from URL."""
        if not url:
            return None
        
        url = url.lower()
        
        # Map of URL patterns to publisher names
        publisher_patterns = {
            'research.google': 'Google Research',
            'blog.google': 'Google',
            'nvidia.com': 'NVIDIA',
            'openai.com': 'OpenAI',
            'anthropic.com': 'Anthropic',
            'microsoft.com': 'Microsoft',
            'meta.com': 'Meta',
            'github.com': 'GitHub',
            'arxiv.org': 'arXiv',
            'ieee.org': 'IEEE',
            'acm.org': 'ACM'
        }
        
        for pattern, publisher in publisher_patterns.items():
            if pattern in url:
                return publisher
        
        # If no pattern matches, try to extract domain
        try:
            domain = urlparse(url).netloc
            if domain:
                # Remove 'www.' prefix and get the main domain
                domain = domain.replace('www.', '')
                # Capitalize first letter
                return domain.split('.')[0].capitalize()
        except:
            pass
        
        return None
    
    def _clean_text(self, text):
        """Clean text for PDF compatibility."""
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('—', '-').replace('–', '-')
        try:
            text = text.encode('latin-1', 'replace').decode('latin-1')
        except:
            text = text.encode('ascii', 'ignore').decode('ascii')
        return text