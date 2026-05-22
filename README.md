# AI Text Summarization API

A Stripe-powered API service for text summarization using transformers.

## Features
- Text summarization using Facebook's BART model
- Credit-based pricing ($10 for 1000 credits)
- JWT authentication
- Rate limiting with Redis
- Stripe payment integration
- Usage tracking and analytics

## API Endpoints

### Authentication
- `POST /register` - Register new user
- `POST /login` - Login and get JWT token

### API Usage
- `POST /summarize` - Summarize text (requires authentication & credits)
- `GET /credits` - Check remaining credits
- `POST /buy-credits` - Purchase credits via Stripe
- `GET /usage-history` - View API usage history

## Deployment
Deployed on Render.com free tier