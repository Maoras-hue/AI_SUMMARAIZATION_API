# auth.py
from functools import wraps
from flask import request, jsonify, g
from models import User

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            # Try API key authentication
            api_key = request.headers.get('X-API-Key')
            if api_key:
                user = User.query.filter_by(api_key=api_key, is_active=True).first()
                if user:
                    g.current_user = user
                    return f(*args, **kwargs)
            
            return jsonify({'error': 'Authentication required'}), 401
        
        from flask import current_app
        payload = User.verify_jwt_token(token, current_app.config['SECRET_KEY'])
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user = User.query.get(payload['user_id'])
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def require_credits(credits_needed=1):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            if g.current_user.credits < credits_needed:
                return jsonify({
                    'error': 'Insufficient credits',
                    'credits_available': g.current_user.credits,
                    'credits_required': credits_needed,
                    'message': 'Please purchase more credits at /buy-credits'
                }), 402
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator