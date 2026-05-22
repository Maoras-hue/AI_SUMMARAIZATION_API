# stripe_handler.py
import stripe
from datetime import datetime
from models import db, Payment, User

class StripeHandler:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        stripe.api_key = app.config['STRIPE_SECRET_KEY']
        self.webhook_secret = app.config['STRIPE_WEBHOOK_SECRET']
        self.price_id = app.config['STRIPE_PRICE_ID']
    
    def create_checkout_session(self, user, success_url, cancel_url):
        """Create a Stripe Checkout Session for buying credits"""
        try:
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={'user_id': user.id}
                )
                user.stripe_customer_id = customer.id
                db.session.commit()
            
            session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': self.price_id,
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user.id
                }
            )
            
            # Create payment record
            payment = Payment(
                user_id=user.id,
                stripe_session_id=session.id,
                amount=10.00,  # $10 for 1000 credits
                credits_purchased=1000,
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()
            
            return {
                'session_id': session.id,
                'url': session.url
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def handle_webhook(self, payload, sig_header):
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                self._handle_successful_payment(session)
            
            elif event['type'] == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                self._handle_failed_payment(payment_intent)
            
            return {'status': 'success'}
            
        except ValueError as e:
            return {'error': 'Invalid payload'}
        except stripe.error.SignatureVerificationError as e:
            return {'error': 'Invalid signature'}
    
    def _handle_successful_payment(self, session):
        """Process successful payment"""
        user_id = int(session['metadata']['user_id'])
        user = User.query.get(user_id)
        
        if user:
            # Update payment record
            payment = Payment.query.filter_by(
                stripe_session_id=session['id']
            ).first()
            
            if payment and payment.status == 'pending':
                payment.status = 'completed'
                payment.stripe_payment_intent_id = session.get('payment_intent')
                payment.completed_at = datetime.utcnow()
                
                # Add credits to user
                user.credits += payment.credits_purchased
                
                db.session.commit()
                print(f"Added {payment.credits_purchased} credits to user {user.email}")
    
    def _handle_failed_payment(self, payment_intent):
        """Handle failed payment"""
        session_id = payment_intent.get('metadata', {}).get('session_id')
        if session_id:
            payment = Payment.query.filter_by(stripe_session_id=session_id).first()
            if payment:
                payment.status = 'failed'
                db.session.commit()