# main.py
import os
import pandas as pd
from typing import Dict, List, Tuple
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

# Avoid name collisions: keep both implementations available if you need them
# from medicare import scrape_medicare as scrape_medicare_v0
from medicare_v1 import scrape_medicare as scrape_medicare_v1
# from yellowpages import scrape_yellowpages  # old
from yellowpages_v3 import scrape_yellowpages
# from gmaps import scrape_google_maps
from gmaps_v1 import scrape_google_maps
from healthgrades import scrape_healthgrades

# from browser import driver
from config import _outfile_from_location, results_dir_for_today

def format_worksheet(worksheet, num_columns, num_rows):
    """Format worksheet with Arial font, orange headers, and specified formatting"""
    # Orange Accent 6, Lighter 60% color
    orange_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    header_font = Font(name="Arial", size=14, bold=True)
    data_font = Font(name="Arial", size=12)
    
    for col in range(1, num_columns + 1):
        # Set column width
        worksheet.column_dimensions[get_column_letter(col)].width = 40
        
        # Format header cell (row 1)
        header_cell = worksheet.cell(row=1, column=col)
        header_cell.fill = orange_fill
        header_cell.font = header_font
        
        # Format data cells (rows 2 and beyond)
        for row in range(2, num_rows + 2):  # +2 because row 1 is header, and range is exclusive
            data_cell = worksheet.cell(row=row, column=col)
            data_cell.font = data_font

def _safe_call_scraper(fn, **kwargs) -> List[Tuple]:
    """
    Call a scraper with flexible kwargs.
    Your scrapers might accept different parameter names; we try several.
    Expected return: list of row tuples/lists like:
      ["Name","Specialty","Contact number","Address","Distance","Source URL"]
    """
    # Try the most descriptive set first
    attempts = [
        {"location": kwargs["location"], "limit": kwargs["limit"], "radius_miles": kwargs["radius_miles"]},
        {"location": kwargs["location"], "limit": kwargs["limit"], "radius": kwargs["radius_miles"]},
        {"query": kwargs["location"], "limit": kwargs["limit"], "radius": kwargs["radius_miles"]},
        {"location": kwargs["location"], "limit": kwargs["limit"]},
        {"location": kwargs["location"]},
        {},  # last resort
    ]
    for params in attempts:
        try:
            out = fn(**params)
            if out is None:
                out = []
            return out
        except TypeError:
            continue
        except Exception:
            # Let other exceptions propagate (network, etc.)
            raise
    return []


def run(
    location: str,
    yp_keyword: str,
    gmaps_keyword: str,
    limit: int,
    radius_miles: int,
    sources: Dict[str, bool],
    hg_categories: Dict[str, bool],
    medicare_categories: Dict[str, bool],
) -> Dict:
    """
    Execute selected scrapers and write Excel.
    Returns a summary dict for the UI.
    """
    cols = ["Name", "Mileage", "Address", "City", "State", "Zip", "Phone Number", "Specialty", "Full Address"]
    rows_medicare: List = []
    rows_yp: List = []
    rows_gmaps: List = []
    rows_hg: List = []
    
    output_name = _outfile_from_location(location)         # from config.py
    results_dir = results_dir_for_today()                  # from config.py
    output_file = os.path.join(results_dir, output_name)
    try:
        if any(medicare_categories.values()):
            rows_medicare = scrape_medicare_v1(location, medicare_categories, limit, radius_miles)
            
        if sources.get("YellowPages"):
            rows_yp = scrape_yellowpages(location, yp_keyword, limit, radius_miles)
            
        if sources.get("GoogleMaps"):
            rows_gmaps = scrape_google_maps(location, gmaps_keyword, limit, radius_miles)
            
        if sources.get("HealthGrades"):
            rows_hg = scrape_healthgrades(location, hg_categories, limit, radius_miles)

        # Build DataFrames
        df_medicare = pd.DataFrame(rows_medicare, columns=cols) if rows_medicare else pd.DataFrame(columns=cols)
        df_yp = pd.DataFrame(rows_yp, columns=cols) if rows_yp else pd.DataFrame(columns=cols)
        df_gmaps = pd.DataFrame(rows_gmaps, columns=cols) if rows_gmaps else pd.DataFrame(columns=cols)
        df_hg = pd.DataFrame(rows_hg, columns=cols) if rows_hg else pd.DataFrame(columns=cols)

        # Remove old file if present
        if os.path.exists(output_file):
            os.remove(output_file)

        # Write only non-empty sheets
        with pd.ExcelWriter(output_file, engine="openpyxl") as xw:
            if not df_medicare.empty:
                df_medicare.to_excel(xw, sheet_name="Medicare", index=False)
                format_worksheet(xw.sheets["Medicare"], len(df_medicare.columns), len(df_medicare))
            
            if not df_yp.empty:
                df_yp.to_excel(xw, sheet_name="YellowPages", index=False)
                format_worksheet(xw.sheets["YellowPages"], len(df_yp.columns), len(df_yp))
            
            if not df_gmaps.empty:
                df_gmaps.to_excel(xw, sheet_name="GoogleMaps", index=False)
                format_worksheet(xw.sheets["GoogleMaps"], len(df_gmaps.columns), len(df_gmaps))
                
            if not df_hg.empty:
                df_hg.to_excel(xw, sheet_name="HealthGrades", index=False)
                format_worksheet(xw.sheets["HealthGrades"], len(df_hg.columns), len(df_hg))

        summary = {
            "outfile": output_file,
            "counts": {
                "Medicare": len(df_medicare),
                "YellowPages": len(df_yp),
                "GoogleMaps": len(df_gmaps),
                "HealthGrades": len(df_hg)
            },
        }
        print(f"\nSaved to: {output_file}")
        print(f"Summary: {summary}")
        for k, v in summary["counts"].items():
            print(f"  {k:11s}: {v} rows")
        return summary
    except Exception as e:
        print(f"Error occurred: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    
    
    # finally:
    #     # Ensure we always close the shared browser
    #     try:
    #         driver.quit()
    #     except Exception:
    #         pass


# if __name__ == "__main__":
    # Optional: quick manual run for testing
    # result = run(
    #     location="Garden Grove, CA",
    #     limit=50,
    #     radius_miles=10,
    #     sources={"Medicare": True, "YellowPages": True, "GoogleMaps": False},
    # )
    # pass
