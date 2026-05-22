# rate_limiter.py
import time
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, g

class InMemoryRateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    
    def cleanup_old_requests(self, key, window):
        """Remove requests older than the window"""
        current_time = time.time()
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time < window
        ]
    
    def limit(self, max_requests=100, window=3600, key_prefix='rate_limit'):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Use user ID if authenticated, otherwise IP
                if hasattr(g, 'current_user'):
                    key = f"{key_prefix}:user:{g.current_user.id}:{f.__name__}"
                else:
                    key = f"{key_prefix}:ip:{request.remote_addr}:{f.__name__}"
                
                # Clean old requests
                self.cleanup_old_requests(key, window)
                
                # Check rate limit
                if len(self.requests[key]) >= max_requests:
                    oldest_request = min(self.requests[key]) if self.requests[key] else time.time()
                    retry_after = int(window - (time.time() - oldest_request))
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': max(0, retry_after),
                        'max_requests': max_requests,
                        'window_seconds': window
                    }), 429
                
                # Add current request
                self.requests[key].append(time.time())
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator

# Create global rate limiter instance
rate_limiter = InMemoryRateLimiter()

def init_rate_limiter(app=None):
    """Initialize rate limiter (no Redis needed)"""
    return rate_limiter