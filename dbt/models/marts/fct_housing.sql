/*
join all_bonds and new_bonds to rents (base)

*/
{{
    config(
        materialized = 'incremental',
        on_schema_change = 'fail'
    )
}}
WITH stg_rents AS (
    SELECT *
    FROM {{ ref("stg_rents") }}
),
fct_housing AS (
    SELECT rents.suburb,
           rents.dwelling_type,
           rents.bedrooms,
           rents.dwelling_scope,
           rents.quarter,
           rents.quarter_date,
           TRY_TO_NUMBER(LEFT(rents.quarter, 4)) AS year,
           rents.median_rent,
           ab.total_bonds,
           nb.new_bonds
    FROM stg_rents rents
    LEFT JOIN {{ref("stg_all_bonds")}} ab
    ON rents.suburb = ab.suburb
        AND rents.dwelling_type = ab.dwelling_type
        AND COALESCE(rents.bedrooms, -1) = COALESCE(ab.bedrooms, -1)
        AND rents.quarter = ab.quarter
    LEFT JOIN {{ref("stg_new_bonds")}} nb
    ON rents.suburb = nb.suburb
        AND rents.dwelling_type = nb.dwelling_type
        AND COALESCE(rents.bedrooms, -1) = COALESCE(nb.bedrooms, -1)
        AND rents.quarter = nb.quarter
    LEFT JOIN {{ ref("stg_suburbs") }} sub
    ON rents.suburb = sub.suburb
)
SELECT *
FROM fct_housing
WHERE quarter is not null
{% if is_incremental() %}
    AND quarter > (select max(quarter) from {{ this }})
{% endif %}



