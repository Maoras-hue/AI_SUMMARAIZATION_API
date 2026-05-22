# models.py
from datetime import datetime, timedelta
import hashlib
import secrets
from flask_sqlalchemy import SQLAlchemy
import jwt

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    credits = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    stripe_customer_id = db.Column(db.String(100))
    
    payments = db.relationship('Payment', backref='user', lazy=True)
    usage_logs = db.relationship('UsageLog', backref='user', lazy=True)
    
    def generate_api_key(self):
        self.api_key = secrets.token_hex(32)
        return self.api_key
    
    def generate_jwt_token(self, secret_key, expiration_hours=24):
        payload = {
            'user_id': self.id,
            'email': self.email,
            'exp': datetime.utcnow() + timedelta(hours=expiration_hours)
        }
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    @staticmethod
    def verify_jwt_token(token, secret_key):
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'api_key': self.api_key,
            'credits': self.credits,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stripe_session_id = db.Column(db.String(100), unique=True)
    stripe_payment_intent_id = db.Column(db.String(100))
    amount = db.Column(db.Float, nullable=False)
    credits_purchased = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class UsageLog(db.Model):
    __tablename__ = 'usage_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    endpoint = db.Column(db.String(50), nullable=False)
    credits_used = db.Column(db.Integer, default=1)
    tokens_processed = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False)  # success, failed
    error_message = db.Column(db.Text)
    request_data = db.Column(db.Text)
    response_data = db.Column(db.Text)
    processing_time = db.Column(db.Float)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)