import re
import time
import math
from typing import Dict, List
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# config imports
from config import WAIT_SECS, GMAPS_MAX_SCROLLS, LOCATION

# helper imports
from helper import geolocator, haversine_distance, get_coordinates_from_location, text_or_none, attr_or_none

# browser imports
from browser import wait, driver

# Google Maps configuration
g_selectors = {
    "scrollableElement": '[role="feed"], .m6QErb[data-value="search"]',
    "itemContainer": '[data-result-index], .Nv2PK, .lI9IFe, [jsaction*="mouseover"]',
    "name": ".qBF1Pd, .fontHeadlineSmall, .qzuQzc, .LkjzGb",
    "infoContainer": ".W4Efsd:not(:has(.MW4etd)), .W4Efsd:not(:has(.AJB7ye)), .CsEnBe, .xltbub",
    "phone": ".UsdlK",
    "sourceUrl": 'a[data-value="directions"], .hfpxzc, a[href*="/maps/place/"]',
    "distance": '.UY7F9, .O1htCb, [data-value*="km"], [data-value*="mi"]',
    "lastPageIndicator": '.HlvSq, [data-value="no_more_results"]',
}

GMAPS_TERMS = [
    "Doctors",
    "Hospitals",
    "Clinics",
    "Healthcare facilities",
    "Medical Center",
    "Urgent Care",
    "Primary Care",
]

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
    try:
        location = geolocator.geocode(location_str)
        if location:
            return (location.latitude, location.longitude)
    except Exception as e:
        print(f"[Geocoding] Error: {e}")
    return None

def extract_coordinates_from_gmaps_url(url):
    """Extract lat/lng from Google Maps place URL"""
    try:
        # Pattern: @lat,lng,zoom
        match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+),', url)
        if match:
            return (float(match.group(1)), float(match.group(2)))
        
        # Pattern: !3d lat !4d lng
        lat_match = re.search(r'!3d(-?\d+\.\d+)', url)
        lng_match = re.search(r'!4d(-?\d+\.\d+)', url)
        if lat_match and lng_match:
            return (float(lat_match.group(1)), float(lng_match.group(1)))
        
        return None
    except:
        return None

def build_gmaps_url(term: str, location: str) -> str:
    """Build Google Maps search URL"""
    return f"https://www.google.com/maps/search/{quote_plus(term)}+in+{quote_plus(location)}"

def gmaps_accept_consent_if_any():
    """Handle Google consent dialogs"""
    try:
        for sel in ['button[aria-label*="Accept"]', 'button:contains("I agree")', '#L2AGLb', 'button[aria-label*="Agree"]']:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                for b in btns:
                    if b.is_displayed():
                        b.click()
                        time.sleep(0.4)
                        return
            except:
                continue
    except:
        pass

def gmaps_wait_results():
    """Wait for Google Maps results to load"""
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, g_selectors["scrollableElement"])))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, g_selectors["itemContainer"])))

def gmaps_get_feed_container():
    """Get the scrollable results container"""
    try:
        return driver.find_element(By.CSS_SELECTOR, g_selectors["scrollableElement"])
    except:
        return None

def _looks_like_address(s: str) -> bool:
    """Heuristic to identify address-like text"""
    if not s:
        return False
    s = s.strip()
    return bool(
        re.search(r'\d', s) or
        re.search(r'\bCA\b', s, flags=re.I) or
        any(city in s for city in ["San Diego", "Garden Grove", "Los Angeles"])
    )

def gmaps_parse_card(card) -> Dict[str, str]:
    """Parse individual Google Maps result card"""
    # Extract name
    name = None
    for sel in g_selectors["name"].split(","):
        sel = sel.strip()
        try:
            el = card.find_element(By.CSS_SELECTOR, sel)
            name = text_or_none(el)
            if name:
                break
        except:
            continue

    # Extract info text (contains address and category info)
    info_text = None
    for sel in g_selectors["infoContainer"].split(","):
        sel = sel.strip()
        try:
            el = card.find_element(By.CSS_SELECTOR, sel)
            info_text = text_or_none(el)
            if info_text:
                break
        except:
            continue

    # Parse address and specialty from info text
    address, specialty = None, None
    if info_text:
        parts = [p.strip() for p in re.split(r'[\n|•·]', info_text) if p.strip()]
        
        # Find address (longest part that looks like an address)
        address_candidates = [p for p in parts if _looks_like_address(p)]
        if address_candidates:
            address = max(address_candidates, key=len)
        
        # Find specialty (medical category keywords)
        medical_keywords = [
            "Doctor", "Clinic", "Physician", "Dentist", "Cardiology", "Dermatology", 
            "Pediatric", "Surgeon", "Family", "Internal", "Orthopedic", "Urology", 
            "Gynecol", "Psychiatrist", "Optometry", "Chiropractor", "Oncology", "Neurology", 
            "Endocrine", "Gastro", "Pulmonary", "Rheumatic", "Radiology", "Nephrology", 
            "Ophthalmology", "Emergency", "Urgent", "Primary Care", "Medical Center"
        ]
        for p in parts:
            if any(keyword.lower() in p.lower() for keyword in medical_keywords):
                specialty = p
                break

    # Extract phone (rarely available in list view)
    phone = None
    try:
        el = card.find_element(By.CSS_SELECTOR, g_selectors["phone"])
        phone = text_or_none(el)
    except:
        pass

    # Extract distance from list view
    distance = None
    for sel in g_selectors["distance"].split(","):
        sel = sel.strip()
        try:
            el = card.find_element(By.CSS_SELECTOR, sel)
            distance = text_or_none(el)
            if distance and (" mi" in distance or " km" in distance):
                break
        except:
            continue

    # Extract source URL (prefer place links)
    source_url = None
    try:
        el = card.find_element(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
        source_url = attr_or_none(el, "href")
    except:
        # Fallback to other link selectors
        for sel in g_selectors["sourceUrl"].split(","):
            sel = sel.strip()
            try:
                el = card.find_element(By.CSS_SELECTOR, sel)
                href = attr_or_none(el, "href")
                if href:
                    source_url = href
                    break
            except:
                continue

    return {
        "Name": name,
        "Specialty": specialty,
        "Contact number": phone,
        "Address": address,
        "Distance": distance,
        "Source URL": source_url,
    }

def _gmaps_parse_detail_tab() -> dict:
    """Extract detailed information from Google Maps place page"""
    # Extract name
    try:
        name = text_or_none(WebDriverWait(driver, WAIT_SECS).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(@class,'DUwDvf')]"))
        ))
    except:
        name = None

    # Extract address
    address = None
    address_selectors = [
        "//button[@data-item-id='address']//div[contains(@class,'fontBodyMedium')]",
        "//div[contains(@aria-label,'Address') and contains(@class,'fontBodyMedium')]",
        "//button[contains(@aria-label,'Address')]/div",
        "//a[contains(@href,'https://maps.google.com') and contains(@aria-label,'Address')]",
    ]
    for xp in address_selectors:
        try:
            el = driver.find_element(By.XPATH, xp)
            address = text_or_none(el)
            if address:
                break
        except:
            continue

    # Extract phone
    phone = None
    phone_selectors = [
        "//button[contains(@data-item-id,'phone:tel')]//div[contains(@class,'fontBodyMedium')]",
        "//a[starts-with(@href,'tel:')]",
        "//button[contains(@aria-label,'Phone')]/div",
    ]
    for xp in phone_selectors:
        try:
            el = driver.find_element(By.XPATH, xp)
            phone = text_or_none(el)
            if not phone:
                href = el.get_attribute("href") or ""
                if href.startswith("tel:"):
                    phone = href.replace("tel:", "").strip()
            if phone:
                break
        except:
            continue

    # Extract specialty/category
    specialty = None
    specialty_selectors = [
        "//button[contains(@aria-label,'Category') or contains(@aria-label,'Categories')]",
        "//div[contains(@class,'W4Efsd')]/span[contains(@class,'fontBodyMedium')][1]",
    ]
    for xp in specialty_selectors:
        try:
            el = driver.find_element(By.XPATH, xp)
            al = (el.get_attribute("aria-label") or "").strip()
            if al:
                m = re.sub(r'^(Category|Categories):\s*', '', al).strip()
                if m:
                    specialty = m
                    break
            txt = text_or_none(el)
            if txt:
                specialty = txt
                break
        except:
            continue

    return {
        "Name": name,
        "Address": address,
        "Contact number": phone,
        "Specialty": specialty,
    }

def _gmaps_collect_from_list_optimized(container, origin_coords) -> Dict[str, Dict[str, str]]:
    """Collect all places from Google Maps results with fast distance calculation"""
    store = {}
    prev_count = -1
    stable_rounds = 0

    for _ in range(GMAPS_MAX_SCROLLS):
        try:
            cards = container.find_elements(By.CSS_SELECTOR, g_selectors["itemContainer"])
        except:
            cards = []

        for card in cards:
            # Get place URL (must have /maps/place/ for coordinate extraction)
            place_url = None
            try:
                a = card.find_element(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                place_url = attr_or_none(a, "href")
            except:
                continue

            if not place_url or place_url in store:
                continue

            # Parse card data
            card_data = gmaps_parse_card(card)
            
            # Calculate distance using coordinates (fast method)
            distance = card_data.get("Distance")  # Use list distance as fallback
            if origin_coords:
                place_coords = extract_coordinates_from_gmaps_url(place_url)
                if place_coords:
                    calc_distance = haversine_distance(
                        origin_coords[0], origin_coords[1],
                        place_coords[0], place_coords[1]
                    )
                    distance = f"{calc_distance}"

            store[place_url] = {
                "Name": card_data.get("Name"),
                "Specialty": card_data.get("Specialty"),
                "Contact number": card_data.get("Contact number"),
                "Address": card_data.get("Address"),
                "Distance": distance,
                "Source URL": place_url,
            }

        # Check if we're getting new results
        count = len(cards)
        if count == prev_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
        if stable_rounds >= 2:
            break
        prev_count = count

        # Scroll to load more results
        try:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", container)
        except:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)

    return store

def _gmaps_enrich_details_batch(place_data, batch_size=3):
    """Enrich places with detailed info, processing in batches"""
    enriched = {}
    main_window = driver.current_window_handle
    
    # Only enrich places that need phone or address
    need_enrichment = {
        url: data for url, data in place_data.items()
        if not data.get("Contact number") or not data.get("Address") or not data.get("Specialty")
    }
    
    if not need_enrichment:
        return place_data

    print(f"[GoogleMaps] Enriching {len(need_enrichment)} places with detailed info")
    
    urls = list(need_enrichment.keys())
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i+batch_size]
        
        for url in batch:
            try:
                driver.execute_script("window.open(arguments[0], '_blank');", url)
                driver.switch_to.window(driver.window_handles[-1])
                
                detail = _gmaps_parse_detail_tab()
                
                # Merge detailed info with existing data
                base_data = place_data[url]
                enriched[url] = {
                    "Name": detail.get("Name") or base_data.get("Name"),
                    "Specialty": detail.get("Specialty") or base_data.get("Specialty") or "Healthcare Provider",
                    "Contact number": detail.get("Contact number") or base_data.get("Contact number"),
                    "Address": detail.get("Address") or base_data.get("Address"),
                    "Distance": base_data.get("Distance"),
                    "Source URL": url,
                }
                
                driver.close()
                driver.switch_to.window(main_window)
                time.sleep(0.2)
                
            except:
                try:
                    driver.close()
                    driver.switch_to.window(main_window)
                except:
                    pass
                # Use original data if enrichment fails
                enriched[url] = place_data[url]
    
    # Add non-enriched places back
    for url, data in place_data.items():
        if url not in enriched:
            enriched[url] = data
    
    return enriched

def scrape_google_maps(location, limit, radius_miles, terms: List[str] = None) -> List[Dict[str, str]]:
    """
    Optimized Google Maps scraper:
    1. Fast distance calculation using coordinates
    2. Selective detail enrichment for missing data
    3. Batch processing for efficiency
    """
    if terms is None:
        terms = GMAPS_TERMS

    # Get origin coordinates
    origin_coords = get_coordinates_from_location(location)
    if not origin_coords:
        print("[GoogleMaps] Warning: Could not get origin coordinates")

    all_places = {}
    consent_done = False

    # Collect places from all search terms
    for term in terms:
        print(f"[GoogleMaps] Searching for: {term}")
        
        driver.get(build_gmaps_url(term, location))
        if not consent_done:
            gmaps_accept_consent_if_any()
            consent_done = True

        try:
            gmaps_wait_results()
        except:
            print(f"[GoogleMaps] No results for '{term}'")
            continue

        container = gmaps_get_feed_container()
        if not container:
            print(f"[GoogleMaps] No results container for '{term}'")
            continue

        # Collect places with fast distance calculation
        term_places = _gmaps_collect_from_list_optimized(container, origin_coords)
        print(f"[GoogleMaps] Found {len(term_places)} places for '{term}'")
        
        # Merge with existing places (avoid duplicates)
        for url, data in term_places.items():
            if url not in all_places:
                all_places[url] = data

    if not all_places:
        print("[GoogleMaps] No places found")
        return []

    print(f"[GoogleMaps] Total unique places: {len(all_places)}")

    # Enrich places that need more detailed information
    enriched_places = _gmaps_enrich_details_batch(all_places, batch_size=3)

    # Convert to list and filter valid entries
    results = []
    for url, data in enriched_places.items():
        if data.get("Name") and float(data.get('Distance')) <= radius_miles and len(results) < int(limit):  # Only include those who pass these.
            results.append(data)

    # Deduplicate by name and address
    seen = set()
    deduped = []
    for r in results:
        key = (r.get("Name"), r.get("Address"))
        if key not in seen and r.get("Name"):
            seen.add(key)
            deduped.append(r)

    print(f"[GoogleMaps] Final results: {len(deduped)} unique healthcare providers")
    return deduped