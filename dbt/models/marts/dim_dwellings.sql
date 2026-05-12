WITH fct_housing AS (
    SELECT *
    FROM  {{ ref("fct_housing") }}
)
SELECT  DISTINCT dwelling_type,
        bedrooms,
        dwelling_scope
FROM fct_housing