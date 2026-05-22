# rate_limiter.py
import redis
from functools import wraps
from flask import request, jsonify, g
import time

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def limit(self, max_requests=100, window=3600, key_prefix='rate_limit'):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Use user ID if authenticated, otherwise IP
                identifier = getattr(g, 'current_user', None)
                if identifier:
                    key = f"{key_prefix}:user:{identifier.id}:{f.__name__}"
                else:
                    key = f"{key_prefix}:ip:{request.remote_addr}:{f.__name__}"
                
                current = self.redis.get(key)
                
                if current is None:
                    # First request in window
                    pipe = self.redis.pipeline()
                    pipe.setex(key, window, 1)
                    pipe.expire(key, window)
                    pipe.execute()
                elif int(current) < max_requests:
                    # Increment counter
                    self.redis.incr(key)
                else:
                    # Rate limit exceeded
                    ttl = self.redis.ttl(key)
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': ttl,
                        'max_requests': max_requests,
                        'window_seconds': window
                    }), 429
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator

# Create global rate limiter instance
rate_limiter = None

def init_rate_limiter(app):
    global rate_limiter
    redis_client = redis.from_url(app.config['REDIS_URL'])
    rate_limiter = RateLimiter(redis_client)
    return rate_limiter