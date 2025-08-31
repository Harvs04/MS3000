import time
import re
import urllib
from typing import Dict, List

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# config imports
from config import START_PAGE, LOCATION, RADIUS_MILES, MAX_PAGES

# helper imports
from helper import extract_city_state_zip, text_or_none, attr_or_none, pretty_provider_type

# browser imports
from browser import driver, wait


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