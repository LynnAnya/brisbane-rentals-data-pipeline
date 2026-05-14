WITH stg AS (
    SELECT *
    FROM {{ ref('stg_occupations') }}
)
SELECT DISTINCT
    sa4_area,
    sa2_area
FROM stg