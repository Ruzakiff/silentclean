from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = 'your-secret-key-here'  # Required for flash messages

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        # Handle booking form submission
        name = request.form.get('name')
        email = request.form.get('email')
        date = request.form.get('date')
        time = request.form.get('time')
        service_type = request.form.get('service_type')
        
        # Here you would typically:
        # 1. Validate the data
        # 2. Save to database
        # 3. Send confirmation email
        
        flash('Booking received! We will contact you shortly.', 'success')
        return redirect(url_for('booking_confirmation'))
        
    return render_template('booking.html')

@app.route('/booking/confirmation')
def booking_confirmation():
    return render_template('confirmation.html')

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
    
    # Run the app
    app.run(debug=True)