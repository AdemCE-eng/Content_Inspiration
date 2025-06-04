from functools import wraps
import time

def retry_on_failure(max_retries=3, delay_seconds=2):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay_seconds * (2 ** attempt))
            return None
        return wrapper
    return decorator