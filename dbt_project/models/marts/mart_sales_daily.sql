-- mart_sales_daily: 每日销售KPI看板
-- 业务方直接查询此表

SELECT
    date_id,
    full_date,
    year,
    quarter,
    month,
    month_name,
    day_of_week,
    day_name,
    is_weekend,
    city_id,
    city_name,
    category,
    order_count,
    unique_customers,
    units_sold,
    total_revenue,
    avg_order_value,
    total_discounts,
    avg_discount_pct,
    -- 环比（昨天）
    LAG(total_revenue) OVER (
        PARTITION BY city_id, category
        ORDER BY full_date
    ) AS prev_day_revenue,
    -- 7日移动平均
    AVG(total_revenue) OVER (
        PARTITION BY city_id, category
        ORDER BY full_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS ma7_revenue,
    -- 累计月度营收
    SUM(total_revenue) OVER (
        PARTITION BY city_id, category, year, month
        ORDER BY full_date
    ) AS mtd_revenue
FROM {{ ref('int_daily_sales') }}
