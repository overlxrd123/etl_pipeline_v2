-- int_weather_sales: 天气×销售关联表

SELECT
    s.date_id,
    s.full_date,
    s.city_id,
    s.city_name,
    s.category,
    s.order_count,
    s.total_revenue,
    s.units_sold,
    s.avg_order_value,

    w.temp_max_c,
    w.temp_min_c,
    w.temp_avg_c,
    w.precipitation_mm,
    w.wind_speed_kmh,
    w.weather_code,
    w.weather_desc,
    w.weather_category,
    w.is_extreme

FROM {{ ref('int_daily_sales') }} s
LEFT JOIN {{ ref('stg_weather') }} w
    ON s.city_id = w.city_id
    AND s.date_id = w.date_id
