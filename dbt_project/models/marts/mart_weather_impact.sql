-- mart_weather_impact: 天气对销售的影响分析
-- 先把粒度统一到「城市×日期」，再按天气类别比较。
--
-- 关键口径：不同日期/季节的订单基数差异很大（周末、节假日、季节波动），
-- 直接比较各类天气的平均营收会把「天气效应」和「季节效应」混在一起。
-- 因此额外计算 orders_index：
--   1. 每天计算各城市订单占当天总订单的份额 day_share
--   2. 用该城市全年的平均份额做基准 base_share
--   3. orders_index = day_share / base_share
-- 这样同一天的季节/周末波动被抵消，1.0 表示该城市处于平常水平。

WITH city_day AS (
    SELECT
        date_id,
        city_id,
        SUM(order_count)   AS orders,
        SUM(total_revenue) AS revenue,
        SUM(units_sold)    AS units,
        SUM(total_revenue) / NULLIF(SUM(order_count), 0) AS avg_order_value,
        MAX(temp_avg_c)         AS temp_avg_c,
        MAX(temp_max_c)         AS temp_max_c,
        MAX(temp_min_c)         AS temp_min_c,
        MAX(precipitation_mm)   AS precipitation_mm,
        MAX(weather_code)       AS weather_code,
        MAX(weather_category)   AS weather_category,
        MAX(is_extreme)         AS is_extreme
    FROM {{ ref('int_weather_sales') }}
    WHERE weather_category IS NOT NULL
    GROUP BY date_id, city_id
),

city_share AS (
    SELECT
        *,
        orders * 1.0 / NULLIF(SUM(orders) OVER (PARTITION BY date_id), 0) AS day_share
    FROM city_day
),

city_baseline AS (
    SELECT
        city_id,
        AVG(day_share) AS base_share
    FROM city_share
    GROUP BY city_id
),

normalized AS (
    SELECT
        s.*,
        s.day_share / NULLIF(b.base_share, 0) AS orders_index
    FROM city_share s
    JOIN city_baseline b ON s.city_id = b.city_id
)

SELECT
    weather_category,
    is_extreme,
    COUNT(DISTINCT date_id)     AS days_count,      -- 覆盖的日历天数
    COUNT(*)                    AS city_days,       -- 城市×天 观测数
    SUM(orders)                 AS total_orders,
    SUM(revenue)                AS total_revenue,
    SUM(units)                  AS total_units,
    AVG(orders)                 AS avg_daily_orders,
    AVG(revenue)                AS avg_daily_revenue,
    AVG(avg_order_value)        AS avg_order_value,
    AVG(temp_avg_c)             AS avg_temperature,
    AVG(precipitation_mm)       AS avg_precipitation,
    AVG(orders_index)           AS orders_index,    -- 1.0 = 该城市平常水平
    ROUND(AVG(orders_index) * 100, 1) AS orders_index_pct,
    RANK() OVER (ORDER BY AVG(orders_index) DESC) AS demand_rank,
    ROUND(
        (AVG(revenue) - AVG(AVG(revenue)) OVER ())
        / AVG(AVG(revenue)) OVER () * 100,
        1
    ) AS revenue_vs_avg_pct
FROM normalized
GROUP BY weather_category, is_extreme
ORDER BY orders_index DESC
