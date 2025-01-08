import os
import stripe
from flask import jsonify, request
from datetime import datetime

# Initialize Stripe with secret key from environment variable
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def init_payment_routes(app):
    @app.route('/api/create-payment-intent', methods=['POST'])
    def create_payment_intent():
        try:
            data = request.get_json()
            
            # Create a PaymentIntent with the order amount and currency
            intent = stripe.PaymentIntent.create(
                amount=int(float(data['amount']) * 100), # Convert to cents
                currency='usd',
                metadata={
                    'date': data.get('date'),
                    'time': data.get('time'),
                    'service_type': data.get('service_type'),
                    'customer_email': data.get('email'),
                    'customer_name': data.get('name')
                }
            )

            return jsonify({
                'clientSecret': intent.client_secret,
                'id': intent.id
            })

        except Exception as e:
            return jsonify({
                'error': str(e)
            }), 400

    @app.route('/api/payment-webhook', methods=['POST'])
    def stripe_webhook():
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )

            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                # Handle successful payment
                print(f"✓ Payment succeeded for: {payment_intent.metadata.customer_email}")
                
                return jsonify({'status': 'success'})

            elif event['type'] == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                # Handle failed payment
                print(f"✗ Payment failed for: {payment_intent.metadata.customer_email}")
                
                return jsonify({'status': 'failed'})

            return jsonify({'status': 'success'})

        except stripe.error.SignatureVerificationError as e:
            print(f"✗ Webhook signature verification failed: {str(e)}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            print(f"✗ Webhook error: {str(e)}")
            return jsonify({'error': str(e)}), 400
