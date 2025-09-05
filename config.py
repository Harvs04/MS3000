import re
import os
from datetime import datetime

LOCATION = "12532 Citruswood Avenue, Garden Grove, CA 92840"
RADIUS_MILES = 5
START_PAGE = 1
MAX_PAGES = 1            # 0 = no hard limit for Medicare / YP
GMAPS_MAX_SCROLLS = 10   # how many scroll passes to load more Google Maps results
WAIT_SECS = 20


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def _outfile_from_location(loc: str) -> str:
    """
    Returns just the *filename* (not full path), e.g. 'garden_grove__ca_92840.xlsx'
    from a location string like '12532 Citruswood Avenue, Garden Grove, CA 92840'.
    """
    parts = [p.strip() for p in loc.split(",")]
    city = state = zip5 = None
    if len(parts) >= 3:
        city = parts[-2]
        m = re.search(r"([A-Za-z]{2})\s*(\d{5})", parts[-1])
        if m:
            state, zip5 = m.group(1), m.group(2)

    if not (city and state and zip5):
        m2 = re.search(r"([^,]+),\s*([A-Za-z]{2})\s*(\d{5})", loc)
        if m2:
            city, state, zip5 = m2.group(1).strip(), m2.group(2), m2.group(3)

    if city and state and zip5:
        return f"{_slug(city)}__{state.lower()}_{zip5}.xlsx"

    return "results.xlsx"

def _desktop_path() -> str:
    home = os.path.expanduser("~")
    desktop = os.path.join(home, "Desktop")
    return desktop if os.path.isdir(desktop) else home

def results_dir_for_today() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    d = os.path.join(_desktop_path(), f"Scraping_Results_{today}")
    os.makedirs(d, exist_ok=True)
    return d


# OUTFILE = _outfile_from_location(LOCATION)