-- mart_weather_impact: 天气对销售的影响分析

WITH weather_metrics AS (
    SELECT
        weather_category,
        is_extreme,
        COUNT(*)                    AS days_count,
        SUM(order_count)            AS total_orders,
        SUM(total_revenue)          AS total_revenue,
        SUM(units_sold)             AS total_units,
        AVG(order_count)            AS avg_daily_orders,
        AVG(total_revenue)          AS avg_daily_revenue,
        AVG(avg_order_value)        AS avg_order_value,
        AVG(temp_avg_c)             AS avg_temperature,
        AVG(precipitation_mm)       AS avg_precipitation
    FROM {{ ref('int_weather_sales') }}
    WHERE weather_category IS NOT NULL
    GROUP BY weather_category, is_extreme
)

SELECT
    *,
    -- 排名（按平均日营收）
    RANK() OVER (ORDER BY avg_daily_revenue DESC) AS revenue_rank,
    -- 与整体均值的偏差
    ROUND((avg_daily_revenue - (SELECT AVG(avg_daily_revenue) FROM weather_metrics))
        / (SELECT AVG(avg_daily_revenue) FROM weather_metrics) * 100, 1) AS revenue_vs_avg_pct
FROM weather_metrics
ORDER BY avg_daily_revenue DESC
