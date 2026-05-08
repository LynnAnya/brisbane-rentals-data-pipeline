--get the source table 
WITH occupations_raw AS (
    SELECT *
    FROM {{ source('raw_brisbane','occupations')}}
),
 -- cleaned - select columns, rename, change case, trim 
/**
 - select all columns except sa3_name 
 - rename columns : sa4_name->region, sa2_name->suburb_area, code_1->occupation_group_code, 
   name_1->occupation_group, code_2-> occupation_detail_code, name_2->occupation_detail,
   sc2_2021, sc2_2026, sc2_2031, sc2_2036 (maybe same name but select and will pivot in next CTE) 
 - clean: trim string, capital
*/
cleaned AS (
    SELECT
        INITCAP(TRIM(sa4_name)) AS sa4_area,
        INITCAP(TRIM(sa2_name)) AS sa2_area,

        TRIM(code_1) AS occupation_group_code,
        INITCAP(TRIM(name_1)) AS occupation_group,

        TRIM(code_2) AS occupation_detail_code,
        INITCAP(TRIM(name_2)) AS occupation_detail,
        sc2_2021,
        sc2_2026,
        sc2_2031,
        sc2_2036
    FROM occupations_raw
),
unpivoted AS (
    SELECT
        sa4_area,
        sa2_area,

        occupation_group_code,
        occupation_group,

        occupation_detail_code,
        occupation_detail,

        RIGHT(projection_year, 4) AS year,
        projected_workers
    FROM cleaned
    UNPIVOT INCLUDE NULLS (
        projected_workers FOR projection_year IN (
            sc2_2021,
            sc2_2026,
            sc2_2031,
            sc2_2036
        )
    )
)
SELECT * 
FROM unpivoted

