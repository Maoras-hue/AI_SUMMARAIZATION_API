# create_stripe_product.py
import stripe
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Create a product
product = stripe.Product.create(
    name="API Credits",
    description="1000 API credits for text summarization"
)

# Create a price
price = stripe.Price.create(
    product=product.id,
    unit_amount=1000,  # $10.00 in cents
    currency="usd",
)

print(f"Product ID: {product.id}")
print(f"Price ID: {price.id}")
print("Add this Price ID to your .env file as STRIPE_PRICE_ID")