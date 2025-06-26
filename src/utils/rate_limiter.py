import time
from functools import wraps

def rate_limit(seconds_per_request=1):
    """Rate limiting decorator"""
    def decorator(func):
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < seconds_per_request:
                time.sleep(seconds_per_request - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator