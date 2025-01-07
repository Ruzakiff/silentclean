from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from datetime import datetime
import os
from getcalendar import init_calendar_routes, get_calendar_service
from directions import TravelTimeCalculator
from flask_mail import Mail, Message

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465  # Changed from 587 to 465
app.config['MAIL_USE_TLS'] = False  # Changed from True
app.config['MAIL_USE_SSL'] = True  # Added SSL
app.config['MAIL_USERNAME'] = 'ryanchenyang@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # Get from environment variable
app.config['MAIL_DEFAULT_SENDER'] = ('Silentwash', 'contact@silentwashev.com')  # Tuple format for name + email
mail = Mail(app)

# Initialize calendar routes and get service instance
init_calendar_routes(app)
calendar_service = get_calendar_service()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        # The actual booking creation is now handled by /api/create-booking
        # This route should only handle the initial page load and form display
        return redirect(url_for('booking_confirmation'))
        
    return render_template('booking.html')

@app.route('/booking/confirmation/<event_id>')
def booking_confirmation(event_id):
    try:
        print(f"Fetching event details for ID: {event_id}")
        event = calendar_service.get_event(event_id)
        print(f"Event data received: {event}")
        
        # Calculate duration in hours and minutes
        start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
        duration = end - start
        duration_hours = duration.total_seconds() / 3600
        
        return render_template(
            'confirmation.html',
            event=event,
            duration=f"{duration_hours:.1f} hours"  # Format as "1.5 hours"
        )
    except Exception as e:
        print(f"Error in booking confirmation: {str(e)}")
        return render_template('error.html', message=str(e))

@app.route('/services')
def services():
    services_list = [
        {
            'name': 'Basic Clean',
            'price': 79,
            'description': 'Exterior wash, interior vacuum, and windows'
        },
        {
            'name': 'Premium Clean',
            'price': 149,
            'description': 'Basic clean plus interior detailing and tire shine'
        },
        {
            'name': 'Ultimate Package',
            'price': 249,
            'description': 'Premium clean plus paint protection and sanitization'
        }
    ]
    return render_template('services.html', services=services_list)

# @app.route('/contact', methods=['GET', 'POST'])
# def contact():
#     if request.method == 'POST':
#         name = request.form.get('name')
#         email = request.form.get('email')
#         message = request.form.get('message')
        
#         # Here you would typically:
#         # 1. Save the message to database
#         # 2. Send notification email
        
#         flash('Message sent! We will get back to you soon.', 'success')
#         return redirect(url_for('contact'))
        
#     return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                             'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/place-suggestions')
def get_place_suggestions():
    """Endpoint to get address suggestions for Maryland locations"""
    query = request.args.get('input')
    if not query:
        return jsonify({'suggestions': []})

    try:
        calculator = TravelTimeCalculator()
        # Using Maryland coordinates (39.0458, -76.6413) with 50km radius
        suggestions = calculator.get_place_suggestions(
            input_text=query,
            location=(39.0458, -76.6413),
            radius=50000
        )
        
        return jsonify({
            'status': 'success',
            'suggestions': suggestions
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'suggestions': []
        }), 500

@app.route('/api/book', methods=['POST'])
def book_appointment():
    try:
        booking_data = request.json
        
        # Validate required fields
        required_fields = ['service_type', 'date', 'time', 'name', 'email', 'phone', 'address']
        missing_fields = [field for field in required_fields if not booking_data.get(field)]
        
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Create the booking
        result = calendar_service.create_booking(booking_data)
        
        # Send confirmation email
        send_booking_confirmation(
            recipient=booking_data['email'],
            booking_details=booking_data,
            calendar_link=result['html_link']
        )
        
        return jsonify({
            'status': 'success',
            'event_id': result['event_id'],
            'calendar_link': result['html_link']
        })

    except Exception as e:
        print(f"Error processing booking: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Context processor for common data
@app.context_processor
def utility_processor():
    def get_current_year():
        return datetime.now().year
    
    return dict(current_year=get_current_year)

# Custom filters
@app.template_filter('currency')
def currency_format(value):
    return f"${value:,.2f}"

@app.template_filter('format_datetime')
def format_datetime(value):
    """Format datetime for the confirmation page"""
    if isinstance(value, str):
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    else:
        dt = value
    return dt.strftime('%B %d, %Y at %I:%M %p')  # Example: March 15, 2024 at 02:30 PM
def send_booking_confirmation(recipient, booking_details, calendar_link):
    """Send booking confirmation email to customer"""
    try:
        
        msg = Message(
            "We've Got You Covered—Your SilentWash Appointment Details",
            sender=('SilentWash', 'contact@silentwashev.com'),
            recipients=[recipient],
            reply_to='contact@silentwashev.com'
        )
        
        # Plain text version
        msg.body = f"""
Hi {booking_details.get('name', 'Valued Customer')},

Thank you for choosing SilentWash! Your booking is confirmed, and we're excited to deliver a spotless experience that fits seamlessly into your lifestyle.

Appointment Details:
- Service: {booking_details['service_type']}
- Date: {booking_details['date']}
- Time: {booking_details['time']}
- Location: {booking_details['address']}

Here's what to expect:
1. **Before Your Service**: You'll receive a reminder the day before.
2. **During the Service**: Our team will clean your vehicle while it stays parked—quietly and efficiently.
3. **After the Service**: You'll receive a notification with before-and-after photos to review the results.

Manage or update your booking here:
{calendar_link}

At SilentWash, we believe your time is priceless. That's why we handle every detail with care and precision, offering you the freedom to focus on what matters most.

If you have any questions or need assistance, feel free to reply to this email.  
We look forward to exceeding your expectations!

Best regards,  
The SilentWash Team  
"Your ride, always spotless. Always effortless."
"""
        
        # HTML version using the template
        msg.html = render_template(
            'emailtemplate.html',
            customer_name=booking_details.get('name', 'Valued Customer'),
            service_type=booking_details['service_type'],
            date=booking_details['date'],
            time=booking_details['time'],
            location=booking_details['address'],
            calendar_link=calendar_link
        )
        
        mail.send(msg)
        print(f"Confirmation email sent to {recipient}")
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")

if __name__ == '__main__':
    # Ensure the static/images directory exists
    os.makedirs('static/images', exist_ok=True)
    
    # # If you want to test email before running the server, use app context:
    # with app.app_context():
    #     test_booking = {
    #         'service_type': 'Basic Clean',
    #         'date': '2025-01-15',
    #         'time': '14:30',
    #         'address': '123 Test St, Baltimore, MD',
    #         'name':'MADISON'
    #     }
    #     send_booking_confirmation(
    #         recipient='madi.enolp@gmail.com',
    #         booking_details=test_booking,
    #         calendar_link='https://calendar.google.com/test'
    #     )
    
    # Run the app with host='0.0.0.0' to make it publicly accessible
    app.run(host='0.0.0.0', port=8080, debug=False)
   

