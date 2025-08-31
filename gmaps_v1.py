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
from helper import geolocator, haversine_distance, get_coordinates_from_location, text_or_none, attr_or_none, extract_city_state_zip, extract_address

# browser imports
from browser import create_driver, create_wait

# Then in your functions where you need the driver:
driver = create_driver()
wait = create_wait(driver)

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
        print("parts: " + str(parts))
        # Find address (longest part that looks like an address)
        address_candidates = [p for p in parts if _looks_like_address(p)]
        if address_candidates:
            address = max(address_candidates, key=len)
            
        specialty = parts[0] if len(parts) > 1 else "Not specified"
        
        # Find specialty (medical category keywords)
        # medical_keywords = [
        #     "Doctor", "Clinic", "Physician", "Dentist", "Cardiology", "Dermatology", 
        #     "Pediatric", "Surgeon", "Family", "Internal", "Orthopedic", "Urology", 
        #     "Gynecol", "Psychiatrist", "Optometry", "Chiropractor", "Oncology", "Neurology", 
        #     "Endocrine", "Gastro", "Pulmonary", "Rheumatic", "Radiology", "Nephrology", 
        #     "Ophthalmology", "Emergency", "Urgent", "Primary Care", "Medical Center"
        # ]
        # for p in parts:
        #     if any(keyword.lower() in p.lower() for keyword in medical_keywords):
        #         specialty = p
        #         break
        

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
    
    # ["Name", "Mileage", "Address", "City", "State", "Zip", "Phone Number", "Specialty", "Full Address"]
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
    
    # return {
    #     "Name": name,
    #     "Specialty": specialty,
    #     "Contact number": phone,
    #     "Address": address,
    #     "Distance": distance,
    #     "Source URL": source_url,
    # }

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

# def _gmaps_collect_from_list_optimized(container, limit, origin_coords) -> Dict[str, Dict[str, str]]:
#     """Collect all places from Google Maps results with fast distance calculation"""
#     store = {}
#     prev_count = -1
#     stable_rounds = 0

#     for _ in range(GMAPS_MAX_SCROLLS):
#         try:
#             cards = container.find_elements(By.CSS_SELECTOR, g_selectors["itemContainer"])
#             # print("limit: " + limit)
#             # print("cards length: " + len(cards))
#         except:
#             cards = []

#         for card in cards:
#             # Get place URL (must have /maps/place/ for coordinate extraction)
#             place_url = None
#             try:
#                 a = card.find_element(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
#                 place_url = attr_or_none(a, "href")
#             except:
#                 continue

#             if not place_url or place_url in store:
#                 continue

#             # Parse card data
#             card_data = gmaps_parse_card(card)
            
#             # Calculate distance using coordinates (fast method)
#             distance = card_data.get("Distance")  # Use list distance as fallback
#             if origin_coords:
#                 place_coords = extract_coordinates_from_gmaps_url(place_url)
#                 if place_coords:
#                     calc_distance = haversine_distance(
#                         origin_coords[0], origin_coords[1],
#                         place_coords[0], place_coords[1]
#                     )
#                     distance = f"{calc_distance}"

#             store[place_url] = {
#                 "Name": card_data.get("Name"),
#                 "Specialty": card_data.get("Specialty"),
#                 "Contact number": card_data.get("Contact number"),
#                 "Address": card_data.get("Address"),
#                 "Distance": distance,
#                 "Source URL": place_url,
#             }

#         # Check if we're getting new results
#         count = len(cards)
#         if count == prev_count:
#             stable_rounds += 1
#         else:
#             stable_rounds = 0
#         if stable_rounds >= 2:
#             break
#         prev_count = count

#         # Scroll to load more results
#         try:
#             driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", container)
#         except:
#             driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#         time.sleep(0.5)

#     return store
def get_address_from_place_url(place_url: str, max_wait: int = 10) -> str:
    """
    Open place URL in new tab to extract full address without losing search results.
    Returns the address string or None if not found.
    """
    original_window = driver.current_window_handle
    
    try:
        # Open new tab
        driver.execute_script("window.open('');")
        
        # Switch to new tab
        new_window = driver.window_handles[-1]
        driver.switch_to.window(new_window)
        
        # Navigate to the place URL in new tab
        driver.get(place_url)
        
        # Wait for page to load
        time.sleep(2)
        
        # Try multiple selectors for the address button
        address_selectors = [
            # Most specific: button with address data-item-id and contains address text
            'button[data-item-id="address"][aria-label*="Address:"]',
            
            # Alternative: button with address data-item-id
            'button[data-item-id="address"]',
            
            # Fallback: look for the specific div structure
            'button[data-item-id="address"] .Io6YTe.fontBodyMedium',
            
            # Even more general fallback
            'button[aria-label*="Address:"]'
        ]
        
        address_text = None
        
        for selector in address_selectors:
            try:
                # Wait for element to be present
                address_elem = WebDriverWait(driver, max_wait).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                
                if selector.endswith('button[aria-label*="Address:"]') or selector.endswith('button[data-item-id="address"]'):
                    # Extract from aria-label
                    aria_label = address_elem.get_attribute('aria-label')
                    if aria_label and 'Address:' in aria_label:
                        # Extract text after "Address: "
                        address_text = aria_label.split('Address: ', 1)[1].strip()
                        break
                else:
                    # Extract from element text
                    address_text = address_elem.text.strip()
                    if address_text:
                        break
                        
            except Exception as e:
                print(f"Selector '{selector}' failed: {e}")
                continue
        
        if not address_text:
            # Last resort: try to find any element with address-like text
            try:
                all_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label*="Address"]')
                for btn in all_buttons:
                    aria_label = btn.get_attribute('aria-label')
                    if aria_label and 'Address:' in aria_label:
                        address_text = aria_label.split('Address: ', 1)[1].strip()
                        break
            except:
                pass
        
        print(f"Extracted address: {address_text}")
        return address_text
        
    except Exception as e:
        print(f"Error extracting address from {place_url}: {e}")
        return None
        
    finally:
        # Close the new tab and switch back to original
        try:
            driver.close()  # Close current tab (the new one)
            driver.switch_to.window(original_window)  # Switch back to original tab
        except Exception as e:
            print(f"Error closing tab: {e}")
            # Try to switch back anyway
            try:
                driver.switch_to.window(original_window)
            except:
                pass

def _format_mileage(mi):
    if mi is None:
        return None
    try:
        return f"{float(mi):.2f}"
    except Exception:
        return None

def _gmaps_collect_from_list_optimized(container, limit, origin_coords) -> Dict[str, Dict[str, str]]:
    """Collect places from Google Maps results with fast distance calculation.
    Respects `limit` (int/str/None). Stops early once limit is reached.
    """
    # --- coerce & sanitize limit ---
    try:
        max_items = int(limit)
        if max_items <= 0:
            max_items = None
    except (TypeError, ValueError):
        max_items = None

    store: Dict[str, Dict[str, str]] = {}
    prev_total = -1
    stable_rounds = 0

    for _ in range(GMAPS_MAX_SCROLLS):
        if max_items is not None and len(store) >= max_items:
            break

        try:
            cards = container.find_elements(By.CSS_SELECTOR, g_selectors["itemContainer"])
        except Exception:
            cards = []

        for card in cards:
            if max_items is not None and len(store) >= max_items:
                break

            # Get place URL (must have /maps/place/ for coordinate extraction)
            try:
                a = card.find_element(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                place_url = attr_or_none(a, "href")
            except Exception:
                continue

            if not place_url or place_url in store:
                continue

            # Parse card data (your gmaps_parse_card now returns the spec keys)
            card_data = gmaps_parse_card(card)

            # Get detailed address from place URL (if available)
            detailed_address = get_address_from_place_url(place_url)
            if detailed_address:
                card_data["Full Address"] = detailed_address
                # if you want street-only too, try to extract:
                try:
                    card_data["Address"] = extract_address(detailed_address)
                    c, s, z = extract_city_state_zip(detailed_address) or (None, None, None)
                    card_data["City"], card_data["State"], card_data["Zip"] = c, s, z
                except Exception:
                    pass

            # Calculate numeric distance in miles using coordinates
            distance_miles = None
            if origin_coords:
                place_coords = extract_coordinates_from_gmaps_url(place_url)
                if place_coords:
                    distance_miles = float(haversine_distance(
                        origin_coords[0], origin_coords[1],
                        place_coords[0], place_coords[1]
                    ))

            # Build standardized record (keep a private numeric for filtering)
            store[place_url] = {
                "Name":           card_data.get("Name"),
                "Mileage":        _format_mileage(distance_miles),   # pretty string
                "Address":        card_data.get("Address"),
                "City":           card_data.get("City"),
                "State":          card_data.get("State"),
                "Zip":            card_data.get("Zip"),
                "Phone Number":   card_data.get("Phone Number"),
                "Specialty":      card_data.get("Specialty"),
                "Full Address":   card_data.get("Full Address") or card_data.get("Address"),
                "_distance_miles": distance_miles,                   # numeric for filtering
                "_source_url":    place_url,                         # optional traceability
            }

        if max_items is not None and len(store) >= max_items:
            break

        # detect no-new-results to avoid infinite scrolling
        total_now = len(store)
        if total_now == prev_total:
            stable_rounds += 1
        else:
            stable_rounds = 0
        if stable_rounds >= 2:
            break
        prev_total = total_now

        # Scroll to load more results
        try:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", container)
        except Exception:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)

    if max_items is not None and len(store) >= max_items:
        print(f"[GoogleMaps] Reached limit {max_items}; stopping early with {len(store)} items.")
    else:
        print(f"[GoogleMaps] Collected {len(store)} items.")

    return store


def _gmaps_enrich_details_batch(place_data, batch_size=3):
    """Enrich places with detailed info, processing in batches.
       Uses consistent keys and preserves numeric _distance_miles.
    """
    enriched = {}
    main_window = driver.current_window_handle

    # Only enrich places that need phone, address, or specialty
    need_enrichment = {
        url: data for url, data in place_data.items()
        if not data.get("Phone Number") or not data.get("Full Address") or not data.get("Specialty")
    }

    if not need_enrichment:
        return place_data

    print(f"[GoogleMaps] Enriching {len(need_enrichment)} places with detailed info")

    urls = list(need_enrichment.keys())
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i+batch_size]

        for url in batch:
            base_data = place_data.get(url, {})
            try:
                driver.execute_script("window.open(arguments[0], '_blank');", url)
                driver.switch_to.window(driver.window_handles[-1])

                detail = _gmaps_parse_detail_tab()  # returns Name, Address, Contact number, Specialty

                # Merge detail with base, prefer detail when present
                merged = {
                    "Name":         detail.get("Name") or base_data.get("Name"),
                    "Specialty":    detail.get("Specialty") or base_data.get("Specialty"),
                    "Phone Number": detail.get("Contact number") or base_data.get("Phone Number"),
                    "Full Address": detail.get("Address") or base_data.get("Full Address") or base_data.get("Address"),
                }

                # Try to keep structured address fields in sync if we got a fresh full address
                if merged.get("Full Address") and not base_data.get("Address"):
                    try:
                        merged["Address"] = extract_address(merged["Full Address"])
                        c, s, z = extract_city_state_zip(merged["Full Address"]) or (None, None, None)
                        merged["City"], merged["State"], merged["Zip"] = c, s, z
                    except Exception:
                        merged["Address"] = base_data.get("Address")
                        merged["City"] = base_data.get("City")
                        merged["State"] = base_data.get("State")
                        merged["Zip"] = base_data.get("Zip")
                else:
                    merged["Address"] = base_data.get("Address")
                    merged["City"] = base_data.get("City")
                    merged["State"] = base_data.get("State")
                    merged["Zip"] = base_data.get("Zip")

                # Preserve distance and source
                merged["Mileage"] = base_data.get("Mileage")
                merged["_distance_miles"] = base_data.get("_distance_miles")
                merged["_source_url"] = url

                enriched[url] = merged

            except Exception:
                # Fall back to original if enrichment fails
                enriched[url] = base_data
            finally:
                try:
                    driver.close()
                    driver.switch_to.window(main_window)
                except Exception:
                    pass
                time.sleep(0.2)

    # Add non-enriched places back
    for url, data in place_data.items():
        if url not in enriched:
            enriched[url] = data

    return enriched


def scrape_google_maps(location, keyword, limit, radius_miles) -> List[Dict[str, str]]:
    """
    Optimized Google Maps scraper:
    1) Fast distance calculation using coordinates
    2) Selective detail enrichment for missing data
    3) Clean filtering by numeric miles
    """
    # Get origin coordinates
    origin_coords = get_coordinates_from_location(location)
    if not origin_coords:
        print("[GoogleMaps] Warning: Could not get origin coordinates")

    print(f"[GoogleMaps] Searching for: {keyword}")

    driver.get(build_gmaps_url(keyword, location))
    gmaps_accept_consent_if_any()

    try:
        gmaps_wait_results()
    except Exception:
        print(f"[GoogleMaps] No results for '{keyword}'")
        return []

    container = gmaps_get_feed_container()
    if not container:
        print(f"[GoogleMaps] No results container for '{keyword}'")
        return []

    # Collect places with fast distance calculation
    all_places = _gmaps_collect_from_list_optimized(container, limit, origin_coords)
    print(f"[GoogleMaps] Found {len(all_places)} places for '{keyword}'")

    if not all_places:
        print("[GoogleMaps] No places found")
        return []

    print(f"[GoogleMaps] Total unique places: {len(all_places)}")

    # Enrich places that need more detailed information
    enriched_places = _gmaps_enrich_details_batch(all_places, batch_size=3)

    # Convert to list and filter by numeric miles
    results = []
    max_results = int(limit) if str(limit).isdigit() else None
    for url, data in enriched_places.items():
        miles = data.get("_distance_miles")
        if (
            data.get("Name")
            and miles is not None
            and float(miles) <= float(radius_miles)
            and (max_results is None or len(results) < max_results)
        ):
            results.append({
                "Name":         data.get("Name"),
                "Mileage":      data.get("Mileage"),
                "Address":      data.get("Address"),
                "City":         data.get("City"),
                "State":        data.get("State"),
                "Zip":          data.get("Zip"),
                "Phone Number": data.get("Phone Number"),
                "Specialty":    data.get("Specialty"),
                "Full Address": data.get("Full Address"),
                # keep the URL if you want to export/debug:
                # "Source URL":   data.get("_source_url"),
            })
            print(f"Added: {data.get('Name')} - {data.get('Mileage')}")

    # Deduplicate by name and address
    seen = set()
    deduped = []
    for r in results:
        key = (r.get("Name"), r.get("Full Address") or r.get("Address"))
        if key not in seen and r.get("Name"):
            seen.add(key)
            deduped.append(r)

    print(f"[GoogleMaps] Final results: {len(deduped)} unique healthcare providers")
    return deduped
