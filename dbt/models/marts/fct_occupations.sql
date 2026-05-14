WITH stg_occupations AS (
     SELECT * 
     FROM {{ ref("stg_occupations") }}
)
SELECT   sa2_area,
        occupation_detail_code,
        year,
        projected_workers
FROM stg_occupations
