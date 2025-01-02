from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from flask import jsonify
import pytz
from googleapiclient.errors import HttpError
import json

class CalendarService:
    def __init__(self):
        # Load credentials from service account file
        SCOPES = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events'
        ]
        try:
            credentials = service_account.Credentials.from_service_account_file(
                'silentwash-4b7a2b2c111e.json', scopes=SCOPES)
            print("✓ Credentials loaded successfully")
        except Exception as e:
            print(f"✗ Error loading credentials: {str(e)}")
            raise

        # Build the service
        try:
            self.service = build('calendar', 'v3', credentials=credentials)
            print("✓ Calendar service built successfully")
        except Exception as e:
            print(f"✗ Error building calendar service: {str(e)}")
            raise

        self.calendar_id = 'b6765108df1c8066b4ed2474361248caa586e63117b11f31dcf25c6d316844dd@group.calendar.google.com'
        self.timezone = pytz.timezone('America/New_York')  # Adjust to your timezone
        
        # Define business hours (24-hour format)
        self.business_hours = {
            'start': 9,  # 9 AM
            'end': 17    # 5 PM
        }

    def get_available_slots(self, date_str, service_duration):
        try:
            print(f"\nFetching slots for {date_str}, duration: {service_duration} minutes")
            
            # Parse the date string and make it timezone-aware
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_obj = self.timezone.localize(date_obj)
            
            # Create timezone-aware datetime objects for the day's boundaries
            time_min = date_obj.replace(
                hour=self.business_hours['start'], 
                minute=0, 
                second=0, 
                microsecond=0
            )
            time_max = date_obj.replace(
                hour=self.business_hours['end'], 
                minute=0, 
                second=0, 
                microsecond=0
            )

            print(f"Querying calendar from {time_min.strftime('%Y-%m-%d %H:%M %Z')} to {time_max.strftime('%Y-%m-%d %H:%M %Z')}")

            # Get existing events with detailed debugging
            try:
                events_result = self.service.events().list(
                    calendarId=self.calendar_id,
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                print(f"\nFound {len(events)} existing events:")
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    summary = event.get('summary', 'No title')
                    print(f"  • {summary}: {start} - {end}")
                    # Print full event data for debugging
                    print(f"    Full event data: {json.dumps(event, indent=2)}")
                
            except Exception as e:
                print(f"✗ Error fetching events: {str(e)}")
                raise

            available_slots = self._calculate_available_slots(events, date_obj, service_duration)
            print(f"\nGenerated {len(available_slots)} available slots:")
            for slot in available_slots:
                print(f"  • {slot['start']} - {slot['end']}")
            return available_slots
            
        except Exception as e:
            print(f"✗ Error in get_available_slots: {str(e)}")
            raise

    def _calculate_available_slots(self, events, date, duration_minutes):
        """Calculate available time slots given existing events"""
        print(f"\nCalculating slots for {date.strftime('%Y-%m-%d')}")
        slots = []
        
        # Convert duration to timedelta
        duration = timedelta(minutes=duration_minutes)
        
        # Start and end times for the business day (timezone-aware)
        day_start = date.replace(
            hour=self.business_hours['start'], 
            minute=0, 
            second=0, 
            microsecond=0
        )
        day_end = date.replace(
            hour=self.business_hours['end'], 
            minute=0, 
            second=0, 
            microsecond=0
        )
        
        print(f"Business hours: {day_start.strftime('%H:%M')} - {day_end.strftime('%H:%M')}")
        
        # Create list of busy periods
        busy_periods = []
        for event in events:
            try:
                start = datetime.fromisoformat(
                    event['start'].get('dateTime', event['start'].get('date'))
                ).astimezone(self.timezone)
                
                end = datetime.fromisoformat(
                    event['end'].get('dateTime', event['end'].get('date'))
                ).astimezone(self.timezone)
                
                busy_periods.append((start, end))
                print(f"Found busy period: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")
                
            except Exception as e:
                print(f"✗ Error parsing event time: {str(e)}")
                continue
        
        # Sort busy periods by start time
        busy_periods.sort(key=lambda x: x[0])
        
        # Find available slots
        current_time = day_start
        
        # If it's today, start from current time
        now = datetime.now(self.timezone)
        if date.date() == now.date():
            current_time = max(
                current_time, 
                now.replace(minute=0, second=0, microsecond=0)
            )
            print(f"\nToday's schedule, starting from: {current_time.strftime('%H:%M')}")
        
        while current_time + duration <= day_end:
            # Check if this slot overlaps with any busy period
            slot_end = current_time + duration
            has_overlap = False
            
            for busy_start, busy_end in busy_periods:
                if (current_time < busy_end and slot_end > busy_start):
                    has_overlap = True
                    # Jump to the end of this busy period
                    current_time = busy_end
                    break
            
            if not has_overlap:
                slot = {
                    'start': current_time.strftime('%H:%M'),
                    'end': slot_end.strftime('%H:%M')
                }
                slots.append(slot)
                print(f"Added available slot: {slot['start']} - {slot['end']}")
                current_time += timedelta(minutes=30)
            
        return slots

    def create_booking(self, booking_data):
        """Create a new calendar event for a booking"""
        try:
            print(f"\nCreating booking:")
            print(f"Date: {booking_data['date']}")
            print(f"Time: {booking_data['time']}")
            print(f"Service: {booking_data['service_type']}")
            print(f"Customer: {booking_data['name']}")

            # Parse the date and time
            date_str = booking_data['date']
            time_str = booking_data['time']
            datetime_str = f"{date_str} {time_str}"
            
            # Create start time (timezone aware)
            start_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            start_time = self.timezone.localize(start_time)
            
            # Calculate end time based on service type
            service_duration = {
                'Essential Clean': timedelta(minutes=60),
                'Premium Detail': timedelta(minutes=120)
            }.get(booking_data['service_type'], timedelta(minutes=60))
            
            end_time = start_time + service_duration

            # Verify the slot is still available
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True
            ).execute()
            
            existing_events = events_result.get('items', [])
            if existing_events:
                error_msg = "This time slot is no longer available"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)

            # Create event details
            event = {
                'summary': f"Car Detail - {booking_data['service_type']}",
                'location': booking_data.get('address', 'TBD'),
                'description': f"""
Booking Details:
---------------
Customer: {booking_data['name']}
Service: {booking_data['service_type']}
Vehicle: {booking_data.get('vehicle', 'Not specified')}
Phone: {booking_data.get('phone', 'Not provided')}
Email: {booking_data.get('email', 'Not provided')}
Special Instructions: {booking_data.get('notes', 'None')}
                """.strip(),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': str(self.timezone),
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': str(self.timezone),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 24 hours
                        {'method': 'popup', 'minutes': 60},       # 1 hour
                    ],
                },
            }

            try:
                event = self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=event
                ).execute()
                print(f"✓ Event created successfully: {event.get('htmlLink')}")
                
                return {
                    'status': 'success',
                    'event_id': event['id'],
                    'html_link': event['htmlLink']
                }
                
            except HttpError as e:
                error_msg = f"Failed to create event: {str(e)}"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)

        except Exception as e:
            print(f"✗ Error creating booking: {str(e)}")
            raise

def init_calendar_routes(app):
    calendar_service = CalendarService()
    
    @app.route('/api/available-slots', methods=['GET'])
    def get_available_slots():
        from flask import request
        
        date = request.args.get('date')
        service_type = request.args.get('service')
        
        print(f"\nAPI Request received:")
        print(f"Date: {date}")
        print(f"Service: {service_type}")
        
        # Map service types to durations (in minutes)
        service_durations = {
            'Essential Clean': 60,
            'Premium Detail': 120
        }
        
        duration = service_durations.get(service_type)
        if not duration:
            error_msg = f"Invalid service type: {service_type}"
            print(f"✗ {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        try:
            available_slots = calendar_service.get_available_slots(date, duration)
            response_data = {'slots': available_slots}
            print(f"✓ Returning {len(available_slots)} slots")
            return jsonify(response_data)
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            print(f"✗ {error_msg}")
            return jsonify({'error': error_msg}), 500

    @app.route('/api/create-booking', methods=['POST'])
    def create_booking():
        from flask import request
        
        try:
            booking_data = request.json
            print("\nReceived booking request:")
            print(json.dumps(booking_data, indent=2))

            # Validate required fields
            required_fields = ['date', 'time', 'service_type', 'name']
            missing_fields = [field for field in required_fields if field not in booking_data]
            
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                print(f"✗ {error_msg}")
                return jsonify({'error': error_msg}), 400

            # Validate service type
            valid_services = ['Essential Clean', 'Premium Detail']
            if booking_data['service_type'] not in valid_services:
                error_msg = f"Invalid service type: {booking_data['service_type']}"
                print(f"✗ {error_msg}")
                return jsonify({'error': error_msg}), 400

            # Create the booking
            result = calendar_service.create_booking(booking_data)
            print("✓ Booking created successfully")
            return jsonify(result)

        except Exception as e:
            error_msg = f"Error processing booking: {str(e)}"
            print(f"✗ {error_msg}")
            return jsonify({'error': error_msg}), 500

if __name__ == "__main__":
    from flask import Flask
    import json
    from datetime import datetime, timedelta

    # Create test Flask app
    app = Flask(__name__)
    init_calendar_routes(app)

    def test_tomorrow_booking():
        print("\nTesting Tomorrow's Booking:")
        print("=" * 50)
        
        # Calculate tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        with app.test_client() as client:
            test_booking = {
                'date': tomorrow,
                'time': '10:00',  # Morning slot
                'service_type': 'Premium Detail',
                'name': 'Test Customer',
                'email': 'test@example.com',
                'phone': '555-0123',
                'vehicle': 'Tesla Model 3',
                'address': '123 Main St',
                'notes': 'Test booking for tomorrow'
            }
            
            print("\nCreating booking for tomorrow:")
            print(json.dumps(test_booking, indent=2))
            
            response = client.post(
                '/api/create-booking',
                json=test_booking,
                content_type='application/json'
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.loads(response.data.decode())}")

    # Run tests
    print("\nStarting Calendar Service Tests")
    print("=" * 50)
    
    try:
        test_tomorrow_booking()
        
        print("\nAll tests completed!")
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")

    # Optional: Run Flask development server
    print("\nStarting Flask development server...")
    app.run(debug=True, port=5000)
