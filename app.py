# app.py
import os
import json
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

from config import Config
from models import db, User, Payment, UsageLog
from auth import require_auth, require_credits
from rate_limiter import init_rate_limiter, rate_limiter
from stripe_handler import StripeHandler

summarizer = None

def get_summarizer():
    global summarizer
    if summarizer is None:
        from summarizer import summarizer as sz
        summarizer = sz
    return summarizer

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    CORS(app)
    
    init_rate_limiter(app)
    stripe_handler = StripeHandler(app)
    
    with app.app_context():
        db.create_all()
    
    @app.route('/')
    def index():
        return jsonify({
            'service': 'AI Text Summarization API',
            'version': '1.0.0',
            'endpoints': {
                'register': 'POST /register',
                'login': 'POST /login',
                'summarize': 'POST /summarize',
                'buy_credits': 'POST /buy-credits',
                'credits': 'GET /credits',
                'webhook': 'POST /webhook/stripe'
            }
        })
    
    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        user = User(
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            credits=100
        )
        user.generate_api_key()
        
        db.session.add(user)
        db.session.commit()
        
        token = user.generate_jwt_token(app.config['SECRET_KEY'])
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict(),
            'token': token
        }), 201
    
    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not check_password_hash(user.password_hash, data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        token = user.generate_jwt_token(app.config['SECRET_KEY'])
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'token': token
        })
    
    @app.route('/summarize', methods=['POST'])
    @require_auth
    @require_credits(credits_needed=1)
    @rate_limiter.limit(max_requests=30, window=3600)
    def summarize_text():
        data = request.get_json()
        
        if not data or not data.get('text'):
            return jsonify({'error': 'Text field is required'}), 400
        
        text = data['text']
        max_length = data.get('max_length', 130)
        min_length = data.get('min_length', 30)
        
        result = get_summarizer().summarize(
            text=text,
            max_length=max_length,
            min_length=min_length
        )
        
        usage_log = UsageLog(
            user_id=g.current_user.id,
            endpoint='summarize',
            credits_used=1,
            status='success' if result['success'] else 'failed',
            error_message=result.get('error'),
            request_data=json.dumps({'text_length': len(text)}),
            response_data=json.dumps(result),
            processing_time=result.get('processing_time', 0)
        )
        
        if result['success']:
            g.current_user.credits -= 1
        
        db.session.add(usage_log)
        db.session.commit()
        
        if result['success']:
            return jsonify({
                'success': True,
                'summary': result['summary'],
                'credits_remaining': g.current_user.credits,
                'metadata': result['metadata']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
    
    @app.route('/buy-credits', methods=['POST'])
    @require_auth
    def buy_credits():
        data = request.get_json()
        success_url = data.get('success_url', 'https://ai-summarization-api.onrender.com/success')
        cancel_url = data.get('cancel_url', 'https://ai-summarization-api.onrender.com/cancel')
        
        result = stripe_handler.create_checkout_session(
            user=g.current_user,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify({
            'message': 'Checkout session created',
            'checkout_url': result['url'],
            'session_id': result['session_id']
        })
    
    @app.route('/credits', methods=['GET'])
    @require_auth
    def get_credits():
        return jsonify({
            'credits': g.current_user.credits,
            'user': g.current_user.to_dict()
        })
    
    @app.route('/webhook/stripe', methods=['POST'])
    def stripe_webhook():
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')
        
        result = stripe_handler.handle_webhook(payload, sig_header)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
    
    @app.route('/usage-history', methods=['GET'])
    @require_auth
    def get_usage_history():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        logs = UsageLog.query.filter_by(user_id=g.current_user.id)\
            .order_by(UsageLog.created_at.desc())\
            .paginate(page=page, per_page=per_page)
        
        return jsonify({
            'usage': [{
                'id': log.id,
                'endpoint': log.endpoint,
                'credits_used': log.credits_used,
                'status': log.status,
                'processing_time': log.processing_time,
                'created_at': log.created_at.isoformat()
            } for log in logs.items],
            'total': logs.total,
            'pages': logs.pages,
            'current_page': logs.page
        })
    
    @app.route('/success')
    def success():
        return jsonify({'message': 'Payment successful! Credits added to your account.'})
    
    @app.route('/cancel')
    def cancel():
        return jsonify({'message': 'Payment cancelled.'})
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)