WITH stg_occupations AS (
    SELECT *
    FROM {{ ref("stg_occupations") }}
)
SELECT DISTINCT
        occupation_group_code,
        occupation_group,
        occupation_detail_code,
        occupation_detail
FROM  stg_occupations
