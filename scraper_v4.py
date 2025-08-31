import re
import time
import os
import random
import math
from urllib.parse import urlencode, urljoin, quote_plus
from selenium.webdriver.common.keys import Keys
from typing import Dict, List

import pandas as pd
from geopy.geocoders import Nominatim
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib

# ===================== CONFIG =====================
LOCATION = "12532 Citruswood Avenue, Garden Grove, CA 92840"
RADIUS_MILES = 5
START_PAGE = 1
MAX_PAGES = 1            # 0 = no hard limit for Medicare / YP
GMAPS_MAX_SCROLLS = 10   # how many scroll passes to load more Google Maps results
WAIT_SECS = 20

# Extract the last part after the last comma
last_part = LOCATION.split(",")[-1].strip()

# If ZIP code is present, remove it (keep only city + state)
last_part = re.sub(r"\d{5}(?:-\d{4})?", "", last_part).strip()

# Replace spaces with underscores for filename safety
file_part = last_part.replace(" ", "_").replace(",", "")

OUTFILE = f"health_data_scraper_{file_part}.xlsx"

service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)
wait = WebDriverWait(driver, WAIT_SECS)

# Fix for Python 3.13 compatibility - use custom user agent
geolocator = Nominatim(user_agent="scraper_v3", timeout=10)

# ===================== COMMON HELPERS =====================
def text_or_none(elem):
    try:
        t = elem.text.strip()
        return t if t else None
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


ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
CITY_ST_ZIP_RE = re.compile(
    r"(?P<city>[A-Za-z .'\-&]+),\s*(?P<state>[A-Za-z]{2})(?:\s+(?P<zip>\d{5}))?$",
    re.I,
)

def extract_city_state_zip(location: str):
    """
    Returns (city, state, zipcode_or_None) from a location string that may contain a street.
    Examples:
      '12532 Citruswood Avenue, Garden Grove, CA 92840' -> ('Garden Grove','CA','92840')
      'San Diego, CA' -> ('San Diego','CA',None)
      '92101' -> (None,None,'92101')
      'San Diego' -> ('San Diego',None,None)
    """
    loc = " ".join(location.strip().split())

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


# ===================== MEDICARE =====================
selectors = {
    "scrollableElement": "div.results-container",
    "itemContainer": 'mat-card[id^="result-card-"]',
    "name": ".ProviderSearchResultsCardContainer-provider-name-link",
    "addressBlock": ".ProviderSearchResultCardContainer__first-address-block .ProviderAddress__address",
    "phone": ".ProviderSearchResultCardContainer__first-address-block .ProviderAddress__phone a",
    "distance": ".ProviderSearchResultCardContainer__distance",
    "specialty": ".PhysicianSpecialties__primary",
    "sourceUrl": ".ProviderSearchResultsCardContainer-provider-name-link",
}

def accept_cookies_if_present():
    try:
        btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        btn.click()
        time.sleep(0.4)
    except Exception:
        pass

def wait_for_results_cards():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors["itemContainer"])))

def scroll_results_container():
    try:
        container = driver.find_element(By.CSS_SELECTOR, selectors["scrollableElement"])
        for frac in (0.35, 0.7, 1.0):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight * arguments[1];", container, frac)
            time.sleep(0.3)
    except Exception:
        for frac in (0.35, 0.7, 1.0):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * arguments[0]);", frac)
            time.sleep(0.3)

# ----------------- Medicare: multi-type + keyword include -----------------
MEDICARE_PROVIDER_TYPES = [
    "Physician",
    "Hospital",
    "NursingHome",
    "HomeHealth",
    "Hospice",
    "DialysisFacility",
    "InpatientRehabilitation",
    "LongTermCare"   
]

# Optional: include-only keywords (case-insensitive). Empty list => include all.
MEDICARE_KEYWORDS = []

def build_url(location: str, radius: int, page: int = 1, provider_type: str = "Physician") -> str:
    city, state, zipcode = extract_city_state_zip(location)  

    params = [
        ("searchType", provider_type),
        ("page", str(page)),
    ]

    # Insert city/state/zip immediately after "page"
    if city:    params.append(("city", city))
    if state:   params.append(("state", state))
    if zipcode: params.append(("zipcode", zipcode))

    # Continue with the rest
    params.extend([
        ("radius", str(radius)),
        ("sort", "closest"),
        ("tealiumEventAction", "Result Page - Search"),
        ("tealiumSearchLocation", "search bar"),
        ("tealiumSearchInputType", "manual search term"),
    ])

    # Fallback if parsing failed
    if not (city or state or zipcode):
        if re.fullmatch(r"\d{5}(?:-\d{4})?", location.strip()):
            params.append(("zipcode", location.strip()[:5]))
        else:
            params.append(("city", location.strip()))
            
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    return f"https://www.medicare.gov/care-compare/results?{query_string}"

def _keyword_ok(row: Dict[str, str], keywords: list[str]) -> bool:
    if not keywords:
        return True
    hay = " ".join([
        (row.get("Name") or ""),
        (row.get("Specialty") or ""),
        (row.get("Address") or "")
    ]).lower()
    for kw in keywords:
        if kw and kw.lower() in hay:
            return True
    return False

def parse_card(card, provider_type="Physician") -> Dict[str, str]:
    # selectors
    name = source_url = specialty = phone = address = distance = None
    try:
        name_el = card.find_element(By.CSS_SELECTOR, selectors["name"])
        name = text_or_none(name_el)
        source_url = attr_or_none(name_el, "href")
    except Exception:
        try:
            alt = card.find_element(By.CSS_SELECTOR, "h3, h2, a[aria-label*='profile']")
            name = text_or_none(alt) or name
            source_url = attr_or_none(alt, "href") or source_url
        except Exception:
            pass
    
    try:
        spec_el = card.find_element(By.CSS_SELECTOR, selectors["specialty"])
        scraped_specialty = text_or_none(spec_el)
    except Exception:
        scraped_specialty = None

    try:
        phone_el = card.find_element(By.CSS_SELECTOR, selectors["phone"])
        phone = text_or_none(phone_el)
    except Exception:
        pass
    
    try:
        addr_el = card.find_element(By.CSS_SELECTOR, selectors["addressBlock"])
        address = text_or_none(addr_el)
    except Exception:
        pass

    try:
        dist_el = card.find_element(By.CSS_SELECTOR, selectors["distance"])
        distance = (dist_el.text or "").strip() or None
    except Exception:
        pass

    if str(provider_type).lower() == "physician":
        specialty = scraped_specialty or "Physician"
    else:
        specialty = pretty_provider_type(provider_type)

    return {
        "Provider type": provider_type,   # <--- new column
        "Name": name,
        "Specialty": specialty,
        "Contact number": phone,
        "Address": address,
        "Distance": distance,
        "Source URL": source_url,
    }

def extract_items_on_page(provider_type="Physician") -> List[Dict[str, str]]:
    cards = driver.find_elements(By.CSS_SELECTOR, selectors["itemContainer"])
    items = []
    for c in cards:
        item = parse_card(c, provider_type=provider_type)
        if item.get("Name"):
            items.append(item)
    return items

def scrape_medicare(
    provider_types: list[str] = MEDICARE_PROVIDER_TYPES,
    keywords: list[str] = MEDICARE_KEYWORDS
) -> List[Dict[str, str]]:
    all_rows: List[Dict[str, str]] = []

    for ptype in provider_types:
        page = START_PAGE
        while True:
            driver.get(build_url(LOCATION, RADIUS_MILES, page, provider_type=ptype))
            accept_cookies_if_present()
            try:
                wait_for_results_cards()
            except Exception:
                print(f"[Medicare:{ptype}] No cards on page {page}. Stopping this type.")
                break

            time.sleep(0.4); scroll_results_container(); time.sleep(0.4)

            rows = extract_items_on_page(provider_type=ptype)
            # apply keyword include filter (if any)
            rows = [r for r in rows if _keyword_ok(r, keywords)]

            if not rows:
                print(f"[Medicare:{ptype}] Empty page {page} after filtering. Stop.")
                break

            print(f"[Medicare:{ptype}] Page {page}: {len(rows)} items")
            all_rows.extend(rows)

            if MAX_PAGES and page >= MAX_PAGES:
                break
            page += 1

    # Deduplicate by (Name, Address, Provider type)
    seen, deduped = set(), []
    for r in all_rows:
        key = (r.get("Name"), r.get("Address"), r.get("Provider type"))
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


# ===================== YELLOW PAGES =====================
yp_selectors = {
    "itemContainer": "div.result",
    "name": "h2 a.business-name, .business-name",
    "address": "div.adr",
    "phone": "div.phone, .phones .phone",
    "distance": None,                        # not always present
    "lastPageIndicator": "li.next.disabled",
    "specialty": "div.categories a",         # categories => specialty tags
}

def build_yp_url(location: str, page: int = 1) -> str:
    base = "https://www.yellowpages.com/search"
    params = {
        "search_terms": "doctor",
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
    html = driver.page_source.lower()
    tokens = [
        "unusual activity", "verify you are", "robot check", "captcha",
        "access denied", "px-captcha"
    ]
    return any(t in html for t in tokens)

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

def yp_parse_card(card) -> Dict[str, str]:
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
        address = text_or_none(address_el)
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
    if yp_selectors["distance"]:
        try:
            d_el = card.find_element(By.CSS_SELECTOR, yp_selectors["distance"])
            distance = text_or_none(d_el)
        except Exception:
            pass
    if not distance:
        for sel in (".distance", "div.distance", ".info-primary .distance"):
            try:
                d_el = card.find_element(By.CSS_SELECTOR, sel)
                distance = text_or_none(d_el)
                if distance:
                    break
            except Exception:
                continue

    return {
        "Name": name,
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

def scrape_yellowpages():
    rows: List[Dict[str, str]] = []
    page = START_PAGE

    # Always load page 1 via URL (establishes session cookies), then click Next
    driver.get(build_yp_url(LOCATION, 1))
    try:
        _yp_wait_results()
    except Exception:
        print("No Yellow Pages results on page 1.")
        return rows

    while True:
        _yp_human_scroll()
        _human_sleep(0.3, 0.7)

        cards = driver.find_elements(By.CSS_SELECTOR, yp_selectors["itemContainer"])
        if not cards:
            # Might be rate-limited; back off once
            if _yp_is_block_page():
                print("[YellowPages] Block page detected; backing off and refreshing...")
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
            item = yp_parse_card(c)
            if item.get("Name"):
                page_rows.append(item)

        if not page_rows:
            print(f"[YellowPages] Empty results on page {page}.")
            break

        print(f"[YellowPages] Page {page}: {len(page_rows)} items")
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
            print("[YellowPages] Block page detected after Next; pausing and refreshing once...")
            _human_sleep(12, 22)
            driver.refresh()
            try:
                _yp_wait_results()
            except Exception:
                break

        page += 1

    # Deduplicate by (Name, Address)
    seen, deduped = set(), []
    for r in rows:
        key = (r.get("Name"), r.get("Address"))
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


# ===================== GOOGLE MAPS =====================
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
                    distance = f"{calc_distance} mi"

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

def scrape_google_maps(terms: List[str] = None) -> List[Dict[str, str]]:
    """
    Optimized Google Maps scraper:
    1. Fast distance calculation using coordinates
    2. Selective detail enrichment for missing data
    3. Batch processing for efficiency
    """
    if terms is None:
        terms = GMAPS_TERMS

    # Get origin coordinates
    origin_coords = get_coordinates_from_location(LOCATION)
    if not origin_coords:
        print("[GoogleMaps] Warning: Could not get origin coordinates")

    all_places = {}
    consent_done = False

    # Collect places from all search terms
    for term in terms:
        print(f"[GoogleMaps] Searching for: {term}")
        
        driver.get(build_gmaps_url(term, LOCATION))
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
        if data.get("Name"):  # Only include places with names
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


# ===================== RUN & EXPORT =====================
def run():
    try:
        # medicare_rows = scrape_medicare()
        # yp_rows = scrape_yellowpages()
        gmaps_rows = scrape_google_maps()

        # if not (medicare_rows or yp_rows or gmaps_rows):
        #     print("No data collected from any source.")
        #     return

        cols = ["Name", "Specialty", "Contact number", "Address", "Distance", "Source URL"]
        # df_medicare = pd.DataFrame(medicare_rows, columns=cols)
        # df_yp = pd.DataFrame(yp_rows, columns=cols)
        df_gmaps = pd.DataFrame(gmaps_rows, columns=cols)

        # Remove old file if present
        if os.path.exists(OUTFILE):
            os.remove(OUTFILE)

        with pd.ExcelWriter(OUTFILE, engine="openpyxl") as xw:
            # if not df_medicare.empty:
            #     df_medicare.to_excel(xw, sheet_name="Medicare", index=False)
            # if not df_yp.empty:
            #     df_yp.to_excel(xw, sheet_name="YellowPages", index=False)
            if not df_gmaps.empty:
                df_gmaps.to_excel(xw, sheet_name="GoogleMaps", index=False)

        print(f"\nSaved to: {OUTFILE}")
        # print(f"  Medicare:   {len(df_medicare)} rows")
        # print(f"  YellowPages:{len(df_yp)} rows")
        print(f"  GoogleMaps: {len(df_gmaps)} rows")

    finally:
        driver.quit()

if __name__ == "__main__":
    run()