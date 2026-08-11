-- 利润率计算宏
{% macro calc_margin(revenue, cost) %}
    ROUND(({{ revenue }} - {{ cost }}) / NULLIF({{ revenue }}, 0) * 100, 1)
{% endmacro %}
