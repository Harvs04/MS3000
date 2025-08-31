import time 
import random
import re

from urllib.parse import urlencode, urljoin
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# from browser import wait, driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, List
from helper import text_or_none, attr_or_none

# config imports 
from config import START_PAGE, LOCATION, MAX_PAGES

# helper imports 
from helper import clean_address

geolocator = Nominatim(user_agent="yellowpages_scraper")

# Define search terms for different healthcare categories
SEARCH_TERMS = [
    "hospitals",
    "pharmacies", 
    "clinics",
    "diagnostics",
    "doctors"
]

yp_selectors = {
    "itemContainer": "div.result",
    "name": "h2 a.business-name, .business-name",
    "address": "div.adr",
    "phone": "div.phone, .phones .phone",
    "distance": None,                        # not always present
    "lastPageIndicator": "li.next.disabled",
    "specialty": "div.categories a",         # categories => specialty tags
}

def build_yp_url(search_term: str, location: str, page: int = 1) -> str:
    base = "https://www.yellowpages.com/search"
    params = {
        "search_terms": search_term,
        "geo_location_terms": location,
        "page": str(page),
        "s": "distance",
    }
    return f"{base}?{urlencode(params)}"

def _human_sleep(a=1.2, b=2.8):
    time.sleep(random.uniform(a, b))

def _yp_wait_results():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, yp_selectors["itemContainer"])))

def _yp_is_last_page() -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR, yp_selectors["lastPageIndicator"])
        return True
    except Exception:
        return False

def _yp_is_block_page() -> bool:
    """Enhanced block detection"""
    html = driver.page_source.lower()
    tokens = [
        "unusual activity", "verify you are", "robot check", "captcha",
        "access denied", "px-captcha", "blocked", "security check",
        "please verify", "human verification", "too many requests"
    ]
    
    # Also check current URL for block indicators
    current_url = driver.current_url.lower()
    url_tokens = ["block", "captcha", "verify", "security"]
    
    return any(t in html for t in tokens) or any(t in current_url for t in url_tokens)

def _yp_click_next(prev_first_card=None) -> bool:
    # Stop if YP explicitly disables Next
    if _yp_is_last_page():
        return False

    # Try common next selectors
    candidates = [
        "a.next:not(.disabled)", "a[aria-label*='Next']:not(.disabled)",
        "//a[contains(@class,'next') and not(ancestor::li[contains(@class,'disabled')])]"
    ]
    clicked = False
    for sel in candidates:
        try:
            if sel.startswith("//"):
                el = driver.find_element(By.XPATH, sel)
            else:
                el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                _human_sleep(0.2, 0.6)
                el.click()
                clicked = True
                break
        except Exception:
            continue
    if not clicked:
        return False

    # Wait for pagination to actually change content
    try:
        if prev_first_card:
            wait.until(EC.staleness_of(prev_first_card))
        else:
            # fallback: wait for *some* result to be present again
            _yp_wait_results()
    except Exception:
        pass

    return True

def yp_parse_card(card, category: str) -> Dict[str, str]:
    # Name + link
    name, link = None, None
    try:
        name_el = card.find_element(By.CSS_SELECTOR, yp_selectors["name"])
        name = text_or_none(name_el)
        link = attr_or_none(name_el, "href")
        if link:
            link = urljoin("https://www.yellowpages.com", link)
    except Exception:
        pass

    # Address
    address = None
    try:
        address_el = card.find_element(By.CSS_SELECTOR, yp_selectors["address"])
        raw_address = text_or_none(address_el)
        address = clean_address(raw_address)
    except Exception:
        pass

    # Phone
    phone = None
    try:
        phone_el = card.find_element(By.CSS_SELECTOR, yp_selectors["phone"])
        phone = text_or_none(phone_el)
    except Exception:
        pass

    # Specialty from <div class="categories"><a>...</a></div>
    specialty = None
    try:
        cat_links = card.find_elements(By.CSS_SELECTOR, yp_selectors["specialty"])
        cats = [text_or_none(a) for a in cat_links]
        cats = [c for c in cats if c]
        if cats:
            # join all categories, keep order (unique)
            seen = {}
            for c in cats:
                if c and c not in seen:
                    seen[c] = True
            specialty = " | ".join(seen.keys())
    except Exception:
        pass

    # Distance (best-effort)
    distance = None
    if address and LOCATION:
        print(f"\naddress: {address}")
        print(f"location: {LOCATION}")
        
        try:
            # Get base location coordinates
            base_loc = geolocator.geocode(LOCATION)
            if base_loc:  # Check if geocoding succeeded
                base_coords = (base_loc.latitude, base_loc.longitude)
                print(f"base_coords: {base_coords}")
                
                # Try multiple formats for the doctor's address
                address_coords = None
                
                # Create version without suite/unit numbers using improved regex
                no_suite_address = re.sub(r'\s+(?:Ste\.?|Suite|Unit|Apt\.?|Apartment|#)\s*[A-Za-z0-9-]+', '', address, flags=re.IGNORECASE).strip()
                
                # List of address formats to try (prioritize formats most likely to work)
                address_formats = [
                    no_suite_address,
                    no_suite_address.replace(',', ''),  # No suite, no commas
                    no_suite_address + ", USA",  # No suite, with country
                    address,  # Original full address with suite
                    address.replace(',', ''),  # Full address, no commas
                    address + ", USA",  # Full address with country
                ]

                # Remove duplicates and None values
                unique_formats = []
                seen = set()
                for fmt in address_formats:
                    if fmt and fmt.strip() and fmt not in seen:
                        seen.add(fmt)
                        unique_formats.append(fmt.strip())
                
                # Try each format
                for i, addr_format in enumerate(unique_formats):
                    print(f"Trying format {i+1}/{len(unique_formats)}: {addr_format}")
                    
                    try:
                        address_loc = geolocator.geocode(addr_format)
                        if address_loc:  # Check if geocoding succeeded
                            address_coords = (address_loc.latitude, address_loc.longitude)
                            print(f"✓ Success! address_coords: {address_coords}")
                            break
                        else:
                            print(f"✗ No results for: {addr_format}")
                            
                    except Exception as geocode_error:
                        print(f"✗ Geocoding error for '{addr_format}': {geocode_error}")
                        continue
                        
                    # Small delay between attempts
                    time.sleep(0.5)
                
                # Calculate distance if both coordinates found
                if address_coords:
                    
                    point1 = base_coords
                    point2 = address_coords
                    
                    dist = geodesic(point1, point2).miles
                    distance = f"{round(dist, 1)} mi"
                    print(f"Geodesic Distance: {distance}")
                    
                else:
                    print("Could not geocode address with any format, trying city/state fallback...")
                    
                    # Fallback: try just city and state
                    try:
                        city_state_match = re.search(r'([A-Za-z\s]+,\s*[A-Z]{2})', address)
                        if city_state_match:
                            city_state = city_state_match.group(1).strip()
                            print(f"Trying city/state only: {city_state}")
                            
                            city_loc = geolocator.geocode(city_state)
                            if city_loc:
                                city_coords = (city_loc.latitude, city_loc.longitude)
                                dist = geodesic(base_coords, city_coords).miles
                                distance = f"~{round(dist, 1)} mi"  # ~ indicates approximate
                                print(f"Approximate distance to city center: {distance}")
                            else:
                                print(f"Could not geocode city/state: {city_state}")
                                
                    except Exception as fallback_error:
                        print(f"City/state fallback failed: {fallback_error}")
                        
            else:
                print(f"Could not geocode base location: {LOCATION}")
                
        except Exception as e:
            print(f"[Distance] Error calculating distance for {address}: {e}")

    return {
        "Name": name,
        "Category": category,  # Add category field
        "Specialty": specialty,
        "Contact number": phone,
        "Address": address,
        "Distance": distance,
        "Source URL": link,
    }

def _yp_human_scroll():
    # Small, random page scrolls to look human and trigger lazy bits
    for frac in (0.3, 0.65, 1.0):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight*arguments[0]);", frac)
        except Exception:
            pass
        _human_sleep(0.2, 0.6)

def scrape_category(search_term: str) -> List[Dict[str, str]]:
    """Scrape Yellow Pages for a specific category/search term"""
    rows: List[Dict[str, str]] = []
    page = START_PAGE
    consecutive_blocks = 0
    max_retries = 3

    print(f"\n{'='*50}")
    print(f"Scraping category: {search_term.upper()}")
    print(f"{'='*50}")

    # Try multiple times if we get blocked
    for attempt in range(max_retries):
        try:
            # Always load page 1 via URL (establishes session cookies), then click Next
            url = build_yp_url(search_term, LOCATION, 1)
            print(f"Loading: {url}")
            driver.get(url)
            _human_sleep(3, 6)  # Longer initial wait
            
            # Check for immediate block
            if _yp_is_block_page():
                consecutive_blocks += 1
                print(f"[BLOCKED] Attempt {attempt+1}: Block page detected immediately")
                if consecutive_blocks >= 2:
                    wait_time = 60 + (consecutive_blocks * 30)
                    print(f"Multiple blocks detected. Waiting {wait_time}s...")
                    _human_sleep(wait_time, wait_time + 30)
                else:
                    _human_sleep(20, 40)
                continue
            
            try:
                _yp_wait_results()
                consecutive_blocks = 0  # Reset on success
                break
            except Exception:
                print(f"No Yellow Pages results for {search_term} on page 1, attempt {attempt+1}")
                if attempt == max_retries - 1:
                    return rows
                _human_sleep(10, 20)
                continue
                
        except Exception as e:
            print(f"Error loading category {search_term}, attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                return rows
            _human_sleep(15, 30)
            continue

    while True:
        _yp_human_scroll()
        _human_sleep(0.3, 0.7)

        cards = driver.find_elements(By.CSS_SELECTOR, yp_selectors["itemContainer"])
        if not cards:
            # Might be rate-limited; back off once
            if _yp_is_block_page():
                print(f"[YellowPages-{search_term}] Block page detected; backing off and refreshing...")
                _human_sleep(10, 18)
                driver.refresh()
                try:
                    _yp_wait_results()
                except Exception:
                    break
                cards = driver.find_elements(By.CSS_SELECTOR, yp_selectors["itemContainer"])
                if not cards:
                    break
            else:
                break

        page_rows = []
        for c in cards:
            item = yp_parse_card(c, search_term)
            if item.get("Name"):
                page_rows.append(item)

        if not page_rows:
            print(f"[YellowPages-{search_term}] Empty results on page {page}.")
            break

        print(f"[YellowPages-{search_term}] Page {page}: {len(page_rows)} items")
        rows.extend(page_rows)

        # Stop if max pages reached
        if MAX_PAGES and page >= MAX_PAGES:
            break

        # Try clicking Next (preferred over constructing ?page=)
        first_card = cards[0] if cards else None
        if not _yp_click_next(prev_first_card=first_card):
            break

        # After navigation, quick human-like pause and sanity checks
        _human_sleep(1.8, 3.5)
        if _yp_is_block_page():
            print(f"[YellowPages-{search_term}] Block page detected after Next; pausing and refreshing once...")
            _human_sleep(12, 22)
            driver.refresh()
            try:
                _yp_wait_results()
            except Exception:
                break

        page += 1

    print(f"[YellowPages-{search_term}] Total items scraped: {len(rows)}")
    return rows

def scrape_yellowpages() -> List[Dict[str, str]]:
    """Scrape Yellow Pages for all healthcare categories with fresh browser sessions"""
    all_rows: List[Dict[str, str]] = []
    
    for i, search_term in enumerate(SEARCH_TERMS):
        print(f"\n{'='*60}")
        print(f"Starting category {i+1}/{len(SEARCH_TERMS)}: {search_term.upper()}")
        print(f"{'='*60}")
        
        # Import browser utilities (assuming they're available)
        from browser_v1 import create_driver, close_driver
        
        try:
            # Create fresh browser session for each category
            print(f"Creating new browser session for {search_term}...")
            global driver, wait
            driver = create_driver()
            
            # Re-initialize wait object with new driver
            from selenium.webdriver.support.ui import WebDriverWait
            wait = WebDriverWait(driver, 10)
            
            # Add some randomness to browser startup
            _human_sleep(2, 5)
            
            # Scrape this category
            category_rows = scrape_category(search_term)
            all_rows.extend(category_rows)
            
            print(f"Completed {search_term}: {len(category_rows)} items found")
            
        except Exception as e:
            print(f"Error scraping category {search_term}: {e}")
            
        finally:
            # Always close the browser after each category
            try:
                print(f"Closing browser session for {search_term}...")
                close_driver()
                _human_sleep(1, 3)
            except Exception as e:
                print(f"Error closing browser: {e}")
        
        # Delay between categories (even with fresh browser)
        if search_term != SEARCH_TERMS[-1]:  # Don't sleep after last category
            delay = 10 + random.randint(0, 10)  # 10-20 second delay
            print(f"Waiting {delay}s before starting next category...\n")
            time.sleep(delay)

    # Deduplicate by (Name, Address) across all categories
    seen, deduped = set(), []
    duplicates_removed = 0
    
    for r in all_rows:
        key = (r.get("Name"), r.get("Address"))
        if key not in seen:
            seen.add(key)
            deduped.append(r)
        else:
            duplicates_removed += 1
    
    print(f"\n{'='*50}")
    print(f"SCRAPING SUMMARY")
    print(f"{'='*50}")
    print(f"Total items found: {len(all_rows)}")
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Final unique items: {len(deduped)}")
    
    # Print category breakdown
    category_counts = {}
    for item in deduped:
        cat = item.get("Category", "Unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print(f"\nCategory breakdown:")
    for category, count in category_counts.items():
        print(f"  {category}: {count} items")
    
    return deduped