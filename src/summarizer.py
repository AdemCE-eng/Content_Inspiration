import json
import os
from typing import Dict
import requests
from src.utils.logger import setup_logger
from src.utils.config import get_config

logger = setup_logger('summarizer')
config = get_config()

class ArticleSummarizer:
    def __init__(self, model: str | None = None):
        self.model = model or config.get('ollama', {}).get('model', 'mistral')
        base_url = config.get('ollama', {}).get('base_url', 'http://localhost:11434')
        self.timeout = config.get('ollama', {}).get('timeout', 60)
        self.api_url = f"{base_url.rstrip('/')}/api/generate"
        
        # Test connection and provide clear error message
        try:
            response = requests.post(
                self.api_url,
                json={"model": self.model, "prompt": "test"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(f"Successfully connected to Ollama using {self.model} model")
        except requests.exceptions.ConnectionError:
            error_msg = (
                "Could not connect to Ollama. Please ensure:\n"
                "1. Ollama is installed (https://ollama.ai)\n"
                "2. Ollama service is running (run 'ollama serve' in terminal)\n"
                "3. Mistral model is pulled (run 'ollama pull mistral')"
            )
            logger.error(error_msg)
            raise ConnectionError(error_msg)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                error_msg = (
                    f"Model '{self.model}' not found. Please run:\n"
                    f"ollama pull {self.model}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            raise

    def summarize_paragraph(self, paragraph: str) -> str:
        """Generate a summary for a single paragraph using local Ollama model."""
        prompt = f"Summarize this paragraph concisely in 1-2 sentences:\n\n{paragraph}"
        
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()['response'].strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return "Error generating summary"

    def process_article(self, article_path: str) -> Dict:
        """Process a single article JSON file and generate summaries."""
        try:
            # Load article
            with open(article_path, 'r', encoding='utf-8') as f:
                article = json.load(f)
            
            summarized_article = {
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'published_date': article.get('published_date', ''),
                'sections': []
            }
            
            # Process each section
            for section in article.get('sections', []):
                summarized_section = {
                    'section_title': section.get('section_title', ''),
                    'paragraphs': []
                }
                
                # Process each paragraph
                for paragraph in section.get('paragraphs', []):
                    if paragraph.strip():
                        summary = self.summarize_paragraph(paragraph)
                        logger.debug(f"Generated summary for paragraph: {summary[:100]}...")
                        
                        summarized_section['paragraphs'].append({
                            'original': paragraph,
                            'summary': summary
                        })
                
                summarized_article['sections'].append(summarized_section)
            
            return summarized_article
            
        except Exception as e:
            logger.error(f"Error processing article {article_path}: {str(e)}")
            return {}

def needs_summarization(article):
    """Check if article needs to be summarized."""
    for section in article.get('sections', []):
        for paragraph in section.get('paragraphs', []):
            if isinstance(paragraph, str):
                return True
            if isinstance(paragraph, dict) and 'summary' not in paragraph:
                return True
    return False

def batch_process_articles(articles_dir: str | None = None):
    """Process articles and add summaries only to those that need it."""
    if articles_dir is None:
        articles_dir = config['data_dir']
    summarizer = ArticleSummarizer()
    processed_count = 0
    skipped_count = 0
    
    for filename in os.listdir(articles_dir):
        if not filename.endswith('.json'):
            continue
            
        file_path = os.path.join(articles_dir, filename) # type: ignore
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                article = json.load(f)
            
            # Skip if already summarized
            if not needs_summarization(article):
                logger.info(f"Skipping already summarized article: {filename}")
                skipped_count += 1
                continue
                
            logger.info(f"Summarizing article: {filename}")
            
            # Process each section's paragraphs
            for section in article.get('sections', []):
                summarized_paragraphs = []
                for paragraph in section.get('paragraphs', []):
                    if isinstance(paragraph, str):
                        summary = summarizer.summarize_paragraph(paragraph)
                        summarized_paragraphs.append({
                            'original': paragraph,
                            'summary': summary
                        })
                    else:
                        # Keep existing paragraph structure
                        summarized_paragraphs.append(paragraph)
                section['paragraphs'] = summarized_paragraphs
            
            # Save back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(article, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Successfully summarized {filename}")
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
    
    return {
        'processed': processed_count,
        'skipped': skipped_count
    }