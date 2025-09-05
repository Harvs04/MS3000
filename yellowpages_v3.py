import time 
import random
import re

from urllib.parse import urlencode, urljoin
from geopy.geocoders import Nominatim

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, List
from helper import text_or_none, attr_or_none
from browser import create_driver, create_wait

# config imports 
from config import START_PAGE, LOCATION, MAX_PAGES

# helper imports 
from helper import extract_city_state_zip, extract_address, calculate_locations_and_distance

driver = create_driver()
wait = create_wait(driver)
geolocator = Nominatim(user_agent="yellowpages_scraper")

yp_selectors = {
    "itemContainer": "div.result:not(.flash-endt)",
    "name": "h2 a.business-name, .business-name",
    "address": "div.adr",
    "phone": "div.phone, .phones .phone",
    "distance": None,                       
    "lastPageIndicator": "li.next.disabled",
    "specialty": "div.categories a",   
}

def build_yp_url(location: str, keyword: str, page: int = 1):
    base = "https://www.yellowpages.com/search"
    params = {
        "search_terms": keyword,
        "geo_location_terms": location,
        "page": str(page),
        "s": "distance",
    }
    return f"{base}?{urlencode(params)}"

def _human_sleep(a=1.2, b=2.8):
    time.sleep(random.uniform(a, b))

def _yp_wait_results():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, yp_selectors["itemContainer"])))

def _yp_is_last_page():
    try:
        driver.find_element(By.CSS_SELECTOR, yp_selectors["lastPageIndicator"])
        return True
    except Exception:
        return False

def _yp_is_block_page():
    html = driver.page_source.lower()
    tokens = [
        "unusual activity", "verify you are", "robot check", "captcha",
        "access denied", "px-captcha"
    ]
    return any(t in html for t in tokens)

def _yp_click_next(prev_first_card=None):
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

def yp_parse_card(card, location):
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
        address_el = card.find_element(By.CSS_SELECTOR, yp_selectors['address'])
        # Grab street and locality (in order), trim, and join with ", "
        parts = []
        for sel in (".street-address", ".locality"):
            el = address_el.find_element(By.CSS_SELECTOR, sel)
            txt = (el.text or el.get_attribute("innerText") or "").strip()
            if txt:
                parts.append(txt)

        address = ", ".join(parts)
    except Exception:
        pass

    # Phone
    phone = None
    try:
        phone_el = card.find_element(By.CSS_SELECTOR, yp_selectors["phone"])
        phone = text_or_none(phone_el)
    except Exception:
        pass

    # Specialty
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

    # Distance
    distance = None
    if address and location:
        try:
            calculated_distance = calculate_locations_and_distance(location, address)
            if calculated_distance:
                distance = calculated_distance
                
        except Exception as e:
            print(f"[Distance] Error calculating distance for {address}: {e}")
            
    city, state, zip = extract_city_state_zip(address)
    return {
        "Name": name,
        "Mileage": distance,
        "Address": extract_address(address),
        "City": city,
        "State": state,
        "Zip": zip,
        "Phone Number": phone,
        "Specialty": specialty,
        "Full Address": address
    }

def _yp_human_scroll():
    # Small, random page scrolls to look human and trigger lazy bits
    for frac in (0.3, 0.65, 1.0):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight*arguments[0]);", frac)
        except Exception:
            pass
        _human_sleep(0.2, 0.6)

def scrape_yellowpages(location, keyword, limit, radius_miles):
    rows: List[Dict[str, str]] = []
    page = START_PAGE

    # Always load page 1 via URL (establishes session cookies), then click Next
    driver.get(build_yp_url(location, keyword, 1))
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
            item = yp_parse_card(c, location)
            if item.get('Mileage'):
                if item.get("Name") and float(item.get('Mileage')) <= radius_miles and len(page_rows) < int(limit):
                    page_rows.append(item)
                if len(page_rows) >= int(limit):
                    break

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