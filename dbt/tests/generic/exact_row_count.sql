{% test exact_row_count(model, row_count) %}
SELECT 1
FROM {{ model }}
HAVING COUNT(*) != {{ row_count }}
{% endtest %}