WITH stg_rents AS (
    SELECT *
    FROM  {{ ref("stg_rents") }}
)
SELECT  DISTINCT dwelling_type,
        bedrooms,
        dwelling_scope
FROM stg_rents