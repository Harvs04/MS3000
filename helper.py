import re 
import math
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import requests
from geopy.extra.rate_limiter import RateLimiter

ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
CITY_ST_ZIP_RE = re.compile(
    r"(?P<city>[A-Za-z .'\-&]+),\s*(?P<state>[A-Za-z]{2})(?:\s+(?P<zip>\d{5}))?$",
    re.I,
)

geolocator = Nominatim(user_agent="scraper_v3", timeout=10)

def text_or_none(elem):
    try:
        t = elem.text.strip()
        return t if t else None
    except Exception:
        return None
    
def text_or_none_medicare(elem):
    try:
        print("Elem: " + str(elem.text))
        t = elem.text.strip()
        print("Stripped text: " + str(t))
        # Replace newlines with spaces and clean up multiple spaces
        cleaned = t.replace('\n', ', ')
        # t = ' '.join(t.split()) if t else None
        return cleaned if cleaned else None 
    except Exception:
        return None

def attr_or_none(elem, attr):
    try:
        v = elem.get_attribute(attr)
        return v.strip() if v else None
    except Exception:
        return None
    
def pretty_provider_type(label: str) -> str:
    # "NursingHome" -> "Nursing Home", "LongTermCare" -> "Long Term Care"
    return re.sub(r"(?<!^)(?=[A-Z])", " ", label).strip()

def clean_address(address_text):
    """Clean and normalize address text"""
    if not address_text:
        return None
    
    # Remove extra whitespace and replace newlines with spaces
    cleaned = ' '.join(address_text.strip().split())
    
    # Remove multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip()

def extract_city_state_zip(location: str):
    """
    Returns (city, state, zipcode_or_None) from a location string that may contain a street.
    Examples:
      '12532 Citruswood Avenue, Garden Grove, CA 92840' -> ('Garden Grove','CA','92840')
      '12532 Citruswood Avenue, Garden Grove, CA 92840, United States' -> ('Garden Grove','CA','92840')
      'San Diego, CA' -> ('San Diego','CA',None)
      '92101' -> (None,None,'92101')
      'San Diego' -> ('San Diego',None,None)
    """
    if not location:
        return (None, None, None)
    
    # Remove ", United States" suffix if present (case insensitive)
    loc = location.strip()
    if loc.lower().endswith(", united states"):
        loc = loc[:-15]  # Remove ", United States"
    elif loc.lower().endswith(",united states"):
        loc = loc[:-14]  # Remove ",United States" (no space after comma)
    
    loc = " ".join(loc.strip().split())

    # ZIP-only input
    m = re.fullmatch(r"\d{5}(?:-\d{4})?", loc)
    if m:
        return (None, None, m.group(0)[:5])

    # Try to find the last "City, ST [ZIP]" anywhere in the string
    last_match = None
    for match in CITY_ST_ZIP_RE.finditer(loc):
        last_match = match
    if last_match:
        city = last_match.group("city").strip()
        state = last_match.group("state").upper()
        z = last_match.group("zip")
        zipcode = z[:5] if z else None
        return (city, state, zipcode)

    # Heuristic: split by commas and parse the tail parts
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if len(parts) >= 2:
        tail = parts[-1]                             # e.g. "CA 92840" or "CA"
        head = parts[-2]                             # e.g. "Garden Grove"
        m2 = re.match(r"^(?P<state>[A-Za-z]{2})(?:\s+(?P<zip>\d{5}))?$", tail)
        if m2:
            city = head
            state = m2.group("state").upper()
            z = m2.group("zip")
            zipcode = z[:5] if z else None
            return (city, state, zipcode)

    # Fallbacks: "City, ST" without ZIP or just a city word
    m3 = re.search(r"([A-Za-z .'\-&]+),\s*([A-Za-z]{2})\b", loc)
    if m3:
        return (m3.group(1).strip(), m3.group(2).upper(), None)

    # last resort: treat whole input as city
    return (loc, None, None)

def extract_address(full_address: str):
    if not full_address:
        return None
    return full_address.split(",")[0].strip()

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate straight-line distance between two points in miles"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return round(c * 3956, 1)  # Earth radius in miles

def get_coordinates_from_location(location_str: str):
    """Return latitude and longitude for a given location dynamically."""
    if not location_str or not location_str.strip():
        return None
        
    try:
        location = geolocator.geocode(location_str, timeout=10)
        if location:
            return (location.latitude, location.longitude)
        else:
            print(f"[Geocoding] No results found for: {location_str}")
            return None
            
    except GeocoderTimedOut:
        print(f"[Geocoding] Timeout for: {location_str}")
        return None
    except GeocoderServiceError as e:
        print(f"[Geocoding] Service error for {location_str}: {e}")
        return None
    except Exception as e:
        print(f"[Geocoding] Unexpected error for {location_str}: {e}")
        return None
    
def format_address_for_geocoding(address):
    """Format address to improve geocoding success"""
    if not address:
        return None
    
    # Clean the address first
    cleaned = ' '.join(address.strip().split())
    
    # Add comma between street number/name and city if missing
    # Pattern: "123 Street Name City, State ZIP" -> "123 Street Name, City, State ZIP"
    
    # Look for pattern: street address followed by city name (no comma)
    # This regex finds: "Harbor Blvd Garden Grove" and adds comma: "Harbor Blvd, Garden Grove"
    formatted = re.sub(r'([A-Za-z]+\s+[A-Za-z]+)\s+([A-Za-z]+\s+[A-Za-z]+,\s*[A-Z]{2}\s+\d{5})', 
                      r'\1, \2', cleaned)
    
    return formatted





# MEDICARE HELPERS

# geolocator = Nominatim(user_agent="geo-no-key-example", timeout=15)
# geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.0)

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

# def calculate_locations_and_distance(a: str, b: str):
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
#             return f"{drive_miles:.2f}"
#         except Exception as e:
#             print(f"Driving distance unavailable via OSRM: {e}")
#     except Exception as e:
#         print(f"Error: {e}")

geolocator = Nominatim(user_agent="geo-no-key-example (you@example.com)", timeout=15)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.0, swallow_exceptions=False)

# Units/buildings (broader)
UNIT_PAT = re.compile(
    r"(?:\b(?:suite|ste|unit|apt|apartment|bldg|building|tower|pav(?:ilion)?|fl|floor|room|dept|department)\b[\s.:#-]*[A-Za-z0-9-]*)"
    r"|(?:\#[ ]?[A-Za-z0-9-]+)",
    flags=re.IGNORECASE,
)

def strip_unit(addr: str) -> str:
    no_unit = UNIT_PAT.sub("", addr)
    no_unit = re.sub(r"\s{2,}", " ", no_unit).strip()
    no_unit = re.sub(r",\s*,+", ", ", no_unit)  # fix ", ,"
    return no_unit

def normalize_address_for_osm(addr: str) -> str:
    """Heuristics to match OSM naming (esp. UCI’s 'The City Dr S')."""
    a = addr
    # Street type → abbreviations
    repl = {
        r"\bStreet\b": "St", r"\bAvenue\b": "Ave", r"\bBoulevard\b": "Blvd",
        r"\bPlace\b": "Pl", r"\bRoad\b": "Rd", r"\bDrive\b": "Dr",
        r"\bLane\b": "Ln", r"\bCourt\b": "Ct", r"\bParkway\b": "Pkwy",
        r"\bHighway\b": "Hwy",
    }
    for pat, rep in repl.items():
        a = re.sub(pat, rep, a, flags=re.IGNORECASE)
    # Cardinal directions
    a = re.sub(r"\bNorth\b", "N", a, flags=re.IGNORECASE)
    a = re.sub(r"\bSouth\b", "S", a, flags=re.IGNORECASE)
    a = re.sub(r"\bEast\b", "E", a, flags=re.IGNORECASE)
    a = re.sub(r"\bWest\b", "W", a, flags=re.IGNORECASE)
    # Special-case this corridor
    a = re.sub(r"\bThe City Dr(?:ive)?\s*S(?:outh)?\b", "The City Dr S", a, flags=re.IGNORECASE)
    # Tidy
    a = re.sub(r"\s{2,}", " ", a).strip()
    a = re.sub(r",\s*,+", ", ", a)
    return a

def try_structured_us(addr: str):
    """
    Parse 'street, city, state zip' → structured Nominatim query.
    Returns geopy Location or None.
    """
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    if len(parts) < 3:
        return None
    street = parts[0]
    city = parts[1]
    tail = parts[2]
    m = re.search(r"\b([A-Z]{2})\b(?:\s+(\d{5})(?:-\d{4})?)?", tail, re.IGNORECASE)
    if not m:
        return None
    state = m.group(1).upper()
    postal = m.group(2)
    q = {"street": street, "city": city, "state": state, "country": "USA"}
    if postal:
        q["postalcode"] = postal
    try:
        return geocode(q, exactly_one=True, addressdetails=False)
    except Exception:
        return None

# ---- No-key fallbacks ----
def photon_geocode(addr: str):
    try:
        r = requests.get(
            "https://photon.komoot.io/api",
            params={"q": addr, "limit": 1},
            headers={"User-Agent": "geo-no-key-example"},
            timeout=15,
        )
        r.raise_for_status()
        js = r.json()
        feats = js.get("features", [])
        if not feats:
            return None
        f = feats[0]
        lon, lat = f["geometry"]["coordinates"]
        props = f.get("properties", {})
        # assemble a friendly label
        street = (props.get("housenumber", "") + " " + (props.get("street") or "")).strip()
        city = props.get("city") or props.get("county") or ""
        state = props.get("state") or ""
        postcode = props.get("postcode") or ""
        label = ", ".join([s for s in [street, city, state, postcode] if s]) or props.get("name") or addr
        return (lat, lon, label)
    except Exception:
        return None

def census_geocode(addr: str):
    try:
        r = requests.get(
            "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
            params={"address": addr, "benchmark": "Public_AR_Current", "format": "json"},
            headers={"User-Agent": "geo-no-key-example"},
            timeout=15,
        )
        r.raise_for_status()
        js = r.json()
        matches = js.get("result", {}).get("addressMatches", [])
        if not matches:
            return None
        m = matches[0]
        lon, lat = m["coordinates"].get("x"), m["coordinates"].get("y")
        if lon is None or lat is None:
            return None
        return (lat, lon, m.get("matchedAddress") or addr)
    except Exception:
        return None

def get_coordinates(addr: str):
    """Return (lat, lon, normalized_address) for the address."""
    cleaned = strip_unit(addr)

    # 1) Structured US
    loc = try_structured_us(cleaned)
    if loc:
        return loc.latitude, loc.longitude, getattr(loc, "address", cleaned)

    # 2) Nominatim – cleaned, US-biased
    loc = geocode(cleaned + ", USA", exactly_one=True, addressdetails=False, country_codes="us")
    if loc:
        return loc.latitude, loc.longitude, getattr(loc, "address", cleaned)

    # 3) OSM-normalized string (e.g., 'The City Dr S')
    normalized = normalize_address_for_osm(cleaned)
    loc = geocode(normalized + ", USA", exactly_one=True, addressdetails=False, country_codes="us")
    if loc:
        return loc.latitude, loc.longitude, getattr(loc, "address", normalized)

    # 4) Original (US-biased)
    loc = geocode(addr + ", USA", exactly_one=True, addressdetails=False, country_codes="us")
    if loc:
        return loc.latitude, loc.longitude, getattr(loc, "address", addr)

    # 5) No-key fallbacks
    ph = photon_geocode(cleaned)
    if ph:
        return ph
    cz = census_geocode(cleaned)
    if cz:
        return cz

    raise ValueError(f"Could not geocode: {addr}")

def osrm_driving_distance_miles(lat1, lon1, lat2, lon2, base_url="https://router.project-osrm.org"):
    """Returns (miles, seconds). No API key. OSRM public demo server = best-effort only."""
    url = f"{base_url}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "false", "alternatives": "false", "steps": "false"}
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

def calculate_locations_and_distance(a: str, b: str):
    try:
        lat1, lon1, addr1 = get_coordinates(a)
        lat2, lon2, addr2 = get_coordinates(b)
        print(f"Base:   {addr1} -> ({lat1:.6f}, {lon1:.6f})")
        print(f"Target: {addr2} -> ({lat2:.6f}, {lon2:.6f})")
        try:
            drive_miles, secs = osrm_driving_distance_miles(lat1, lon1, lat2, lon2)
            mins = round(secs / 60)
            print(f"Driving distance (OSRM): {drive_miles:.2f} miles (~{mins} min, no traffic)")
            return f"{drive_miles:.2f}"
        except Exception as e:
            print(f"Driving distance unavailable via OSRM: {e}")
    except Exception as e:
        print(f"Error: {e}")