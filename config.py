# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-super-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///api_credits.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_key')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_your_webhook_secret')
    STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID', 'price_1234567890')  # $10 for 1000 credits
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    JWT_EXPIRATION_HOURS = 24
    CREDIT_COST_PER_REQUEST = 1  # credits per API call
    CREDITS_PER_PURCHASE = 1000  # credits per $10 purchase