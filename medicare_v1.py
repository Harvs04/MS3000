import time
import re
import urllib
from typing import Dict, List

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from typing import List, Dict
from urllib.parse import urljoin
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# config imports
from config import START_PAGE, LOCATION, RADIUS_MILES, MAX_PAGES

# helper imports
from helper import extract_city_state_zip, text_or_none, text_or_none_medicare, attr_or_none, pretty_provider_type, calculate_locations_and_distance

# browser imports
from browser import create_driver, create_wait


driver = create_driver()
wait = create_wait(driver)

# Initialize geolocator
geolocator = Nominatim(user_agent="medicare_scraper")

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

MEDICARE_KEYWORDS = []

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

def accept_cookies_if_present():
    try:
        btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        btn.click()
        time.sleep(0.4)
    except Exception:
        pass

def scrape_address_from_url(source_url: str) -> str:
    """Visit the source URL and scrape the address"""
    if not source_url:
        return None

    try:
        print(f"  🔗 Visiting source URL: {source_url}")
        current_window = driver.current_window_handle

        # Open new tab
        driver.execute_script("window.open();")
        driver.switch_to.window(driver.window_handles[-1])

        try:
            driver.get(source_url)
            time.sleep(2)  # wait for page load

            address = None
            container = driver.find_element(By.CSS_SELECTOR, ".ProviderAddress__address")

            # Get first and second child divs
            divs = container.find_elements(By.TAG_NAME, "div")
            if len(divs) >= 2:
                street = divs[0].text.strip()
                city_state_zip = divs[1].text.strip()
                address = f"{street}, {city_state_zip}"
                print(address)

            if not address:
                page_text = driver.page_source
                match = re.search(r'[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}', page_text)
                if match:
                    address = match.group(0)
                    print(f"  ✅ Found address via regex: {address}")

        finally:
            driver.close()
            driver.switch_to.window(current_window)

        return address

    except Exception as e:
        print(f"  ❌ Error scraping address from URL: {e}")
        try:
            driver.switch_to.window(driver.window_handles[0])
        except:
            pass
        return None

def build_url(location: str, radius: int, page: int = 1, provider_type: str = "Physician") -> str:
    city, state, zipcode = extract_city_state_zip(location)  
    params = [("searchType", provider_type), ("page", str(page))]
    if city: params.append(("city", city))
    if state: params.append(("state", state))
    if zipcode: params.append(("zipcode", zipcode))
    params.extend([
        ("radius", str(radius)),
        ("sort", "closest"),
        ("tealiumEventAction", "Result Page - Search"),
        ("tealiumSearchLocation", "search bar"),
        ("tealiumSearchInputType", "manual search term"),
    ])
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
    hay = " ".join([(row.get("Name") or ""), (row.get("Specialty") or ""), (row.get("Address") or "")]).lower()
    for kw in keywords:
        if kw and kw.lower() in hay:
            return True
    return False

def extract_address_only(full_address):
    """Extract just the street address without city, state, zip"""
    if not full_address:
        return ""
    
    try:
        # Split by comma - everything before the last comma should be the address
        parts = full_address.split(', ')
        if len(parts) >= 2:
            # Join all parts except the last one (which contains city, state, zip)
            return ', '.join(parts[:-2]).strip()
        else:
            # No comma found, might be malformed - return as is
            return full_address.strip()
    except Exception:
        return full_address or ""

STATE_ZIP_RE = re.compile(r"\b([A-Z]{2})(?:\s*\d{5}(?:-\d{4})?)?\b")

def extract_city_only(full_address: str):
    """Return just the city from typical US addresses.

    Works for:
      - '123 Main St, Garden Grove, CA 92840'
      - '123 Main St, Garden Grove, CA 92840, United States'
      - 'Garden Grove, CA 92840'
      - 'Garden Grove, CA'
    """
    print("Extracting city from address: " + str(full_address))
    if not full_address:
        return ""

    # Split on commas and trim
    parts = [p.strip() for p in full_address.split(",") if p.strip()]
    if not parts:
        return ""

    # Find the chunk that contains the state (with optional ZIP).
    # The city is the chunk immediately BEFORE that.
    idx_state = None
    for i in range(len(parts) - 1, -1, -1):
        if STATE_ZIP_RE.search(parts[i].upper()):
            idx_state = i
            break

    if idx_state is not None and idx_state - 1 >= 0:
        return parts[idx_state - 1]

    # Fallbacks

    # If we have two chunks like: [street, 'City ST ZIP']
    if len(parts) == 2:
        m = re.match(r"^(.*)\s+[A-Z]{2}(?:\s*\d{5}(?:-\d{4})?)?$", parts[1])
        if m:
            return m.group(1).strip()

    # If last chunk is a country, try city = 3rd-from-last
    if parts[-1].lower() in {"united states", "usa", "canada"} and len(parts) >= 3:
        return parts[-3]

    # Otherwise, best guess: second-to-last if it exists
    if len(parts) >= 2:
        return parts[-2]

    return parts[0]  # worst-case: return the only chunk

def extract_state(full_address):
    """Extract state from full address"""
    if not full_address:
        return ""
    
    try:
        parts = full_address.split(', ')
        if len(parts) >= 2:
            city_state_zip = parts[-1].strip()
            words = city_state_zip.split()
            if len(words) >= 2:
                return words[-2]  # Second to last should be state
        return ""
    except Exception:
        return ""

def extract_zip(full_address):
    """Extract zip code from full address"""
    if not full_address:
        return ""
    
    try:
        parts = full_address.split(', ')
        if len(parts) >= 2:
            city_state_zip = parts[-1].strip()
            words = city_state_zip.split()
            if len(words) >= 1:
                return words[-1]  # Last word should be zip
        return ""
    except Exception:
        return ""

def parse_card(card, provider_type="Physician") -> Dict[str, str]:
    name = source_url = specialty = phone = address = distance = None

    # Get name + source url
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

    # Get specialty
    try:
        spec_el = card.find_element(By.CSS_SELECTOR, selectors["specialty"])
        scraped_specialty = text_or_none(spec_el)
    except Exception:
        scraped_specialty = None

    # Get phone from list page
    try:
        phone_el = card.find_element(By.CSS_SELECTOR, selectors["phone"])
        phone = text_or_none(phone_el)
    except Exception:
        pass

    # Get address from list page
    try:
        addr_el = card.find_element(By.CSS_SELECTOR, selectors["addressBlock"])
        address = text_or_none_medicare(addr_el)
    except Exception:
        pass

    # Get distance from list page
    try:
        dist_el = card.find_element(By.CSS_SELECTOR, selectors["distance"])
        distance = (dist_el.text or "").strip()
        if distance:
            distance = distance.replace(" mi", "").replace("mi", "").strip() or None
        else:
            distance = None
    except Exception:
        pass

    # Conditions to visit detail page
    needs_detail_page = False
    if provider_type in ["HomeHealth", "Hospice"]:
        needs_detail_page = True
    if not phone:
        needs_detail_page = True

    if needs_detail_page and source_url:
        print(f"  🔎 Visiting detail page in new tab for {name} ({provider_type})")
        try:
            # Open new tab
            driver.execute_script("window.open(arguments[0], '_blank');", source_url)
            driver.switch_to.window(driver.window_handles[-1])  # switch to new tab
            time.sleep(2)

            # If HomeHealth/Hospice → replace address & recalc distance
            if provider_type in ["HomeHealth", "Hospice"]:
                scraped_address = scrape_address_from_url(source_url)
                if scraped_address:
                    address = scraped_address
                    calculated_distance = calculate_locations_and_distance(LOCATION, scraped_address)
                    if calculated_distance:
                        distance = calculated_distance
                else:
                    print(f"  ⚠️ Could not scrape address for {name}")

            # If phone missing → try to scrape from detail page
            if not phone:
                try:
                    detail_phone_el = driver.find_element(By.CSS_SELECTOR, "a[href^='tel:']")
                    phone = detail_phone_el.text.strip()
                    print(f"  ✅ Found phone on detail page: {phone}")
                except Exception:
                    print(f"  ⚠️ No phone found for {name} on detail page")

        except Exception as e:
            print(f"  ⚠️ Error scraping detail page for {name}: {str(e)}")

        finally:
            # Close the detail tab and return to original tab
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                print(f"  ↩️ Returned to search results tab")

    # Finalize specialty
    specialty = scraped_specialty or (
        "Physician" if str(provider_type).lower() == "physician" else pretty_provider_type(provider_type)
    )

    # return {
    #     "Provider type": provider_type,
    #     "Name": name,
    #     "Specialty": specialty,
    #     "Contact number": phone,
    #     "Address": address,
    #     "Distance": distance,
    #     "Source URL": source_url,
    # }
    # ["Name", "Mileage", "Address", "City", "State", "Zip", "Phone Number", "Full Address"]
    # city, state, zip_code = parse_address_components(address)

    return {
        "Name": name or "",
        "Mileage": distance or "",
        "Address": extract_address_only(address),
        "City": extract_city_only(address),
        "State": extract_state(address),
        "Zip": extract_zip(address),
        "Phone Number": phone or "",
        "Specialty": specialty or "",
        "Full Address": address or ""
    }

_miles_re = re.compile(r"(\d+(?:\.\d+)?)")

def _to_float_miles(v) -> float:
    if v is None:
        return float("inf")
    if isinstance(v, (int, float)):
        return float(v)
    m = _miles_re.search(str(v))
    return float(m.group(1)) if m else float("inf")


def extract_items_on_page(per_type_remaining: int,
                          radius_miles: float,
                          provider_type: str = "Physician") -> List[Dict[str, str]]:
    """
    Collect up to `per_type_remaining` items from the CURRENT page only,
    filtering by distance <= radius_miles. No global counters here.
    """
    cards = driver.find_elements(By.CSS_SELECTOR, selectors["itemContainer"])
    print(f"Found {len(cards)} cards")
    items: List[Dict[str, str]] = []

    for c in cards:
        if len(items) >= per_type_remaining:
            break

        item = parse_card(c, provider_type=provider_type)
        if not item or not item.get("Name"):
            continue

        miles = _to_float_miles(item.get("Mileage"))
        if miles <= float(radius_miles):
            items.append(item)

    return items


def scrape_medicare(location, medicare_categories, limit, radius_miles):
    """
    `limit` = per-type cap. For each provider type:
      - paginate while we need more for THAT type,
      - add up to `limit` rows for that type,
      - then move on to the next type.
    """
    all_rows: List[Dict[str, str]] = []

    # If dict like {"Physician": True, "Hospital": True, ...}, keep enabled ones
    if isinstance(medicare_categories, dict):
        types_to_scrape = [k for k, v in medicare_categories.items() if v]
    else:
        types_to_scrape = list(medicare_categories)

    print(medicare_categories)

    for ptype in types_to_scrape:
        print(f"\n{'='*50}")
        print(f"Scraping provider type: {ptype}")
        print(f"{'='*50}")

        results: List[Dict[str, str]] = []
        page = START_PAGE

        while len(results) < limit:
            print(f"\n📄 Page {page} for {ptype}")
            # IMPORTANT: use radius_miles param, not a constant
            driver.get(build_url(location, radius_miles, page, provider_type=ptype))
            accept_cookies_if_present()

            try:
                wait_for_results_cards()
            except Exception:
                print(f"[Medicare:{ptype}] No cards on page {page}. Stopping this type.")
                break

            time.sleep(0.4)
            scroll_results_container()
            time.sleep(0.4)

            remaining = limit - len(results)
            if remaining <= 0:
                break

            rows = extract_items_on_page(remaining, radius_miles, provider_type=ptype)
            if not rows:
                print(f"[Medicare:{ptype}] Empty page {page} after filtering. Stop this type.")
                break

            results.extend(rows[:remaining])
            print(f"[Medicare:{ptype}] Page {page}: +{len(rows[:remaining])}"
                  f" (type total {len(results)}/{limit})")

            if len(results) >= limit:
                break

            page += 1
            if ptype in ["HomeHealth", "Hospice"]:
                print("  ⏳ Adding delay for provider type...")
                time.sleep(2)

        # Add this type’s batch to global store
        all_rows.extend(results)

    # Final dedupe (optional, across all types)
    print(f"\n📊 Scraping Summary:")
    print(f"Total items collected (pre-dedupe): {len(all_rows)}")

    seen, deduped, duplicates = set(), [], 0
    for r in all_rows:
        key = (r.get("Name"), r.get("Address"), r.get("Provider type"))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(r)

    print(f"Duplicates removed: {duplicates}")
    print(f"Final unique items: {len(deduped)}")
    return deduped
