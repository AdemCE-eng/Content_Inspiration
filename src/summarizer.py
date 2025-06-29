import json
import os
from typing import Dict
import requests
from src.utils.logger import setup_logger
from src.utils.config import get_config
import subprocess
import time

logger = setup_logger('summarizer')
config = get_config()

class ArticleSummarizer:
    def __init__(self, model: str | None = None):
        self.model = model or config.get('ollama', {}).get('model', 'mistral')
        base_url = config.get('ollama', {}).get('base_url', 'http://localhost:11434')
        self.timeout = config.get('ollama', {}).get('timeout', 60)
        self.api_url = f"{base_url.rstrip('/')}/api/generate"
        
        self.server_process = None
        self.started_server = False
        self.server_running_before = False

        if self._test_connection():
            logger.info("Connected to existing Ollama server")
            self.server_running_before = True
        else:
            logger.info("Ollama server not running. Attempting to start it...")
            if self._start_server() and self._wait_for_server():
                logger.info("Ollama server started successfully")
            else:
                error_msg = (
                    "Could not connect to Ollama. Please ensure:\n"
                    "1. Ollama is installed (https://ollama.ai)\n"
                    "2. Ollama service is running (run 'ollama serve' in terminal)\n"
                    "3. The required model is pulled (run 'ollama pull mistral')"
                )
                logger.error(error_msg)
                raise ConnectionError(error_msg)

    def _test_connection(self) -> bool:
        try:
            response = requests.post(
                self.api_url,
                json={"model": self.model, "prompt": "test"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                error_msg = (
                    f"Model '{self.model}' not found. Please run:\n"
                    f"ollama pull {self.model}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            return False
        except Exception:
            return False

    def _start_server(self) -> bool:
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            self.server_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            return True
        except FileNotFoundError:
            logger.error("Ollama executable not found. Is it installed and on your PATH?")
            return False
        except Exception as e:
            logger.error(f"Failed to start Ollama server: {e}")
            return False

    def _wait_for_server(self, retries: int = 10, delay: float = 1.0) -> bool:
        for _ in range(retries):
            if self._test_connection():
                return True
            time.sleep(delay)
        return False
    
    def stop_server(self):
        """Terminate Ollama server regardless of who started it."""
        if self.server_process and self.server_process.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.server_process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        elif self.server_running_before:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "ollama.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(
                    ["pkill", "-f", "ollama"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        self.server_process = None
        self.started_server = False
        self.server_running_before = False

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
            
    summarizer.stop_server()
    return {
        'processed': processed_count,
        'skipped': skipped_count
    }