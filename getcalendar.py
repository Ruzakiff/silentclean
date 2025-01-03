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

        # Add a dictionary to track pending bookings
        # Format: {'2024-03-20 14:00': {'expires': datetime, 'duration': timedelta}}
        self.pending_bookings = {}
        
    def _clean_expired_pending(self):
        """Remove expired pending bookings"""
        now = datetime.now(self.timezone)
        expired = [
            time_slot for time_slot, data in self.pending_bookings.items()
            if data['expires'] < now
        ]
        for time_slot in expired:
            del self.pending_bookings[time_slot]

    def hold_slot(self, date_str, time_str, service_type):
        """Place a temporary hold on a time slot"""
        try:
            self._clean_expired_pending()
            
            # Create the datetime key
            slot_key = f"{date_str} {time_str}"
            
            # Check if slot is already pending
            if slot_key in self.pending_bookings:
                return {
                    'status': 'error',
                    'message': 'This slot is currently being booked by another customer'
                }

            # Add pending booking (expires in 5 minutes)
            self.pending_bookings[slot_key] = {
                'expires': datetime.now(self.timezone) + timedelta(minutes=5),
                'duration': timedelta(minutes=120 if service_type == 'Premium Detail' else 60)
            }
            
            return {
                'status': 'success',
                'message': 'Slot held for 5 minutes',
                'expires_in': '5 minutes'
            }
            
        except Exception as e:
            print(f"✗ Error holding slot: {str(e)}")
            raise

    def get_available_slots(self, date_str, service_duration, destination_address=None):
        """Get available time slots for a given date"""
        try:
            # Parse the date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_obj = self.timezone.localize(date_obj)
            
            # Get time bounds for the day
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

            # Get existing events
            events = self._get_day_events(time_min, time_max)
            
            # Initialize travel calculator if needed
            travel_calculator = None
            if destination_address:
                from directions import TravelTimeCalculator
                travel_calculator = TravelTimeCalculator()

            # Calculate available slots
            available_slots = self._calculate_available_slots(
                events, 
                date_obj, 
                service_duration,
                destination_address,
                travel_calculator
            )
            
            return available_slots
            
        except Exception as e:
            print(f"✗ Error in get_available_slots: {str(e)}")
            raise

    def _calculate_available_slots(self, events, date, duration_minutes, destination_address=None, travel_calculator=None):
        """Calculate available slots considering travel times from/to adjacent bookings"""
        def round_up_to_10(dt):
            """Round up datetime to nearest 10 minutes"""
            minutes = dt.minute
            rounded = ((minutes + 9) // 10) * 10
            if rounded == 60:
                return dt.replace(minute=0) + timedelta(hours=1)
            return dt.replace(minute=rounded)

        def format_time_12hr(dt):
            """Format datetime to 12-hour time with AM/PM"""
            return dt.strftime('%I:%M %p').lstrip('0')  # lstrip('0') removes leading zero

        slots = []
        duration = timedelta(minutes=duration_minutes)
        BUFFER_MINUTES = 15
        
        # Start and end times for the business day
        current_time = date.replace(hour=self.business_hours['start'], minute=0)
        day_end = date.replace(hour=self.business_hours['end'], minute=0)

        # If it's today, start from current time
        now = datetime.now(self.timezone)
        if date.date() == now.date():
            current_time = round_up_to_10(max(current_time, now))
            print(f"Today's date - adjusted start time: {current_time.strftime('%H:%M')}")

        while current_time + duration <= day_end:
            slot_start = current_time
            slot_end = current_time + duration
            can_schedule = True
            
            print(f"\n{'-'*50}")
            print(f"Evaluating slot: {slot_start.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}")

            # Check for overlaps
            has_overlap = any(
                datetime.fromisoformat(event['start'].get('dateTime')).astimezone(self.timezone) < slot_end
                and datetime.fromisoformat(event['end'].get('dateTime')).astimezone(self.timezone) > slot_start
                for event in events
            )

            if has_overlap:
                print("❌ Slot overlaps with existing booking")
                current_time = max(
                    datetime.fromisoformat(event['end'].get('dateTime')).astimezone(self.timezone)
                    for event in events
                    if datetime.fromisoformat(event['start'].get('dateTime')).astimezone(self.timezone) < slot_end
                    and datetime.fromisoformat(event['end'].get('dateTime')).astimezone(self.timezone) > slot_start
                )
                continue

            # Find previous and next bookings
            previous_booking = next((
                event for event in reversed(events)
                if datetime.fromisoformat(event['end'].get('dateTime')).astimezone(self.timezone) <= slot_start
            ), None)

            next_booking = next((
                event for event in events
                if datetime.fromisoformat(event['start'].get('dateTime')).astimezone(self.timezone) >= slot_end
            ), None)

            # Check travel from previous booking
            if previous_booking:
                prev_end = datetime.fromisoformat(previous_booking['end'].get('dateTime')).astimezone(self.timezone)
                prev_location = previous_booking.get('location')
                
                print(f"\nChecking travel FROM previous booking:")
                print(f"• Previous ends: {prev_end.strftime('%H:%M')} @ {prev_location or 'No location'}")
                
                if prev_location and destination_address and travel_calculator:
                    travel_times = travel_calculator.get_travel_times(
                        prev_location,
                        destination_address,
                        prev_end
                    )
                    if travel_times:
                        travel_minutes = travel_times[str(prev_location)][str(destination_address)]['minutes']
                        earliest_possible = round_up_to_10(prev_end + timedelta(minutes=travel_minutes + BUFFER_MINUTES))
                        print(f"• Travel time: {travel_minutes} mins (+{BUFFER_MINUTES} min buffer)")
                        print(f"• Earliest possible: {earliest_possible.strftime('%H:%M')}")
                else:
                    earliest_possible = round_up_to_10(prev_end + timedelta(minutes=BUFFER_MINUTES))
                    print(f"• No location - using {BUFFER_MINUTES} min buffer")
                    print(f"• Earliest possible: {earliest_possible.strftime('%H:%M')}")
                
                if earliest_possible > slot_start:
                    print(f"❌ Cannot start at requested time")
                    current_time = earliest_possible
                    can_schedule = False

            # Check travel to next booking
            if can_schedule and next_booking:
                next_start = datetime.fromisoformat(next_booking['start'].get('dateTime')).astimezone(self.timezone)
                next_location = next_booking.get('location')
                
                print(f"\nChecking travel TO next booking:")
                print(f"• Next starts: {next_start.strftime('%H:%M')} @ {next_location or 'No location'}")
                
                if next_location and destination_address and travel_calculator:
                    travel_times = travel_calculator.get_travel_times(
                        destination_address,
                        next_location,
                        slot_end
                    )
                    if travel_times:
                        travel_minutes = travel_times[str(destination_address)][str(next_location)]['minutes']
                        travel_buffer = travel_minutes + BUFFER_MINUTES
                        must_leave_by = next_start - timedelta(minutes=travel_buffer)
                        arrival_time = slot_end + timedelta(minutes=travel_buffer)
                        
                        print(f"• Travel time: {travel_minutes} mins (+{BUFFER_MINUTES} min buffer)")
                        print(f"• Must leave by: {must_leave_by.strftime('%H:%M')}")
                        print(f"• Would arrive at: {arrival_time.strftime('%H:%M')}")
                        
                        if arrival_time > next_start:
                            print(f"❌ Would arrive too late for next booking")
                            current_time = next_start
                            can_schedule = False
                else:
                    buffer_end = slot_end + timedelta(minutes=BUFFER_MINUTES)
                    print(f"• No location - using {BUFFER_MINUTES} min buffer")
                    print(f"• Must have {BUFFER_MINUTES} min gap")
                    
                    if buffer_end > next_start:
                        print(f"❌ Not enough buffer time to next booking")
                        current_time = next_start
                        can_schedule = False

            if can_schedule:
                print("\n✅ SLOT APPROVED")
                slots.append({
                    'start': format_time_12hr(slot_start),
                    'end': format_time_12hr(slot_end)
                })
            
            current_time += timedelta(minutes=10)

        print(f"\n{'='*50}")
        print(f"Found {len(slots)} available slots")
        return slots

    def create_booking(self, booking_data):
        """Create a new calendar event for a booking"""
        try:
            # Check if slot was held and is still valid
            slot_key = f"{booking_data['date']} {booking_data['time']}"
            if slot_key not in self.pending_bookings:
                raise Exception("Booking session expired. Please try again.")

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
                
                # If successful, remove from pending
                del self.pending_bookings[slot_key]
                
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

    def _get_day_events(self, time_min, time_max):
        """Get all events for a specific day period"""
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except Exception as e:
            print(f"✗ Error fetching events: {str(e)}")
            raise

def init_calendar_routes(app):
    calendar_service = CalendarService()
    
    @app.route('/api/hold-slot', methods=['POST'])
    def hold_slot():
        from flask import request
        
        try:
            data = request.json
            result = calendar_service.hold_slot(
                data['date'],
                data['time'],
                data['service_type']
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/available-slots', methods=['GET'])
    def get_available_slots():
        from flask import request
        
        date = request.args.get('date')
        service_type = request.args.get('service')
        address = request.args.get('address')
        unit = request.args.get('unit')
        
        # Construct full address
        full_address = f"{address}{f' Unit {unit}' if unit else ''}"
        
        print(f"\nAPI Request received:")
        print(f"Date: {date}")
        print(f"Service: {service_type}")
        print(f"Location: {full_address}")
        
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
            # Pass the full_address to get_available_slots
            available_slots = calendar_service.get_available_slots(
                date, 
                duration,
                destination_address=full_address  # Make sure to pass the address
            )
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

    @app.route('/api/release-hold', methods=['POST'])
    def release_hold():
        from flask import request
        
        try:
            data = request.get_json()
            if not data or 'date' not in data or 'time' not in data:
                print(f"✗ Invalid release hold request data: {data}")
                return jsonify({
                    'status': 'error',
                    'message': 'Missing date or time in request'
                }), 400

            slot_key = f"{data['date']} {data['time']}"
            print(f"Attempting to release hold for slot: {slot_key}")
            
            # Remove the hold if it exists
            if slot_key in calendar_service.pending_bookings:
                del calendar_service.pending_bookings[slot_key]
                print(f"✓ Released hold for slot: {slot_key}")
                return jsonify({
                    'status': 'success',
                    'message': 'Hold released successfully'
                })
            
            print(f"ℹ No hold found for slot: {slot_key}")
            return jsonify({
                'status': 'success',
                'message': 'No hold found to release'
            })
            
        except Exception as e:
            print(f"✗ Error releasing hold: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400

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
