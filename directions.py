import googlemaps
import os
from datetime import datetime, timedelta
from functools import lru_cache

class TravelTimeCalculator:
    def __init__(self):
        self.gmaps = googlemaps.Client(key=os.environ['GOOGLE_MAPS_API_KEY'])
    
    @lru_cache(maxsize=128)
    def get_travel_times(self, origins, destinations):
        """Batch query travel times using Distance Matrix API"""
        # Convert tuples/strings to lists for the API call
        if isinstance(origins, (str, tuple)):
            origins = [origins] if isinstance(origins, str) else list(origins)
        if isinstance(destinations, (str, tuple)):
            destinations = [destinations] if isinstance(destinations, str) else list(destinations)
        
        result = self.gmaps.distance_matrix(
            origins=origins,
            destinations=destinations,
            mode="driving",
            departure_time="now"
        )
        
        # Extract durations into a more usable format
        travel_times = {}
        for i, origin in enumerate(origins):
            travel_times[str(origin)] = {}
            for j, dest in enumerate(destinations):
                duration = result['rows'][i]['elements'][j]['duration']['text']
                travel_times[str(origin)][str(dest)] = duration
                
        return travel_times

def calculate_travel_scenario(current_location, next_booking_location, home_location, 
                            current_booking_end, next_booking_start):
    """Calculate optimal travel scenario between bookings"""
    calculator = TravelTimeCalculator()
    
    # Convert lists to tuples for caching
    origins = tuple([current_location, home_location])
    destinations = tuple([next_booking_location, home_location])
    
    travel_times = calculator.get_travel_times(origins, destinations)
    
    # Use string keys when accessing the dictionary
    direct_travel = travel_times[str(current_location)][str(next_booking_location)]
    to_home = travel_times[str(current_location)][str(home_location)]
    from_home = travel_times[str(home_location)][str(next_booking_location)]
    
    # Calculate time gap in minutes
    time_gap = (next_booking_start - current_booking_end).total_seconds() / 60
    direct_minutes = _convert_time_to_minutes(direct_travel)
    
    if time_gap < (direct_minutes + 60):
        return {
            'recommendation': 'direct',
            'travel_time': direct_travel,
            'adjusted_start': next_booking_start - timedelta(minutes=direct_minutes + 30)
        }
    
    to_home_minutes = _convert_time_to_minutes(to_home)
    from_home_minutes = _convert_time_to_minutes(from_home)
    time_at_home = time_gap - (to_home_minutes + from_home_minutes)
    
    if time_at_home > 90:
        return {
            'recommendation': 'home',
            'travel_time_to_home': to_home,
            'travel_time_from_home': from_home,
            'time_at_home': f"{time_at_home} minutes",
            'adjusted_start': next_booking_start - timedelta(minutes=from_home_minutes + 30)
        }
    
    return {
        'recommendation': 'direct',
        'travel_time': direct_travel,
        'adjusted_start': next_booking_start - timedelta(minutes=direct_minutes + 30)
    }

def _convert_time_to_minutes(time_str):
    """Convert Google Maps time string to minutes"""
    try:
        if 'hour' in time_str.lower():
            parts = time_str.split()
            hours = int(parts[0])
            minutes = int(parts[2]) if len(parts) > 3 else 0
            return hours * 60 + minutes
        else:
            return int(time_str.split()[0])
    except Exception as e:
        raise

if __name__ == "__main__":
    # Test scenario
    current_location = "New Jersey"
    next_location = "Washington DC"
    home = "5159 Pooks Hill Rd, Bethesda, MD"
    
    current_end = datetime.now()
    next_start = current_end + timedelta(hours=3)
    
    try:
        # First call will query the API
        result1 = calculate_travel_scenario(
            current_location, next_location, home,
            current_end, next_start
        )
        print("\nFirst Query Results:")
        for key, value in result1.items():
            print(f"{key}: {value}")
            
        # Second call with same locations will use cached results
        result2 = calculate_travel_scenario(
            current_location, next_location, home,
            current_end, next_start
        )
        print("\nSecond Query Results (from cache):")
        for key, value in result2.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"Error calculating travel scenario: {e}")

