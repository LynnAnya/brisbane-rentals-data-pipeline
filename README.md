# Brisbane Rentals Data Analytics Pipeline
Cloud native data pipeline and data modeling using Snowflake &amp; dbt for Brisbane, Australia rental market trend.

## Overview
An end-to-end data anlytics project on Brisbane current rental market and resident's careers in each area. It aims tp help renters understand rental situation (Q1, 2026) in the area they would like to rent, where rents are rising, what kind of careers their neighbours work, demand of renters, growth of the market, and also comparing rents based on property types and bedrooms in each area.

## Business Requirements 
The purpose of this data pipeline is to answer following questions:
 - How does median rent in a selected suburb compare to the market average?
 - How have rents changed over time ?
 - Which property types dominate the rental market in a selected suburb?
 - How is the rental demand in each area? 
 - What do residents mostly work in selected areas?

## Data Architecture 
![Architecture Diagram](images/architect_diagram.png)

Data Flow:
1. **Ingestion** — Python scripts extract raw Excel files and APIs from open data sources and then convert to Parquet
2. **Storage** — Raw data is loaded into Snowflake raw schema
3. **Transformation** — dbt models transform data through 2 layers:
   staging → marts (dims and facts)
4. **Visualisation** — Interactive dashboard for rental market 
   and workforce insights with Power BI

## Data Sources 
 - Bonds, median weekly rent by suburbs
https://www.rta.qld.gov.au/sites/default/files/2023-04/rta-bond-statistics.xlsx

- Brisbane suburb boundaries and occupation employment by resident employment
https://data.brisbane.qld.gov.au/pages/home/


## Tech Stack
- Python: Ingestion, raw data, parquet files
- Snowflake: Data Warehouse
- dbt: Transformation
- Power BI: Dashboard

## Data Model




## DashBoard

## Issues & Limitations
- The dashboard presents the current rental market for and individual suburb or selected suburbs, without comparision between each area.
- Brisbane suburbs cannot fully connect to SA2 statistical area as I first assumed. So, I separated dim_suburbs and dim_geography
- It does not have all 195 suburbs in Brisbane because data source for rental data does not include all suburbs (some suburbs do not have resident property aka. Brisbane Airport, Port of Brisbane or very few data)
## Future Improvememts 
- Comparing between selected suburbs such as Chermside VS New Farm to make better decisions 
- Big picture in SA4 boundaries such as overall rental in Brisbane - North area
- Rental yield for better investment decision
- Ranking top 10 most afforable/expensive suburb
## How to run 