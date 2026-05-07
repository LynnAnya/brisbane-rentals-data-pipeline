
-- clean suburb
WITH cleaned_suburbs AS (
    SELECT
        TRIM(REGEXP_REPLACE(suburb, '\\s*\\(\\d+\\)', '')) AS suburb,
        rent.* EXCLUDE (suburb)
    FROM {{ source('raw_brisbane','rents') }} rent
    WHERE
        REGEXP_SUBSTR(suburb, '\\d+') IS NULL
        OR TRY_TO_NUMBER(REGEXP_SUBSTR(suburb, '\\d+')) BETWEEN 4000 AND 4179
),
-- get only brisbane suburbs
raw_rents AS (
    SELECT
        rent.*
    FROM cleaned_suburbs rent
    INNER JOIN {{ ref('stg_suburbs') }} sub
        ON INITCAP(TRIM(rent.suburb)) = INITCAP(TRIM(sub.suburb))
),
-- unpivot
unpivoted AS (
    SELECT
        suburb,
        dwelling,
        qrt_period,
        median_rent
    FROM raw_rents
    UNPIVOT INCLUDE NULLS (
        median_rent FOR qrt_period IN (
            mar_2021, jun_2021, sep_2021, dec_2021,
            mar_2022, jun_2022, sep_2022, dec_2022,
            mar_2023, jun_2023, sep_2023, dec_2023,
            mar_2024, jun_2024, sep_2024, dec_2024,
            mar_2025, jun_2025, sep_2025, dec_2025,
            mar_2026
        )
    )
),
-- final transform
final AS (
    SELECT
        suburb,
        CASE 
            WHEN LOWER(TRIM(dwelling)) IN ('all dwellings', 'other') THEN INITCAP(TRIM(dwelling))
            ELSE SPLIT_PART(TRIM(dwelling), ' ', 1)
        END AS dwelling_type,

        CASE 
            WHEN LOWER(TRIM(dwelling)) IN ('all dwellings', 'other') THEN NULL
            ELSE TRY_TO_NUMBER(SPLIT_PART(TRIM(dwelling), ' ', 2))
        END AS bedrooms,

        CASE 
            WHEN LOWER(TRIM(dwelling)) = 'all dwellings' THEN 'ALL'
            ELSE 'DETAILED'
        END AS dwelling_scope,

        CONCAT(
            RIGHT(qrt_period, 4), 
            '-Q',
            CASE 
                WHEN LEFT(qrt_period, 3) = 'MAR' THEN '1'
                WHEN LEFT(qrt_period, 3) = 'JUN' THEN '2'
                WHEN LEFT(qrt_period, 3) = 'SEP' THEN '3'
                WHEN LEFT(qrt_period, 3) = 'DEC' THEN '4'
            END
        ) AS quarter,
        median_rent
    FROM unpivoted
)
SELECT *
FROM final