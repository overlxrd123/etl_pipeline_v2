-- stg_weather: 天气维度清洗 + 分类
SELECT
    w.weather_id,
    w.city_id,
    ci.city_name,
    w.date_id,
    d.full_date,
    w.temp_max_c,
    w.temp_min_c,
    w.temp_avg_c,
    w.precipitation_mm,
    w.wind_speed_kmh,
    w.weather_code,
    w.weather_desc,
    -- 天气分类
    CASE
        WHEN w.weather_code IN (0, 1) THEN 'Clear'
        WHEN w.weather_code = 2 THEN 'Partly Cloudy'
        WHEN w.weather_code = 3 THEN 'Overcast'
        WHEN w.weather_code BETWEEN 45 AND 48 THEN 'Fog'
        WHEN w.weather_code BETWEEN 51 AND 55 THEN 'Drizzle'
        WHEN w.weather_code BETWEEN 61 AND 65 THEN 'Rain'
        WHEN w.weather_code BETWEEN 71 AND 75 THEN 'Snow'
        WHEN w.weather_code BETWEEN 80 AND 82 THEN 'Showers'
        WHEN w.weather_code BETWEEN 95 AND 99 THEN 'Storm'
        ELSE 'Other'
    END AS weather_category,
    -- 是否极端天气
    CASE WHEN w.weather_code >= 65 OR w.weather_code >= 95 THEN 1 ELSE 0 END AS is_extreme
FROM dim_weather w
JOIN dim_city ci ON w.city_id = ci.city_id
JOIN dim_date d ON w.date_id = d.date_id
