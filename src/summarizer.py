import json
import os
from typing import Dict
import requests
from src.utils.logger import setup_logger

logger = setup_logger('summarizer')

class ArticleSummarizer:
    def __init__(self, model="mistral"):
        self.model = model
        self.api_url = "http://localhost:11434/api/generate"
        
        # Test connection and provide clear error message
        try:
            response = requests.post(self.api_url, json={"model": self.model, "prompt": "test"})
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
                }
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

def batch_process_articles(articles_dir: str = './data/processed/google_articles') -> None:
    """Process articles and add summaries to existing JSON files."""
    summarizer = ArticleSummarizer()
    
    article_files = [f for f in os.listdir(articles_dir) if f.endswith('.json')]
    total_articles = len(article_files)
    
    logger.info(f"Starting summarization of {total_articles} articles")
    
    for idx, article_file in enumerate(article_files, 1):
        article_path = os.path.join(articles_dir, article_file)
        logger.info(f"Processing article {idx}/{total_articles}: {article_file}")
        
        # Load existing article
        with open(article_path, 'r', encoding='utf-8') as f:
            article = json.load(f)
        
        # Add summaries to existing sections
        for section in article.get('sections', []):
            summarized_paragraphs = []
            for paragraph in section.get('paragraphs', []):
                if paragraph.strip():
                    summary = summarizer.summarize_paragraph(paragraph)
                    summarized_paragraphs.append({
                        'original': paragraph,
                        'summary': summary
                    })
            section['paragraphs'] = summarized_paragraphs
        
        # Save back to same file
        with open(article_path, 'w', encoding='utf-8') as f:
            json.dump(article, f, indent=2, ensure_ascii=False)
        logger.info(f"Updated article with summaries: {article_file}")