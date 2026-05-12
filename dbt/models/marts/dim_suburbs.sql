WITH stg_suburbs AS (
    SELECT *
    FROM {{ ref("stg_suburbs") }}
),
areas AS (
    SELECT DISTINCT 
           sa4_area,
           sa2_area,
           TRIM(value::string) AS suburb_part
    FROM {{ ref("stg_occupations") }},
    LATERAL FLATTEN(
        input => SPLIT(sa2_area, '-')
    )
)
SELECT a.sa4_area,
       a.sa2_area,
       sub.suburb,
       sub.longitude,
       sub.latitude
FROM {{ ref("stg_suburbs")}} sub
LEFT JOIN areas a
 ON LOWER(sub.suburb) = LOWER(TRIM(a.suburb_part))