from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from datetime import datetime
import os
from getcalendar import init_calendar_routes, get_calendar_service
from directions import TravelTimeCalculator

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = 'your-secret-key-here'  # Required for flash messages

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
        # Get booking details from calendar
        event = calendar_service.get_event(event_id)
        
        return render_template(
            'booking-confirmation.html',
            booking=event
        )
    except Exception as e:
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

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # Here you would typically:
        # 1. Save the message to database
        # 2. Send notification email
        
        flash('Message sent! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

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
        
        # # Send confirmation email
        # send_booking_confirmation(
        #     recipient=booking_data['email'],
        #     booking_details=booking_data,
        #     calendar_link=result['html_link']
        # )
        
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

if __name__ == '__main__':
    # Ensure the static/images directory exists
    os.makedirs('static/images', exist_ok=True)
    
    # Run the app with host='0.0.0.0' to make it publicly accessible
    app.run(host='0.0.0.0', port=8080, debug=False)
