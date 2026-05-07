WITH raw_suburbs AS (
    SELECT *
    FROM {{source('raw_brisbane','suburbs')}}
)

SELECT INITCAP(TRIM(suburb_name)) AS suburb,
       longitude,
       latitude
FROM raw_suburbs