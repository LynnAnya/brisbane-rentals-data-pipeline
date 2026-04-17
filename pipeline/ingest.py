import sys
import pandas as pd
import os
import requests
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

#0 prep source
RTA_URL = 'https://www.rta.qld.gov.au/sites/default/files/2023-04/rta-bond-statistics.xlsx'
SOURCE_FOLDER = "../data/source_files"
RAW_FOLDER = "../data/raw"
SUBURBS_API_URL = "https://data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets/suburb-boundaries/records"
suburbs_params = {
    "select": "suburb_name,geo_point_2d"
}
OCCUPATIONS_API_URL = "https://data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets/occupation-employment-by-usual-resident-employment/records"
occupations_params = {
    "select": "sa4_name,sa3_name,sa2_name,code_1,name_1,code_2,name_2,"
              "sc2_2021,sc2_2026,sc2_2031,sc2_2036"
}

# ==============================
# get static data file from source
# ==============================
def download_file(url: str, prefix: str, file_type: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name =  f"{prefix}_{timestamp}.{file_type}"
    file_path = os.path.join(SOURCE_FOLDER,file_name )
    
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

# ==============================
#  Get api json from bne council + store source file   
# ==============================
def get_json_api(url: str, prefix: str, params: dict) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{prefix}_{timestamp}.json"
    file_path = os.path.join(SOURCE_FOLDER, file_name)

    os.makedirs(SOURCE_FOLDER, exist_ok=True)

    all_results = []
    offset = 0
    limit = 100  # API max for brisbane council data

    while True:
        # update params for pagination
        params["limit"] = limit
        params["offset"] = offset

        try:
            response = requests.get(url, params=params)
            print("Request URL:", response.url)
            print("Status:", response.status_code)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

        except Exception as e:
            print(f"API failed: {e}")
            raise

        all_results.extend(results)

        # if we get less than limit, means we have the last batch
        if len(results) < limit:
            break

        offset += limit

    #combined data
    final_data = {
        "total_count": len(all_results),
        "results": all_results
    }
    #save raw JSON
    with open(file_path, "w") as f:
        json.dump(final_data, f)

    print(f"Saved JSON --> {file_path}")
    print(f"####### get {prefix} api success ########")
    return final_data

# ==============================
# extrarct excel multiple sheets  
# ==============================
def extract_rta_excel(file_path: str) -> dict[str, pd.DataFrame]:
    sheet_name_map= {
        "4 sub-rents": "sub_rents",
        "5 sub-new-bonds": "sub_new_bonds",
        "6 sub-all-bonds": "sub_all_bonds"
    }

    cleaned_sheets = {}
    for sheet, clean_name in sheet_name_map.items():  #made cahgne 16/4/26
        df = pd.read_excel(
            file_path,
            sheet_name=sheet,
            skiprows=4,          
            header=None,         
            usecols="C,D,S:AM"   
        )
        #  Rows 0–2 = Excel rows 5–7 (header)
        header_rows = df.iloc[0:3]

        #define headers manually here
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

        #notice it is float type when see in parquet -- correct it here
        for col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[$,]", "", regex=True) 
                .str.strip()
                .replace({"": None, "-": None})
            )
        # 2. Convert ALL numeric columns (except text ones)
        for col in df.columns:
            if col not in ["SUBURB", "DWELLING"]:
                numeric = pd.to_numeric(df[col], errors="coerce")

                rounded = numeric.round(0)
                try:
                    df[col] = rounded.astype("Int64")
                except Exception:
                    #  if something really wrong
                    df[col] = numeric

        cleaned_sheets[clean_name] = df
    return cleaned_sheets

# ==============================
#  extract sanitize suburbs data
# ==============================
def extract_bne_suburbs(data: dict) -> pd.DataFrame:
    df = pd.json_normalize(data["results"])

    # select only needed columns
    df = df[[
        "suburb_name",
        "geo_point_2d.lon",
        "geo_point_2d.lat"
    ]]
    #  rename columns
    df = df.rename(columns={
        "suburb_name": "SUBURB_NAME",
        "geo_point_2d.lon": "LONGITUDE",
        "geo_point_2d.lat": "LATITUDE"
    })

    #light clean data
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        df[col] = df[col].str.strip()

    print("####### We are in extract brisbane suburbs ##########")
    print(df.info)
    return df
# ==============================
#  sanitize occupation-employment-by-usual-resident-employment data
# ==============================
def extract_occupations(data: dict) -> pd.DataFrame:
    df = pd.json_normalize(data["results"])
    # enforce schema columns
    df = df[[
        "sa4_name",
        "sa3_name",
        "sa2_name",
        "code_1",
        "name_1",
        "code_2",
        "name_2",
        "sc2_2021",
        "sc2_2026",
        "sc2_2031",
        "sc2_2036"
    ]]

    #  clean column names 
    df.columns = (
        df.columns
        .str.upper()
        .str.strip()
        .str.replace(".", "_", regex=False)
    )
    # light clean data
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        df[col] = df[col].str.strip()

    print("####### extract occupation dataset ##########")
    print(df.info())

    return df
# ==============================
#  SAVE RAW PARQUET. 
# ==============================
def save_to_parquet(sheets: dict[str, pd.DataFrame]) -> None:
    os.makedirs(RAW_FOLDER, exist_ok=True)

    for name, df in sheets.items():
        try:
            file_name = name.lower().replace(" ", "_").replace("-", "_")
            file_path = os.path.join(RAW_FOLDER, f"{file_name}.parquet")

            df.to_parquet(file_path, index=False)
            
        except Exception as e:
            print(f"Failed to save {name}: {e}")
            raise
# ==============================
# validate if df to parquet succeeded 
# ==============================
def validate_parquet_files() -> None:
    file_count = 0
    for file in os.listdir(RAW_FOLDER):
        if file.endswith(".parquet"):
            file_count += 1

            file_path = os.path.join(RAW_FOLDER, file)
            df_check = pd.read_parquet(file_path)

            print(f"\nPreview Validate: {file}")
            print(df_check.head())
            print(df_check.dtypes)
            
    print(f"\nTotal parquet files found: {file_count}")

# ==============================
# group 3 data sources 
# ==============================
def run_rta_pipeline():
    file_path = download_file(RTA_URL, "rta_bond", "xlsx")
    sheets = extract_rta_excel(file_path)
    save_to_parquet(sheets)

def run_suburbs_pipeline():
    data = get_json_api(
        url=SUBURBS_API_URL,
        prefix="bne_suburbs",
        params=suburbs_params
    )
    df = extract_bne_suburbs(data)
    save_to_parquet({"bne_suburbs": df})

def run_occupation_pipeline():
    data = get_json_api(
        url=OCCUPATIONS_API_URL,
        prefix="bne_occupations",
        params=occupations_params
    )
    df = extract_occupations(data)
    save_to_parquet({"bne_occupations": df})

# ==============================
# RUN ALL PIPELINES ALTOGETHER
# ==============================
def run_pipelines():
    pipelines = [
        ("RTA Pipeline", run_rta_pipeline),
        ("Suburbs Pipeline", run_suburbs_pipeline),
        ("Occupation Pipeline", run_occupation_pipeline)
    ]

    print("🚀 Starting ingestion pipelines...")

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_name = {
            executor.submit(func): name for name, func in pipelines
        }

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                future.result()
                print(f"✅ {name} completed successfully")
            except Exception as e:
                print(f"❌ {name} failed: {e}")
                raise  # stop pipeline immediately

    print("🔍 Running validation...")
    validate_parquet_files()
    print("🎉 All pipelines completed successfully!")

# ==============================
# call main 
# ==============================
if __name__ == "__main__":
   
    run_pipelines()

   


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


