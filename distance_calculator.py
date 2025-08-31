# import re
# import math
# import requests
# from geopy.geocoders import Nominatim
# from geopy.extra.rate_limiter import RateLimiter


# geolocator = Nominatim(user_agent="geo-no-key-example", timeout=15)
# geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.0)

# import re

# UNIT_PAT = re.compile(
#     r"(?:\b(?:suite|ste|unit|apt|apartment|bldg|building|fl|floor)\b[\s.:#-]*[A-Za-z0-9-]+)"
#     r"|(?:\#[ ]?[A-Za-z0-9-]+)",
#     flags=re.IGNORECASE,
# )

# def strip_unit(addr: str) -> str:
#     no_unit = UNIT_PAT.sub("", addr)
#     no_unit = re.sub(r"\s{2,}", " ", no_unit).strip()
#     no_unit = re.sub(r",\s*,+", ", ", no_unit)
#     return no_unit

# def get_coordinates(addr: str):
#     """Return (lat, lon, normalized_address) for the address."""
#     cleaned = strip_unit(addr)
#     loc = geocode(cleaned + ", USA", exactly_one=True, addressdetails=False, country_codes="us")
#     if not loc:
#         # last-ditch: try original
#         loc = geocode(addr + ", USA", exactly_one=True, addressdetails=False, country_codes="us")
#     if not loc:
#         raise ValueError(f"Could not geocode: {addr}")
#     return loc.latitude, loc.longitude, getattr(loc, "display_name", getattr(loc, "address", addr))

# def osrm_driving_distance_miles(lat1, lon1, lat2, lon2, base_url="https://router.project-osrm.org"):
#     """
#     Returns (miles, seconds). No API key. OSRM public demo server = best-effort only.
#     """
#     url = f"{base_url}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
#     params = {
#         "overview": "false",
#         "alternatives": "false",
#         "steps": "false"
#     }
#     headers = {"User-Agent": "geo-no-key-example"}
#     r = requests.get(url, params=params, headers=headers, timeout=15)
#     r.raise_for_status()
#     data = r.json()
#     if data.get("code") != "Ok" or not data.get("routes"):
#         raise RuntimeError(f"OSRM routing failed: {data.get('message', 'unknown error')}")
#     meters = data["routes"][0]["distance"]
#     seconds = data["routes"][0]["duration"]
#     miles = meters / 1609.344
#     return miles, seconds

# def print_locations_and_distance(a: str, b: str):
#     try:
#         lat1, lon1, addr1 = get_coordinates(a)
#         lat2, lon2, addr2 = get_coordinates(b)

#         print(f"Base:   {addr1} -> ({lat1:.6f}, {lon1:.6f})")
#         print(f"Target: {addr2} -> ({lat2:.6f}, {lon2:.6f})")

#         # Driving distance (road network)
#         try:
#             drive_miles, secs = osrm_driving_distance_miles(lat1, lon1, lat2, lon2)
#             mins = round(secs / 60)
#             print(f"Driving distance (OSRM): {drive_miles:.2f} miles (~{mins} min, no traffic)")
#             return f"{drive_miles: .2f} mi."
#         except Exception as e:
#             print(f"Driving distance unavailable via OSRM: {e}")
#     except Exception as e:
#         print(f"Error: {e}")

# if __name__ == "__main__":
#     print_locations_and_distance(
#         "12532 Citruswood Avenue, Garden Grove, CA 92840",
#         "101 The City Drive South Pavilion 3 Building 29, Orange, CA 92868"
#     )

import re
import math
import requests
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

geolocator = Nominatim(user_agent="geo-no-key-example", timeout=15)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.0)

# Improved regex pattern to catch more unit variations
UNIT_PAT = re.compile(
    r"(?:\b(?:suite|ste|unit|apt|apartment|bldg|building|pavilion|pav|fl|floor|tower|twr)\b[\s.:#-]*[A-Za-z0-9-]+)"
    r"|(?:\#[ ]?[A-Za-z0-9-]+)"
    r"|(?:\b(?:building|pavilion)\s+[A-Za-z0-9-]+)",
    flags=re.IGNORECASE,
)

def strip_unit(addr: str) -> str:
    """Remove unit/suite/building identifiers from address"""
    print(f"Original address: {addr}")
    
    # Apply the regex substitution
    no_unit = UNIT_PAT.sub("", addr)
    print(f"After unit removal: {no_unit}")
    
    # Clean up extra whitespace
    no_unit = re.sub(r"\s{2,}", " ", no_unit).strip()
    
    # Clean up multiple commas
    no_unit = re.sub(r",\s*,+", ", ", no_unit)
    
    # Remove trailing commas and clean up
    no_unit = re.sub(r",\s*$", "", no_unit)
    
    print(f"Final cleaned: {no_unit}")
    return no_unit

def get_coordinates(addr: str):
    """Return (lat, lon, normalized_address) for the address."""
    print(f"\n--- Geocoding: {addr} ---")
    
    # Try cleaned address first
    cleaned = strip_unit(addr)
    print(f"Trying cleaned address: {cleaned}")
    
    loc = geocode(cleaned + ", USA", exactly_one=True, addressdetails=False, country_codes="us")
    
    if not loc:
        print("Cleaned address failed, trying original...")
        # last-ditch: try original
        loc = geocode(addr + ", USA", exactly_one=True, addressdetails=False, country_codes="us")
    
    if not loc:
        # Try even more simplified version - just street number and name
        simplified = re.sub(r'\b(?:pavilion|building|bldg)\s+\d+.*$', '', addr, flags=re.IGNORECASE).strip()
        simplified = re.sub(r',\s*,+', ', ', simplified)
        print(f"Trying simplified address: {simplified}")
        loc = geocode(simplified + ", USA", exactly_one=True, addressdetails=False, country_codes="us")
    
    if not loc:
        raise ValueError(f"Could not geocode: {addr}")
    
    return loc.latitude, loc.longitude, getattr(loc, "display_name", getattr(loc, "address", addr))

def osrm_driving_distance_miles(lat1, lon1, lat2, lon2, base_url="https://router.project-osrm.org"):
    """
    Returns (miles, seconds). No API key. OSRM public demo server = best-effort only.
    """
    url = f"{base_url}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {
        "overview": "false",
        "alternatives": "false",
        "steps": "false"
    }
    headers = {"User-Agent": "geo-no-key-example"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM routing failed: {data.get('message', 'unknown error')}")
    
    meters = data["routes"][0]["distance"]
    seconds = data["routes"][0]["duration"]
    miles = meters / 1609.344
    return miles, seconds

def print_locations_and_distance(a: str, b: str):
    try:
        lat1, lon1, addr1 = get_coordinates(a)
        lat2, lon2, addr2 = get_coordinates(b)
        print(f"\nBase:   {addr1} -> ({lat1:.6f}, {lon1:.6f})")
        print(f"Target: {addr2} -> ({lat2:.6f}, {lon2:.6f})")
        
        # Driving distance (road network)
        try:
            drive_miles, secs = osrm_driving_distance_miles(lat1, lon1, lat2, lon2)
            mins = round(secs / 60)
            print(f"Driving distance (OSRM): {drive_miles:.2f} miles (~{mins} min, no traffic)")
            return f"{drive_miles:.2f} mi."
        except Exception as e:
            print(f"Driving distance unavailable via OSRM: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Test the problematic address cleaning
if __name__ == "__main__":
    # Test the unit stripping on the problematic address
    test_addr = "101 The City Drive South Pavilion 3 Building 29, Orange, CA 92868"
    print("=== Testing address cleaning ===")
    cleaned = strip_unit(test_addr)
    print(f"Result: '{cleaned}'\n")
    
    # Try the full geocoding
    print("=== Full geocoding test ===")
    print_locations_and_distance(
        "12532 Citruswood Avenue, Garden Grove, CA 92840",
        "101 The City Drive South Pavilion 3 Building 29, Orange, CA 92868"
    )