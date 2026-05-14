WITH stg_suburbs AS (
    SELECT *
    FROM {{ ref("stg_suburbs") }}
),
stg_rents AS (
    SELECT DISTINCT suburb
    FROM {{ ref("stg_rents") }}
), 
final AS (
    SELECT rent.suburb,
        sub.longitude,
        sub.latitude
    FROM stg_rents  rent
    LEFT JOIN stg_suburbs sub
    ON rent.suburb = sub.suburb
)
SELECT * 
FROM final
