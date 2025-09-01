import time 
import random
import re

from urllib.parse import urlencode, urljoin
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from typing import Dict, List
from helper import text_or_none, attr_or_none
from browser import create_driver, create_wait

# config imports 
from config import START_PAGE, MAX_PAGES

# helper imports 
from helper import extract_city_state_zip, extract_address, calculate_locations_and_distance

opts = Options()
opts.add_argument("--lang=en-US")
opts.add_experimental_option("prefs", {"intl.accept_languages": "en-US,en"})

driver = webdriver.Chrome(options=opts)

# driver = create_driver()
wait = create_wait(driver)
geolocator = Nominatim(user_agent="healthgrades_scraper")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# Timezone & locale (CDP)
driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "America/New_York"})
try:
    driver.execute_cdp_cmd("Emulation.setLocaleOverride", {"locale": "en-US"})
except Exception:
    pass

hg_selectors = {
    "itemContainer": ".nXvFk4bhgUAwE5wE > div",
    "name": '[data-qa-target="provider-name"] a',
    "address": '[data-qa-target="location-info-address"]',
    "phone": None,
    "distance": '[data-qa-target="location-info-distance"]',                       
    "lastPageIndicator": '[data-qa-target*="last-page"]',
    "specialty": '[data-qa-target="provider-specialty"]'
}

# https://www.healthgrades.com/usearch?what=dentist&where=New%20York%2C%20NY&pt=40.7465%2C-74.0014&distances=5&pageNum=1&sort.provider=bestmatch&state=NY
def build_hg_url(location: str, keyword: str, radius: int, page: int = 1):
    base = "https://www.healthgrades.com/usearch"
    params = {
        "what": keyword,
        "where": location,
        "distances": radius,
        "pageNum": str(page),
        "sort.provider": "bestmatch",
    }
    return f"{base}?{urlencode(params)}"

def _human_sleep(a=1.2, b=2.8):
    time.sleep(random.uniform(a, b))

def _hg_wait_results():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, hg_selectors["itemContainer"])))

def _hg_is_last_page():
    try:
        driver.find_element(By.CSS_SELECTOR, hg_selectors["lastPageIndicator"])
        return True
    except Exception:
        return False

def _hg_is_block_page() -> bool:
    html = driver.page_source.lower()
    tokens = [
        "unusual activity", "verify you are", "robot check", "captcha",
        "access denied", "px-captcha"
    ]
    return any(t in html for t in tokens)

def _hg_click_next(prev_first_card=None) -> bool:
    # Stop if YP explicitly disables Next
    if _hg_is_last_page():
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
            _hg_wait_results()
    except Exception:
        pass

    return True

def hg_parse_card(card, location) -> Dict[str, str]:
    # Name + link
    name, link = None, None
    try:
        name_el = card.find_element(By.CSS_SELECTOR, hg_selectors["name"])
        name = text_or_none(name_el)
        link = attr_or_none(name_el, "href")
        if link:
            link = urljoin("https://www.healthgrades.com", link)
    except Exception:
        pass

    # Address
    address = None
    try:
        # address_el = card.find_element(By.CSS_SELECTOR, hg_selectors["address"])
        # print("Address El: " + address_el)
        # raw_address = text_or_none(address_el)
        # address = clean_address(raw_address)

        address_el = card.find_element(By.CSS_SELECTOR, hg_selectors['address'])

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
        phone_el = card.find_element(By.CSS_SELECTOR, hg_selectors["phone"])
        phone = text_or_none(phone_el)
    except Exception:
        pass

    # Specialty from <div class="categories"><a>...</a></div>
    specialty = None
    try:
        cat_links = card.find_elements(By.CSS_SELECTOR, hg_selectors["specialty"])
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
    try:
        distance = card.find_element(By.CSS_SELECTOR, hg_selectors["distance"])
        phone = text_or_none(distance)
    except Exception:
        pass
    
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

def _hg_human_scroll():
    # Small, random page scrolls to look human and trigger lazy bits
    for frac in (0.3, 0.65, 1.0):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight*arguments[0]);", frac)
        except Exception:
            pass
        _human_sleep(0.2, 0.6)

def scrape_healthgrades(location, keywords, limit, radius_miles):
    print("Location: " + location)
    print(f"Keywords: {keywords}")
    print(f"Limit: {limit}")
    print(f"radius: {radius_miles}")
    
    rows: List[Dict[str, str]] = []
    page = START_PAGE

    # Always load page 1 via URL (establishes session cookies), then click Next
    driver.get(build_hg_url(location, keywords, radius_miles, 1))
    try:
        _hg_wait_results()
    except Exception:
        print("No HealthGrades results on page 1.")
        return rows

    while True:
        _hg_human_scroll()
        _human_sleep(0.3, 0.7)

        cards = driver.find_elements(By.CSS_SELECTOR, hg_selectors["itemContainer"])
        if not cards:
            # Might be rate-limited; back off once
            if _hg_is_block_page():
                print("[HealthGrades] Block page detected; backing off and refreshing...")
                _human_sleep(10, 18)
                driver.refresh()
                try:
                    _hg_wait_results()
                except Exception:
                    break       
                cards = driver.find_elements(By.CSS_SELECTOR, hg_selectors["itemContainer"])
                if not cards:
                    break
            else:
                break

        page_rows = []
        for c in cards:
            item = hg_parse_card(c, location)
            if item.get('Mileage'):
                if item.get("Name") and float(item.get('Mileage')) <= radius_miles and len(page_rows) < int(limit):
                    page_rows.append(item)
                if len(page_rows) >= int(limit):
                    break

        if not page_rows:
            print(f"[HealthGrades] Empty results on page {page}.")
            break

        print(f"[HealthGrades] Page {page}: {len(page_rows)} items")
        rows.extend(page_rows)

        # # Stop if max pages reached
        # if MAX_PAGES and page >= MAX_PAGES:
        #     break

        # Try clicking Next (preferred over constructing ?page=)
        first_card = cards[0] if cards else None
        if not _hg_click_next(prev_first_card=first_card):
            break

        # After navigation, quick human-like pause and sanity checks
        _human_sleep(1.8, 3.5)
        if _hg_is_block_page():
            print("[HealthGrades] Block page detected after Next; pausing and refreshing once...")
            _human_sleep(12, 22)
            driver.refresh()
            try:
                _hg_wait_results()
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