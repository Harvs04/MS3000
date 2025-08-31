import pandas as pd
import os

# from medicare import scrape_medicare
from medicare_v1 import scrape_medicare
# from yellowpages import scrape_yellowpages
from yellowpages_v3 import scrape_yellowpages
from gmaps import scrape_google_maps
from config import OUTFILE

from browser import driver

def run():
    try:
        medicare_rows = scrape_medicare()
        yp_rows = scrape_yellowpages()
        # gmaps_rows = scrape_google_maps() 

        # if not (medicare_rows or yp_rows or gmaps_rows):
        #     print("No data collected from any source.")
        #     return

        cols = ["Name", "Specialty", "Contact number", "Address", "Distance", "Source URL"]
        df_medicare = pd.DataFrame(medicare_rows, columns=cols) 
        df_yp = pd.DataFrame(yp_rows, columns=cols)
        # df_gmaps = pd.DataFrame(gmaps_rows, columns=cols)

        # Remove old file if present
        if os.path.exists(OUTFILE):
            os.remove(OUTFILE)

        with pd.ExcelWriter(OUTFILE, engine="openpyxl") as xw:
            if not df_medicare.empty:
                df_medicare.to_excel(xw, sheet_name="Medicare", index=False)
            if not df_yp.empty:
                df_yp.to_excel(xw, sheet_name="YellowPages", index=False)
            # if not df_gmaps.empty:
            #     df_gmaps.to_excel(xw, sheet_name="GoogleMaps", index=False)

        print(f"\nSaved to: {OUTFILE}")
        print(f"  Medicare:   {len(df_medicare)} rows")
        print(f"  YellowPages:{len(df_yp)} rows")
        # print(f"  GoogleMaps: {len(df_gmaps)} rows") 

    finally:
        driver.quit()

if __name__ == "__main__":
    run()