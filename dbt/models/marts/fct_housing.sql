/*
join all_bonds and new_bonds

*/

{{
    config(
        materialized = 'incremental'
        on_schema_change - 'fail'
    )
}}
WITH stg_rents AS (
    SELECT rents.suburb,
           rents.dwelling_type,
           rents.bedrooms,
           rents.dwelling_scope,
           rents.quarter,
           TRY_TO_NUMBER(LEFT(rents.quarter, 4)) AS year,
           rents.median_rent,
           all.total_bonds,
           new.new_bonds
    FROM {{ref("stg_rents")}} rents
    LEFT JOIN {{ref("stg_all_bonds")}} all
     ON rents.suburb = all_bonds.suburb
        AND rents.dwelling_type = all.dwelling_type
        AND COALESCE(rents.bedrooms, -1) = COALESCE(all.bedrooms, -1)
        AND rents.dwelling_level = all.dwelling_level
        AND rents.quarter = all.quarter
    LEFT JOIN {{ref("stg_new_bonds")}} new
      ON rents.suburb = new.suburb
        AND rents.dwelling_type = new.dwelling_type
        AND COALESCE(rents.bedrooms, -1) = COALESCE(new_bonds.bedrooms, -1)
        AND rents.dwelling_level = new.dwelling_level
        AND rents.quarter = new.quarter
)





/*

WITH src_reviews AS (
    SELECT * FROM {{ ref('src_reviews') }}
)

SELECT * FROM src_reviews
WHERE review_text is not null
{% if is_incremental() %}
    AND review_date > (select max(review_date) from {{ this }})
{% endif %}
*/