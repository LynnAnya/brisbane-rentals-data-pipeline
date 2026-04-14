
import sys
import pandas as pd
import os
import requests
from datetime import datetime

#0 prep source
RTA_URL = 'https://www.rta.qld.gov.au/sites/default/files/2023-04/rta-bond-statistics.xlsx'
SOURCE_FOLDER = "../data/source_files"
RAW_FOLDER = "../data/raw"


# ==============================
# get static data file from source
# ==============================

def download_file(url: str, prefix: str, file_type: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name =  f"{prefix}_{timestamp}.{file_type}"
    file_path = os.path.join(SOURCE_FOLDER,file_name )
    #Return file path 
    # Create folder if not exists
    os.makedirs(SOURCE_FOLDER, exist_ok=True)

    try:
        response = requests.get(url)
        print("Content-Type:", response.headers.get("Content-Type"))
        print(response.status_code)
        response.raise_for_status()
    except Exception as e:
        print(f"Download failed: {e}")
        raise  

    with open(file_path, "wb") as f:
        f.write(response.content)

    print(f"Downloaded file success here: {file_path}")
    return file_path

    # download_file(RTA_URL, "rta_bond", "xlsx")
# ==============================
# extrarct excel multiple sheets  
# ==============================

def extract_rta_excel(file_path: str) -> dict[str, pd.DataFrame]:
    sheet_names = [
        "4 sub-rents",
        "5 sub-new-bonds",
        "6 sub-all-bonds"
    ]

    cleaned_sheets = {}
    for sheet in sheet_names:
        df = pd.read_excel(
            file_path,
            sheet_name=sheet,
            skiprows=4,          
            header=None,         #  build header manually
            usecols="C,D,S:AM"   
        )
        #  Rows 0–2 = Excel rows 5–7 (header)
        header_rows = df.iloc[0:3]

        head_columns = []
        for col in header_rows.columns:
            parts = header_rows[col].astype(str)
            parts = [p for p in parts if p not in ["nan", ""]]
            head_columns.append("_".join(parts))

        #  repalce with new headers
        df.columns = head_columns

        #  Remove header rows (5–7) + dropdown row (row 8)
        df = df.iloc[4:].reset_index(drop=True)

        #  Standardize column names
        df.columns = [c.upper().replace(" ", "_") for c in df.columns]

        print(f"\n{sheet} columns:")
        print(df.columns.tolist())

        cleaned_sheets[sheet] = df
    return cleaned_sheets

print("happy girl")
# ==============================
# STEP 3: SAVE RAW PARQUET
# ==============================
'''
def save_raw_parquet(df: pd.DataFrame) -> str:

    os.makedirs(RAW_FOLDER, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(RAW_FOLDER, f"rta_bonds_{timestamp}.parquet")

    df.to_parquet(file_path, index=False)

    print(f"Saved raw parquet → {file_path}")
    return file_path
'''

# ==============================
# RUN PIPELINE (FIRST PART ONLY)
# ==============================

if __name__ == "__main__":

    # 1. Download file
    
    file_path = download_file(RTA_URL, "rta_bond", "xlsx")

    sheets = extract_rta_excel(file_path)
    
    #df = sheets["4 sub-rents"]
    #df


    
    # 3. Simple check (important)
    for name, df in sheets.items():
        print(f"\n{name} preview:")
        print(df.head())

    # 👉 Put breakpoint here to view table in VS Code
    #raw_file = save_raw_parquet(df)
    






"""
df = pd.DataFrame({"day": [1, 2], "month": ["January","December"], "year": [2025, 2026]}) #source
df.to_parquet() #compress

print('hello pipeline cutie', sys.argv) 

age = int(sys.argv[1])
dollar = int(sys.argv[3])

print(f'one day you will be {age} ')
print(f'I have AUD {dollar} as I am rich')

## dealing with file
df = pd.DataFrame({"Fruit": ["banana", "pineapple", "orange", "kiwi", "nectarin"], 
                   "Amount": [14, 49, 32,46,11]})
print(df.head())

df.to_parquet(f"output_day_{sys.argv[1]}.parquet")
"""


