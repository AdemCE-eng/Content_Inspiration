import logging
import os
from datetime import datetime
from .config import get_config

def setup_logger(name: str) -> logging.Logger:
    """Configure logging with file and console handlers."""
    config = get_config()
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    log_dir = config.get('logs_dir', 'logs')
    if not os.path.isabs(log_dir):
        log_dir = os.path.join(root_dir, log_dir)
    os.makedirs(log_dir, exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    level_name = config.get('log_level', 'INFO').upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    # Prevent adding handlers multiple times
    if not logger.handlers:
        # File handler - daily log file
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logger.level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger.level)

        # Create formatters and add to handlers
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger